"""
认证服务

提供安全的 API Key 校验与 FastAPI 依赖封装
"""

import hashlib
import hmac
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import DASHBOARD_API_KEY, ENABLE_DASHBOARD

# HTTP Bearer 安全方案，auto_error=False 便于自定义错误响应
_security = HTTPBearer(auto_error=False)

# API Key 最大长度限制，防止 DOS 攻击
MAX_API_KEY_LENGTH = 1024


def _sha256_digest(value: str) -> bytes:
    """返回固定长度的 SHA-256 摘要，避免长度泄露导致的计时差异"""
    return hashlib.sha256(value.encode("utf-8")).digest()


def _constant_time_equals(provided: str, expected: str) -> bool:
    """
    使用固定长度摘要配合 hmac.compare_digest 进行常量时间比较，抵御计时攻击
    """
    return hmac.compare_digest(_sha256_digest(provided), _sha256_digest(expected))


def dashboard_auth_dependency():
    """
    FastAPI 依赖工厂，可在路由装饰器或 dependencies 参数中复用
    """
    return Depends(verify_dashboard_api_key)


async def verify_dashboard_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
) -> bool:
    """
    验证 Dashboard API Key（常量时间比较）

    Raises:
        HTTPException: 403 - Dashboard disabled
        HTTPException: 401 - 未提供或无效的 API key，或未配置 API key
    """
    if not ENABLE_DASHBOARD:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard is disabled"
        )

    expected_key = DASHBOARD_API_KEY or ""
    # 未配置 key 时禁止编辑，避免绕过鉴权
    if expected_key == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Dashboard API key is not configured",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查凭据是否存在且为 Bearer 类型
    if not credentials or credentials.scheme.lower() != "bearer":
        provided_key = ""
    else:
        # 检查 API Key 长度，防止 DOS 攻击
        if len(credentials.credentials) > MAX_API_KEY_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        provided_key = credentials.credentials

    # 无论是否提供凭据，都执行常量时间比较以平衡时序
    keys_match = _constant_time_equals(provided_key, expected_key)

    if not credentials or not keys_match:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True
