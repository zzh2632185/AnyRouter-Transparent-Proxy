# Backend 模块文档

> 📍 **导航**: [根目录](../CLAUDE.md) > **backend**

---

## 变更日志

### v2.1.0 (2025-12-30)
- 新增配置管理服务 (`config_service.py`)
- 新增认证服务 (`auth_service.py`)
- 新增重启服务 (`restart_service.py`)
- 新增配置数据模型 (`schemas/config.py`)
- 增强 admin API 路由，支持配置读写和服务重启

---

## 📋 模块概述

**Backend** 是基于 FastAPI 的异步 HTTP 代理服务，负责请求转发、System Prompt 处理、统计收集、配置管理和管理面板 API。

**技术栈**: FastAPI + httpx + Uvicorn + sse-starlette + Pydantic

---

## 📁 目录结构

```
backend/
├── app.py                    # 主应用入口
├── config.py                 # 配置管理
├── requirements.txt          # 依赖清单
├── services/                 # 业务逻辑
│   ├── proxy.py             # 代理处理
│   ├── stats.py             # 统计收集
│   ├── log_storage.py       # 日志持久化
│   ├── config_service.py    # 配置持久化（新增）
│   ├── auth_service.py      # 认证服务（新增）
│   └── restart_service.py   # 重启服务（新增）
├── routers/                  # 路由层
│   └── admin.py             # 管理面板 API
├── schemas/                  # 数据模型（新增）
│   └── config.py            # 配置模型
├── utils/                    # 工具函数
│   └── encoding.py          # 编码处理
└── tests/                    # 单元测试
    └── test_config_service.py
```

---

## 🧩 核心模块

### 1. 主应用 ([app.py](app.py))

**职责**: FastAPI 应用定义、生命周期管理、主代理路由

**关键函数**:
| 函数 | 行号 | 功能 |
|------|------|------|
| `lifespan()` | 54-128 | 生命周期管理，初始化 HTTP 客户端和后台任务 |
| `health_check()` | ~145 | 健康检查端点 |
| `proxy()` | ~190+ | **核心**: 捕获所有路由并转发请求，支持流式响应 |

**代理流程**:
1. 读取请求体
2. 过滤请求头（移除 hop-by-hop 头部）
3. 对 `/v1/messages` 执行 System Prompt 处理
4. 构建并发送上游请求（`httpx.build_request()` + `send(stream=True)`）
5. 返回流式响应（`BackgroundTask` 管理连接关闭）

---

### 2. 配置管理 ([config.py](config.py))

**职责**: 加载环境变量、管理全局配置、自定义请求头加载

**主要配置**:
| 配置 | 类型 | 说明 |
|------|------|------|
| `TARGET_BASE_URL` | str | 上游 API 地址 |
| `SYSTEM_PROMPT_REPLACEMENT` | str\|None | System Prompt 替换文本 |
| `SYSTEM_PROMPT_BLOCK_INSERT_IF_NOT_EXIST` | bool | 启用插入模式 |
| `HOP_BY_HOP_HEADERS` | set[str] | RFC 7230 hop-by-hop 头部列表 |
| `CUSTOM_HEADERS` | dict | 自定义请求头（从 `env/.env.headers.json` 加载） |

---

### 3. 代理处理 ([services/proxy.py](services/proxy.py))

**职责**: 请求/响应过滤、System Prompt 处理

**关键函数**:
| 函数 | 功能 |
|------|------|
| `filter_request_headers()` | 过滤请求头，移除 hop-by-hop 头部 |
| `filter_response_headers()` | 过滤响应头 |
| `process_request_body()` | 处理请求体，替换/插入 System Prompt |
| `prepare_forward_headers()` | 准备转发请求头，注入自定义头部 |

**System Prompt 处理逻辑** (仅 `/v1/messages` 路由):
```python
# 插入模式
if SYSTEM_PROMPT_BLOCK_INSERT_IF_NOT_EXIST:
    if "Claude Code" not in original_text:
        data["system"].insert(0, new_element)
    else:
        data["system"][0]["text"] = SYSTEM_PROMPT_REPLACEMENT
# 替换模式（默认）
else:
    data["system"][0]["text"] = SYSTEM_PROMPT_REPLACEMENT
```

---

### 4. 统计收集 ([services/stats.py](services/stats.py))

**职责**: 收集请求统计、性能指标、错误日志，提供实时日志流

**全局数据**:
| 变量 | 类型 | 用途 |
|------|------|------|
| `request_stats` | dict | 全局统计（请求数、成功数、失败数、流量） |
| `recent_requests` | deque | 最近 1000 个请求的性能数据 |
| `error_logs` | deque | 最近 500 个错误日志 |
| `log_queue` | asyncio.Queue | 日志消息队列（SSE 推送） |

**关键函数**:
- `record_request_start()`: 记录请求开始
- `record_request_success()`: 记录请求成功
- `record_request_error()`: 记录请求错误
- `broadcast_log_message()`: 广播日志到所有 SSE 订阅者
- `periodic_stats_update()`: 后台任务，定期更新统计
- `log_producer()`: 后台任务，消费日志队列并广播

---

### 5. 配置持久化服务 ([services/config_service.py](services/config_service.py)) **【新增】**

**职责**: 安全的 .env 文件读写操作，包括原子写入、备份机制和文件锁安全

**类结构**:
```python
class ConfigService:
    def __init__(self, env_file: str = ".env", backup_dir: str = "backups")

    def load_env(self) -> Dict[str, str]
    def save_env(self, updates: Dict[str, Any]) -> bool
    def update_custom_headers(self, headers: Dict[str, str]) -> bool

    # 私有方法
    def _acquire_file_lock(self, file_obj, non_blocking: bool = False) -> bool
    def _release_file_lock(self, file_obj)
    def _create_backup(self) -> bool
```

**关键特性**:
- **原子写入**: tmpfile + `os.fsync()` + `os.rename()`
- **备份机制**: 保存前自动备份到 `backups/` 目录
- **文件锁**: 使用 `fcntl.flock()` 保证并发安全
- **Docker 兼容**: 不支持 flock 的文件系统自动降级为无锁模式

**保存流程**:
1. 获取文件锁
2. 创建备份
3. 写入临时文件
4. fsync 刷盘
5. 原子重命名
6. 释放文件锁

---

### 6. 认证服务 ([services/auth_service.py](services/auth_service.py)) **【新增】**

**职责**: 提供安全的 API Key 校验与 FastAPI 依赖封装

**关键函数**:
```python
def _constant_time_equals(provided: str, expected: str) -> bool
    """常量时间比较，抵御计时攻击"""

async def verify_dashboard_api_key(credentials) -> bool
    """验证 Dashboard API Key（常量时间比较）"""

def dashboard_auth_dependency():
    """FastAPI 依赖工厂"""
```

**安全特性**:
- **常量时间比较**: 使用 `hmac.compare_digest()` 防止计时攻击
- **SHA-256 摘要**: 避免长度泄露导致的计时差异
- **长度限制**: API Key 最大长度 1024 字节，防止 DOS 攻击

---

### 7. 重启服务 ([services/restart_service.py](services/restart_service.py)) **【新增】**

**职责**: 调度服务重启

**函数**:
```python
def schedule_restart(delay: float = 1.0, strategy: str = "auto"):
    """
    调度服务重启

    Args:
        delay: 延迟时间（秒）
        strategy: 重启策略 ("auto", "signal", "exec")
            - "auto": 自动选择（默认 exec）
            - "signal": SIGTERM 信号（需要 Supervisor）
            - "exec": os.execv 自重启
    """
```

**重启策略**:
- **exec 模式** (默认): 使用 `os.execv()` 自重启，支持重新加载 .env
- **signal 模式**: 发送 SIGTERM 信号，由 Supervisor 重启
- **auto 模式**: 检测 `SUPERVISOR_ENABLED` 环境变量自动选择

---

### 8. 配置数据模型 ([schemas/config.py](schemas/config.py)) **【新增】**

**职责**: 定义配置项的数据结构、类型验证与响应格式

**核心模型**:

```python
class ConfigValueType(str, Enum):
    string = "string"
    number = "number"
    boolean = "boolean"
    json = "json"

class ConfigMetadata(BaseModel):
    value_type: ConfigValueType
    editable: bool
    requires_restart: bool
    description: str
    category: ConfigCategory
    example: Optional[ConfigValue]

class ConfigEntry(BaseModel):
    key: str
    value: ConfigValue
    metadata: ConfigMetadata

class ConfigUpdateRequest(BaseModel):
    target_base_url: Optional[AnyHttpUrl]
    preserve_host: Optional[bool]
    system_prompt_replacement: Optional[str]
    # ... 其他字段

class ConfigResponse(BaseModel):
    entries: List[ConfigEntry]
    api_key_configured: bool
    read_only: bool
    needs_restart: bool
```

**验证器**:
- `custom_headers` 验证: 检查 key 为字符串、value 可序列化
- `value_type` 验证: 根据元数据类型验证配置值

---

### 9. 管理面板路由 ([routers/admin.py](routers/admin.py))

**职责**: Web 管理面板 RESTful API

**API 端点**:
| 端点 | 方法 | 功能 | 认证 |
|------|------|------|------|
| `/api/stats` | GET | 获取系统统计 | 否 |
| `/api/errors` | GET | 获取错误日志 | 否 |
| `/api/config` | GET | 获取配置 | 否 |
| `/api/config` | POST | 更新配置（新增） | **是** |
| `/api/restart` | POST | 重启服务（新增） | **是** |
| `/api/logs/stream` | GET | 实时日志流 (SSE) | 否 |
| `/api/logs/history` | GET | 查询历史日志 | 否 |
| `/api/logs/clear` | DELETE | 清空日志 | 否 |

**配置更新流程** (`POST /api/config`):
1. 验证 API Key（需要认证）
2. 解析请求数据（`ConfigUpdateRequest`）
3. 调用 `ConfigService.save_env()` 保存到 .env
4. 调用 `schedule_restart()` 安排重启

---

## 🔧 依赖管理

```txt
fastapi==0.115.5
uvicorn==0.32.1
httpx==0.28.1
python-dotenv==1.0.1
sse-starlette==2.2.1
```

---

## 🚀 启动方式

### 开发模式
```bash
python backend/app.py
```

### 生产模式
```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8088 --workers 1
```

**注意**: 使用全局状态管理统计，建议单 worker 模式。

---

## 🧪 测试

```bash
# 运行测试
pytest backend/tests/

# 单个测试文件
pytest backend/tests/test_config_service.py
```

---

**返回**: [根目录文档](../CLAUDE.md)
