"""
配置相关 Pydantic 模型

用于描述配置项、类型验证与响应结构
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ConfigDict, model_validator, validator, AnyHttpUrl

ConfigValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]


class ConfigValueType(str, Enum):
    """配置值类型枚举"""
    string = "string"
    number = "number"
    boolean = "boolean"
    json = "json"


class ConfigCategory(str, Enum):
    """配置分类枚举"""
    BASIC = "基础设置"
    PROXY = "代理核心设置"
    SECURITY = "管理与安全"


class ConfigMetadata(BaseModel):
    """配置字段的元数据定义"""
    value_type: ConfigValueType = Field(..., description="配置值类型")
    editable: bool = Field(default=False, description="是否允许运行时修改")
    requires_restart: bool = Field(default=False, description="是否需要重启生效")
    description: str = Field(..., description="配置项描述")
    category: ConfigCategory = Field(..., description="配置项分类")
    example: Optional[ConfigValue] = Field(default=None, description="示例值")


class ConfigEntry(BaseModel):
    """单条配置项，包含值与元数据"""
    key: str = Field(..., min_length=1, description="配置键名")
    value: ConfigValue = Field(default=None, description="配置值")
    metadata: ConfigMetadata = Field(..., description="配置元数据")

    @model_validator(mode="after")
    def _validate_value_type(self):
        """根据元数据验证配置值类型"""
        if self.metadata is not None:
            _validate_value_for_type(self.metadata.value_type, self.value)
        return self


class ConfigUpdateRequest(BaseModel):
    """配置更新请求模型"""
    model_config = ConfigDict(
        validate_by_name=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="ignore"
    )
    target_base_url: Optional[AnyHttpUrl] = Field(default=None, description="上游基础地址")
    preserve_host: Optional[bool] = Field(default=None, description="是否保留原始 Host")
    system_prompt_replacement: Optional[str] = Field(default=None, description="System prompt 替换内容")
    system_prompt_block_insert_if_not_exist: Optional[bool] = Field(default=None, description="System prompt 插入模式")
    debug_mode: Optional[bool] = Field(default=None, description="调试模式开关")
    port: Optional[int] = Field(default=None, ge=1, le=65535, description="服务端口")
    enable_dashboard: Optional[bool] = Field(
        default=None,
        validation_alias="dashboard_enabled",
        serialization_alias="dashboard_enabled",
        description="是否启用 Dashboard"
    )
    dashboard_api_key: Optional[str] = Field(default=None, description="Dashboard API Key")
    custom_headers: Optional[Dict[str, Union[str, int, float, bool]]] = Field(default=None, description="自定义请求头")

    @validator("custom_headers")
    def _validate_custom_headers(cls, value: Optional[Dict[str, Union[str, int, float, bool]]]) -> Optional[Dict[str, Union[str, int, float, bool]]]:
        """验证自定义请求头格式和可序列化性"""
        if value is None:
            return value
        if not isinstance(value, dict):
            raise ValueError("custom_headers 必须是字典类型")

        # 验证 key 为字符串
        invalid_keys = [key for key in value.keys() if not isinstance(key, str)]
        if invalid_keys:
            raise ValueError("custom_headers 的 key 必须为字符串")

        # 验证 value 为可序列化类型
        import json
        for k, v in value.items():
            try:
                json.dumps(v)
            except (TypeError, ValueError):
                raise ValueError(f"custom_headers[{k}] 的值不支持 JSON 序列化")

        return value


class ConfigResponse(BaseModel):
    """配置响应模型，兼容旧的扁平字段与新的 entries 输出"""
    model_config = ConfigDict(validate_by_name=True, populate_by_name=True)
    entries: List[ConfigEntry] = Field(default_factory=list, description="配置条目列表")
    api_key_configured: bool = Field(default=False, description="是否配置了 Dashboard API Key")
    read_only: bool = Field(default=True, description="是否为只读模式")
    needs_restart: bool = Field(default=False, description="是否需要重启")

    # 旧版扁平字段（向后兼容）
    target_base_url: Optional[str] = Field(default=None, description="上游基础地址")
    preserve_host: Optional[bool] = Field(default=None, description="是否保留原始 Host")
    system_prompt_replacement: Optional[str] = Field(default=None, description="System prompt 替换内容")
    system_prompt_block_insert_if_not_exist: Optional[bool] = Field(default=None, description="System prompt 插入模式")
    debug_mode: Optional[bool] = Field(default=None, description="调试模式开关")
    port: Optional[int] = Field(default=None, description="服务端口")
    enable_dashboard: Optional[bool] = Field(
        default=None,
        validation_alias="dashboard_enabled",
        serialization_alias="dashboard_enabled",
        description="是否启用 Dashboard"
    )
    dashboard_api_key: Optional[str] = Field(default=None, description="Dashboard API Key")
    custom_headers: Optional[Dict[str, Any]] = Field(default=None, description="自定义请求头")


def _validate_value_for_type(value_type: ConfigValueType, value: ConfigValue) -> None:
    """根据类型枚举验证配置值类型"""
    if value is None:
        return

    if value_type == ConfigValueType.string:
        if not isinstance(value, str):
            raise ValueError("value 必须为 string 类型")
        return

    if value_type == ConfigValueType.number:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("value 必须为 number 类型")
        return

    if value_type == ConfigValueType.boolean:
        if not isinstance(value, bool):
            raise ValueError("value 必须为 boolean 类型")
        return

    if value_type == ConfigValueType.json:
        if not isinstance(value, (dict, list)):
            raise ValueError("value 必须为 json 类型")
        return

    raise ValueError("未知的 value_type")


# 配置元数据定义
CONFIG_METADATA = [
    ConfigEntry(
        key="target_base_url",
        value="https://anyrouter.top",
        metadata=ConfigMetadata(
            value_type=ConfigValueType.string,
            editable=True,
            requires_restart=True,
            description="所有请求转发到的目标基础地址",
            category=ConfigCategory.PROXY,
            example="https://api.openai.com"
        )
    ),
    ConfigEntry(
        key="preserve_host",
        value=False,
        metadata=ConfigMetadata(
            value_type=ConfigValueType.boolean,
            editable=False,  # 这个通常是固定值
            requires_restart=True,
            description="是否保留原始请求中的 Host 头部",
            category=ConfigCategory.PROXY
        )
    ),
    ConfigEntry(
        key="system_prompt_replacement",
        value=None,
        metadata=ConfigMetadata(
            value_type=ConfigValueType.string,
            editable=True,
            requires_restart=True,
            description="用于替换请求中 system prompt 的内容",
            category=ConfigCategory.PROXY,
            example="你是一个有帮助的AI助手"
        )
    ),
    ConfigEntry(
        key="system_prompt_block_insert_if_not_exist",
        value=False,
        metadata=ConfigMetadata(
            value_type=ConfigValueType.boolean,
            editable=True,
            requires_restart=True,
            description="如果原始请求中没有 system prompt，是否插入新内容",
            category=ConfigCategory.PROXY
        )
    ),
    ConfigEntry(
        key="debug_mode",
        value=False,
        metadata=ConfigMetadata(
            value_type=ConfigValueType.boolean,
            editable=True,
            requires_restart=True,
            description="是否启用调试模式，输出详细日志",
            category=ConfigCategory.BASIC
        )
    ),
    ConfigEntry(
        key="port",
        value=8088,
        metadata=ConfigMetadata(
            value_type=ConfigValueType.number,
            editable=True,
            requires_restart=True,
            description="服务监听的端口号",
            category=ConfigCategory.BASIC,
            example=8088
        )
    ),
    ConfigEntry(
        key="enable_dashboard",
        value=True,
        metadata=ConfigMetadata(
            value_type=ConfigValueType.boolean,
            editable=False,  # 这个通常通过环境变量控制
            requires_restart=True,
            description="是否启用 Web 管理面板",
            category=ConfigCategory.SECURITY
        )
    ),
    ConfigEntry(
        key="dashboard_api_key",
        value="",
        metadata=ConfigMetadata(
            value_type=ConfigValueType.string,
            editable=True,
            requires_restart=True,
            description="Web 管理面板的访问密钥，为空时无需认证",
            category=ConfigCategory.SECURITY,
            example="your-secret-api-key"
        )
    ),
    ConfigEntry(
        key="custom_headers",
        value={},
        metadata=ConfigMetadata(
            value_type=ConfigValueType.json,
            editable=True,
            requires_restart=False,  # 运行时可以更新
            description="自定义请求头，以 JSON 格式配置",
            category=ConfigCategory.PROXY,
            example={"Authorization": "Bearer token", "X-Custom-Header": "value"}
        )
    )
]
