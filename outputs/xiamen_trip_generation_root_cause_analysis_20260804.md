# 厦门行程生成异常：真实三路检索复现与根因分析

## 1. 结论先行

这次截图中的结果并不是大模型根据完整用户偏好规划出来的。

真实运行日志证明：

1. Query Rewrite 大模型调用失败：`429 FreeUsageLimitError`。
2. Planner 大模型调用也失败：`429 FreeUsageLimitError`。
3. 接口没有失败，而是继续以 HTTP 200 返回，由 `trip_service.py` 使用三路 RAG 候选做规则回退拼装。
4. 三路确实都执行了，但当前实现不是严格的“景点 / 住宿 / 餐饮”类型隔离检索：
   - 主路 Top5；
   - 固定住宿路 Top2；
   - 固定餐饮路 Top2；
   - 三路都只过滤 `destination=厦门` 与 `retrieval_scope=planning`，没有按 `category` 隔离。
5. 餐饮路 Top2 中只有 1 个真正的餐厅，另一个是“中山路步行街”景点，因此合并后只有 1 个餐厅候选。规则回退按天用下标取候选，导致 Day1 有餐厅，Day2-Day4 全部为空。
6. 酒店路有 2 家酒店，但代码永远取第一家，并复制到每一天，所以四天都是同一家酒店。
7. 每天只有一个景点不是偶然，是 Planner Schema、Prompt 与 service 组装代码共同限定的固定产品结构。
8. “温泉、地铁、减少换乘”没有落实：备注关键词没有进入规则回退 Query，厦门知识库也没有温泉实体；交通方式被 service 固定写成“打车”。

## 2. 截图输入还原

- 目的地：厦门
- 日期：2026-08-09 至 2026-08-12，共 4 天
- 人数：1 人
- 节奏：轻松（界面文案“悠闲放松”）
- 住宿偏好：豪华型
- 页面预算区间：人均 ¥2500-¥5500
- 旅行偏好：自然风景、购物、城市漫游、夜生活
- 饮食偏好：本地特色、海鲜
- 备注：希望体验当地文化，安排一次温泉体验，偏好地铁出行，减少换乘。

前端实际只发送 `budget: formState.budgetMax`，所以后端只收到 `5500`，没有收到最低预算 `2500`。此外，前端标注为“人均预算”，后端 `TripRequest.budget` 描述为“总预算”；本次只有 1 人所以数值暂时等价，多人场景会出现语义错误。

## 3. 原样真实请求与复现结果

使用真实生产接口 `POST /trip/generate`，没有运行测试脚本。请求走了完整主链：Query Rewrite、主路 Top5、住宿路 Top2、餐饮路 Top2、Planner、name guard/fallback、地图补全与预算回算。

按已保存行程反推出的原始标签顺序重发后，得到与截图一致的核心结果：

| 天数 | 景点 | 餐饮 | 酒店 |
|---|---|---|---|
| Day1 | 曾厝垵文创村 | 醉壹号海鲜大排档 | 厦门佳逸酒店 |
| Day2 | 中山路步行街 | 无 | 厦门佳逸酒店 |
| Day3 | 沙坡尾艺术西区 | 无 | 厦门佳逸酒店 |
| Day4 | 云上厦门观光厅 | 无 | 厦门佳逸酒店 |

原始已保存行程的 token 状态：

```text
rewrite_prompt_tokens = 0
planner_prompt_tokens = 0
rerank_prompt_tokens = 3041
```

结合后端日志中的两个 429，可确认 Rewrite 与 Planner 均未成功，只有 Embedding / Rerank 与规则拼装在工作。

## 4. 三路检索实际返回

### 4.1 主路 Top5

规则回退 Query：

```text
厦门 自然风景 购物 城市漫游 夜生活 轻松 景点 行程 攻略 推荐 餐饮 住宿
```

异常点：主路本应承担景点发现，却被固定追加“餐饮、住宿”；同时没有 `category=attraction` 过滤。当前景点 metadata 仍为 `category=guide`。

本次最终候选为：

1. 曾厝垵文创村
2. 中山路步行街
3. 沙坡尾艺术西区
4. 云上厦门观光厅
5. 另一个景点候选（Top5 中未被 4 天行程使用）

### 4.2 住宿路 Top2

固定 Query：

```text
厦门 住宿 酒店 民宿
```

返回：

1. 厦门佳逸酒店，希尔顿格芮精选酒店，豪华型
2. 厦门W酒店，豪华型

本次恰好召回了豪华酒店，但不是因为请求中的 `hotel_level=豪华型` 参与了检索；住宿 Query 根本没有酒店档次和预算。代码之后执行：

```python
fallback_hotel_name = fallback_hotel_names[0]
```

因此永远选择第一名，再在每个 DayPlan 中重复使用。

### 4.3 餐饮路 Top2

固定 Query：

```text
厦门 餐饮 美食 餐厅
```

返回：

1. `category=restaurant`：醉壹号海鲜大排档·老厦门特色菜
2. `category=guide`：中山路步行街

第二条不是餐厅。`extract_fallback_candidates` 只接受标题以 `餐饮：` 开头的实体，因此合并后只有一个餐厅候选。

规则回退使用：

```python
meal_name = fallback_meal_names[index] if index < len(fallback_meal_names) else None
```

因此只有 Day1 能取到索引 0；Day2-Day4 必然为空。这正是截图中连续出现“未从当前攻略检索到餐饮信息”的直接原因。

## 5. 从输入到异常结果的完整因果链

```text
用户完整表单
  ├─ budgetMin 被前端丢弃，只发送 budgetMax
  ├─ dietary_preferences / hotel_level 不传给 collect_trip_context
  └─ special_notes 只进入主路 Rewrite
          ↓
Query Rewrite LLM 429
          ↓
规则 Query 只保留偏好标签；“温泉/地铁/减少换乘”无规则命中而丢失
          ↓
三路检索只做 destination + planning 过滤
  ├─ 主路 Top5：景点，但 Query 混有餐饮/住宿
  ├─ 酒店 Top2：有 2 家，后续只取第一家
  └─ 餐厅 Top2：1 家餐厅 + 1 个景点，正式餐厅池仅 1 家
          ↓
Planner LLM 429
          ↓
规则回退
  ├─ 第 N 天取 fallback_spots[N]
  ├─ 第 N 天取 fallback_meals[N]，只有第 0 个存在
  ├─ 所有天复制 fallback_hotels[0]
  ├─ 每天固定 1 景点、最多 1 午餐
  ├─ 景点时间固定 10:00-12:00
  └─ 交通方式固定“打车”，起点固定“厦门 出发点”
          ↓
高德只补地址、坐标和驾车路线，不会重新规划行程
          ↓
前端只展示 spots[0]、meals[0]、transport[0] 和 notes 最后一条
```

## 6. 具体问题分级

### P0：失败被伪装成成功

`generate_planner_draft` 遇到 429 后返回 `None`，接口继续 HTTP 200。页面显示“行程生成成功”，用户完全不知道个性化 Planner 没有运行。

建议：Planner 不可用时返回明确的降级状态，例如 `generation_mode=rules_fallback`、`warnings`；若产品要求必须智能规划，则直接返回 503，而不是把模板拼装当完整规划。

### P0：三路没有类别硬隔离

当前 Chroma where 只含：

```text
destination=厦门 AND retrieval_scope=planning
```

餐饮路已真实串入景点。应改为：

- 景点路：`category=attraction`
- 住宿路：`category=hotel`
- 餐饮路：`category=restaurant`

同时需要把当前景点的 `category=guide` 正式改成 attraction，并重新入库。

### P0：用户约束没有进入对应检索路

- `hotel_level=豪华型` 不进入住宿 Query，也没有使用现有 `budget_tier` metadata 过滤。
- `dietary_preferences=[本地特色, 海鲜]` 不进入餐饮 Query。
- `budget` 不进入任何检索路。
- 备注中的温泉、地铁、减少换乘没有进入可用 Query。

应先将一次 TripRequest 解析成三个结构化检索意图，再分别检索，而不是主路带少量偏好、两条补充路使用固定模板 Query。

### P1：规则回退不是行程规划器

规则回退只是“候选数组按天顺序分配”，没有：

- 地理聚类与邻近组合
- 开放时间和早晚适配
- 夜生活安排在夜间
- 多景点半日 / 全日组合
- 餐厅与当日景点的空间关联
- 地铁优先和少换乘优化
- 明确约束满足检查

所以即使三路召回内容都真实，最终也仍然只是检索结果列表，不是可执行行程。

### P1：餐厅候选数量与天数不匹配

餐饮路固定 Top2，却要规划 4 天，每天一个餐饮。即使 Top2 全是餐厅，也最多覆盖两天。应根据天数动态计算候选数量，例如至少 `max(day_count * meals_per_day, minimum_pool)`，再去重和多样化选择。

### P1：住宿逻辑过度简化

同住一家酒店本身不一定错误，反而能减少换酒店；真正的问题是系统没有经过“档次、预算、区域、交通便利性”决策，而是无条件取检索第一名。应把“是否全程同住”作为显式策略，并给出选择理由。

### P1：温泉诉求被静默忽略

`retrieval_rules.json` 没有温泉、地铁、换乘、文化相关触发规则；厦门知识库也没有温泉实体。遵守“不伪造”是对的，但系统应明确返回“当前知识库没有可核验的厦门温泉候选”，而不是生成成功后完全不提。

### P1：Planner 实体名单解析已过时

`trip_planner_agent.py` 使用 `【酒店名】` / `【餐厅名】` 正则抽取候选；当前 RAG context 格式是 `[来源: ... | 标题: ...]`。真实验证结果：8 个 contexts 中酒店名单和餐厅名单都解析为空。

这不是本次截图的直接原因，因为 Planner 已经 429；但模型恢复后，Prompt 仍会把“可选真实酒店/餐厅”写成“暂无”。应直接复用 `extract_fallback_candidates` 或 metadata，不要再维护第二套正则。

### P2：交通与地图只是展示性补全

`trip_service.py` 固定：

```text
mode = 打车
from_place = 厦门 出发点
start_time = 10:00
end_time = 12:00
```

高德随后只对这些既定文本做 POI 和驾车路线补全。它不会理解“偏好地铁、减少换乘”，也不会从酒店或上一景点作为真实起点。因此路线距离虽然有数值，但不代表真实的逐段行程组织。

### P2：结果页放大了降级感

结果页只展示：

- `spots[0]`
- `meals[0]`
- `transport[0]`
- `notes[notes.length - 1]`

当餐饮为空时，最后一条 note 正好是“未检索到餐饮信息”，于是页面四天中三天都把同一失败提示放在最显眼位置。前端不是根因，但放大了后端候选不足的问题。

## 7. 推荐修复顺序

1. **先处理 Planner 失败语义**：不要把 429 降级结果伪装成完整智能规划；响应中显式标记模式和未满足约束。
2. **建立真正的三路类型隔离**：attraction / hotel / restaurant，Chroma 召回阶段硬过滤。
3. **把用户条件分流到对应 Query 与 metadata**：酒店档次/预算进入住宿路，饮食偏好进入餐饮路，节奏/活动/备注进入景点路。
4. **候选池数量跟随天数**：景点、餐厅分别保证足够数量；餐饮还需要结果级多样性选择。
5. **用 metadata/entity_name 贯穿候选、Planner 与 name guard**：删除旧 `【】` 正则和全文跨类型子串放行。
6. **将规则 fallback 升级为约束规划**：地理聚类、时段、交通模式、餐厅邻近、去重和未满足约束说明。
7. **修复预算契约**：明确 budget_min / budget_max、per_person / total，并结合 travelers 计算。
8. **最后改善结果页**：展示结构化警告，不要让最后一条 note 覆盖当天正常规划说明。

## 8. 复现产物

- 截图对应的已保存原始行程：`outputs/xiamen_trip_original_saved_20260809.json`
- 第一次同值复现：`outputs/xiamen_trip_reproduction_20260804.json`
- 按原始偏好点击顺序精确复现：`outputs/xiamen_trip_exact_reproduction_20260804.json`

本轮只做真实请求、运行追踪与源码分析，没有修改业务源码和配置。
