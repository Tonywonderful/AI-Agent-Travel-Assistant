# 🗺️ 旅游推荐助手

> 融合大模型、RAG、本地攻略与高德地图能力的智能旅行规划系统

智旅云图是一个面向中文旅行场景的 AI 旅行规划项目。用户输入目的地、日期、预算、人数和偏好后，系统会自动生成结构化旅行方案，并进一步补充地图点位、天气信息、预算拆分、景点图片；同时提供热门目的地推荐与可调用工具的 AI 对话助手。

相比只输出一段文本的 LLM Demo，这个项目更强调完整链路落地：从 **行程生成、攻略检索、地图信息补全、天气补充、对话助手，到历史管理**，尽量把 AI 能力组织成一个可交互、可保存、可展示的产品原型。

## 📝 最近更新

更多更新见：[CHANGELOG.md](./CHANGELOG.md)

> **数据边界**：当前本地 Markdown 攻略用于 RAG 参考，并不等同于已逐条核验的实时 POI、门票、餐饮或住宿数据。涉及价格、营业状态和可预订性时，应以外部服务或人工核验结果为准。

---

## 📸 效果展示

![1784973950038](image/README/1784973950038.png)

![1784974020820](image/README/1784974020820.png)

![1784974097819](image/README/1784974097819.png)

## ✨ 项目亮点

- 🧠 **LLM 行程生成**：基于 LangChain 与 OpenAI-compatible 接口生成结构化旅行计划，Chat、Embedding、Rerank 模型可分别配置
- 📚 **本地攻略 RAG**：覆盖北京、大理、成都、西安、厦门、三亚 6 城；Query Rewrite + 向量召回 + Cross-encoder Rerank，并按 destination metadata 隔离，避免跨城市内容混入
- 🛡️ **不伪造的失败降级**：RAG 候选不足时返回空安排和原因说明，只用攻略上下文中的真实名称，不再用模板化景点/餐饮/住宿填充
- 💬 AI**对话助手**：SSE流式 Chat，携带当前页面与行程只读上下文；模型原生 tool calling 按需调用天气、地图、攻略与联网搜索
- 🧰 **统一工具层 + MCP**：天气、地理编码、POI、路线、本地攻略检索、联网搜索共用同一批实现；既服务 Chat，也可通过 FastMCP 对外暴露
- 🔥 **热门目的地推荐**：首页轮播展示 6 城封面与近几日天气，按出行适宜度排序；点击卡片自动填入规划表单
- 🗺️ **高德地图补全与可视化**：补充地址、经纬度、POI、路线距离/耗时与图片，前端虚线箭头路线 + 打卡标记
- 🌦️ **天气感知**：结果页展示预报，并根据雨天/阴天修正旅行提示；推荐流用固定 adcode 有界并发拉天气
- 🔄 **知识库更新同步**：本地知识库变更可轮询检测并增量入库 / 替换 / 删除，同步清理相关chunk缓存
- ⚡ **Redis 缓存层**：覆盖天气、地图、RAG 检索与 Rerank 结果，Redis 不可用时自动降级
- 📊 **Token 消耗统计**：按 Query Rewrite、Query Embedding、Rerank、Planner 分项统计，接口响应与后端日志同步输出
- 💰 **预算拆分与智能编辑**：费用按交通/住宿/餐饮/门票等拆分；支持自然语言调整某一天行程后自动刷新地图信息
- 🗂️ **历史管理与前端闭环**：保存 / 查看 / 打开 / 删除历史行程；规划页、结果页、历史页覆盖核心业务路径

---

## 🏗️ 技术架构

### 技术栈

- 后端：FastAPI + Pydantic + SQLAlchemy
- LLM / Agent：LangChain（OpenAI-compatible Chat / Embedding / Rerank）
- 向量库：ChromaDB
- 缓存：Redis
- 工具层：统一 Tool Registry + FastMCP
- 外部服务：HTTPX + 高德地图 Web 服务 + 高德 JavaScript API
- 前端：Vue 3 + Vite + Ant Design Vue + TypeScript
- 数据库：SQLite

### 核心架构分层

| 层级        | 关键文件                                                | 职责                                                            |
| :---------- | :------------------------------------------------------ | :-------------------------------------------------------------- |
| 前端        | `frontend/src/views/`、`components/`、`services/` | 规划页、结果页、历史页；地图 / 对话 / 推荐组件与 API 封装       |
| 接口层      | `backend/app/api/routes/`                             | trip、weather、chat、recommendations 路由                       |
| 服务层      | `backend/app/services/`                               | 行程编排、对话、推荐、地图 enrich、天气、缓存、存储             |
| Agent 层    | `backend/app/agents/`                                 | 行程生成 Agent、对话 Agent（tool calling + SSE）、Query Rewrite |
| Tools / MCP | `backend/app/tools/`、`backend/app/mcp/`            | 天气 / 地图 / 攻略 / 联网搜索工具注册与执行；FastMCP 对外暴露   |
| RAG 层      | `backend/app/rag/`                                    | 向量入库、检索、Rerank、知识库同步与校验                        |
| 数据层      | `backend/data/`、SQLite、Redis、ChromaDB              | 本地攻略文档、行程持久化、缓存、向量索引                        |

### 系统数据流

```mermaid
```

数据流路径：前端收集用户输入 → 后端调用 LLM + RAG 生成结构化行程 → 地图 / 天气服务补全展示信息 → 前端展示地图、天气、预算和每日行程；对话助手经统一工具层按需查询天气、地图、攻略与联网结果；用户可保存、编辑与查看历史行程。

### 数据存储与缓存分工

项目中将长期业务数据和短期高频查询结果分开处理：

- **SQLite：负责持久化存储**

  - 实现位置：`backend/app/config.py`、`backend/app/models/db_models.py`、`backend/app/services/storage_service.py`
  - 使用场景：保存用户生成后的完整旅行方案，并支持历史列表、详情查询与删除。
  - 存储方式：通过 SQLAlchemy 定义 `TripRecord` 表，核心字段包括 `trip_id`、`destination`、`summary`、`itinerary_json`、`created_at`、`updated_at`。
  - 设计原因：旅行方案属于用户主动保存的业务数据，需要长期保留、可查询、可删除；当前阶段采用 SQLite 轻量部署，适合个人项目和 Demo 场景。
- **Redis：负责缓存加速**

  - 实现位置：`backend/app/services/cache_service.py`，并被 `weather_service.py`、`map_service.py`、`retriever.py` 复用。
  - 使用场景：缓存天气查询、高德地图地理编码/POI/路线结果、RAG 检索结果和 qwen3-rerank 重排序结果。
  - 存储方式：业务模块生成缓存 key，`cache_service.py` 统一加上 `trip_planner` 前缀，将 Python `dict/list` 序列化为 JSON 字符串写入 Redis，并设置 TTL 自动过期。
  - 设计原因：天气、地图和 RAG/Rerank 结果存在明显重复查询，且在一段时间内相对稳定；使用 Redis 可以减少外部 API 调用和重复检索开销，提升接口响应速度与稳定性。

简言之：**SQLite 存“用户要留下来的行程数据”，Redis 存“短时间内可复用的中间查询结果”。**

### RAG 检索流程

**离线阶段**

```text
本地 Markdown 攻略 → 按标题切块（49 个片段） → text-embedding-v4 转向量 → 写入 ChromaDB
```

这一步只做一次，数据入库后就不再动了。

**在线阶段**

```text
用户输入（目的地 / 偏好 / 节奏 / 备注）
    ↓
① Query Rewrite（LLM-based / 规则 fallback）
    输出：检索关键词，如"大理 美食 拍照 古城 洱海"
    ↓
② Embedding（同一个 text-embedding-v4）
    把检索关键词转向量，才能和 ChromaDB 里的文档向量做相似度计算
    ↓
③ 向量召回（ChromaDB）
    用向量相似度找到 candidate_k 候选片段（candidate_k = max(RAG_TOP_K×2, 6)）
    ↓
④ 噪声预过滤
    去掉"文档开头"等低信息量片段，避免浪费 rerank 的 API 调用
    ↓
⑤ Cross-encoder Rerank（qwen3-rerank / 规则 fallback）
    语义级重排序，选出 RAG_TOP_K 条最相关片段
    ↓
⑥ 写入 Redis 缓存
    RAG 缓存：query → top-k 文本
    Rerank 缓存：query + 候选哈希 → 排序分数
    ↓
⑦ 返回 top-k 文本给 LLM
    和用户信息一起组装成 prompt，调 qwen-max 生成行程
```

---

## 📁 项目结构

```text
AI Agent Travel Assistant/
├── backend/
│   ├── app/
│   │   ├── config.py                    # 环境变量、数据库与全局配置
│   │   ├── agents/
│   │   │   ├── trip_planner_agent.py    # LLM 行程生成
│   │   │   ├── chat_agent.py            # 对话 Agent：tool calling 循环与SSE流式输出
│   │   │   └── tools/
│   │   │       └── rag_tool.py           # 查询改写与检索规则加载
│   │   ├── api/
│   │   │   ├── main.py                   # FastAPI 应用入口
│   │   │   └── routes/
│   │   │       ├── trip.py               # 行程生成、编辑与历史接口
│   │   │       ├── chat.py               # 流式对话接口
│   │   │       ├── recommendations.py    # 热门目的地推荐接口
│   │   │       └── weather.py            # 天气预报接口
│   │   ├── models/
│   │   │   ├── schemas.py                # 行程相关 Pydantic 模型
│   │   │   ├── chat_schemas.py           # 对话请求 / 上下文 / 流式事件模型
│   │   │   └── db_models.py              # SQLAlchemy 数据表定义
│   │   ├── rag/
│   │   │   ├── guide_catalog.py          # 攻略文件与目的地映射
│   │   │   ├── vector_db.py              # 文档切片、Chroma 入库与检索
│   │   │   ├── retriever.py              # 检索、重排序与缓存
│   │   │   ├── document_registry.py      # 知识库文档清单与内容哈希
│   │   │   ├── knowledge_poller.py       # 本地攻略变更检测与增量同步
│   │   │   └── knowledge_validation.py   # 攻略、规则与评估配置一致性校验
│   │   ├── tools/      
│   │   │   ├── base.py                   # ToolResult 统一返回结构
│   │   │   ├── registry.py               # 工具注册表、规格与执行入口
│   │   │   ├── knowledge_tools.py        # 本地攻略检索工具
│   │   │   ├── map_tools.py              # 地理编码 / POI / 路线工具
│   │   │   ├── weather_tools.py          # 天气预报工具
│   │   │   └── web_search_tools.py       # 联网搜索工具
│   │   ├── mcp/
│   │   │   └── server.py                 # FastMCP Server，对外暴露旅行工具
│   │   └── services/
│   │       ├── trip_service.py           # 行程主编排、预算与地图补全
│   │       ├── chat_service.py           # 对话服务编排
│   │       ├── recommendation_service.py # 热门目的地推荐与天气排序
│   │       ├── fallback_candidates.py    # 从攻略上下文提取真实候选
│   │       ├── map_service.py            # 高德 POI、路线与图片
│   │       ├── weather_service.py        # 天气服务
│   │       ├── storage_service.py        # SQLite 行程存储
│   │       └── cache_service.py          # Redis 缓存与降级
│   ├── data/
│   │   ├── *_guide.md                    # 6 个目的地的本地攻略
│   │   └── retrieval_rules.json          # 查询扩展词配置
│   ├── eval/rag_eval_cases.json          # RAG 评估样例集
│   ├── scripts/                          # 入库、同步、调试、评估与校验脚本
│   ├── tests/                            # pytest 测试
│   ├── .env.example                      # 后端环境变量模板
│   └── requirements.txt
├── frontend/
│   ├── public/covers/                    # 热门目的地封面图
│   ├── src/
│   │   ├── views/
│   │   │   ├── Home.vue                   # 规划页：表单 + 热门目的地
│   │   │   ├── Result.vue                 # 结果页：行程 / 地图 / 天气 / 预算
│   │   │   └── History.vue                # 我的行程页
│   │   ├── components/
│   │   │   ├── AmapTripMap.vue            # 高德地图路线与打卡标记
│   │   │   ├── DestinationCarousel.vue   # 热门目的地轮播卡片
│   │   │   ├── FloatingChatAssistant.vue # AI对话助手
│   │   │   └── AppIcon.vue               # 统一图标组件
│   │   ├── services/
│   │   │   ├── api.ts                     # 行程 / 天气 / 推荐接口封装
│   │   │   └── chatApi.ts                 # 流式对话接口封装
│   │   ├── types/
│   │   │   ├── index.ts                   # 行程与推荐相关类型
│   │   │   └── chat.ts                    # 对话消息与上下文类型
│   │   ├── utils/
│   │   │   ├── chatContext.ts             # 页面 / 行程上下文组装
│   │   │   ├── clientCache.ts             # 前端本地缓存
│   │   │   └── markdown.ts                # 对话 Markdown 渲染
│   │   ├── App.vue                        # 页面切换与全局布局
│   │   └── main.ts                        # 前端入口
│   ├── .env.example                      # 前端环境变量模板
│   └── package.json
├── assets/                               # 展示素材与目的地封面源文件
├── docs/                                 # 架构、数据与优化文档（默认 gitignore）
├── README.md
└── CHANGELOG.md
```

> `docs/` 是本地开发与面试准备文档目录，默认已被 `.gitignore` 忽略，不随 GitHub 上传。

---

## 🚀 启动项目

以下命令默认从项目根目录开始执行。需要本机已安装 Python 3.11、Node.js 与 npm。后端和前端请分别在两个终端中启动。

### 1. 配置并启动后端

```powershell
cd backend
Copy-Item .env.example .env
# 编辑 .env，填写 LLM、Embedding 和高德地图等配置
pip install -r requirements.txt
uvicorn app.api.main:app --host 0.0.0.0 --port 8000
```

后端启动后可访问：

```text
API:      http://127.0.0.1:8000
API 文档: http://127.0.0.1:8000/docs
```

首次使用 RAG 时，另开终端执行以下命令将本地攻略写入 Chroma：

```powershell
cd backend
python scripts/ingest_data.py
```

### 2. 配置并启动前端

```powershell
cd frontend
Copy-Item .env.example .env
# 本机运行时，将 VITE_API_BASE_URL 配置为 http://127.0.0.1:8000
# 填写 VITE_AMAP_JS_KEY（高德 JS API Key）
npm install
npm run dev
```

前端地址：`http://127.0.0.1:5173`。

### 3. 可选：开启本地 Redis 缓存

默认 `REDIS_ENABLED=false`，即使未安装 Redis 也可以运行项目。若本机已安装 Redis，可运行 `redis-server`，再将 `backend/.env` 中的 `REDIS_ENABLED` 改为 `true`，以启用天气、地图和检索缓存。

---

## 🔄 关键业务链路

### 显式编排工作流

项目采用显式编排（而非 Agent 自主决策）的方式组织业务流程，每个步骤由 `trip_service.py` 按固定顺序调用，适合当前业务确定性强、步骤可预期的场景。
