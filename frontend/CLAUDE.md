# Frontend 模块文档

> 📍 **导航**: [根目录](../CLAUDE.md) > **frontend**

---

## 变更日志

### v2.1.0 (2025-12-30)
- 新增配置编辑器组件 (`ConfigEditor.vue`)
- 新增认证弹窗组件 (`ConfigAuthModal.vue`)
- 新增重启确认对话框 (`RestartConfirmDialog.vue`)
- 增强配置管理页面，支持运行时配置编辑和自动重启

---

## 📋 模块概述

**Frontend** 是基于 Vue 3 + TypeScript 的 Web 管理面板,提供实时监控、日志查看和配置管理界面。

**技术栈**: Vue 3 + TypeScript + Vite + Pinia + TailwindCSS 4 + Chart.js

**核心特性**:
- 实时监控仪表板（请求统计、性能指标、图表）
- 实时日志流（SSE，支持过滤和搜索）
- 历史日志查询（按日期、路径、方法、状态码过滤）
- **配置管理**（环境变量、自定义请求头、API Key 认证）
- PWA 支持（离线访问、桌面安装）

---

## 📁 目录结构

```
frontend/
├── public/
│   └── icons/
│       └── pwa.svg              # PWA 图标
├── src/
│   ├── main.ts                  # 应用入口
│   ├── App.vue                  # 根组件
│   ├── router/
│   │   └── index.ts             # 路由配置
│   ├── stores/
│   │   └── index.ts             # Pinia 状态管理
│   ├── services/
│   │   └── api.ts               # API 服务层
│   ├── views/                   # 页面组件
│   │   ├── Dashboard.vue        # 仪表板
│   │   ├── Monitoring.vue       # 监控中心
│   │   └── Config.vue           # 配置管理（增强）
│   ├── components/              # 公共组件
│   │   ├── BaseLayout.vue       # 布局组件
│   │   ├── Icon.vue             # 图标组件
│   │   ├── NotificationContainer.vue  # 通知容器
│   │   ├── ConfigEditor.vue     # 配置编辑器（新增）
│   │   ├── ConfigAuthModal.vue  # 认证弹窗（新增）
│   │   └── RestartConfirmDialog.vue  # 重启确认对话框（新增）
│   ├── composables/             # 组合式函数
│   │   ├── useRealtime.ts       # 实时数据
│   │   └── useServiceRestart.ts # 服务重启（新增）
│   ├── utils/                   # 工具函数
│   │   ├── statusStyle.ts       # 状态样式
│   │   └── configValidation.ts  # 配置验证（新增）
│   └── types/
│       └── index.ts             # TypeScript 类型
├── package.json                 # 依赖配置
├── vite.config.ts               # Vite 构建配置
└── tsconfig.json                # TypeScript 配置
```

---

## 🧩 核心模块

### 1. 应用入口 ([src/main.ts](src/main.ts))

**职责**: 初始化 Vue 应用、注册插件、挂载应用、注册 PWA Service Worker

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { registerSW } from 'virtual:pwa-register'
import router from './router'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')

// 仅在生产环境注册 Service Worker
if (import.meta.env.PROD) {
  registerSW({ immediate: true })
}
```

---

### 2. 路由配置 ([src/router/index.ts](src/router/index.ts))

**路由列表**:
| 路径 | 组件 | 功能 |
|------|------|------|
| `/` | - | 重定向到 `/dashboard` |
| `/dashboard` | Dashboard.vue | 仪表板页面 |
| `/monitoring` | Monitoring.vue | 监控中心 |
| `/config` | Config.vue | 配置管理（增强） |

**路由守卫**:
- 设置页面标题

---

### 3. API 服务层 ([src/services/api.ts](src/services/api.ts))

**职责**: 封装后端 API 调用，统一错误处理

**API 方法**:
| 方法 | 端点 | 功能 |
|------|------|------|
| `fetchSystemStats()` | GET `/api/stats` | 获取系统统计 |
| `fetchErrorLogs()` | GET `/api/errors` | 获取错误日志 |
| `fetchSystemConfig()` | GET `/api/config` | 获取配置 |
| `updateSystemConfig()` | POST `/api/config` | **更新配置（新增）** |
| `restartService()` | POST `/api/restart` | **重启服务（新增）** |
| `subscribeToLogs()` | SSE `/api/logs/stream` | 订阅实时日志 |
| `fetchLogHistory()` | GET `/api/logs/history` | 查询历史日志 |
| `clearAllLogs()` | DELETE `/api/logs/clear` | 清空日志 |

---

### 4. 状态管理 ([src/stores/index.ts](src/stores/index.ts))

**职责**: 全局状态管理（使用 Pinia）

**Store 结构**:
```typescript
export const useMainStore = defineStore('main', {
  state: () => ({
    systemStats: null as SystemStats | null,
    errorLogs: [] as ErrorLog[],
    systemConfig: null as SystemConfig | null,
    logs: [] as LogEntry[],
    isLoading: false,
    notifications: [] as Notification[]
  }),
  actions: {
    async loadSystemStats(),
    async loadErrorLogs(),
    async loadSystemConfig(),
    async updateConfig(data),
    addNotification(notification),
    removeNotification(id)
  }
})
```

---

### 5. 页面组件

#### Dashboard ([src/views/Dashboard.vue](src/views/Dashboard.vue))
- 显示系统概览、统计卡片、快速操作
- 使用 Chart.js 绘制趋势图

#### Monitoring ([src/views/Monitoring.vue](src/views/Monitoring.vue))
- 实时监控、性能指标、路径统计
- 使用 `useRealtime()` 订阅实时数据

#### Config ([src/views/Config.vue](src/views/Config.vue)) **【增强】**
- **新功能**:
  - 配置项分类显示（基础设置、代理核心设置、管理与安全）
  - 可编辑字段标识
  - 配置保存需要 API Key 认证
  - 保存后自动重启服务
- **组件结构**:
  - `ConfigEditor`: 配置编辑表单
  - `ConfigAuthModal`: API Key 认证弹窗
  - `RestartConfirmDialog`: 重启确认对话框

---

### 6. 公共组件（新增）

#### ConfigEditor ([src/components/ConfigEditor.vue](src/components/ConfigEditor.vue))

**职责**: 配置项编辑表单

**功能**:
- 按分类分组显示配置项
- 根据 `value_type` 渲染不同输入控件（文本、数字、开关、JSON）
- 可编辑/只读状态控制
- 字段验证（URL、JSON 格式）

**关键特性**:
```vue
<template>
  <div v-for="(entries, category) in groupedEntries" :key="category">
    <h3>{{ category }}</h3>
    <div v-for="entry in entries" :key="entry.key">
      <!-- 根据 value_type 渲染输入框 -->
      <input v-if="entry.metadata.value_type === 'string'" />
      <input v-if="entry.metadata.value_type === 'number'" type="number" />
      <input v-if="entry.metadata.value_type === 'boolean'" type="checkbox" />
      <textarea v-if="entry.metadata.value_type === 'json'" />
    </div>
  </div>
</template>
```

#### ConfigAuthModal ([src/components/ConfigAuthModal.vue](src/components/ConfigAuthModal.vue))

**职责**: API Key 认证弹窗

**功能**:
- 输入 API Key
- 提交认证请求
- 错误提示

#### RestartConfirmDialog ([src/components/RestartConfirmDialog.vue](src/components/RestartConfirmDialog.vue))

**职责**: 服务重启确认对话框

**功能**:
- 显示重启提示信息
- 确认/取消操作
- 倒计时显示

---

### 7. 组合式函数（新增）

#### useServiceRestart ([src/composables/useServiceRestart.ts](src/composables/useServiceRestart.ts))

**职责**: 封装服务重启逻辑

**功能**:
```typescript
export function useServiceRestart() {
  const restartService = async (apiKey: string) => {
    await api.restartService(apiKey)
  }

  const confirmRestart = async () => {
    // 显示确认对话框
    // 调用 restartService
  }

  return { restartService, confirmRestart }
}
```

---

### 8. 工具函数（新增）

#### configValidation ([src/utils/configValidation.ts](src/utils/configValidation.ts))

**职责**: 配置项验证

**功能**:
- URL 格式验证
- JSON 格式验证
- 数字范围验证

```typescript
export function validateUrl(url: string): boolean {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}

export function validateJson(value: string): boolean {
  try {
    JSON.parse(value)
    return true
  } catch {
    return false
  }
}
```

---

### 9. TypeScript 类型 ([src/types/index.ts](src/types/index.ts))

**核心类型**:
```typescript
// 系统统计
export interface SystemStats {
  total_requests: number
  successful_requests: number
  failed_requests: number
  total_bytes_sent: number
  total_bytes_received: number
  uptime: number
  avg_response_time: number
}

// 配置项（新增）
export interface ConfigEntry {
  key: string
  value: string | number | boolean | object | null
  metadata: ConfigMetadata
}

export interface ConfigMetadata {
  value_type: 'string' | 'number' | 'boolean' | 'json'
  editable: boolean
  requires_restart: boolean
  description: string
  category: string
  example?: any
}

// 配置响应（新增）
export interface ConfigResponse {
  entries: ConfigEntry[]
  api_key_configured: boolean
  read_only: boolean
  needs_restart: boolean
}
```

---

## 🔧 依赖管理

```json
{
  "dependencies": {
    "vue": "^3.5.25",
    "vue-router": "^4.6.3",
    "pinia": "^3.0.4",
    "ky": "^1.14.1",
    "chart.js": "^4.5.1",
    "vue-chartjs": "^5.3.3",
    "workbox-window": "^7.4.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^6.0.2",
    "vite": "^7.2.4",
    "typescript": "~5.9.3",
    "tailwindcss": "^4.0.0",
    "vite-plugin-pwa": "^0.21.1"
  }
}
```

---

## 🚀 构建和部署

### 开发模式
```bash
cd frontend
npm install
npm run dev
```

访问: `http://localhost:5173`

### 生产构建
```bash
npm run build
```

**构建输出**: `../static/`（由后端静态服务）

---

## 🎨 样式系统

### TailwindCSS 配置
```typescript
// tailwind.config.ts
export default {
  theme: {
    extend: {
      colors: {
        primary: '#0ea5e9',   // 天蓝色
        success: '#10b981',   // 绿色
        warning: '#f59e0b',   // 橙色
        error: '#ef4444',     // 红色
      }
    }
  }
}
```

---

## 📱 PWA 配置

**Service Worker 策略**:
- **静态资源**: CacheFirst（优先缓存）
- **API 请求**: NetworkFirst（优先网络）

**离线支持**:
- 缓存静态资源（HTML、CSS、JS、图片）
- 离线页面提示

---

## 🧪 测试

```bash
# 运行测试
npm run test

# 测试 UI
npm run test:ui

# 测试覆盖率
npm run test:coverage
```

---

**返回**: [根目录文档](../CLAUDE.md)
