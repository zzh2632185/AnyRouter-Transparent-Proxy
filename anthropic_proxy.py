from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import httpx
from typing import Iterable
from urllib.parse import urlparse

app = FastAPI(title="Anthropic Transparent Proxy", version="1.1")

# ===== 基础配置 =====

TARGET_BASE = "https://q.quuvv.cn"
PRESERVE_HOST = False  # 是否保留原始 Host

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}

# 可选自定义 Header（覆盖原请求同名项）
CUSTOM_HEADERS = {
    # 例如：
    # "User-Agent": "Claude-Proxy/1.0",
    # "x-anthropic-system-prompt": "你是一个透明代理，请保持请求不变。",
}


# ===== 工具函数 =====

def filter_request_headers(headers: Iterable[tuple]) -> dict:
    out = {}
    for k, v in headers:
        lk = k.lower()
        if lk in HOP_BY_HOP_HEADERS:
            continue
        if lk == "host" and not PRESERVE_HOST:
            continue
        out[k] = v
    return out


def filter_response_headers(headers: Iterable[tuple]) -> dict:
    out = {}
    for k, v in headers:
        if k.lower() in HOP_BY_HOP_HEADERS:
            continue
        out[k] = v
    return out


# ===== 主代理逻辑 =====

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def proxy(path: str, request: Request):
    # 构造目标 URL
    query = request.url.query
    target_url = f"{TARGET_BASE}/{path}"
    if query:
        target_url += f"?{query}"

    # 读取 body
    body = await request.body()
    print(body)

    # 复制并过滤请求头
    incoming_headers = list(request.headers.items())
    forward_headers = filter_request_headers(incoming_headers)

    # 设置 Host
    if not PRESERVE_HOST:
        parsed = urlparse(TARGET_BASE)
        forward_headers["Host"] = parsed.netloc

    # 注入自定义 Header
    for k, v in CUSTOM_HEADERS.items():
        forward_headers[k] = v

    # 添加 X-Forwarded-For
    client_host = request.client.host if request.client else None
    if client_host:
        existing = forward_headers.get("X-Forwarded-For")
        forward_headers["X-Forwarded-For"] = f"{existing}, {client_host}" if existing else client_host

    # 发起上游请求
    async with httpx.AsyncClient(follow_redirects=False, timeout=60.0) as client:
        try:
            resp = await client.request(
                method=request.method,
                url=target_url,
                headers=forward_headers,
                content=body,
            )
        except httpx.RequestError as e:
            return Response(content=f"Upstream request failed: {e}", status_code=502)

        response_headers = filter_response_headers(resp.headers.items())

        async def iter_response():
            async for chunk in resp.aiter_bytes():
                yield chunk

        return StreamingResponse(
            iter_response(),
            status_code=resp.status_code,
            headers=response_headers,
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("anthropic_proxy:app", host="0.0.0.0", port=8080, reload=True)