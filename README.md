# RoleBridge

跨职能沟通翻译助手 - 在不同职能角色之间进行角色视角转换式的需求与技术表达翻译。

## 项目简介

RoleBridge 是一个专业的跨职能沟通翻译工具，帮助产品经理、开发工程师、运营人员、管理层等不同角色之间进行更有效的沟通。

## 技术栈

- **后端**: FastAPI (Python)
- **前端**: Vue.js + Vite
- **LLM**: DeepSeek API
- **容器化**: Docker + Docker Compose

## 快速开始

### 环境要求

- Python 3.9+
- Node.js 16+
- Docker & Docker Compose

### 安装步骤

1. 克隆项目
```bash
git clone <repository-url>
cd RoleBridge
```

2. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的配置
```

3. 启动服务
```bash
docker-compose up -d
```

## 项目结构

```
RoleBridge/
├── backend/          # FastAPI 后端服务
├── frontend/         # Vue.js 前端应用
├── product.md        # 产品规范文档
└── docker-compose.yml # Docker 编排配置
```

## 开发指南

详见 [product.md](product.md) 了解产品规范和开发指导。

## License

MIT

