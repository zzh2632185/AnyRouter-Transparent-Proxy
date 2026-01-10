"""
AnyRouter 透明代理 - 主应用模块

基于 FastAPI 的轻量级透明 HTTP 代理服务
"""

from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse, RedirectResponse
from contextlib import asynccontextmanager
from starlette.background import BackgroundTask
import httpx
import json
import os
import socket
import time
import asyncio
import uuid

# 导入配置
from .config import (
    TARGET_BASE_URL,
    DEBUG_MODE,
    PORT,
    ENABLE_DASHBOARD,
    DASHBOARD_API_KEY,
    CUSTOM_HEADERS,
    KEY_TO_TARGET_INDEX
)

# 导入统计服务
from .services.stats import (
    record_request_start,
    record_request_success,
    record_request_error,
    periodic_stats_update,
    cleanup_stale_requests
)

# 导入代理服务
from .services.proxy import (
    process_request_body,
    filter_response_headers,
    prepare_forward_headers
)

# 导入编码工具
from .utils.encoding import ensure_unicode


def extract_api_key_from_auth_header(request: Request) -> str:
    """
    从请求的 Authorization header 或 x-api-key header 中提取 API Key

    支持格式:
    - Authorization: Bearer sk-xxx
    - Authorization: sk-xxx (直接传递)
    - x-api-key: sk-xxx

    Returns:
        str: 提取的 API Key，如果未找到则返回空字符串
    """
    # 首先尝试从 x-api-key header 获取（Anthropic API 常用格式）
    api_key = request.headers.get("x-api-key", "")
    if api_key:
        return api_key.strip()

    # 然后尝试从 Authorization header 获取
    auth_header = request.headers.get("authorization", "")
    if not auth_header:
        return ""

    # 去除 Bearer 前缀（如果存在）
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()

    return auth_header.strip()


def get_target_url_for_key(api_key: str) -> str:
    """
    根据 API Key 获取对应的目标服务器地址

    Args:
        api_key: API Key

    Returns:
        str: 目标服务器地址，如果未找到映射则返回默认的 TARGET_BASE_URL
    """
    from . import config as config_module

    if not api_key:
        print(f"[Key Routing] No API key provided, using default: {config_module.TARGET_BASE_URL}")
        return config_module.TARGET_BASE_URL

    # 调试：打印索引内容和当前 key
    print(f"[Key Routing] Incoming API key: {api_key}")
    print(f"[Key Routing] KEY_TO_TARGET_INDEX has {len(config_module.KEY_TO_TARGET_INDEX)} keys")
    print(f"[Key Routing] INDEX keys: {list(config_module.KEY_TO_TARGET_INDEX.keys())}")

    # 首先从动态更新的索引中查找
    target_url = config_module.KEY_TO_TARGET_INDEX.get(api_key)

    if target_url:
        print(f"[Key Routing] Found mapping for key: {api_key[:8]}... -> {target_url}")
        return target_url

    print(f"[Key Routing] No mapping for key: {api_key[:8]}..., using default: {config_module.TARGET_BASE_URL}")

    return config_module.TARGET_BASE_URL

# 导入 Admin 路由
from .routers.admin import router as admin_router

# Shared HTTP client for connection pooling and proper lifecycle management
http_client: httpx.AsyncClient = None  # type: ignore


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    global http_client

    # 生成启动标识
    app.state.boot_id = str(uuid.uuid4())
    app.state.started_at = int(time.time())

    # 启动定时统计更新任务
    stats_task = asyncio.create_task(periodic_stats_update())

    # 启动超时请求清理任务
    cleanup_task = asyncio.create_task(cleanup_stale_requests())

    # 输出应用配置信息（只在 worker 进程启动时输出一次）
    print("=" * 60)
    print("Application Configuration:")
    print(f"  Base URL: {TARGET_BASE_URL}")
    print(f"  Server Port: {PORT}")
    print(f"  Custom Headers: {len(CUSTOM_HEADERS)} headers loaded")
    if CUSTOM_HEADERS:
        print(f"  Custom Headers Keys: {list(CUSTOM_HEADERS.keys())}")
    print(f"  Debug Mode: {DEBUG_MODE}")
    print(f"  Hot Reload: {DEBUG_MODE}")
    print(f"  Dashboard Enabled: {ENABLE_DASHBOARD}")
    if ENABLE_DASHBOARD:
        print(f"  Dashboard API Key Configured: {'Yes' if DASHBOARD_API_KEY else 'No'}")
        if DASHBOARD_API_KEY:
            print(f"  Dashboard Access: http://localhost:{PORT}/admin")
    print("=" * 60)

    # 读取代理配置
    http_proxy = os.getenv("HTTP_PROXY")
    https_proxy = os.getenv("HTTPS_PROXY")

    # 构建 mounts 配置（httpx 0.28.0+ 的新语法）
    mounts = {}

    if http_proxy:
        # 确保代理 URL 包含协议
        if "://" not in http_proxy:
            http_proxy = f"http://{http_proxy}"
        mounts["http://"] = httpx.AsyncHTTPTransport(proxy=http_proxy)
        print(f"HTTP Proxy configured: {http_proxy}")

    if https_proxy:
        # 注意：HTTPS 代理通常也使用 http:// 协议（这不是错误！）
        if "://" not in https_proxy:
            https_proxy = f"http://{https_proxy}"
        mounts["https://"] = httpx.AsyncHTTPTransport(proxy=https_proxy)
        print(f"HTTPS Proxy configured: {https_proxy}")

    try:
        # 使用新的 mounts 参数初始化客户端
        if mounts:
            http_client = httpx.AsyncClient(
                follow_redirects=False,
                timeout=60.0,
                mounts=mounts
            )
            print(f"HTTP client initialized with proxy mounts: {list(mounts.keys())}")
        else:
            http_client = httpx.AsyncClient(
                follow_redirects=False,
                timeout=60.0
            )
            print("HTTP client initialized without proxy")
    except Exception as e:
        print(f"Failed to initialize HTTP client: {e}")
        raise

    print("=" * 60)

    yield

    # Shutdown: Close HTTP client and stop background tasks
    stats_task.cancel()
    cleanup_task.cancel()

    try:
        await stats_task
    except asyncio.CancelledError:
        pass

    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    await http_client.aclose()


def _choose_available_port(preferred_port: int) -> int:
    """Select an available port, falling back to configured alternatives."""
    candidates = [preferred_port]
    fallback_port = int(os.getenv("FALLBACK_PORT", "8088"))
    if fallback_port not in candidates:
        candidates.append(fallback_port)
    # Use 0 as last resort to let OS assign a free port
    candidates.append(0)

    for port in candidates:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0", port))
                selected_port = sock.getsockname()[1]
                if selected_port != preferred_port:
                    print(f"[Port] {preferred_port} unavailable, switching to {selected_port}")
                return selected_port
            except OSError as exc:
                # 无权限或端口占用都视为不可用，尝试下一候选
                print(f"[Port] Unable to bind {port}: {exc}")
                continue
    return preferred_port


app = FastAPI(
    title="Anthropic Transparent Proxy",
    version="1.1",
    lifespan=lifespan
)

# 注册 Admin 路由
app.include_router(admin_router)


# ===== 健康检查端点 =====

@app.get("/health")
async def health_check(request: Request):
    """
    健康检查端点，用于容器健康检查和服务状态监控
    不依赖上游服务，仅检查代理服务本身是否正常运行
    """
    return Response(
        content=json.dumps({
            "status": "healthy",
            "service": "anthropic-transparent-proxy",
            "boot_id": request.app.state.boot_id,
            "started_at": request.app.state.started_at
        }),
        media_type="application/json",
        headers={"Cache-Control": "no-store"}
    )


@app.api_route("/", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def root_redirect(request: Request):
    """
    根路径：浏览器访问时重定向到 /admin，API 访问保持代理行为
    """
    accept_header = request.headers.get("accept", "")
    wants_html = "text/html" in accept_header or "application/xhtml+xml" in accept_header

    if wants_html:
        return RedirectResponse(url="/admin", status_code=307)

    return await proxy("", request)


# ===== 主代理逻辑 =====

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def proxy(path: str, request: Request):
    # 记录请求开始
    start_time = time.time()
    body = await request.body()

    # 跳过 Dashboard 相关路径的统计
    if not path.startswith("api/admin") and not path.startswith("admin"):
        request_id = await record_request_start(path, request.method, len(body))
    else:
        request_id = None
    
    # 构造目标 URL（根据 API Key 动态选择目标服务器）
    api_key = extract_api_key_from_auth_header(request)
    target_base = get_target_url_for_key(api_key)
    query = request.url.query
    target_url = f"{target_base}/{path}"
    if query:
        target_url += f"?{query}"

    # 仅测试环境打印详细日志
    if DEBUG_MODE:
        try:
            data = json.loads(body.decode('utf-8'))
            print(f"[Proxy] Request body ({len(body)} bytes): {json.dumps(data, indent=4)}")
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"[Proxy] Failed to parse JSON: {e}")
    else:
        print(f"[Proxy] Request: {request.method} {path}")
        print(f"[Proxy] Request body ({len(body)} bytes): {body[:200]}..." if len(body) > 200 else f"[Proxy] Request body: {body}")

    # 处理请求体（替换 system prompt）
    # 仅在路由为 /v1/messages 时执行处理
    print(f"[Proxy] Processing request for path: {path}")
    # 处理 v1/messages 路径（可能带有 query 参数如 ?beta=true）
    if path == "v1/messages" or path == "v1/messages/" or path.startswith("v1/messages?"):
        body = process_request_body(body, api_key=api_key, target_url=target_base)
    
    # 如果请求的是 v1/messages 且没有 beta=true 参数，自动添加
    if (path == "v1/messages" or path == "v1/messages/") and "beta=true" not in (query or ""):
        if query:
            query = f"{query}&beta=true"
        else:
            query = "beta=true"
        # 重新构造 target_url
        target_url = f"{target_base}/{path}?{query}"

    # 准备转发的请求头
    incoming_headers = list(request.headers.items())
    client_host = request.client.host if request.client else None
    forward_headers = prepare_forward_headers(incoming_headers, client_host, target_base)
    
    # 打印转发的请求头（调试用）
    if DEBUG_MODE:
        print(f"[Proxy] Target URL: {target_url}")
        print(f"[Proxy] Forward headers: {json.dumps(forward_headers, indent=2)}")

    # 发起上游请求并流式处理响应
    response_time = 0
    bytes_received = 0
    error_response_content = b""  # 新增：缓存错误响应内容（仅当状态码 >= 400 时）
    try:
        # 构建请求但不使用 context manager
        req = http_client.build_request(
            method=request.method,
            url=target_url,
            headers=forward_headers,
            content=body,
        )

        # 发送请求并开启流式模式 (不使用 async with)
        resp = await http_client.send(req, stream=True)
        
        # 打印上游响应信息（调试用）
        if DEBUG_MODE:
            print(f"[Proxy] Upstream response status: {resp.status_code}")
            print(f"[Proxy] Upstream response headers: {dict(resp.headers)}")

        # 过滤响应头
        response_headers = filter_response_headers(resp.headers.items())

        # 统计响应时间
        response_time = time.time() - start_time

        # 异步生成器:流式读取响应内容并统计字节数
        async def iter_response():
            nonlocal bytes_received
            nonlocal error_response_content
            try:
                async for chunk in resp.aiter_bytes():
                    bytes_received += len(chunk)
                    # 如果是错误响应，缓存内容（限制 50KB）
                    if resp.status_code >= 400 and len(error_response_content) < 50*1024:
                        error_response_content += chunk
                    yield chunk
            except Exception as e:
                # 优雅处理客户端断开连接
                if DEBUG_MODE:
                    print(f"[Stream Error] {e}")
                # 静默处理,避免日志污染
            finally:
                # 确保资源被释放 (作为备份,主要由 BackgroundTask 处理)
                pass

        # 创建响应完成后的统计任务
        async def close_and_record():
            await resp.aclose()
            if request_id:
                if resp.status_code < 400:
                    await record_request_success(
                        request_id,
                        path,
                        request.method,
                        bytes_received,
                        response_time,
                        resp.status_code
                    )
                else:
                    # 使用缓存的响应内容
                    response_content = ensure_unicode(error_response_content) if error_response_content else None
                    if DEBUG_MODE:
                        print(f"[Proxy] Response: {response_content}")
                    else:
                        err_content_len = len(error_response_content)
                        print(f"[Proxy] Response ({err_content_len} bytes): {response_content[:200]}..." if err_content_len > 200 else f"[Proxy] Response: {response_content}")

                    # 记录错误到统计服务
                    await record_request_error(
                        request_id,
                        path,
                        request.method,
                        f"HTTP {resp.status_code}: {resp.reason_phrase}",
                        response_time,
                        response_content,  # 新增参数
                        resp.status_code
                    )

        # 使用 BackgroundTask 在响应完成后关闭连接和记录统计
        return StreamingResponse(
            iter_response(),
            status_code=resp.status_code,
            headers=response_headers,
            background=BackgroundTask(close_and_record),
        )

    except httpx.RequestError as e:
        # 记录请求错误
        if request_id:
            await record_request_error(
                request_id,
                path,
                request.method,
                str(e),
                time.time() - start_time,
                None,
                502
            )
        return Response(content=f"Upstream request failed: {e}", status_code=502)


if __name__ == "__main__":
    import uvicorn
    # 开发模式启用热重载，生产模式禁用（通过 DEBUG_MODE 环境变量控制）
    # 注意：使用模块路径而非文件路径，以支持相对导入
    reload_enabled = DEBUG_MODE and os.getenv("ENABLE_RELOAD", "false").lower() in ("true", "1", "yes")
    if reload_enabled:
        print("[Uvicorn] Reload enabled via ENABLE_RELOAD")
    else:
        print("[Uvicorn] Reload disabled (set ENABLE_RELOAD=true to enable)")
    try:
        selected_port = _choose_available_port(PORT)
        uvicorn.run("backend.app:app", host="0.0.0.0", port=selected_port, reload=reload_enabled)
    except (PermissionError, OSError) as exc:
        if reload_enabled:
            print(f"[Uvicorn] Reload mode failed ({exc}); fallback to non-reload")
            uvicorn.run("backend.app:app", host="0.0.0.0", port=PORT, reload=False)
        else:
            raise
