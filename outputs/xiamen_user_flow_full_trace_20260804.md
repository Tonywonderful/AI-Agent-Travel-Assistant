# 厦门真实前端用户流全流程跟踪记录（2026-08-04）

> 本记录来自 `http://127.0.0.1:5173/` 的真实前端表单操作和实际 `POST /trip/generate` 生产链路。
> 未调用 `tests/`、`test_*.py`、`outputs/chengdu_user_flow_trace_runner_20260804.py` 或其他测试/诊断 runner。

## 1. 执行结论

- HTTP 结果：`200 OK`，前端成功进入结果页，行程 ID 为 `trip_厦门_2026-08-05`。
- 后端总耗时：`143.564s`。
- 三路检索确实独立条件化：景点路只过滤 `attraction`，住宿路过滤 `hotel + 豪华型预算档次`，餐饮路过滤 `restaurant`。
- 为观察完整召回/重排过程，提交前只失效了 RAG 与 rerank 缓存；实际删除 `rag=15`、`rerank=15`，没有删除知识库或业务数据。
- 景点主路的 Chroma 在 `destination=厦门 + planning + attraction` 硬过滤下返回 0 条，因此真实回退到关键词召回；住宿和餐饮路使用了 Chroma 向量召回。
- 三路随后都成功调用 OpenRouter Cross-encoder 重排，没有命中 rerank 缓存，也没有使用规则重排 fallback。
- Planner 输出经过名称硬校验后拒绝了 `3` 个名称：`中山路步行街、环岛路与黄厝海滩、厦门园林植物园`。
- 地图补全成功，最终预算重算为 `¥10551.88`，处于人均预算 `¥10,000-15,000` 内。

## 2. 执行方式与边界

1. 在真实页面逐项选择/填写截图中的值，然后点击页面上的“开始规划”。
2. 后端仍由正常 FastAPI/uvicorn 应用处理，未替换、未 mock、未 monkeypatch 任何业务函数。
3. 本次仅通过 Python profiling hook 旁路观察指定函数的入参、返回值和局部阶段结果；它不改变控制流与返回值。
4. 原始旁路事件保存在 `outputs/xiamen_user_flow_full_trace_20260804.jsonl`，共 118 个 call/return 事件。

## 3. 第一张图对应输入

| 前端字段 | 实际输入 | 后端值 |
|---|---|---|
| 目的地 | 厦门 | `厦门` |
| 日期 | 2026-08-05 至 2026-08-08 | `4` 天（含首尾） |
| 人数 | 1 | `1` |
| 人均预算 | ¥10,000-¥15,000 | `budget_min_per_person=10000`，`budget_max_per_person=15000` |
| 节奏 | 悠闲放松 | `轻松` |
| 住宿 | 豪华型 | `豪华型` |
| 旅行偏好 | 自然风景、城市漫游、美食探索、轻徒步 | 同左 |
| 饮食偏好 | 无辣、本地特色、海鲜 | 后端数组顺序为 `本地特色、海鲜、无辣`（选择顺序导致，语义不变） |
| 备注 | 希望体验当地文化，偏好地铁出行，减少换乘。 | 同左 |

<details>
<summary>实际进入 generate_trip_itinerary 的完整请求体</summary>

```json
{
  "destination": "厦门",
  "start_date": "2026-08-05",
  "end_date": "2026-08-08",
  "travelers": 1,
  "budget_min_per_person": 10000.0,
  "budget_max_per_person": 15000.0,
  "budget": null,
  "preferences": [
    "自然风景",
    "城市漫游",
    "美食探索",
    "轻徒步"
  ],
  "pace": "轻松",
  "dietary_preferences": [
    "本地特色",
    "海鲜",
    "无辣"
  ],
  "hotel_level": "豪华型",
  "special_notes": "希望体验当地文化，偏好地铁出行，减少换乘。"
}
```

</details>

## 4. 总体时间线

| 阶段 | 耗时 | 结果 |
|---|---:|---|
| Query Rewrite | 19.873s | LLM 改写成功 |
| 三路上下文收集（含 Rewrite） | 37.506s | 5 景点 + 3 酒店 + 8 餐饮 contexts |
| Planner | 105.423s | 结构化 4 天草稿解析成功 |
| 地图补全 | 0.610s | POI/路线补全成功 |
| 预算重算 | 0.822ms | 总计 ¥10551.88 |
| 完整后端请求 | 143.564s | 200 OK |

## 5. Query Rewrite

- 输出 Query：`厦门 环岛路 鼓浪屿 中山路 沙坡尾 曾厝垵 园林植物园 白鹭洲公园 云顶岩 天竺山 南普陀寺 闽南文化 非遗体验 城市漫步 轻徒步 特色小吃 慢游`
- Token：`prompt=228`，`completion=620`。
- 耗时：`19.873s`。
- 清洗结果中仍出现“特色小吃”，说明当前 `_sanitize_activity_query` 只按空格 token 包含词过滤；它没有把“特色小吃”归入餐饮排除词。

## 6. 三路检索

### 主路：景点/活动

| 字段 | 实际值 |
|---|---|
| Query | `厦门 环岛路 鼓浪屿 中山路 沙坡尾 曾厝垵 园林植物园 白鹭洲公园 云顶岩 天竺山 南普陀寺 闽南文化 非遗体验 城市漫步 轻徒步 特色小吃 慢游` |
| top_k | `5` |
| category 硬过滤 | `['attraction']` |
| budget_tier 硬过滤 | `None` |
| Chroma where | `{"$and": [{"destination": "厦门"}, {"retrieval_scope": "planning"}, {"category": "attraction"}]}` |
| 实际召回路径 | Chroma 返回 0 条，随后使用关键词 fallback |
| 原始去重候选数 | `10` |
| 重排路径 | OpenRouter Cross-encoder |
| 重排后数量 | `5` |
| 最终 context 数 | `5` |
| Embedding usage | `{'prompt_tokens': 0, 'completion_tokens': 0}` |
| Rerank usage | `{'prompt_tokens': 1927, 'completion_tokens': 0}` |

<details>
<summary>关键词 fallback 原始候选（10 条）</summary>

```json
[
  {
    "rank": 1,
    "title": "2.11 厦门大学思明校区（校园建筑与人文）",
    "entity_name": "厦门大学思明校区（校园建筑与人文）",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.11 厦门大学思明校区（校园建筑与人文）",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "* **位置**：思明区思明南路422号\n* **门票**：免费，通常需要按校方规定实名预约\n* **游玩时长**：约1.5-2小时\n* **简介**：校园建筑与山海环境结合，可与南普陀寺、沙坡尾组成步行线路。入校政策可能调整，应以校方最新通知为准。"
  },
  {
    "rank": 2,
    "title": "2.1 鼓浪屿风景名胜区",
    "entity_name": "鼓浪屿风景名胜区",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.1 鼓浪屿风景名胜区",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "* **位置**：晃岩路35-6号\n* **门票**：免费（部分景点需购票）\n* **游玩时长**：建议半天至一天\n* **简介**：鼓浪屿是厦门最著名的旅游目的地之一，以其美丽的海滩、欧式建筑以及丰富的历史文化而闻名。岛上禁止机动车行驶，非常适合漫步探索。"
  },
  {
    "rank": 3,
    "title": "2.2 日光岩",
    "entity_name": "日光岩",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.2 日光岩",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "* **位置**：晃岩路66之6-7号\n* **门票**：成人票60元\n* **游玩时长**：约1小时\n* **简介**：日光岩位于鼓浪屿上，是观赏厦门全景的最佳地点之一。登上山顶可以俯瞰整个岛屿及周边海域美景。"
  },
  {
    "rank": 4,
    "title": "2.9 厦门园林植物园（自然生态与摄影）",
    "entity_name": "厦门园林植物园（自然生态与摄影）",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.9 厦门园林植物园（自然生态与摄影）",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "* **位置**：思明区虎园路25号\n* **门票**：成人票约 **30元**，部分优待票约 **15元**；观光车通常另收费约 **10-20元**\n* **游玩时长**：约3-5小时\n* **简介**：热门区域包括雨林世界和多肉植物区。园区面积较大，建议穿防滑舒适的鞋，并提前确认雨林喷雾时间。"
  },
  {
    "rank": 5,
    "title": "2.10 钟鼓索道（城市与山海观景）",
    "entity_name": "钟鼓索道（城市与山海观景）",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.10 钟鼓索道（城市与山海观景）",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "* **位置**：思明区虎园路附近，靠近厦门园林植物园西门\n* **门票**：成人往返票约 **80元**\n* **游玩时长**：约40分钟，排队时间另计\n* **简介**：可从高空观看厦门城市、山海和铁路景观，节假日及日落时段较热门，建议提前预约。"
  },
  {
    "rank": 6,
    "title": "2.12 沙坡尾艺术西区（老港口与文创街区）",
    "entity_name": "沙坡尾艺术西区（老港口与文创街区）",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.12 沙坡尾艺术西区（老港口与文创街区）",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "* **位置**：思明区沙坡尾区域\n* **门票**：街区免费；展览、手作和咖啡消费约 **20-100元/人**\n* **游玩时长**：约2-3小时\n* **简介**：保留老厦门避风坞风貌，同时聚集文创店、咖啡馆和小型展览，适合傍晚散步和拍照。"
  },
  {
    "rank": 7,
    "title": "2.13 环岛路与黄厝海滩（海滨骑行与日出）",
    "entity_name": "环岛路与黄厝海滩（海滨骑行与日出）",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.13 环岛路与黄厝海滩（海滨骑行与日出）",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "* **位置**：厦门岛东南海岸\n* **门票**：公共海滩及道路免费；骑行约 **10-60元/次**\n* **游玩时长**：约2-4小时\n* **简介**：适合骑行、看海和日出。下海前应留意风浪、潮汐和救生提示，不进入未开放海域。"
  },
  {
    "rank": 8,
    "title": "2.15 中山路步行街（骑楼建筑与老字号小吃）",
    "entity_name": "中山路步行街（骑楼建筑与老字号小吃）",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.15 中山路步行街（骑楼建筑与老字号小吃）",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "* **位置**：思明区中山路\n* **门票**：街区免费；小吃消费约 **30-80元/人**\n* **游玩时长**：约2-3小时\n* **简介**：适合体验骑楼建筑和厦门老字号小吃，可与八市、鹭江夜景安排在一起。"
  },
  {
    "rank": 9,
    "title": "2.20 云上厦门观光厅（高空城市观景）",
    "entity_name": "云上厦门观光厅（高空城市观景）",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.20 云上厦门观光厅（高空城市观景）",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "* **位置**：思明区演武西路世茂海峡大厦\n* **门票**：常见成人观光产品约 **160元**，部分夜场或优惠产品约 **88元**\n* **游玩时长**：约1-1.5小时\n* **简介**：适合俯瞰演武大桥、厦门大学和鼓浪屿方向的城市景观，天气通透度会显著影响观景体验。"
  },
  {
    "rank": 10,
    "title": "2.3 南普陀寺",
    "entity_name": "南普陀寺",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.3 南普陀寺",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "* **位置**：思明南路515号\n* **门票**：免费\n* **游玩时长**：约1-2小时\n* **简介**：南普陀寺是一座有着悠久历史的佛教寺庙，以其精美的建筑和宁静的氛围著称。寺内还有许多珍贵文物可供参观。"
  }
]
```

</details>

<details>
<summary>进入重排的去重候选（10 条）</summary>

```json
[
  {
    "rank": 1,
    "title": "2.11 厦门大学思明校区（校园建筑与人文）",
    "entity_name": "厦门大学思明校区（校园建筑与人文）",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.11 厦门大学思明校区（校园建筑与人文）",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "* **位置**：思明区思明南路422号\n* **门票**：免费，通常需要按校方规定实名预约\n* **游玩时长**：约1.5-2小时\n* **简介**：校园建筑与山海环境结合，可与南普陀寺、沙坡尾组成步行线路。入校政策可能调整，应以校方最新通知为准。"
  },
  {
    "rank": 2,
    "title": "2.1 鼓浪屿风景名胜区",
    "entity_name": "鼓浪屿风景名胜区",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.1 鼓浪屿风景名胜区",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "* **位置**：晃岩路35-6号\n* **门票**：免费（部分景点需购票）\n* **游玩时长**：建议半天至一天\n* **简介**：鼓浪屿是厦门最著名的旅游目的地之一，以其美丽的海滩、欧式建筑以及丰富的历史文化而闻名。岛上禁止机动车行驶，非常适合漫步探索。"
  },
  {
    "rank": 3,
    "title": "2.2 日光岩",
    "entity_name": "日光岩",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.2 日光岩",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "* **位置**：晃岩路66之6-7号\n* **门票**：成人票60元\n* **游玩时长**：约1小时\n* **简介**：日光岩位于鼓浪屿上，是观赏厦门全景的最佳地点之一。登上山顶可以俯瞰整个岛屿及周边海域美景。"
  },
  {
    "rank": 4,
    "title": "2.9 厦门园林植物园（自然生态与摄影）",
    "entity_name": "厦门园林植物园（自然生态与摄影）",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.9 厦门园林植物园（自然生态与摄影）",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "* **位置**：思明区虎园路25号\n* **门票**：成人票约 **30元**，部分优待票约 **15元**；观光车通常另收费约 **10-20元**\n* **游玩时长**：约3-5小时\n* **简介**：热门区域包括雨林世界和多肉植物区。园区面积较大，建议穿防滑舒适的鞋，并提前确认雨林喷雾时间。"
  },
  {
    "rank": 5,
    "title": "2.10 钟鼓索道（城市与山海观景）",
    "entity_name": "钟鼓索道（城市与山海观景）",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.10 钟鼓索道（城市与山海观景）",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "* **位置**：思明区虎园路附近，靠近厦门园林植物园西门\n* **门票**：成人往返票约 **80元**\n* **游玩时长**：约40分钟，排队时间另计\n* **简介**：可从高空观看厦门城市、山海和铁路景观，节假日及日落时段较热门，建议提前预约。"
  },
  {
    "rank": 6,
    "title": "2.12 沙坡尾艺术西区（老港口与文创街区）",
    "entity_name": "沙坡尾艺术西区（老港口与文创街区）",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.12 沙坡尾艺术西区（老港口与文创街区）",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "* **位置**：思明区沙坡尾区域\n* **门票**：街区免费；展览、手作和咖啡消费约 **20-100元/人**\n* **游玩时长**：约2-3小时\n* **简介**：保留老厦门避风坞风貌，同时聚集文创店、咖啡馆和小型展览，适合傍晚散步和拍照。"
  },
  {
    "rank": 7,
    "title": "2.13 环岛路与黄厝海滩（海滨骑行与日出）",
    "entity_name": "环岛路与黄厝海滩（海滨骑行与日出）",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.13 环岛路与黄厝海滩（海滨骑行与日出）",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "* **位置**：厦门岛东南海岸\n* **门票**：公共海滩及道路免费；骑行约 **10-60元/次**\n* **游玩时长**：约2-4小时\n* **简介**：适合骑行、看海和日出。下海前应留意风浪、潮汐和救生提示，不进入未开放海域。"
  },
  {
    "rank": 8,
    "title": "2.15 中山路步行街（骑楼建筑与老字号小吃）",
    "entity_name": "中山路步行街（骑楼建筑与老字号小吃）",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.15 中山路步行街（骑楼建筑与老字号小吃）",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "* **位置**：思明区中山路\n* **门票**：街区免费；小吃消费约 **30-80元/人**\n* **游玩时长**：约2-3小时\n* **简介**：适合体验骑楼建筑和厦门老字号小吃，可与八市、鹭江夜景安排在一起。"
  },
  {
    "rank": 9,
    "title": "2.20 云上厦门观光厅（高空城市观景）",
    "entity_name": "云上厦门观光厅（高空城市观景）",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.20 云上厦门观光厅（高空城市观景）",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "* **位置**：思明区演武西路世茂海峡大厦\n* **门票**：常见成人观光产品约 **160元**，部分夜场或优惠产品约 **88元**\n* **游玩时长**：约1-1.5小时\n* **简介**：适合俯瞰演武大桥、厦门大学和鼓浪屿方向的城市景观，天气通透度会显著影响观景体验。"
  },
  {
    "rank": 10,
    "title": "2.3 南普陀寺",
    "entity_name": "南普陀寺",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.3 南普陀寺",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "* **位置**：思明南路515号\n* **门票**：免费\n* **游玩时长**：约1-2小时\n* **简介**：南普陀寺是一座有着悠久历史的佛教寺庙，以其精美的建筑和宁静的氛围著称。寺内还有许多珍贵文物可供参观。"
  }
]
```

</details>

<details>
<summary>重排结果（5 条）</summary>

```json
[
  {
    "rank": 1,
    "title": "2.1 鼓浪屿风景名胜区",
    "entity_name": "鼓浪屿风景名胜区",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.1 鼓浪屿风景名胜区",
    "retrieval_scope": "planning",
    "rerank_score": 0.0066,
    "rerank_reasons": [
      "cross-encoder:0.0066"
    ],
    "text": "* **位置**：晃岩路35-6号\n* **门票**：免费（部分景点需购票）\n* **游玩时长**：建议半天至一天\n* **简介**：鼓浪屿是厦门最著名的旅游目的地之一，以其美丽的海滩、欧式建筑以及丰富的历史文化而闻名。岛上禁止机动车行驶，非常适合漫步探索。"
  },
  {
    "rank": 2,
    "title": "2.13 环岛路与黄厝海滩（海滨骑行与日出）",
    "entity_name": "环岛路与黄厝海滩（海滨骑行与日出）",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.13 环岛路与黄厝海滩（海滨骑行与日出）",
    "retrieval_scope": "planning",
    "rerank_score": 0.0063,
    "rerank_reasons": [
      "cross-encoder:0.0063"
    ],
    "text": "* **位置**：厦门岛东南海岸\n* **门票**：公共海滩及道路免费；骑行约 **10-60元/次**\n* **游玩时长**：约2-4小时\n* **简介**：适合骑行、看海和日出。下海前应留意风浪、潮汐和救生提示，不进入未开放海域。"
  },
  {
    "rank": 3,
    "title": "2.9 厦门园林植物园（自然生态与摄影）",
    "entity_name": "厦门园林植物园（自然生态与摄影）",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.9 厦门园林植物园（自然生态与摄影）",
    "retrieval_scope": "planning",
    "rerank_score": 0.0061,
    "rerank_reasons": [
      "cross-encoder:0.0061"
    ],
    "text": "* **位置**：思明区虎园路25号\n* **门票**：成人票约 **30元**，部分优待票约 **15元**；观光车通常另收费约 **10-20元**\n* **游玩时长**：约3-5小时\n* **简介**：热门区域包括雨林世界和多肉植物区。园区面积较大，建议穿防滑舒适的鞋，并提前确认雨林喷雾时间。"
  },
  {
    "rank": 4,
    "title": "2.15 中山路步行街（骑楼建筑与老字号小吃）",
    "entity_name": "中山路步行街（骑楼建筑与老字号小吃）",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.15 中山路步行街（骑楼建筑与老字号小吃）",
    "retrieval_scope": "planning",
    "rerank_score": 0.0046,
    "rerank_reasons": [
      "cross-encoder:0.0046"
    ],
    "text": "* **位置**：思明区中山路\n* **门票**：街区免费；小吃消费约 **30-80元/人**\n* **游玩时长**：约2-3小时\n* **简介**：适合体验骑楼建筑和厦门老字号小吃，可与八市、鹭江夜景安排在一起。"
  },
  {
    "rank": 5,
    "title": "2.11 厦门大学思明校区（校园建筑与人文）",
    "entity_name": "厦门大学思明校区（校园建筑与人文）",
    "category": "attraction",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "2. 核心景点推荐 (含门票与位置信息)",
    "subsection": "2.11 厦门大学思明校区（校园建筑与人文）",
    "retrieval_scope": "planning",
    "rerank_score": 0.0032,
    "rerank_reasons": [
      "cross-encoder:0.0032"
    ],
    "text": "* **位置**：思明区思明南路422号\n* **门票**：免费，通常需要按校方规定实名预约\n* **游玩时长**：约1.5-2小时\n* **简介**：校园建筑与山海环境结合，可与南普陀寺、沙坡尾组成步行线路。入校政策可能调整，应以校方最新通知为准。"
  }
]
```

</details>

<details>
<summary>最终传给 Planner 的 context（5 条）</summary>

```text
[来源: xiamen_guide.md | 标题: 2.1 鼓浪屿风景名胜区]
* **位置**：晃岩路35-6号
* **门票**：免费（部分景点需购票）
* **游玩时长**：建议半天至一天
* **简介**：鼓浪屿是厦门最著名的旅游目的地之一，以其美丽的海滩、欧式建筑以及丰富的历史文化而闻名。岛上禁止机动车行驶，非常适合漫步探索。

[来源: xiamen_guide.md | 标题: 2.13 环岛路与黄厝海滩（海滨骑行与日出）]
* **位置**：厦门岛东南海岸
* **门票**：公共海滩及道路免费；骑行约 **10-60元/次**
* **游玩时长**：约2-4小时
* **简介**：适合骑行、看海和日出。下海前应留意风浪、潮汐和救生提示，不进入未开放海域。

[来源: xiamen_guide.md | 标题: 2.9 厦门园林植物园（自然生态与摄影）]
* **位置**：思明区虎园路25号
* **门票**：成人票约 **30元**，部分优待票约 **15元**；观光车通常另收费约 **10-20元**
* **游玩时长**：约3-5小时
* **简介**：热门区域包括雨林世界和多肉植物区。园区面积较大，建议穿防滑舒适的鞋，并提前确认雨林喷雾时间。

[来源: xiamen_guide.md | 标题: 2.15 中山路步行街（骑楼建筑与老字号小吃）]
* **位置**：思明区中山路
* **门票**：街区免费；小吃消费约 **30-80元/人**
* **游玩时长**：约2-3小时
* **简介**：适合体验骑楼建筑和厦门老字号小吃，可与八市、鹭江夜景安排在一起。

[来源: xiamen_guide.md | 标题: 2.11 厦门大学思明校区（校园建筑与人文）]
* **位置**：思明区思明南路422号
* **门票**：免费，通常需要按校方规定实名预约
* **游玩时长**：约1.5-2小时
* **简介**：校园建筑与山海环境结合，可与南普陀寺、沙坡尾组成步行线路。入校政策可能调整，应以校方最新通知为准。
```

</details>

### 住宿路

| 字段 | 实际值 |
|---|---|
| Query | `厦门 住宿 酒店 豪华型 人均总预算 10000-15000 元 希望体验当地文化，偏好地铁出行，减少换乘。` |
| top_k | `3` |
| category 硬过滤 | `['hotel']` |
| budget_tier 硬过滤 | `豪华型（500 元/晚以上）` |
| Chroma where | `{"$and": [{"destination": "厦门"}, {"retrieval_scope": "planning"}, {"category": "hotel"}, {"budget_tier": "豪华型（500 元/晚以上）"}]}` |
| 实际召回路径 | Chroma 向量检索 |
| 原始去重候选数 | `6` |
| 重排路径 | OpenRouter Cross-encoder |
| 重排后数量 | `3` |
| 最终 context 数 | `3` |
| Embedding usage | `{'prompt_tokens': 0, 'completion_tokens': 0}` |
| Rerank usage | `{'prompt_tokens': 1012, 'completion_tokens': 0}` |

<details>
<summary>进入重排的去重候选（6 条）</summary>

```json
[
  {
    "rank": 1,
    "title": "厦门W酒店",
    "entity_name": "厦门W酒店",
    "category": "hotel",
    "budget_tier": "豪华型（500 元/晚以上）",
    "source": "xiamen_guide.md",
    "section": "4. 住宿区域建议",
    "subsection": "厦门W酒店",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "- **住宿档次**：豪华型（500 元/晚以上）\n- **参考价格**：约 1000-1800 元/晚\n- **所在区域**：思明区吕岭路1599号\n- **相关描述**：位于思明区吕岭路1599号，靠近岭兜地铁站、宝龙一城和五缘湾片区，设计与夜间休闲特色突出。"
  },
  {
    "rank": 2,
    "title": "厦门安达仕酒店",
    "entity_name": "厦门安达仕酒店",
    "category": "hotel",
    "budget_tier": "豪华型（500 元/晚以上）",
    "source": "xiamen_guide.md",
    "section": "4. 住宿区域建议",
    "subsection": "厦门安达仕酒店",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "- **住宿档次**：豪华型（500 元/晚以上）\n- **参考价格**：约 1200-2000 元/晚\n- **所在区域**：思明区厦门华润中心\n- **相关描述**：位于思明区厦门华润中心，靠近厦门站、万象城和地铁，采用南洋风格设计，适合城市度假、购物和商务出行。"
  },
  {
    "rank": 3,
    "title": "厦门磐基希尔顿酒店",
    "entity_name": "厦门磐基希尔顿酒店",
    "category": "hotel",
    "budget_tier": "豪华型（500 元/晚以上）",
    "source": "xiamen_guide.md",
    "section": "4. 住宿区域建议",
    "subsection": "厦门磐基希尔顿酒店",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "- **住宿档次**：豪华型（500 元/晚以上）\n- **参考价格**：约 600-1000 元/晚\n- **所在区域**：思明区嘉禾路199号\n- **相关描述**：位于思明区嘉禾路199号，处于莲花和磐基商圈，靠近地铁，适合商务、购物和岛内多区域出行。"
  },
  {
    "rank": 4,
    "title": "厦门佳逸酒店，希尔顿格芮精选酒店",
    "entity_name": "厦门佳逸酒店，希尔顿格芮精选酒店",
    "category": "hotel",
    "budget_tier": "豪华型（500 元/晚以上）",
    "source": "xiamen_guide.md",
    "section": "4. 住宿区域建议",
    "subsection": "厦门佳逸酒店，希尔顿格芮精选酒店",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "- **住宿档次**：豪华型（500 元/晚以上）\n- **参考价格**：约 550-1000 元/晚\n- **所在区域**：思明区曾厝垵龙虎山路6-8号\n- **相关描述**：位于思明区曾厝垵龙虎山路6-8号，靠近曾厝垵、环岛路、厦门植物园和厦门大学，设有无边际泳池及亲子房。"
  },
  {
    "rank": 5,
    "title": "厦门康莱德酒店",
    "entity_name": "厦门康莱德酒店",
    "category": "hotel",
    "budget_tier": "豪华型（500 元/晚以上）",
    "source": "xiamen_guide.md",
    "section": "4. 住宿区域建议",
    "subsection": "厦门康莱德酒店",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "- **住宿档次**：豪华型（500 元/晚以上）\n- **参考价格**：约 1400-2500 元/晚\n- **所在区域**：思明区演武西路186号双子塔内\n- **相关描述**：位于思明区演武西路186号双子塔内，靠近沙坡尾、厦门大学和南普陀寺，高层客房可观鼓浪屿及海岸线。"
  },
  {
    "rank": 6,
    "title": "厦门华尔道夫酒店",
    "entity_name": "厦门华尔道夫酒店",
    "category": "hotel",
    "budget_tier": "豪华型（500 元/晚以上）",
    "source": "xiamen_guide.md",
    "section": "4. 住宿区域建议",
    "subsection": "厦门华尔道夫酒店",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "- **住宿档次**：豪华型（500 元/晚以上）\n- **参考价格**：约 1800-3000 元/晚\n- **所在区域**：思明区莲花北路1号磐基·莲花里\n- **相关描述**：位于思明区莲花北路1号磐基·莲花里，毗邻莲花公园，适合高端城市度假、购物和商务行程。"
  }
]
```

</details>

<details>
<summary>重排结果（3 条）</summary>

```json
[
  {
    "rank": 1,
    "title": "厦门安达仕酒店",
    "entity_name": "厦门安达仕酒店",
    "category": "hotel",
    "budget_tier": "豪华型（500 元/晚以上）",
    "source": "xiamen_guide.md",
    "section": "4. 住宿区域建议",
    "subsection": "厦门安达仕酒店",
    "retrieval_scope": "planning",
    "rerank_score": 0.0267,
    "rerank_reasons": [
      "cross-encoder:0.0267"
    ],
    "text": "- **住宿档次**：豪华型（500 元/晚以上）\n- **参考价格**：约 1200-2000 元/晚\n- **所在区域**：思明区厦门华润中心\n- **相关描述**：位于思明区厦门华润中心，靠近厦门站、万象城和地铁，采用南洋风格设计，适合城市度假、购物和商务出行。"
  },
  {
    "rank": 2,
    "title": "厦门磐基希尔顿酒店",
    "entity_name": "厦门磐基希尔顿酒店",
    "category": "hotel",
    "budget_tier": "豪华型（500 元/晚以上）",
    "source": "xiamen_guide.md",
    "section": "4. 住宿区域建议",
    "subsection": "厦门磐基希尔顿酒店",
    "retrieval_scope": "planning",
    "rerank_score": 0.0263,
    "rerank_reasons": [
      "cross-encoder:0.0263"
    ],
    "text": "- **住宿档次**：豪华型（500 元/晚以上）\n- **参考价格**：约 600-1000 元/晚\n- **所在区域**：思明区嘉禾路199号\n- **相关描述**：位于思明区嘉禾路199号，处于莲花和磐基商圈，靠近地铁，适合商务、购物和岛内多区域出行。"
  },
  {
    "rank": 3,
    "title": "厦门W酒店",
    "entity_name": "厦门W酒店",
    "category": "hotel",
    "budget_tier": "豪华型（500 元/晚以上）",
    "source": "xiamen_guide.md",
    "section": "4. 住宿区域建议",
    "subsection": "厦门W酒店",
    "retrieval_scope": "planning",
    "rerank_score": 0.0111,
    "rerank_reasons": [
      "cross-encoder:0.0111"
    ],
    "text": "- **住宿档次**：豪华型（500 元/晚以上）\n- **参考价格**：约 1000-1800 元/晚\n- **所在区域**：思明区吕岭路1599号\n- **相关描述**：位于思明区吕岭路1599号，靠近岭兜地铁站、宝龙一城和五缘湾片区，设计与夜间休闲特色突出。"
  }
]
```

</details>

<details>
<summary>最终传给 Planner 的 context（3 条）</summary>

```text
[来源: xiamen_guide.md | 标题: 厦门安达仕酒店]
- **住宿档次**：豪华型（500 元/晚以上）
- **参考价格**：约 1200-2000 元/晚
- **所在区域**：思明区厦门华润中心
- **相关描述**：位于思明区厦门华润中心，靠近厦门站、万象城和地铁，采用南洋风格设计，适合城市度假、购物和商务出行。

[来源: xiamen_guide.md | 标题: 厦门磐基希尔顿酒店]
- **住宿档次**：豪华型（500 元/晚以上）
- **参考价格**：约 600-1000 元/晚
- **所在区域**：思明区嘉禾路199号
- **相关描述**：位于思明区嘉禾路199号，处于莲花和磐基商圈，靠近地铁，适合商务、购物和岛内多区域出行。

[来源: xiamen_guide.md | 标题: 厦门W酒店]
- **住宿档次**：豪华型（500 元/晚以上）
- **参考价格**：约 1000-1800 元/晚
- **所在区域**：思明区吕岭路1599号
- **相关描述**：位于思明区吕岭路1599号，靠近岭兜地铁站、宝龙一城和五缘湾片区，设计与夜间休闲特色突出。
```

</details>

### 餐饮路

| 字段 | 实际值 |
|---|---|
| Query | `厦门 餐饮 餐厅 本地特色 海鲜 无辣 人均总预算 10000-15000 元` |
| top_k | `8` |
| category 硬过滤 | `['restaurant']` |
| budget_tier 硬过滤 | `None` |
| Chroma where | `{"$and": [{"destination": "厦门"}, {"retrieval_scope": "planning"}, {"category": "restaurant"}]}` |
| 实际召回路径 | Chroma 向量检索 |
| 原始去重候选数 | `5` |
| 重排路径 | OpenRouter Cross-encoder |
| 重排后数量 | `5` |
| 最终 context 数 | `5` |
| Embedding usage | `{'prompt_tokens': 0, 'completion_tokens': 0}` |
| Rerank usage | `{'prompt_tokens': 475, 'completion_tokens': 0}` |

<details>
<summary>进入重排的去重候选（5 条）</summary>

```json
[
  {
    "rank": 1,
    "title": "餐饮：醉壹号海鲜大排档·老厦门特色菜（厦门美食地标店）",
    "entity_name": "醉壹号海鲜大排档·老厦门特色菜（厦门美食地标店）",
    "category": "restaurant",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "3. 特色餐饮与预算参考",
    "subsection": "餐饮：醉壹号海鲜大排档·老厦门特色菜（厦门美食地标店）",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "- **人均预算**：120 元\n- **推荐菜品**：清蒸石斑鱼\n- **相关描述**：适合品尝清蒸石斑鱼。"
  },
  {
    "rank": 2,
    "title": "餐饮：临家闽南菜（环岛路店）",
    "entity_name": "临家闽南菜（环岛路店）",
    "category": "restaurant",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "3. 特色餐饮与预算参考",
    "subsection": "餐饮：临家闽南菜（环岛路店）",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "- **人均预算**：250 元\n- **推荐菜品**：红烧鲍鱼\n- **相关描述**：适合品尝红烧鲍鱼。"
  },
  {
    "rank": 3,
    "title": "餐饮：荣誉·海上江南",
    "entity_name": "荣誉·海上江南",
    "category": "restaurant",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "3. 特色餐饮与预算参考",
    "subsection": "餐饮：荣誉·海上江南",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "- **人均预算**：300 元\n- **推荐菜品**：佛跳墙\n- **相关描述**：适合品尝佛跳墙。"
  },
  {
    "rank": 4,
    "title": "餐饮：阿忠食坊大排档·20年老店（万象城店）",
    "entity_name": "阿忠食坊大排档·20年老店（万象城店）",
    "category": "restaurant",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "3. 特色餐饮与预算参考",
    "subsection": "餐饮：阿忠食坊大排档·20年老店（万象城店）",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "- **人均预算**：80 元\n- **推荐菜品**：椒盐虾蛄\n- **相关描述**：适合品尝椒盐虾蛄。"
  },
  {
    "rank": 5,
    "title": "餐饮：局口拌面（中山路店）",
    "entity_name": "局口拌面（中山路店）",
    "category": "restaurant",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "3. 特色餐饮与预算参考",
    "subsection": "餐饮：局口拌面（中山路店）",
    "retrieval_scope": "planning",
    "rerank_score": null,
    "rerank_reasons": null,
    "text": "- **人均预算**：25 元\n- **推荐菜品**：特色拌面\n- **相关描述**：适合品尝特色拌面。"
  }
]
```

</details>

<details>
<summary>重排结果（5 条）</summary>

```json
[
  {
    "rank": 1,
    "title": "餐饮：醉壹号海鲜大排档·老厦门特色菜（厦门美食地标店）",
    "entity_name": "醉壹号海鲜大排档·老厦门特色菜（厦门美食地标店）",
    "category": "restaurant",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "3. 特色餐饮与预算参考",
    "subsection": "餐饮：醉壹号海鲜大排档·老厦门特色菜（厦门美食地标店）",
    "retrieval_scope": "planning",
    "rerank_score": 0.1274,
    "rerank_reasons": [
      "cross-encoder:0.1274"
    ],
    "text": "- **人均预算**：120 元\n- **推荐菜品**：清蒸石斑鱼\n- **相关描述**：适合品尝清蒸石斑鱼。"
  },
  {
    "rank": 2,
    "title": "餐饮：阿忠食坊大排档·20年老店（万象城店）",
    "entity_name": "阿忠食坊大排档·20年老店（万象城店）",
    "category": "restaurant",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "3. 特色餐饮与预算参考",
    "subsection": "餐饮：阿忠食坊大排档·20年老店（万象城店）",
    "retrieval_scope": "planning",
    "rerank_score": 0.0096,
    "rerank_reasons": [
      "cross-encoder:0.0096"
    ],
    "text": "- **人均预算**：80 元\n- **推荐菜品**：椒盐虾蛄\n- **相关描述**：适合品尝椒盐虾蛄。"
  },
  {
    "rank": 3,
    "title": "餐饮：临家闽南菜（环岛路店）",
    "entity_name": "临家闽南菜（环岛路店）",
    "category": "restaurant",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "3. 特色餐饮与预算参考",
    "subsection": "餐饮：临家闽南菜（环岛路店）",
    "retrieval_scope": "planning",
    "rerank_score": 0.0079,
    "rerank_reasons": [
      "cross-encoder:0.0079"
    ],
    "text": "- **人均预算**：250 元\n- **推荐菜品**：红烧鲍鱼\n- **相关描述**：适合品尝红烧鲍鱼。"
  },
  {
    "rank": 4,
    "title": "餐饮：局口拌面（中山路店）",
    "entity_name": "局口拌面（中山路店）",
    "category": "restaurant",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "3. 特色餐饮与预算参考",
    "subsection": "餐饮：局口拌面（中山路店）",
    "retrieval_scope": "planning",
    "rerank_score": 0.0074,
    "rerank_reasons": [
      "cross-encoder:0.0074"
    ],
    "text": "- **人均预算**：25 元\n- **推荐菜品**：特色拌面\n- **相关描述**：适合品尝特色拌面。"
  },
  {
    "rank": 5,
    "title": "餐饮：荣誉·海上江南",
    "entity_name": "荣誉·海上江南",
    "category": "restaurant",
    "budget_tier": "",
    "source": "xiamen_guide.md",
    "section": "3. 特色餐饮与预算参考",
    "subsection": "餐饮：荣誉·海上江南",
    "retrieval_scope": "planning",
    "rerank_score": 0.0051,
    "rerank_reasons": [
      "cross-encoder:0.0051"
    ],
    "text": "- **人均预算**：300 元\n- **推荐菜品**：佛跳墙\n- **相关描述**：适合品尝佛跳墙。"
  }
]
```

</details>

<details>
<summary>最终传给 Planner 的 context（5 条）</summary>

```text
[来源: xiamen_guide.md | 标题: 餐饮：醉壹号海鲜大排档·老厦门特色菜（厦门美食地标店）]
- **人均预算**：120 元
- **推荐菜品**：清蒸石斑鱼
- **相关描述**：适合品尝清蒸石斑鱼。

[来源: xiamen_guide.md | 标题: 餐饮：阿忠食坊大排档·20年老店（万象城店）]
- **人均预算**：80 元
- **推荐菜品**：椒盐虾蛄
- **相关描述**：适合品尝椒盐虾蛄。

[来源: xiamen_guide.md | 标题: 餐饮：临家闽南菜（环岛路店）]
- **人均预算**：250 元
- **推荐菜品**：红烧鲍鱼
- **相关描述**：适合品尝红烧鲍鱼。

[来源: xiamen_guide.md | 标题: 餐饮：局口拌面（中山路店）]
- **人均预算**：25 元
- **推荐菜品**：特色拌面
- **相关描述**：适合品尝特色拌面。

[来源: xiamen_guide.md | 标题: 餐饮：荣誉·海上江南]
- **人均预算**：300 元
- **推荐菜品**：佛跳墙
- **相关描述**：适合品尝佛跳墙。
```

</details>

## 7. 合并后的 RAG 上下文

- 合并后共 `13` 条，顺序为景点路、住宿路、餐饮路。
- Rewrite token：`{'prompt_tokens': 228, 'completion_tokens': 620}`。
- 三路 Rerank token 合计：`{'prompt_tokens': 3414, 'completion_tokens': 0}`。
- 三路 Embedding token 合计：`{'prompt_tokens': 0, 'completion_tokens': 0}`。Ollama 实际执行了 3 次 2560 维 query embedding，但本地接口不返回官方 token usage，因此统计为 0。

<details>
<summary>合并后的完整 contexts</summary>

```text
[来源: xiamen_guide.md | 标题: 2.1 鼓浪屿风景名胜区]
* **位置**：晃岩路35-6号
* **门票**：免费（部分景点需购票）
* **游玩时长**：建议半天至一天
* **简介**：鼓浪屿是厦门最著名的旅游目的地之一，以其美丽的海滩、欧式建筑以及丰富的历史文化而闻名。岛上禁止机动车行驶，非常适合漫步探索。

[来源: xiamen_guide.md | 标题: 2.13 环岛路与黄厝海滩（海滨骑行与日出）]
* **位置**：厦门岛东南海岸
* **门票**：公共海滩及道路免费；骑行约 **10-60元/次**
* **游玩时长**：约2-4小时
* **简介**：适合骑行、看海和日出。下海前应留意风浪、潮汐和救生提示，不进入未开放海域。

[来源: xiamen_guide.md | 标题: 2.9 厦门园林植物园（自然生态与摄影）]
* **位置**：思明区虎园路25号
* **门票**：成人票约 **30元**，部分优待票约 **15元**；观光车通常另收费约 **10-20元**
* **游玩时长**：约3-5小时
* **简介**：热门区域包括雨林世界和多肉植物区。园区面积较大，建议穿防滑舒适的鞋，并提前确认雨林喷雾时间。

[来源: xiamen_guide.md | 标题: 2.15 中山路步行街（骑楼建筑与老字号小吃）]
* **位置**：思明区中山路
* **门票**：街区免费；小吃消费约 **30-80元/人**
* **游玩时长**：约2-3小时
* **简介**：适合体验骑楼建筑和厦门老字号小吃，可与八市、鹭江夜景安排在一起。

[来源: xiamen_guide.md | 标题: 2.11 厦门大学思明校区（校园建筑与人文）]
* **位置**：思明区思明南路422号
* **门票**：免费，通常需要按校方规定实名预约
* **游玩时长**：约1.5-2小时
* **简介**：校园建筑与山海环境结合，可与南普陀寺、沙坡尾组成步行线路。入校政策可能调整，应以校方最新通知为准。

[来源: xiamen_guide.md | 标题: 厦门安达仕酒店]
- **住宿档次**：豪华型（500 元/晚以上）
- **参考价格**：约 1200-2000 元/晚
- **所在区域**：思明区厦门华润中心
- **相关描述**：位于思明区厦门华润中心，靠近厦门站、万象城和地铁，采用南洋风格设计，适合城市度假、购物和商务出行。

[来源: xiamen_guide.md | 标题: 厦门磐基希尔顿酒店]
- **住宿档次**：豪华型（500 元/晚以上）
- **参考价格**：约 600-1000 元/晚
- **所在区域**：思明区嘉禾路199号
- **相关描述**：位于思明区嘉禾路199号，处于莲花和磐基商圈，靠近地铁，适合商务、购物和岛内多区域出行。

[来源: xiamen_guide.md | 标题: 厦门W酒店]
- **住宿档次**：豪华型（500 元/晚以上）
- **参考价格**：约 1000-1800 元/晚
- **所在区域**：思明区吕岭路1599号
- **相关描述**：位于思明区吕岭路1599号，靠近岭兜地铁站、宝龙一城和五缘湾片区，设计与夜间休闲特色突出。

[来源: xiamen_guide.md | 标题: 餐饮：醉壹号海鲜大排档·老厦门特色菜（厦门美食地标店）]
- **人均预算**：120 元
- **推荐菜品**：清蒸石斑鱼
- **相关描述**：适合品尝清蒸石斑鱼。

[来源: xiamen_guide.md | 标题: 餐饮：阿忠食坊大排档·20年老店（万象城店）]
- **人均预算**：80 元
- **推荐菜品**：椒盐虾蛄
- **相关描述**：适合品尝椒盐虾蛄。

[来源: xiamen_guide.md | 标题: 餐饮：临家闽南菜（环岛路店）]
- **人均预算**：250 元
- **推荐菜品**：红烧鲍鱼
- **相关描述**：适合品尝红烧鲍鱼。

[来源: xiamen_guide.md | 标题: 餐饮：局口拌面（中山路店）]
- **人均预算**：25 元
- **推荐菜品**：特色拌面
- **相关描述**：适合品尝特色拌面。

[来源: xiamen_guide.md | 标题: 餐饮：荣誉·海上江南]
- **人均预算**：300 元
- **推荐菜品**：佛跳墙
- **相关描述**：适合品尝佛跳墙。
```

</details>

## 8. Planner

- 模型：`nemotron-3-ultra-free`（`opencode_zen`）。
- 耗时：`105.423s`。
- Token：`prompt=2856`，`completion=2639`。
- 结构化解析：成功，返回 4 个 day draft。

<details>
<summary>Planner system prompt</summary>

```text
你是一名旅行规划助手。请用中文生成简洁的结构化旅行草稿。需要遵守用户给出的目的地、预算、节奏和本地攻略上下文。你必须只输出一个 JSON 对象，不要输出 Markdown，不要输出解释文字，不要输出代码块。输出内容必须严格符合给定的结构化字段要求。餐饮和住宿必须使用上下文中提供的真实商户名称，禁止使用泛称。如果用户在额外备注里提出了明确诉求，例如看日落、不想早起、少辣、拍照等，你要优先把这些诉求落实到具体某一天的主要景点或当天安排里，而不是只写成泛泛的提示。如果用户明确提到想看日落，请优先把适合看日落的地点安排为某一天的主要景点，或至少让当天主景点与日落安排保持强关联。
```

</details>

<details>
<summary>Planner human prompt（含全部 RAG context 和实体白名单）</summary>

```text

目的地：厦门
出发日期：2026-08-05
结束日期：2026-08-08
天数：4
人数：1
人均预算：10000.0-15000.0 元
总预算范围：10000-15000 元
偏好：自然风景、城市漫游、美食探索、轻徒步
节奏：轻松
饮食偏好：本地特色、海鲜、无辣
酒店档次：豪华型
额外备注：希望体验当地文化，偏好地铁出行，减少换乘。

本地攻略上下文：
[来源: xiamen_guide.md | 标题: 2.1 鼓浪屿风景名胜区]
* **位置**：晃岩路35-6号
* **门票**：免费（部分景点需购票）
* **游玩时长**：建议半天至一天
* **简介**：鼓浪屿是厦门最著名的旅游目的地之一，以其美丽的海滩、欧式建筑以及丰富的历史文化而闻名。岛上禁止机动车行驶，非常适合漫步探索。

[来源: xiamen_guide.md | 标题: 2.13 环岛路与黄厝海滩（海滨骑行与日出）]
* **位置**：厦门岛东南海岸
* **门票**：公共海滩及道路免费；骑行约 **10-60元/次**
* **游玩时长**：约2-4小时
* **简介**：适合骑行、看海和日出。下海前应留意风浪、潮汐和救生提示，不进入未开放海域。

[来源: xiamen_guide.md | 标题: 2.9 厦门园林植物园（自然生态与摄影）]
* **位置**：思明区虎园路25号
* **门票**：成人票约 **30元**，部分优待票约 **15元**；观光车通常另收费约 **10-20元**
* **游玩时长**：约3-5小时
* **简介**：热门区域包括雨林世界和多肉植物区。园区面积较大，建议穿防滑舒适的鞋，并提前确认雨林喷雾时间。

[来源: xiamen_guide.md | 标题: 2.15 中山路步行街（骑楼建筑与老字号小吃）]
* **位置**：思明区中山路
* **门票**：街区免费；小吃消费约 **30-80元/人**
* **游玩时长**：约2-3小时
* **简介**：适合体验骑楼建筑和厦门老字号小吃，可与八市、鹭江夜景安排在一起。

[来源: xiamen_guide.md | 标题: 2.11 厦门大学思明校区（校园建筑与人文）]
* **位置**：思明区思明南路422号
* **门票**：免费，通常需要按校方规定实名预约
* **游玩时长**：约1.5-2小时
* **简介**：校园建筑与山海环境结合，可与南普陀寺、沙坡尾组成步行线路。入校政策可能调整，应以校方最新通知为准。

[来源: xiamen_guide.md | 标题: 厦门安达仕酒店]
- **住宿档次**：豪华型（500 元/晚以上）
- **参考价格**：约 1200-2000 元/晚
- **所在区域**：思明区厦门华润中心
- **相关描述**：位于思明区厦门华润中心，靠近厦门站、万象城和地铁，采用南洋风格设计，适合城市度假、购物和商务出行。

[来源: xiamen_guide.md | 标题: 厦门磐基希尔顿酒店]
- **住宿档次**：豪华型（500 元/晚以上）
- **参考价格**：约 600-1000 元/晚
- **所在区域**：思明区嘉禾路199号
- **相关描述**：位于思明区嘉禾路199号，处于莲花和磐基商圈，靠近地铁，适合商务、购物和岛内多区域出行。

[来源: xiamen_guide.md | 标题: 厦门W酒店]
- **住宿档次**：豪华型（500 元/晚以上）
- **参考价格**：约 1000-1800 元/晚
- **所在区域**：思明区吕岭路1599号
- **相关描述**：位于思明区吕岭路1599号，靠近岭兜地铁站、宝龙一城和五缘湾片区，设计与夜间休闲特色突出。

[来源: xiamen_guide.md | 标题: 餐饮：醉壹号海鲜大排档·老厦门特色菜（厦门美食地标店）]
- **人均预算**：120 元
- **推荐菜品**：清蒸石斑鱼
- **相关描述**：适合品尝清蒸石斑鱼。

[来源: xiamen_guide.md | 标题: 餐饮：阿忠食坊大排档·20年老店（万象城店）]
- **人均预算**：80 元
- **推荐菜品**：椒盐虾蛄
- **相关描述**：适合品尝椒盐虾蛄。

[来源: xiamen_guide.md | 标题: 餐饮：临家闽南菜（环岛路店）]
- **人均预算**：250 元
- **推荐菜品**：红烧鲍鱼
- **相关描述**：适合品尝红烧鲍鱼。

[来源: xiamen_guide.md | 标题: 餐饮：局口拌面（中山路店）]
- **人均预算**：25 元
- **推荐菜品**：特色拌面
- **相关描述**：适合品尝特色拌面。

[来源: xiamen_guide.md | 标题: 餐饮：荣誉·海上江南]
- **人均预算**：300 元
- **推荐菜品**：佛跳墙
- **相关描述**：适合品尝佛跳墙。

可选的真实酒店名称（住宿安排必须从中选择）：
厦门安达仕酒店、厦门磐基希尔顿酒店、厦门W酒店

可选的真实餐厅名称（餐饮建议必须从中选择）：
醉壹号海鲜大排档·老厦门特色菜（厦门美食地标店）、阿忠食坊大排档·20年老店（万象城店）、临家闽南菜（环岛路店）、局口拌面（中山路店）、荣誉·海上江南

要求：
1. 输出一个整体 summary。
2. 输出 4 天的 daily draft。
3. 每天只给一个主要景点、一个餐饮建议和一条当天备注；同时给出符合当天安排的景点时段、餐次和首选交通方式。
4. tips 保持简洁。
5. day_index 必须从 1 到 4。
6. 如果额外备注里有”想看日落””不想早起”这类明确要求，必须在 days 中体现，不要只放到 tips。
7. 如果安排了看日落，当天的 spot_name 应尽量就是适合看日落的地点，或与 daily_note 中的日落安排保持一致，避免”主景点”和”日落地点”完全割裂。
8. 每天的安排要符合”轻松”节奏，避免过满、避免太早出发。
9. meal_name 必须从”可选的真实餐厅名称”列表中选择，不要用泛称。例如用”泸州幺妹私房菜(望花路店)”而不要用”当地私房菜”。
10. 住宿安排必须从”可选的真实酒店名称”列表中选择，严禁使用”舒适型住宿””当地酒店””XX 舒适型住宿 1”等泛称。例如用”北京中关村皇冠假日酒店”而不要用”北京 舒适型住宿 1”。
11. 上下文没有可核验实体的要求必须明确写“暂无可核验候选”，严禁自行补全名称或活动。
12. 只返回 JSON 对象，不要返回任何额外说明，不要使用 ```json 代码块。

JSON 结构示例：
{
  "summary": "整体概述",
  "tips": ["提示1", "提示2"],
  "days": [
    {
      "day_index": 1,
      "theme": "当天主题",
      "spot_name": "主要景点",
      "spot_description": "景点推荐理由",
      "meal_name": "餐饮名称",
      "meal_notes": "餐饮说明",
      "meal_type": "晚餐",
      "spot_start_time": "14:00",
      "spot_end_time": "17:00",
      "transport_mode": "地铁",
      "daily_note": "当天备注"
    }
  ]
}

```

</details>

<details>
<summary>Planner 原始模型输出</summary>

```json
{
  "summary": "4天厦门轻松游，入住厦门安达仕酒店（地铁直达），以地铁为主减少换乘。依次体验中山路骑楼老街、鼓浪屿海岛文化、环岛路海滨骑行、园林植物园自然漫步，搭配本地特色海鲜与闽南菜，预算控制在1-1.5万元。",
  "tips": [
    "提前在官方小程序预约鼓浪屿轮渡及厦门大学入校",
    "植物园建议穿防滑鞋，关注雨林喷雾时间",
    "环岛路骑行可共享单车，注意潮汐与救生提示",
    "餐厅高峰期建议提前排号或预订"
  ],
  "days": [
    {
      "day_index": 1,
      "theme": "城市漫游·骑楼美食",
      "spot_name": "中山路步行街",
      "spot_description": "骑楼建筑群与老字号小吃集中，地铁1号线中山路站直达，适合轻松漫步体验本地文化。",
      "meal_name": "局口拌面（中山路店）",
      "meal_notes": "特色拌面，人均约25元，适合午餐快速品尝地道面食。",
      "meal_type": "午餐",
      "spot_start_time": "10:00",
      "spot_end_time": "13:00",
      "transport_mode": "地铁",
      "daily_note": "入住后步行至中山路，地铁直达，感受骑楼风貌与街头小吃，节奏轻松。"
    },
    {
      "day_index": 2,
      "theme": "海岛文化·鼓浪屿",
      "spot_name": "鼓浪屿风景名胜区",
      "spot_description": "岛上无机动车，欧式建筑与海滩交织，半天可深度漫步，体验厦门最具代表性的历史文化景观。",
      "meal_name": "醉壹号海鲜大排档·老厦门特色菜（厦门美食地标店）",
      "meal_notes": "清蒸石斑鱼为招牌，人均约120元，晚餐享用地道海鲜。",
      "meal_type": "晚餐",
      "spot_start_time": "10:00",
      "spot_end_time": "16:00",
      "transport_mode": "地铁+轮渡",
      "daily_note": "地铁至轮渡码头乘船上岛，全天漫步鼓浪屿，晚餐返回市区品尝海鲜。"
    },
    {
      "day_index": 3,
      "theme": "海滨骑行·环岛路",
      "spot_name": "环岛路与黄厝海滩",
      "spot_description": "厦门最美海岸线，共享单车骑行约2-4小时，海景开阔，适合轻松骑行与拍照。",
      "meal_name": "临家闽南菜（环岛路店）",
      "meal_notes": "红烧鲍鱼等闽南高端菜，人均约250元，午餐享用海景餐厅。",
      "meal_type": "午餐",
      "spot_start_time": "10:00",
      "spot_end_time": "13:00",
      "transport_mode": "地铁",
      "daily_note": "地铁1号线至环岛路站，租借共享单车沿海骑行，午餐在环岛路店用餐。"
    },
    {
      "day_index": 4,
      "theme": "自然生态·植物园",
      "spot_name": "厦门园林植物园",
      "spot_description": "雨林世界、多肉植物区等生态景观丰富，园区面积大，适合轻徒步与摄影，约3-5小时游览。",
      "meal_name": "荣誉·海上江南",
      "meal_notes": "佛跳墙等高端闽南宴席，人均约300元，晚餐作为行程收尾。",
      "meal_type": "晚餐",
      "spot_start_time": "10:00",
      "spot_end_time": "14:00",
      "transport_mode": "地铁+公交",
      "daily_note": "地铁至最近站换乘公交前往植物园，轻松漫步自然，傍晚返回酒店享用告别晚餐。"
    }
  ]
}
```

</details>

<details>
<summary>Planner 解析后的结构化草稿</summary>

```json
{
  "summary": "4天厦门轻松游，入住厦门安达仕酒店（地铁直达），以地铁为主减少换乘。依次体验中山路骑楼老街、鼓浪屿海岛文化、环岛路海滨骑行、园林植物园自然漫步，搭配本地特色海鲜与闽南菜，预算控制在1-1.5万元。",
  "tips": [
    "提前在官方小程序预约鼓浪屿轮渡及厦门大学入校",
    "植物园建议穿防滑鞋，关注雨林喷雾时间",
    "环岛路骑行可共享单车，注意潮汐与救生提示",
    "餐厅高峰期建议提前排号或预订"
  ],
  "days": [
    {
      "day_index": 1,
      "theme": "城市漫游·骑楼美食",
      "spot_name": "中山路步行街",
      "spot_description": "骑楼建筑群与老字号小吃集中，地铁1号线中山路站直达，适合轻松漫步体验本地文化。",
      "meal_name": "局口拌面（中山路店）",
      "meal_notes": "特色拌面，人均约25元，适合午餐快速品尝地道面食。",
      "meal_type": "午餐",
      "spot_start_time": "10:00",
      "spot_end_time": "13:00",
      "transport_mode": "地铁",
      "daily_note": "入住后步行至中山路，地铁直达，感受骑楼风貌与街头小吃，节奏轻松。"
    },
    {
      "day_index": 2,
      "theme": "海岛文化·鼓浪屿",
      "spot_name": "鼓浪屿风景名胜区",
      "spot_description": "岛上无机动车，欧式建筑与海滩交织，半天可深度漫步，体验厦门最具代表性的历史文化景观。",
      "meal_name": "醉壹号海鲜大排档·老厦门特色菜（厦门美食地标店）",
      "meal_notes": "清蒸石斑鱼为招牌，人均约120元，晚餐享用地道海鲜。",
      "meal_type": "晚餐",
      "spot_start_time": "10:00",
      "spot_end_time": "16:00",
      "transport_mode": "地铁+轮渡",
      "daily_note": "地铁至轮渡码头乘船上岛，全天漫步鼓浪屿，晚餐返回市区品尝海鲜。"
    },
    {
      "day_index": 3,
      "theme": "海滨骑行·环岛路",
      "spot_name": "环岛路与黄厝海滩",
      "spot_description": "厦门最美海岸线，共享单车骑行约2-4小时，海景开阔，适合轻松骑行与拍照。",
      "meal_name": "临家闽南菜（环岛路店）",
      "meal_notes": "红烧鲍鱼等闽南高端菜，人均约250元，午餐享用海景餐厅。",
      "meal_type": "午餐",
      "spot_start_time": "10:00",
      "spot_end_time": "13:00",
      "transport_mode": "地铁",
      "daily_note": "地铁1号线至环岛路站，租借共享单车沿海骑行，午餐在环岛路店用餐。"
    },
    {
      "day_index": 4,
      "theme": "自然生态·植物园",
      "spot_name": "厦门园林植物园",
      "spot_description": "雨林世界、多肉植物区等生态景观丰富，园区面积大，适合轻徒步与摄影，约3-5小时游览。",
      "meal_name": "荣誉·海上江南",
      "meal_notes": "佛跳墙等高端闽南宴席，人均约300元，晚餐作为行程收尾。",
      "meal_type": "晚餐",
      "spot_start_time": "10:00",
      "spot_end_time": "14:00",
      "transport_mode": "地铁+公交",
      "daily_note": "地铁至最近站换乘公交前往植物园，轻松漫步自然，傍晚返回酒店享用告别晚餐。"
    }
  ]
}
```

</details>

## 9. Fallback 候选与名称硬校验

<details>
<summary>按 RAG context 提取出的 fallback 候选</summary>

```json
{
  "spots": [
    "鼓浪屿风景名胜区",
    "环岛路与黄厝海滩（海滨骑行与日出）",
    "厦门园林植物园（自然生态与摄影）",
    "中山路步行街（骑楼建筑与老字号小吃）",
    "厦门大学思明校区（校园建筑与人文）"
  ],
  "meals": [
    "醉壹号海鲜大排档·老厦门特色菜（厦门美食地标店）",
    "阿忠食坊大排档·20年老店（万象城店）",
    "临家闽南菜（环岛路店）",
    "局口拌面（中山路店）",
    "荣誉·海上江南"
  ],
  "hotels": [
    "厦门安达仕酒店",
    "厦门磐基希尔顿酒店",
    "厦门W酒店"
  ]
}
```

</details>

<details>
<summary>保留真实 metadata 的酒店候选</summary>

```json
[
  {
    "name": "厦门安达仕酒店",
    "level": "豪华型（500 元/晚以上）",
    "reference_price": "约 1200-2000 元/晚",
    "location": "思明区厦门华润中心",
    "source": "xiamen_guide.md"
  },
  {
    "name": "厦门磐基希尔顿酒店",
    "level": "豪华型（500 元/晚以上）",
    "reference_price": "约 600-1000 元/晚",
    "location": "思明区嘉禾路199号",
    "source": "xiamen_guide.md"
  },
  {
    "name": "厦门W酒店",
    "level": "豪华型（500 元/晚以上）",
    "reference_price": "约 1000-1800 元/晚",
    "location": "思明区吕岭路1599号",
    "source": "xiamen_guide.md"
  }
]
```

</details>

| 类别 | Planner 名称 | 校验结果 |
|---|---|---|
| `spots` | `中山路步行街` | `拒绝` |
| `meals` | `局口拌面（中山路店）` | `通过` |
| `spots` | `鼓浪屿风景名胜区` | `通过` |
| `meals` | `醉壹号海鲜大排档·老厦门特色菜（厦门美食地标店）` | `通过` |
| `spots` | `环岛路与黄厝海滩` | `拒绝` |
| `meals` | `临家闽南菜（环岛路店）` | `通过` |
| `spots` | `厦门园林植物园` | `拒绝` |
| `meals` | `荣誉·海上江南` | `通过` |

最终拒绝列表：`['中山路步行街', '环岛路与黄厝海滩', '厦门园林植物园']`。

<details>
<summary>名称校验及 fallback 后的 raw_days</summary>

```json
[
  {
    "day_index": 1,
    "date": "2026-08-05",
    "theme": "城市漫游·骑楼美食",
    "spot_name": "鼓浪屿风景名胜区",
    "spot_description": "根据本地攻略检索到的景点信息安排。",
    "meal_name": "局口拌面（中山路店）",
    "meal_note": "特色拌面，人均约25元，适合午餐快速品尝地道面食。",
    "meal_type": "午餐",
    "spot_start_time": "10:00",
    "spot_end_time": "13:00",
    "transport_mode": "地铁",
    "daily_note": "入住后步行至中山路，地铁直达，感受骑楼风貌与街头小吃，节奏轻松。",
    "unavailable_notes": [],
    "ticket_cost": 59.0
  },
  {
    "day_index": 2,
    "date": "2026-08-06",
    "theme": "海岛文化·鼓浪屿",
    "spot_name": "鼓浪屿风景名胜区",
    "spot_description": "岛上无机动车，欧式建筑与海滩交织，半天可深度漫步，体验厦门最具代表性的历史文化景观。",
    "meal_name": "醉壹号海鲜大排档·老厦门特色菜（厦门美食地标店）",
    "meal_note": "清蒸石斑鱼为招牌，人均约120元，晚餐享用地道海鲜。",
    "meal_type": "晚餐",
    "spot_start_time": "10:00",
    "spot_end_time": "16:00",
    "transport_mode": "地铁+轮渡",
    "daily_note": "地铁至轮渡码头乘船上岛，全天漫步鼓浪屿，晚餐返回市区品尝海鲜。",
    "unavailable_notes": [],
    "ticket_cost": 59.0
  },
  {
    "day_index": 3,
    "date": "2026-08-07",
    "theme": "海滨骑行·环岛路",
    "spot_name": "厦门园林植物园（自然生态与摄影）",
    "spot_description": "根据本地攻略检索到的景点信息安排。",
    "meal_name": "临家闽南菜（环岛路店）",
    "meal_note": "红烧鲍鱼等闽南高端菜，人均约250元，午餐享用海景餐厅。",
    "meal_type": "午餐",
    "spot_start_time": "10:00",
    "spot_end_time": "13:00",
    "transport_mode": "地铁",
    "daily_note": "地铁1号线至环岛路站，租借共享单车沿海骑行，午餐在环岛路店用餐。",
    "unavailable_notes": [],
    "ticket_cost": 71.0
  },
  {
    "day_index": 4,
    "date": "2026-08-08",
    "theme": "自然生态·植物园",
    "spot_name": "中山路步行街（骑楼建筑与老字号小吃）",
    "spot_description": "根据本地攻略检索到的景点信息安排。",
    "meal_name": "荣誉·海上江南",
    "meal_note": "佛跳墙等高端闽南宴席，人均约300元，晚餐作为行程收尾。",
    "meal_type": "晚餐",
    "spot_start_time": "10:00",
    "spot_end_time": "14:00",
    "transport_mode": "地铁+公交",
    "daily_note": "地铁至最近站换乘公交前往植物园，轻松漫步自然，傍晚返回酒店享用告别晚餐。",
    "unavailable_notes": [],
    "ticket_cost": 71.0
  }
]
```

</details>

## 10. 组装结果（地图补全前）

- 交通起点均为当天酒店 `厦门安达仕酒店`，没有固定“厦门 出发点”。
- 交通方式来自 Planner 或用户地铁偏好，没有固定“打车”。
- 餐次与时间来自 Planner，没有统一固定成“午餐”和“10:00-12:00”。
- 酒店实体保留真实 `level/reference_price/source/location` metadata。

<details>
<summary>组装后的完整 itinerary（地图补全前、预算汇总前）</summary>

```json
{
  "trip_id": "trip_厦门_2026-08-05",
  "destination": "厦门",
  "summary": "4天厦门轻松游，入住厦门安达仕酒店（地铁直达），以地铁为主减少换乘。依次体验中山路骑楼老街、鼓浪屿海岛文化、环岛路海滨骑行、园林植物园自然漫步，搭配本地特色海鲜与闽南菜，预算控制在1-1.5万元。",
  "days": [
    {
      "day_index": 1,
      "date": "2026-08-05",
      "theme": "城市漫游·骑楼美食",
      "spots": [
        {
          "name": "鼓浪屿风景名胜区",
          "start_time": "10:00",
          "end_time": "13:00",
          "description": "根据本地攻略检索到的景点信息安排。",
          "estimated_cost": 59.0,
          "location": "厦门",
          "image_url": null,
          "address": null,
          "latitude": null,
          "longitude": null,
          "poi_id": null
        }
      ],
      "meals": [
        {
          "name": "局口拌面（中山路店）",
          "meal_type": "午餐",
          "estimated_cost": 528.52,
          "notes": "特色拌面，人均约25元，适合午餐快速品尝地道面食。"
        }
      ],
      "hotel": {
        "name": "厦门安达仕酒店",
        "level": "豪华型（500 元/晚以上）",
        "reference_price": "约 1200-2000 元/晚",
        "source": "xiamen_guide.md",
        "estimated_cost": 1377.93,
        "location": "思明区厦门华润中心",
        "address": null,
        "latitude": null,
        "longitude": null
      },
      "transport": [
        {
          "mode": "地铁",
          "from_place": "厦门安达仕酒店",
          "to_place": "鼓浪屿风景名胜区",
          "estimated_cost": 416.62,
          "duration": null,
          "distance_km": null,
          "estimated_minutes": null
        }
      ],
      "notes": [
        "当前旅行节奏：轻松",
        "入住后步行至中山路，地铁直达，感受骑楼风貌与街头小吃，节奏轻松。"
      ]
    },
    {
      "day_index": 2,
      "date": "2026-08-06",
      "theme": "海岛文化·鼓浪屿",
      "spots": [
        {
          "name": "鼓浪屿风景名胜区",
          "start_time": "10:00",
          "end_time": "16:00",
          "description": "岛上无机动车，欧式建筑与海滩交织，半天可深度漫步，体验厦门最具代表性的历史文化景观。",
          "estimated_cost": 59.0,
          "location": "厦门",
          "image_url": null,
          "address": null,
          "latitude": null,
          "longitude": null,
          "poi_id": null
        }
      ],
      "meals": [
        {
          "name": "醉壹号海鲜大排档·老厦门特色菜（厦门美食地标店）",
          "meal_type": "晚餐",
          "estimated_cost": 549.67,
          "notes": "清蒸石斑鱼为招牌，人均约120元，晚餐享用地道海鲜。"
        }
      ],
      "hotel": {
        "name": "厦门安达仕酒店",
        "level": "豪华型（500 元/晚以上）",
        "reference_price": "约 1200-2000 元/晚",
        "source": "xiamen_guide.md",
        "estimated_cost": 1446.82,
        "location": "思明区厦门华润中心",
        "address": null,
        "latitude": null,
        "longitude": null
      },
      "transport": [
        {
          "mode": "地铁+轮渡",
          "from_place": "厦门安达仕酒店",
          "to_place": "鼓浪屿风景名胜区",
          "estimated_cost": 368.26,
          "duration": null,
          "distance_km": null,
          "estimated_minutes": null
        }
      ],
      "notes": [
        "当前旅行节奏：轻松",
        "地铁至轮渡码头乘船上岛，全天漫步鼓浪屿，晚餐返回市区品尝海鲜。"
      ]
    },
    {
      "day_index": 3,
      "date": "2026-08-07",
      "theme": "海滨骑行·环岛路",
      "spots": [
        {
          "name": "厦门园林植物园（自然生态与摄影）",
          "start_time": "10:00",
          "end_time": "13:00",
          "description": "根据本地攻略检索到的景点信息安排。",
          "estimated_cost": 71.0,
          "location": "厦门",
          "image_url": null,
          "address": null,
          "latitude": null,
          "longitude": null,
          "poi_id": null
        }
      ],
      "meals": [
        {
          "name": "临家闽南菜（环岛路店）",
          "meal_type": "午餐",
          "estimated_cost": 613.09,
          "notes": "红烧鲍鱼等闽南高端菜，人均约250元，午餐享用海景餐厅。"
        }
      ],
      "hotel": {
        "name": "厦门安达仕酒店",
        "level": "豪华型（500 元/晚以上）",
        "reference_price": "约 1200-2000 元/晚",
        "source": "xiamen_guide.md",
        "estimated_cost": 1625.96,
        "location": "思明区厦门华润中心",
        "address": null,
        "latitude": null,
        "longitude": null
      },
      "transport": [
        {
          "mode": "地铁",
          "from_place": "厦门安达仕酒店",
          "to_place": "厦门园林植物园（自然生态与摄影）",
          "estimated_cost": 379.42,
          "duration": null,
          "distance_km": null,
          "estimated_minutes": null
        }
      ],
      "notes": [
        "当前旅行节奏：轻松",
        "地铁1号线至环岛路站，租借共享单车沿海骑行，午餐在环岛路店用餐。"
      ]
    },
    {
      "day_index": 4,
      "date": "2026-08-08",
      "theme": "自然生态·植物园",
      "spots": [
        {
          "name": "中山路步行街（骑楼建筑与老字号小吃）",
          "start_time": "10:00",
          "end_time": "14:00",
          "description": "根据本地攻略检索到的景点信息安排。",
          "estimated_cost": 71.0,
          "location": "厦门",
          "image_url": null,
          "address": null,
          "latitude": null,
          "longitude": null,
          "poi_id": null
        }
      ],
      "meals": [
        {
          "name": "荣誉·海上江南",
          "meal_type": "晚餐",
          "estimated_cost": 528.52,
          "notes": "佛跳墙等高端闽南宴席，人均约300元，晚餐作为行程收尾。"
        }
      ],
      "hotel": {
        "name": "厦门安达仕酒店",
        "level": "豪华型（500 元/晚以上）",
        "reference_price": "约 1200-2000 元/晚",
        "source": "xiamen_guide.md",
        "estimated_cost": 1805.09,
        "location": "思明区厦门华润中心",
        "address": null,
        "latitude": null,
        "longitude": null
      },
      "transport": [
        {
          "mode": "地铁+公交",
          "from_place": "厦门安达仕酒店",
          "to_place": "中山路步行街（骑楼建筑与老字号小吃）",
          "estimated_cost": 450.1,
          "duration": null,
          "distance_km": null,
          "estimated_minutes": null
        }
      ],
      "notes": [
        "当前旅行节奏：轻松",
        "地铁至最近站换乘公交前往植物园，轻松漫步自然，傍晚返回酒店享用告别晚餐。"
      ]
    }
  ],
  "estimated_budget": 0.0,
  "budget_breakdown": {
    "transport": 0.0,
    "hotel": 0.0,
    "meals": 0.0,
    "tickets": 0.0,
    "other": 0.0,
    "total": 0.0
  },
  "tips": [
    "提前在官方小程序预约鼓浪屿轮渡及厦门大学入校",
    "植物园建议穿防滑鞋，关注雨林喷雾时间",
    "环岛路骑行可共享单车，注意潮汐与救生提示",
    "餐厅高峰期建议提前排号或预订",
    "如计划骑行，请以当地实时路况和可通行区域为准。"
  ],
  "source_notes": [
    "Itinerary is assembled by trip_service.py and can optionally use LangChain structured output.",
    "[来源: xiamen_guide.md | 标题: 2.1 鼓浪屿风景名胜区]\n* **位置**：晃岩路35-6号\n* **门票**：免费（部分景点需购票）\n* **游玩时长**：建议半天至一天\n* **简介**：鼓浪屿是厦门最著名的旅游目的地之一，以其美丽的海滩、欧式建筑以及丰富的历史文化而闻名。岛上禁止机动车行驶，非常适合漫步探索。",
    "[来源: xiamen_guide.md | 标题: 2.13 环岛路与黄厝海滩（海滨骑行与日出）]\n* **位置**：厦门岛东南海岸\n* **门票**：公共海滩及道路免费；骑行约 **10-60元/次**\n* **游玩时长**：约2-4小时\n* **简介**：适合骑行、看海和日出。下海前应留意风浪、潮汐和救生提示，不进入未开放海域。",
    "已过滤 3 个无法在本地攻略中核验的名称，相应位置改用攻略中的真实条目或留空。"
  ],
  "token_usage": {
    "rewrite_prompt_tokens": 228,
    "rewrite_completion_tokens": 620,
    "embedding_prompt_tokens": 0,
    "embedding_completion_tokens": 0,
    "planner_prompt_tokens": 2856,
    "planner_completion_tokens": 2639,
    "rerank_prompt_tokens": 3414,
    "rerank_completion_tokens": 0
  }
}
```

</details>

## 11. 地图补全

| 类型 | 输入 A | 输入 B | 缓存 | 输出 A | 输出 B |
|---|---|---|---|---|---|
| POI | `鼓浪屿风景名胜区` | `厦门` | 命中 | `鼓浪屿风景名胜区` | `晃岩路35-6号` |
| POI | `厦门安达仕酒店` | `厦门` | 命中 | `厦门安达仕酒店` | `湖滨东路101号(湖滨东路地铁站2号口步行320米)` |
| POI | `厦门安达仕酒店` | `厦门` | 命中 | `厦门安达仕酒店` | `湖滨东路101号(湖滨东路地铁站2号口步行320米)` |
| POI | `鼓浪屿风景名胜区` | `厦门` | 命中 | `鼓浪屿风景名胜区` | `晃岩路35-6号` |
| POI | `鼓浪屿风景名胜区` | `厦门` | 命中 | `鼓浪屿风景名胜区` | `晃岩路35-6号` |
| POI | `厦门安达仕酒店` | `厦门` | 命中 | `厦门安达仕酒店` | `湖滨东路101号(湖滨东路地铁站2号口步行320米)` |
| POI | `厦门安达仕酒店` | `厦门` | 命中 | `厦门安达仕酒店` | `湖滨东路101号(湖滨东路地铁站2号口步行320米)` |
| POI | `鼓浪屿风景名胜区` | `厦门` | 命中 | `鼓浪屿风景名胜区` | `晃岩路35-6号` |
| POI | `厦门园林植物园（自然生态与摄影）` | `厦门` | 未命中 | `厦门园林植物园` | `虎园路25号` |
| POI | `厦门安达仕酒店` | `厦门` | 命中 | `厦门安达仕酒店` | `湖滨东路101号(湖滨东路地铁站2号口步行320米)` |
| POI | `厦门安达仕酒店` | `厦门` | 命中 | `厦门安达仕酒店` | `湖滨东路101号(湖滨东路地铁站2号口步行320米)` |
| POI | `厦门园林植物园（自然生态与摄影）` | `厦门` | 命中 | `厦门园林植物园` | `虎园路25号` |
| POI | `中山路步行街（骑楼建筑与老字号小吃）` | `厦门` | 命中 | `中山路小吃街` | `中山路步行街62号` |
| POI | `厦门安达仕酒店` | `厦门` | 命中 | `厦门安达仕酒店` | `湖滨东路101号(湖滨东路地铁站2号口步行320米)` |
| POI | `厦门安达仕酒店` | `厦门` | 命中 | `厦门安达仕酒店` | `湖滨东路101号(湖滨东路地铁站2号口步行320米)` |
| POI | `中山路步行街（骑楼建筑与老字号小吃）` | `厦门` | 命中 | `中山路小吃街` | `中山路步行街62号` |
| 路线 | `118.110267,24.471337` | `118.06702,24.444695` | 命中 | `10.55` | `70` |
| 路线 | `118.110267,24.471337` | `118.06702,24.444695` | 命中 | `10.55` | `70` |
| 路线 | `118.110267,24.471337` | `118.109277,24.447728` | 未命中 | `7.55` | `22` |
| 路线 | `118.110267,24.471337` | `118.079259,24.455453` | 未命中 | `4.43` | `20` |

<details>
<summary>地图补全后的完整 itinerary</summary>

```json
{
  "trip_id": "trip_厦门_2026-08-05",
  "destination": "厦门",
  "summary": "4天厦门轻松游，入住厦门安达仕酒店（地铁直达），以地铁为主减少换乘。依次体验中山路骑楼老街、鼓浪屿海岛文化、环岛路海滨骑行、园林植物园自然漫步，搭配本地特色海鲜与闽南菜，预算控制在1-1.5万元。",
  "days": [
    {
      "day_index": 1,
      "date": "2026-08-05",
      "theme": "城市漫游·骑楼美食",
      "spots": [
        {
          "name": "鼓浪屿风景名胜区",
          "start_time": "10:00",
          "end_time": "13:00",
          "description": "根据本地攻略检索到的景点信息安排。",
          "estimated_cost": 59.0,
          "location": "厦门",
          "image_url": "http://store.is.autonavi.com/showpic/05b0e6e576cf50058e6e2fad7e7dacdc",
          "address": "晃岩路35-6号",
          "latitude": 24.444695,
          "longitude": 118.06702,
          "poi_id": "B025003YN2"
        }
      ],
      "meals": [
        {
          "name": "局口拌面（中山路店）",
          "meal_type": "午餐",
          "estimated_cost": 528.52,
          "notes": "特色拌面，人均约25元，适合午餐快速品尝地道面食。"
        }
      ],
      "hotel": {
        "name": "厦门安达仕酒店",
        "level": "豪华型（500 元/晚以上）",
        "reference_price": "约 1200-2000 元/晚",
        "source": "xiamen_guide.md",
        "estimated_cost": 1377.93,
        "location": "思明区厦门华润中心",
        "address": "湖滨东路101号(湖滨东路地铁站2号口步行320米)",
        "latitude": 24.471337,
        "longitude": 118.110267
      },
      "transport": [
        {
          "mode": "地铁",
          "from_place": "厦门安达仕酒店",
          "to_place": "鼓浪屿风景名胜区",
          "estimated_cost": 416.62,
          "duration": "70 分钟",
          "distance_km": 10.55,
          "estimated_minutes": 70
        }
      ],
      "notes": [
        "当前旅行节奏：轻松",
        "入住后步行至中山路，地铁直达，感受骑楼风貌与街头小吃，节奏轻松。"
      ]
    },
    {
      "day_index": 2,
      "date": "2026-08-06",
      "theme": "海岛文化·鼓浪屿",
      "spots": [
        {
          "name": "鼓浪屿风景名胜区",
          "start_time": "10:00",
          "end_time": "16:00",
          "description": "岛上无机动车，欧式建筑与海滩交织，半天可深度漫步，体验厦门最具代表性的历史文化景观。",
          "estimated_cost": 59.0,
          "location": "厦门",
          "image_url": "http://store.is.autonavi.com/showpic/05b0e6e576cf50058e6e2fad7e7dacdc",
          "address": "晃岩路35-6号",
          "latitude": 24.444695,
          "longitude": 118.06702,
          "poi_id": "B025003YN2"
        }
      ],
      "meals": [
        {
          "name": "醉壹号海鲜大排档·老厦门特色菜（厦门美食地标店）",
          "meal_type": "晚餐",
          "estimated_cost": 549.67,
          "notes": "清蒸石斑鱼为招牌，人均约120元，晚餐享用地道海鲜。"
        }
      ],
      "hotel": {
        "name": "厦门安达仕酒店",
        "level": "豪华型（500 元/晚以上）",
        "reference_price": "约 1200-2000 元/晚",
        "source": "xiamen_guide.md",
        "estimated_cost": 1446.82,
        "location": "思明区厦门华润中心",
        "address": "湖滨东路101号(湖滨东路地铁站2号口步行320米)",
        "latitude": 24.471337,
        "longitude": 118.110267
      },
      "transport": [
        {
          "mode": "地铁+轮渡",
          "from_place": "厦门安达仕酒店",
          "to_place": "鼓浪屿风景名胜区",
          "estimated_cost": 368.26,
          "duration": "70 分钟",
          "distance_km": 10.55,
          "estimated_minutes": 70
        }
      ],
      "notes": [
        "当前旅行节奏：轻松",
        "地铁至轮渡码头乘船上岛，全天漫步鼓浪屿，晚餐返回市区品尝海鲜。"
      ]
    },
    {
      "day_index": 3,
      "date": "2026-08-07",
      "theme": "海滨骑行·环岛路",
      "spots": [
        {
          "name": "厦门园林植物园（自然生态与摄影）",
          "start_time": "10:00",
          "end_time": "13:00",
          "description": "根据本地攻略检索到的景点信息安排。",
          "estimated_cost": 71.0,
          "location": "厦门",
          "image_url": "http://store.is.autonavi.com/showpic/a63581fcb3adda672d35f22d835504a4",
          "address": "虎园路25号",
          "latitude": 24.447728,
          "longitude": 118.109277,
          "poi_id": "B025003OPX"
        }
      ],
      "meals": [
        {
          "name": "临家闽南菜（环岛路店）",
          "meal_type": "午餐",
          "estimated_cost": 613.09,
          "notes": "红烧鲍鱼等闽南高端菜，人均约250元，午餐享用海景餐厅。"
        }
      ],
      "hotel": {
        "name": "厦门安达仕酒店",
        "level": "豪华型（500 元/晚以上）",
        "reference_price": "约 1200-2000 元/晚",
        "source": "xiamen_guide.md",
        "estimated_cost": 1625.96,
        "location": "思明区厦门华润中心",
        "address": "湖滨东路101号(湖滨东路地铁站2号口步行320米)",
        "latitude": 24.471337,
        "longitude": 118.110267
      },
      "transport": [
        {
          "mode": "地铁",
          "from_place": "厦门安达仕酒店",
          "to_place": "厦门园林植物园（自然生态与摄影）",
          "estimated_cost": 379.42,
          "duration": "22 分钟",
          "distance_km": 7.55,
          "estimated_minutes": 22
        }
      ],
      "notes": [
        "当前旅行节奏：轻松",
        "地铁1号线至环岛路站，租借共享单车沿海骑行，午餐在环岛路店用餐。"
      ]
    },
    {
      "day_index": 4,
      "date": "2026-08-08",
      "theme": "自然生态·植物园",
      "spots": [
        {
          "name": "中山路步行街（骑楼建筑与老字号小吃）",
          "start_time": "10:00",
          "end_time": "14:00",
          "description": "根据本地攻略检索到的景点信息安排。",
          "estimated_cost": 71.0,
          "location": "厦门",
          "image_url": "http://store.is.autonavi.com/showpic/654bdaaa16ffeee0a8df58c6edd5864a",
          "address": "中山路56号",
          "latitude": 24.455453,
          "longitude": 118.079259,
          "poi_id": "B025003IUP"
        }
      ],
      "meals": [
        {
          "name": "荣誉·海上江南",
          "meal_type": "晚餐",
          "estimated_cost": 528.52,
          "notes": "佛跳墙等高端闽南宴席，人均约300元，晚餐作为行程收尾。"
        }
      ],
      "hotel": {
        "name": "厦门安达仕酒店",
        "level": "豪华型（500 元/晚以上）",
        "reference_price": "约 1200-2000 元/晚",
        "source": "xiamen_guide.md",
        "estimated_cost": 1805.09,
        "location": "思明区厦门华润中心",
        "address": "湖滨东路101号(湖滨东路地铁站2号口步行320米)",
        "latitude": 24.471337,
        "longitude": 118.110267
      },
      "transport": [
        {
          "mode": "地铁+公交",
          "from_place": "厦门安达仕酒店",
          "to_place": "中山路步行街（骑楼建筑与老字号小吃）",
          "estimated_cost": 450.1,
          "duration": "20 分钟",
          "distance_km": 4.43,
          "estimated_minutes": 20
        }
      ],
      "notes": [
        "当前旅行节奏：轻松",
        "地铁至最近站换乘公交前往植物园，轻松漫步自然，傍晚返回酒店享用告别晚餐。"
      ]
    }
  ],
  "estimated_budget": 0.0,
  "budget_breakdown": {
    "transport": 0.0,
    "hotel": 0.0,
    "meals": 0.0,
    "tickets": 0.0,
    "other": 0.0,
    "total": 0.0
  },
  "tips": [
    "提前在官方小程序预约鼓浪屿轮渡及厦门大学入校",
    "植物园建议穿防滑鞋，关注雨林喷雾时间",
    "环岛路骑行可共享单车，注意潮汐与救生提示",
    "餐厅高峰期建议提前排号或预订",
    "如计划骑行，请以当地实时路况和可通行区域为准。"
  ],
  "source_notes": [
    "Itinerary is assembled by trip_service.py and can optionally use LangChain structured output.",
    "[来源: xiamen_guide.md | 标题: 2.1 鼓浪屿风景名胜区]\n* **位置**：晃岩路35-6号\n* **门票**：免费（部分景点需购票）\n* **游玩时长**：建议半天至一天\n* **简介**：鼓浪屿是厦门最著名的旅游目的地之一，以其美丽的海滩、欧式建筑以及丰富的历史文化而闻名。岛上禁止机动车行驶，非常适合漫步探索。",
    "[来源: xiamen_guide.md | 标题: 2.13 环岛路与黄厝海滩（海滨骑行与日出）]\n* **位置**：厦门岛东南海岸\n* **门票**：公共海滩及道路免费；骑行约 **10-60元/次**\n* **游玩时长**：约2-4小时\n* **简介**：适合骑行、看海和日出。下海前应留意风浪、潮汐和救生提示，不进入未开放海域。",
    "已过滤 3 个无法在本地攻略中核验的名称，相应位置改用攻略中的真实条目或留空。",
    "已补充高德地图地址、坐标或路线估算信息。"
  ],
  "token_usage": {
    "rewrite_prompt_tokens": 228,
    "rewrite_completion_tokens": 620,
    "embedding_prompt_tokens": 0,
    "embedding_completion_tokens": 0,
    "planner_prompt_tokens": 2856,
    "planner_completion_tokens": 2639,
    "rerank_prompt_tokens": 3414,
    "rerank_completion_tokens": 0
  }
}
```

</details>

## 12. 预算重算

| 项目 | 金额（元） |
|---|---:|
| 交通 | 16.28 |
| 酒店 | 6255.80 |
| 餐饮 | 2219.80 |
| 门票 | 260.00 |
| 其他 | 1800.00 |
| 总计 | **10551.88** |

<details>
<summary>预算重算阶段局部输出</summary>

```json
{
  "transport_total": 16.28,
  "hotel_total": 6255.8,
  "meal_total": 2219.8,
  "ticket_total": 260.0,
  "subtotal": 8751.880000000001,
  "other_total": 1800.0,
  "total": 10551.88,
  "itinerary": {
    "trip_id": "trip_厦门_2026-08-05",
    "destination": "厦门",
    "summary": "4天厦门轻松游，入住厦门安达仕酒店（地铁直达），以地铁为主减少换乘。依次体验中山路骑楼老街、鼓浪屿海岛文化、环岛路海滨骑行、园林植物园自然漫步，搭配本地特色海鲜与闽南菜，预算控制在1-1.5万元。",
    "days": [
      {
        "day_index": 1,
        "date": "2026-08-05",
        "theme": "城市漫游·骑楼美食",
        "spots": [
          {
            "name": "鼓浪屿风景名胜区",
            "start_time": "10:00",
            "end_time": "13:00",
            "description": "根据本地攻略检索到的景点信息安排。",
            "estimated_cost": 59.0,
            "location": "厦门",
            "image_url": "http://store.is.autonavi.com/showpic/05b0e6e576cf50058e6e2fad7e7dacdc",
            "address": "晃岩路35-6号",
            "latitude": 24.444695,
            "longitude": 118.06702,
            "poi_id": "B025003YN2"
          }
        ],
        "meals": [
          {
            "name": "局口拌面（中山路店）",
            "meal_type": "午餐",
            "estimated_cost": 528.52,
            "notes": "特色拌面，人均约25元，适合午餐快速品尝地道面食。"
          }
        ],
        "hotel": {
          "name": "厦门安达仕酒店",
          "level": "豪华型（500 元/晚以上）",
          "reference_price": "约 1200-2000 元/晚",
          "source": "xiamen_guide.md",
          "estimated_cost": 1377.93,
          "location": "思明区厦门华润中心",
          "address": "湖滨东路101号(湖滨东路地铁站2号口步行320米)",
          "latitude": 24.471337,
          "longitude": 118.110267
        },
        "transport": [
          {
            "mode": "地铁",
            "from_place": "厦门安达仕酒店",
            "to_place": "鼓浪屿风景名胜区",
            "estimated_cost": 4.64,
            "duration": "70 分钟",
            "distance_km": 10.55,
            "estimated_minutes": 70
          }
        ],
        "notes": [
          "当前旅行节奏：轻松",
          "入住后步行至中山路，地铁直达，感受骑楼风貌与街头小吃，节奏轻松。"
        ]
      },
      {
        "day_index": 2,
        "date": "2026-08-06",
        "theme": "海岛文化·鼓浪屿",
        "spots": [
          {
            "name": "鼓浪屿风景名胜区",
            "start_time": "10:00",
            "end_time": "16:00",
            "description": "岛上无机动车，欧式建筑与海滩交织，半天可深度漫步，体验厦门最具代表性的历史文化景观。",
            "estimated_cost": 59.0,
            "location": "厦门",
            "image_url": "http://store.is.autonavi.com/showpic/05b0e6e576cf50058e6e2fad7e7dacdc",
            "address": "晃岩路35-6号",
            "latitude": 24.444695,
            "longitude": 118.06702,
            "poi_id": "B025003YN2"
          }
        ],
        "meals": [
          {
            "name": "醉壹号海鲜大排档·老厦门特色菜（厦门美食地标店）",
            "meal_type": "晚餐",
            "estimated_cost": 549.67,
            "notes": "清蒸石斑鱼为招牌，人均约120元，晚餐享用地道海鲜。"
          }
        ],
        "hotel": {
          "name": "厦门安达仕酒店",
          "level": "豪华型（500 元/晚以上）",
          "reference_price": "约 1200-2000 元/晚",
          "source": "xiamen_guide.md",
          "estimated_cost": 1446.82,
          "location": "思明区厦门华润中心",
          "address": "湖滨东路101号(湖滨东路地铁站2号口步行320米)",
          "latitude": 24.471337,
          "longitude": 118.110267
        },
        "transport": [
          {
            "mode": "地铁+轮渡",
            "from_place": "厦门安达仕酒店",
            "to_place": "鼓浪屿风景名胜区",
            "estimated_cost": 4.64,
            "duration": "70 分钟",
            "distance_km": 10.55,
            "estimated_minutes": 70
          }
        ],
        "notes": [
          "当前旅行节奏：轻松",
          "地铁至轮渡码头乘船上岛，全天漫步鼓浪屿，晚餐返回市区品尝海鲜。"
        ]
      },
      {
        "day_index": 3,
        "date": "2026-08-07",
        "theme": "海滨骑行·环岛路",
        "spots": [
          {
            "name": "厦门园林植物园（自然生态与摄影）",
            "start_time": "10:00",
            "end_time": "13:00",
            "description": "根据本地攻略检索到的景点信息安排。",
            "estimated_cost": 71.0,
            "location": "厦门",
            "image_url": "http://store.is.autonavi.com/showpic/a63581fcb3adda672d35f22d835504a4",
            "address": "虎园路25号",
            "latitude": 24.447728,
            "longitude": 118.109277,
            "poi_id": "B025003OPX"
          }
        ],
        "meals": [
          {
            "name": "临家闽南菜（环岛路店）",
            "meal_type": "午餐",
            "estimated_cost": 613.09,
            "notes": "红烧鲍鱼等闽南高端菜，人均约250元，午餐享用海景餐厅。"
          }
        ],
        "hotel": {
          "name": "厦门安达仕酒店",
          "level": "豪华型（500 元/晚以上）",
          "reference_price": "约 1200-2000 元/晚",
          "source": "xiamen_guide.md",
          "estimated_cost": 1625.96,
          "location": "思明区厦门华润中心",
          "address": "湖滨东路101号(湖滨东路地铁站2号口步行320米)",
          "latitude": 24.471337,
          "longitude": 118.110267
        },
        "transport": [
          {
            "mode": "地铁",
            "from_place": "厦门安达仕酒店",
            "to_place": "厦门园林植物园（自然生态与摄影）",
            "estimated_cost": 3.89,
            "duration": "22 分钟",
            "distance_km": 7.55,
            "estimated_minutes": 22
          }
        ],
        "notes": [
          "当前旅行节奏：轻松",
          "地铁1号线至环岛路站，租借共享单车沿海骑行，午餐在环岛路店用餐。"
        ]
      },
      {
        "day_index": 4,
        "date": "2026-08-08",
        "theme": "自然生态·植物园",
        "spots": [
          {
            "name": "中山路步行街（骑楼建筑与老字号小吃）",
            "start_time": "10:00",
            "end_time": "14:00",
            "description": "根据本地攻略检索到的景点信息安排。",
            "estimated_cost": 71.0,
            "location": "厦门",
            "image_url": "http://store.is.autonavi.com/showpic/654bdaaa16ffeee0a8df58c6edd5864a",
            "address": "中山路56号",
            "latitude": 24.455453,
            "longitude": 118.079259,
            "poi_id": "B025003IUP"
          }
        ],
        "meals": [
          {
            "name": "荣誉·海上江南",
            "meal_type": "晚餐",
            "estimated_cost": 528.52,
            "notes": "佛跳墙等高端闽南宴席，人均约300元，晚餐作为行程收尾。"
          }
        ],
        "hotel": {
          "name": "厦门安达仕酒店",
          "level": "豪华型（500 元/晚以上）",
          "reference_price": "约 1200-2000 元/晚",
          "source": "xiamen_guide.md",
          "estimated_cost": 1805.09,
          "location": "思明区厦门华润中心",
          "address": "湖滨东路101号(湖滨东路地铁站2号口步行320米)",
          "latitude": 24.471337,
          "longitude": 118.110267
        },
        "transport": [
          {
            "mode": "地铁+公交",
            "from_place": "厦门安达仕酒店",
            "to_place": "中山路步行街（骑楼建筑与老字号小吃）",
            "estimated_cost": 3.11,
            "duration": "20 分钟",
            "distance_km": 4.43,
            "estimated_minutes": 20
          }
        ],
        "notes": [
          "当前旅行节奏：轻松",
          "地铁至最近站换乘公交前往植物园，轻松漫步自然，傍晚返回酒店享用告别晚餐。"
        ]
      }
    ],
    "estimated_budget": 10551.88,
    "budget_breakdown": {
      "transport": 16.28,
      "hotel": 6255.8,
      "meals": 2219.8,
      "tickets": 260.0,
      "other": 1800.0,
      "total": 10551.88
    },
    "tips": [
      "提前在官方小程序预约鼓浪屿轮渡及厦门大学入校",
      "植物园建议穿防滑鞋，关注雨林喷雾时间",
      "环岛路骑行可共享单车，注意潮汐与救生提示",
      "餐厅高峰期建议提前排号或预订",
      "如计划骑行，请以当地实时路况和可通行区域为准。"
    ],
    "source_notes": [
      "Itinerary is assembled by trip_service.py and can optionally use LangChain structured output.",
      "[来源: xiamen_guide.md | 标题: 2.1 鼓浪屿风景名胜区]\n* **位置**：晃岩路35-6号\n* **门票**：免费（部分景点需购票）\n* **游玩时长**：建议半天至一天\n* **简介**：鼓浪屿是厦门最著名的旅游目的地之一，以其美丽的海滩、欧式建筑以及丰富的历史文化而闻名。岛上禁止机动车行驶，非常适合漫步探索。",
      "[来源: xiamen_guide.md | 标题: 2.13 环岛路与黄厝海滩（海滨骑行与日出）]\n* **位置**：厦门岛东南海岸\n* **门票**：公共海滩及道路免费；骑行约 **10-60元/次**\n* **游玩时长**：约2-4小时\n* **简介**：适合骑行、看海和日出。下海前应留意风浪、潮汐和救生提示，不进入未开放海域。",
      "已过滤 3 个无法在本地攻略中核验的名称，相应位置改用攻略中的真实条目或留空。",
      "已补充高德地图地址、坐标或路线估算信息。"
    ],
    "token_usage": {
      "rewrite_prompt_tokens": 228,
      "rewrite_completion_tokens": 620,
      "embedding_prompt_tokens": 0,
      "embedding_completion_tokens": 0,
      "planner_prompt_tokens": 2856,
      "planner_completion_tokens": 2639,
      "rerank_prompt_tokens": 3414,
      "rerank_completion_tokens": 0
    }
  }
}
```

</details>

## 13. 最终 API 响应

<details>
<summary>POST /trip/generate 的完整 200 响应体</summary>

```json
{
  "trip_id": "trip_厦门_2026-08-05",
  "destination": "厦门",
  "summary": "4天厦门轻松游，入住厦门安达仕酒店（地铁直达），以地铁为主减少换乘。依次体验中山路骑楼老街、鼓浪屿海岛文化、环岛路海滨骑行、园林植物园自然漫步，搭配本地特色海鲜与闽南菜，预算控制在1-1.5万元。",
  "days": [
    {
      "day_index": 1,
      "date": "2026-08-05",
      "theme": "城市漫游·骑楼美食",
      "spots": [
        {
          "name": "鼓浪屿风景名胜区",
          "start_time": "10:00",
          "end_time": "13:00",
          "description": "根据本地攻略检索到的景点信息安排。",
          "estimated_cost": 59.0,
          "location": "厦门",
          "image_url": "http://store.is.autonavi.com/showpic/05b0e6e576cf50058e6e2fad7e7dacdc",
          "address": "晃岩路35-6号",
          "latitude": 24.444695,
          "longitude": 118.06702,
          "poi_id": "B025003YN2"
        }
      ],
      "meals": [
        {
          "name": "局口拌面（中山路店）",
          "meal_type": "午餐",
          "estimated_cost": 528.52,
          "notes": "特色拌面，人均约25元，适合午餐快速品尝地道面食。"
        }
      ],
      "hotel": {
        "name": "厦门安达仕酒店",
        "level": "豪华型（500 元/晚以上）",
        "reference_price": "约 1200-2000 元/晚",
        "source": "xiamen_guide.md",
        "estimated_cost": 1377.93,
        "location": "思明区厦门华润中心",
        "address": "湖滨东路101号(湖滨东路地铁站2号口步行320米)",
        "latitude": 24.471337,
        "longitude": 118.110267
      },
      "transport": [
        {
          "mode": "地铁",
          "from_place": "厦门安达仕酒店",
          "to_place": "鼓浪屿风景名胜区",
          "estimated_cost": 4.64,
          "duration": "70 分钟",
          "distance_km": 10.55,
          "estimated_minutes": 70
        }
      ],
      "notes": [
        "当前旅行节奏：轻松",
        "入住后步行至中山路，地铁直达，感受骑楼风貌与街头小吃，节奏轻松。"
      ]
    },
    {
      "day_index": 2,
      "date": "2026-08-06",
      "theme": "海岛文化·鼓浪屿",
      "spots": [
        {
          "name": "鼓浪屿风景名胜区",
          "start_time": "10:00",
          "end_time": "16:00",
          "description": "岛上无机动车，欧式建筑与海滩交织，半天可深度漫步，体验厦门最具代表性的历史文化景观。",
          "estimated_cost": 59.0,
          "location": "厦门",
          "image_url": "http://store.is.autonavi.com/showpic/05b0e6e576cf50058e6e2fad7e7dacdc",
          "address": "晃岩路35-6号",
          "latitude": 24.444695,
          "longitude": 118.06702,
          "poi_id": "B025003YN2"
        }
      ],
      "meals": [
        {
          "name": "醉壹号海鲜大排档·老厦门特色菜（厦门美食地标店）",
          "meal_type": "晚餐",
          "estimated_cost": 549.67,
          "notes": "清蒸石斑鱼为招牌，人均约120元，晚餐享用地道海鲜。"
        }
      ],
      "hotel": {
        "name": "厦门安达仕酒店",
        "level": "豪华型（500 元/晚以上）",
        "reference_price": "约 1200-2000 元/晚",
        "source": "xiamen_guide.md",
        "estimated_cost": 1446.82,
        "location": "思明区厦门华润中心",
        "address": "湖滨东路101号(湖滨东路地铁站2号口步行320米)",
        "latitude": 24.471337,
        "longitude": 118.110267
      },
      "transport": [
        {
          "mode": "地铁+轮渡",
          "from_place": "厦门安达仕酒店",
          "to_place": "鼓浪屿风景名胜区",
          "estimated_cost": 4.64,
          "duration": "70 分钟",
          "distance_km": 10.55,
          "estimated_minutes": 70
        }
      ],
      "notes": [
        "当前旅行节奏：轻松",
        "地铁至轮渡码头乘船上岛，全天漫步鼓浪屿，晚餐返回市区品尝海鲜。"
      ]
    },
    {
      "day_index": 3,
      "date": "2026-08-07",
      "theme": "海滨骑行·环岛路",
      "spots": [
        {
          "name": "厦门园林植物园（自然生态与摄影）",
          "start_time": "10:00",
          "end_time": "13:00",
          "description": "根据本地攻略检索到的景点信息安排。",
          "estimated_cost": 71.0,
          "location": "厦门",
          "image_url": "http://store.is.autonavi.com/showpic/a63581fcb3adda672d35f22d835504a4",
          "address": "虎园路25号",
          "latitude": 24.447728,
          "longitude": 118.109277,
          "poi_id": "B025003OPX"
        }
      ],
      "meals": [
        {
          "name": "临家闽南菜（环岛路店）",
          "meal_type": "午餐",
          "estimated_cost": 613.09,
          "notes": "红烧鲍鱼等闽南高端菜，人均约250元，午餐享用海景餐厅。"
        }
      ],
      "hotel": {
        "name": "厦门安达仕酒店",
        "level": "豪华型（500 元/晚以上）",
        "reference_price": "约 1200-2000 元/晚",
        "source": "xiamen_guide.md",
        "estimated_cost": 1625.96,
        "location": "思明区厦门华润中心",
        "address": "湖滨东路101号(湖滨东路地铁站2号口步行320米)",
        "latitude": 24.471337,
        "longitude": 118.110267
      },
      "transport": [
        {
          "mode": "地铁",
          "from_place": "厦门安达仕酒店",
          "to_place": "厦门园林植物园（自然生态与摄影）",
          "estimated_cost": 3.89,
          "duration": "22 分钟",
          "distance_km": 7.55,
          "estimated_minutes": 22
        }
      ],
      "notes": [
        "当前旅行节奏：轻松",
        "地铁1号线至环岛路站，租借共享单车沿海骑行，午餐在环岛路店用餐。"
      ]
    },
    {
      "day_index": 4,
      "date": "2026-08-08",
      "theme": "自然生态·植物园",
      "spots": [
        {
          "name": "中山路步行街（骑楼建筑与老字号小吃）",
          "start_time": "10:00",
          "end_time": "14:00",
          "description": "根据本地攻略检索到的景点信息安排。",
          "estimated_cost": 71.0,
          "location": "厦门",
          "image_url": "http://store.is.autonavi.com/showpic/654bdaaa16ffeee0a8df58c6edd5864a",
          "address": "中山路56号",
          "latitude": 24.455453,
          "longitude": 118.079259,
          "poi_id": "B025003IUP"
        }
      ],
      "meals": [
        {
          "name": "荣誉·海上江南",
          "meal_type": "晚餐",
          "estimated_cost": 528.52,
          "notes": "佛跳墙等高端闽南宴席，人均约300元，晚餐作为行程收尾。"
        }
      ],
      "hotel": {
        "name": "厦门安达仕酒店",
        "level": "豪华型（500 元/晚以上）",
        "reference_price": "约 1200-2000 元/晚",
        "source": "xiamen_guide.md",
        "estimated_cost": 1805.09,
        "location": "思明区厦门华润中心",
        "address": "湖滨东路101号(湖滨东路地铁站2号口步行320米)",
        "latitude": 24.471337,
        "longitude": 118.110267
      },
      "transport": [
        {
          "mode": "地铁+公交",
          "from_place": "厦门安达仕酒店",
          "to_place": "中山路步行街（骑楼建筑与老字号小吃）",
          "estimated_cost": 3.11,
          "duration": "20 分钟",
          "distance_km": 4.43,
          "estimated_minutes": 20
        }
      ],
      "notes": [
        "当前旅行节奏：轻松",
        "地铁至最近站换乘公交前往植物园，轻松漫步自然，傍晚返回酒店享用告别晚餐。"
      ]
    }
  ],
  "estimated_budget": 10551.88,
  "budget_breakdown": {
    "transport": 16.28,
    "hotel": 6255.8,
    "meals": 2219.8,
    "tickets": 260.0,
    "other": 1800.0,
    "total": 10551.88
  },
  "tips": [
    "提前在官方小程序预约鼓浪屿轮渡及厦门大学入校",
    "植物园建议穿防滑鞋，关注雨林喷雾时间",
    "环岛路骑行可共享单车，注意潮汐与救生提示",
    "餐厅高峰期建议提前排号或预订",
    "如计划骑行，请以当地实时路况和可通行区域为准。"
  ],
  "source_notes": [
    "Itinerary is assembled by trip_service.py and can optionally use LangChain structured output.",
    "[来源: xiamen_guide.md | 标题: 2.1 鼓浪屿风景名胜区]\n* **位置**：晃岩路35-6号\n* **门票**：免费（部分景点需购票）\n* **游玩时长**：建议半天至一天\n* **简介**：鼓浪屿是厦门最著名的旅游目的地之一，以其美丽的海滩、欧式建筑以及丰富的历史文化而闻名。岛上禁止机动车行驶，非常适合漫步探索。",
    "[来源: xiamen_guide.md | 标题: 2.13 环岛路与黄厝海滩（海滨骑行与日出）]\n* **位置**：厦门岛东南海岸\n* **门票**：公共海滩及道路免费；骑行约 **10-60元/次**\n* **游玩时长**：约2-4小时\n* **简介**：适合骑行、看海和日出。下海前应留意风浪、潮汐和救生提示，不进入未开放海域。",
    "已过滤 3 个无法在本地攻略中核验的名称，相应位置改用攻略中的真实条目或留空。",
    "已补充高德地图地址、坐标或路线估算信息。"
  ],
  "token_usage": {
    "rewrite_prompt_tokens": 228,
    "rewrite_completion_tokens": 620,
    "embedding_prompt_tokens": 0,
    "embedding_completion_tokens": 0,
    "planner_prompt_tokens": 2856,
    "planner_completion_tokens": 2639,
    "rerank_prompt_tokens": 3414,
    "rerank_completion_tokens": 0
  }
}
```

</details>

### Token 汇总

| 阶段 | 输入 | 输出 |
|---|---:|---:|
| Query Rewrite | 228 | 620 |
| Query Embedding | 0 | 0 |
| Rerank | 3414 | 0 |
| Planner | 2856 | 2639 |
| 合计 | **6498** | **3259** |

## 14. 本次真实流量暴露的问题

1. **名称硬校验与 fallback 组装仍存在语义错位。** Planner 的 Day 1“中山路步行街”、Day 3“环岛路与黄厝海滩”、Day 4“厦门园林植物园”被拒绝后，代码按 fallback 列表序号替换，造成主题/备注与实际景点错位；Day 1 和 Day 2 最终还重复为鼓浪屿。
2. **景点向量路在新硬过滤下召回 0 条。** 当前 Chroma collection 对 `category=attraction` 没有返回可用实体，但关键词 fallback 能返回候选。需要检查当前 collection 是否按最新 entity chunk metadata 重新入库。
3. **主路 Query 清洗不彻底。** Rewrite 输出仍带“特色小吃”，与“主路只负责景点/活动”的目标不完全一致。
4. **餐饮条件只有总行程人均预算，没有餐饮人均预算。** 餐饮 Query 确实包含 `本地特色、海鲜、无辣`，但预算文本是整趟 `10000-15000 元`，不是每餐人均预算；当前知识库人均价因此主要依赖语义重排。
5. **酒店按 4 天计了 4 晚。** 2026-08-05 至 2026-08-08 通常是 3 晚，但当前每天都挂载酒店费用，住宿合计 `6255.80`。
6. **结果页预算明细没有展示“其他”费用。** API 的 `other=1800.00` 被计入总计 `10551.88`，但 UI 可见分项只有门票、酒店、餐饮、交通，四项合计与总计相差 1800 元。
7. **Embedding token 显示为 0 不代表没有执行向量化。** 本次 Ollama 日志显示实际执行了 3 次 embedding，trace 也记录了 2560 维向量；只是本地接口没有官方 token usage。

## 15. 对 P0/P1 修复的实测判断

P0/P1 的方向是对的，而且本次真实 UI 流量证明多数约束已生效：预算契约、三类硬过滤、真实酒店 metadata、动态餐饮候选、真实交通起点、非固定交通/餐次/时段、无候选禁止 Planner 自由补全都已进入生产链路。

但它还不能视为完全闭环。优先剩余项是：重新入库或迁移最新 Chroma entity metadata；让名称校验支持“正式实体名的安全短名/别名”或在 fallback 时同步重写主题与备注；明确餐饮的每餐人均预算字段；按住宿晚数计费；在结果页展示 `other`。

---

记录开始：`2026-08-04T18:20:23.847747+08:00`  
记录结束：`2026-08-04T18:22:47.411548+08:00`  
原始事件：`outputs/xiamen_user_flow_full_trace_20260804.jsonl`
