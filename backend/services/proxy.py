"""
代理服务模块

负责处理 HTTP 请求和响应，包括请求头过滤、请求体处理和 System Prompt 替换
"""

import json
from typing import Iterable
from urllib.parse import urlparse

from ..config import (
    HOP_BY_HOP_HEADERS,
    PRESERVE_HOST,
    SYSTEM_PROMPT_REPLACEMENT,
    SYSTEM_PROMPT_BLOCK_INSERT_IF_NOT_EXIST,
    CLAUDE_CODE_KEYWORD,
    CUSTOM_HEADERS,
    TARGET_BASE_URL
)


def filter_request_headers(headers: Iterable[tuple]) -> dict:
    """
    过滤请求头，移除 hop-by-hop 头部和 Content-Length

    Args:
        headers: 原始请求头（可迭代的元组列表）

    Returns:
        dict: 过滤后的请求头字典（保留原始大小写）
    """
    out = {}
    seen_keys = set()  # 用于追踪已处理的小写 key，避免重复
    for k, v in headers:
        lk = k.lower()
        if lk in HOP_BY_HOP_HEADERS:
            continue
        if lk == "host" and not PRESERVE_HOST:
            continue
        # 移除 Content-Length，让 httpx 根据实际内容自动计算
        # 因为我们可能会修改请求体，导致长度改变
        if lk == "content-length":
            continue
        # 避免重复 key（后面的会覆盖前面的）
        if lk in seen_keys:
            continue
        seen_keys.add(lk)
        # 保留原始大小写
        out[k] = v
    return out


def filter_response_headers(headers: Iterable[tuple]) -> dict:
    """
    过滤响应头，移除 hop-by-hop 头部和 Content-Length

    Args:
        headers: 原始响应头（可迭代的元组列表）

    Returns:
        dict: 过滤后的响应头字典
    """
    out = {}
    for k, v in headers:
        lk = k.lower()
        if lk in HOP_BY_HOP_HEADERS:
            continue
        # 移除 Content-Length，避免流式响应时长度不匹配
        # StreamingResponse 会自动处理传输编码
        if lk == "content-length":
            continue
        # httpx 会自动解压 gzip/deflate，去掉 Content-Encoding 避免客户端重复解压导致 ZlibError
        if lk == "content-encoding":
            continue
        out[k] = v
    return out


# AnyRouter 专用提示词（当 AnyRouter key 请求 AnyRouter 目标时强制使用）
ANYROUTER_SYSTEM_PROMPT = "You are Claude Code, Anthropic's official CLI for Claude."


def _is_anyrouter_to_anyrouter(api_key: str, target_url: str) -> bool:
    """
    判断是否为 AnyRouter key 请求 AnyRouter 目标的场景
    
    Args:
        api_key: API Key
        target_url: 目标服务器 URL
    
    Returns:
        bool: 如果是 AnyRouter key 请求 AnyRouter 目标则返回 True
    """
    if not api_key or not target_url:
        return False
    
    # 检查目标是否为 AnyRouter（包含 anyrouter.top）
    is_anyrouter_target = "anyrouter.top" in target_url.lower()
    
    # AnyRouter key 通常以 sk- 开头，且目标是 anyrouter.top
    # 这里主要判断目标是否为 anyrouter，因为只有 anyrouter 的 key 才能访问 anyrouter
    return is_anyrouter_target


def _ensure_anyrouter_beta_header(headers: dict) -> None:
    """
    确保 AnyRouter 请求的 anthropic-beta 头部包含必需的 claude-code-20250219 标识
    
    AnyRouter 需要此标识才能正确识别和处理 Claude Code 的请求。
    此函数仅在目标为 anyrouter.top 时被调用，不影响其他代理目标。
    
    Args:
        headers: 请求头字典，将被原地修改
    """
    CLAUDE_CODE_BETA = "claude-code-20250219"
    
    # 查找现有的 anthropic-beta 头部（不区分大小写）
    existing_key = None
    existing_value = None
    for key in headers:
        if key.lower() == "anthropic-beta":
            existing_key = key
            existing_value = headers[key]
            break
    
    if existing_key:
        # 检查是否已包含 claude-code beta 标识
        if CLAUDE_CODE_BETA not in existing_value:
            # 在现有值前面添加 claude-code beta 标识
            new_value = f"{CLAUDE_CODE_BETA},{existing_value}"
            headers[existing_key] = new_value
            print(f"[AnyRouter Beta Header] Added {CLAUDE_CODE_BETA} to existing anthropic-beta: {new_value}")
        else:
            print(f"[AnyRouter Beta Header] anthropic-beta already contains {CLAUDE_CODE_BETA}, no change needed")
    else:
        # 没有 anthropic-beta 头部，添加一个包含必需标识的
        headers["anthropic-beta"] = f"{CLAUDE_CODE_BETA},interleaved-thinking-2025-05-14"
        print(f"[AnyRouter Beta Header] Added new anthropic-beta header with {CLAUDE_CODE_BETA}")


def _force_anyrouter_system_prompt(body: bytes) -> bytes:
    """
    强制将 system prompt 设置为 AnyRouter 唯一提示词
    
    注意：AnyRouter 要求 system 必须是列表格式，不能是字符串格式！
    
    Args:
        body: 原始请求体（bytes）
    
    Returns:
        处理后的请求体（bytes），如果无法处理则返回原始 body
    """
    try:
        data = json.loads(body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"[AnyRouter System Prompt] Failed to parse JSON: {e}, keeping original body")
        return body
    
    # 强制设置 system 为唯一提示词（必须使用列表格式！）
    # AnyRouter 要求 system 是列表格式，字符串格式会导致 500 错误
    data["system"] = [{"type": "text", "text": ANYROUTER_SYSTEM_PROMPT}]
    print(f"[AnyRouter System Prompt] Forced system prompt to list format: {ANYROUTER_SYSTEM_PROMPT}")
    
    # 转换回 JSON bytes
    try:
        modified_body = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        print(f"[AnyRouter System Prompt] Successfully modified body (original size: {len(body)} bytes, new size: {len(modified_body)} bytes)")
        return modified_body
    except Exception as e:
        print(f"[AnyRouter System Prompt] Failed to serialize modified JSON: {e}, keeping original body")
        return body


def process_request_body(body: bytes, api_key: str = None, target_url: str = None) -> bytes:
    """
    处理请求体,替换 system 数组中第一个元素的 text 内容

    注意：此函数仅在 proxy() 中处理 /v1/messages 路由时被调用
    其他路由（如 /v1/completions, /v1/models 等）跳过此处理

    Args:
        body: 原始请求体（bytes）
        api_key: API Key（用于判断是否为 AnyRouter 请求）
        target_url: 目标服务器 URL（用于判断是否请求 AnyRouter）

    Returns:
        处理后的请求体（bytes），如果无法处理则返回原始 body
    """
    # 判断是否为 AnyRouter key 请求 AnyRouter 目标
    is_anyrouter = _is_anyrouter_to_anyrouter(api_key, target_url)
    
    if is_anyrouter:
        # AnyRouter -> AnyRouter：强制使用唯一提示词
        print(f"[System Replacement] AnyRouter key to AnyRouter target detected, forcing unique system prompt")
        return _force_anyrouter_system_prompt(body)
    
    # 如果未配置替换文本，直接返回原始 body
    if SYSTEM_PROMPT_REPLACEMENT is None:
        print("[System Replacement] Not configured, keeping original body")
        # try:
        #     print(f"[System Replacement None] Original system[0].text: {json.loads(body.decode('utf-8'))['system'][0]['text']}")
        # except (json.JSONDecodeError, UnicodeDecodeError, KeyError, IndexError, TypeError) as e:
        #     print(f"[System Replacement None] Failed to parse or access system prompt: {e}")
        return body

    # 尝试解析 JSON
    try:
        data = json.loads(body.decode('utf-8'))
        print("[System Replacement] Successfully parsed JSON body")
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"[System Replacement] Failed to parse JSON: {e}, keeping original body")
        return body

    # 检查 system 字段是否存在且为列表
    if "system" not in data:
        # 如果没有 system 字段，且配置了 SYSTEM_PROMPT_REPLACEMENT，则创建一个
        if SYSTEM_PROMPT_REPLACEMENT:
            data["system"] = SYSTEM_PROMPT_REPLACEMENT
            print(f"[System Replacement] No 'system' field found, adding system prompt: {SYSTEM_PROMPT_REPLACEMENT[:100]}..." if len(SYSTEM_PROMPT_REPLACEMENT) > 100 else f"[System Replacement] No 'system' field found, adding system prompt: {SYSTEM_PROMPT_REPLACEMENT}")
            # 转换回 JSON bytes
            try:
                modified_body = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
                print(f"[System Replacement] Successfully modified body (original size: {len(body)} bytes, new size: {len(modified_body)} bytes)")
                return modified_body
            except Exception as e:
                print(f"[System Replacement] Failed to serialize modified JSON: {e}, keeping original body")
                return body
        else:
            print("[System Replacement] No 'system' field found and no replacement configured, keeping original body")
            return body

    if not isinstance(data["system"], list):
        print(f"[System Replacement] 'system' field is not a list (type: {type(data['system'])}), keeping original body")
        return body

    if len(data["system"]) == 0:
        print("[System Replacement] 'system' array is empty, keeping original body")
        return body

    # 获取第一个元素
    first_element = data["system"][0]

    # 检查第一个元素是否有 'text' 字段
    if not isinstance(first_element, dict) or "text" not in first_element:
        print(f"[System Replacement] First element doesn't have 'text' field, keeping original body")
        return body

    # 记录原始内容
    original_text = first_element["text"]
    print(f"[System Replacement] Original system[0].text: {original_text[:100]}..." if len(original_text) > 100 else f"[System Replacement] Original system[0].text: {original_text}")

    # 判断是否启用插入模式
    if SYSTEM_PROMPT_BLOCK_INSERT_IF_NOT_EXIST:
        # 插入模式：检查是否包含关键字（忽略大小写）
        if CLAUDE_CODE_KEYWORD.lower() in original_text.lower():
            # 包含关键字：执行替换
            first_element["text"] = SYSTEM_PROMPT_REPLACEMENT
            print(f"[System Replacement] Found '{CLAUDE_CODE_KEYWORD}', replacing with: {SYSTEM_PROMPT_REPLACEMENT[:100]}..." if len(SYSTEM_PROMPT_REPLACEMENT) > 100 else f"[System Replacement] Found '{CLAUDE_CODE_KEYWORD}', replacing with: {SYSTEM_PROMPT_REPLACEMENT}")
        else:
            # 不包含关键字：执行插入
            new_element = {
                "type": "text",
                "text": SYSTEM_PROMPT_REPLACEMENT,
                "cache_control": {
                    "type": "ephemeral"
                }
            }
            data["system"].insert(0, new_element)
            print(f"[System Replacement] '{CLAUDE_CODE_KEYWORD}' not found, inserting at position 0: {SYSTEM_PROMPT_REPLACEMENT[:100]}..." if len(SYSTEM_PROMPT_REPLACEMENT) > 100 else f"[System Replacement] '{CLAUDE_CODE_KEYWORD}' not found, inserting at position 0: {SYSTEM_PROMPT_REPLACEMENT}")
            print(f"[System Replacement] Array length changed: {len(data['system'])-1} -> {len(data['system'])}")
    else:
        # 原始模式：直接替换
        first_element["text"] = SYSTEM_PROMPT_REPLACEMENT
        print(f"[System Replacement] Replaced with: {SYSTEM_PROMPT_REPLACEMENT[:100]}..." if len(SYSTEM_PROMPT_REPLACEMENT) > 100 else f"[System Replacement] Replaced with: {SYSTEM_PROMPT_REPLACEMENT}")

    print(f"[System Replacement] original_text == SYSTEM_PROMPT_REPLACEMENT:{SYSTEM_PROMPT_REPLACEMENT == original_text}")

    # 转换回 JSON bytes
    try:
        # 这里必须加 separators 压缩空格，我也不知道为什么有空格不行。。。
        modified_body = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        print(f"[System Replacement] Successfully modified body (original size: {len(body)} bytes, new size: {len(modified_body)} bytes)")
        return modified_body
    except Exception as e:
        print(f"[System Replacement] Failed to serialize modified JSON: {e}, keeping original body")
        return body


def prepare_forward_headers(incoming_headers: Iterable[tuple], client_host: str = None, target_url: str = None) -> dict:
    """
    准备转发的请求头

    Args:
        incoming_headers: 原始请求头
        client_host: 客户端 IP 地址
        target_url: 目标服务器 URL（用于设置 Host 头）

    Returns:
        dict: 准备好的转发请求头
    """
    # 复制并过滤请求头（所有 key 已小写化）
    forward_headers = filter_request_headers(incoming_headers)

    # 设置 host（使用传入的 target_url 或默认的 TARGET_BASE_URL）
    if not PRESERVE_HOST:
        actual_target = target_url or TARGET_BASE_URL
        parsed = urlparse(actual_target)
        forward_headers["host"] = parsed.netloc

    # 注入自定义 Header（保留原始大小写）
    for k, v in CUSTOM_HEADERS.items():
        # 先检查是否有相同的 key（不区分大小写），如果有则删除旧的
        for existing_key in list(forward_headers.keys()):
            if existing_key.lower() == k.lower():
                del forward_headers[existing_key]
                break
        forward_headers[k] = v

    # AnyRouter 专用处理：确保 anthropic-beta 头部包含 claude-code-20250219
    # 这是 Claude Code CLI 的必需标识，AnyRouter 需要此标识才能正确处理请求
    if target_url and "anyrouter.top" in target_url.lower():
        _ensure_anyrouter_beta_header(forward_headers)

    # 将 x-api-key 转换为 Authorization: Bearer 格式（模拟真实 Claude Code CLI）
    # 检查小写和原始大小写两种情况
    api_key_value = None
    for key in list(forward_headers.keys()):
        if key.lower() == "x-api-key":
            api_key_value = forward_headers.pop(key)
            break
    if api_key_value:
        forward_headers["Authorization"] = f"Bearer {api_key_value}"

    # 不添加 x-forwarded-for，保持与真实 Claude Code CLI 一致

    return forward_headers
