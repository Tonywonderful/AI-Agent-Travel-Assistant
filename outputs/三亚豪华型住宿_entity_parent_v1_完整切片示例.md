# 三亚豪华型住宿：entity_parent_v1 完整切片示例

> 数据源：`backend/data/sanya_guide.md` 第 254-280 行。
> 本文展示设计模拟结果，尚未修改业务代码，也尚未写入 Chroma。
> 样本包含 3 个非叶子层级节点和 25 个酒店叶子节点，共 28 个节点。三个非叶子节点广义上都有自己的子节点，但对某一家酒店叶子而言，只有 `category_parent` 是直接父节点；`section_parent` 是祖父层，`document_root` 是根祖先。三个非叶子节点均不生成 Embedding，每个酒店叶子独立生成 Embedding。

## 1. 切片前的完整原始 Markdown

```markdown
### 豪华型（500 元/晚以上）

* **【三亚阳光大酒店】**：位于三亚湾路、凤凰机场方向，适合航空中转、三亚湾日落及家庭度假。酒店预算：**500 元/晚以上**。
* **【三亚福朋喜来登酒店】**：位于三亚湾椰梦长廊，靠近沙滩和市区美食商圈，适合家庭、商务和海滨度假游客。酒店预算：**500 元/晚以上**。
* **【三亚海韵度假酒店】**：位于三亚湾、海虹广场附近，设有亲子和度假设施，适合家庭及三亚湾日落行程。酒店预算：**500 元/晚以上**。
* **【三亚天丽湾凯悦酒店】**：位于天涯海角、西岛方向的海湾区域，适合亲子、安静海滨度假及西线景点行程。酒店预算：**500 元/晚以上**。
* **【三亚绿发山海天 JW 万豪酒店】**：位于大东海、鹿回头方向，依山面海，适合亲子、商务和高端海滨度假。酒店预算：**500 元/晚以上**。
* **【三亚绿发山海天酒店·傲途格精选】**：位于小东海片区，以设计和海景体验为特色，适合情侣、摄影和度假游客。酒店预算：**500 元/晚以上**。
* **【三亚珊瑚湾文华东方酒店】**：位于珊瑚湾、大东海方向，拥有相对私密的海湾环境，适合高端度假、情侣和潜水爱好者。酒店预算：**500 元/晚以上**。
* **【三亚悦榕庄】**：位于鹿回头、小东海方向，以泳池别墅、私人海滩和水疗体验为特色，适合私密度假及纪念日行程。酒店预算：**500 元/晚以上**。
* **【三亚亚龙湾红树林度假酒店】**：位于亚龙湾一线海滨，适合亲子、沙滩休闲及综合度假。酒店预算：**500 元/晚以上**。
* **【三亚亚龙湾万豪度假酒店】**：位于亚龙湾国家旅游度假区，拥有海滨和亲子设施，适合家庭及长住度假游客。酒店预算：**500 元/晚以上**。
* **【三亚亚龙湾喜来登度假酒店】**：位于亚龙湾海滨，设有泳池、沙滩和亲子活动，适合家庭和休闲度假。酒店预算：**500 元/晚以上**。
* **【金茂三亚亚龙湾丽思卡尔顿酒店】**：位于亚龙湾，提供豪华海滨度假和别墅产品，适合高端家庭、情侣及纪念日行程。酒店预算：**500 元/晚以上**。
* **【三亚亚龙湾希尔顿酒店】**：位于亚龙湾国家旅游度假区，适合亲子、沙滩和品牌度假体验。酒店预算：**500 元/晚以上**。
* **【三亚亚龙湾美高梅度假酒店】**：位于亚龙湾中心区域，强调亲子娱乐、海滩和活动体验，适合家庭及年轻游客。酒店预算：**500 元/晚以上**。
* **【三亚太阳湾柏悦酒店】**：位于太阳湾，环境相对私密，适合艺术、安静海湾和高端度假体验。酒店预算：**500 元/晚以上**。
* **【三亚海棠湾君悦酒店】**：位于海棠湾，靠近国际免税城方向，适合亲子、购物和海滨度假游客。酒店预算：**500 元/晚以上**。
* **【三亚海棠湾喜来登度假酒店】**：位于海棠湾，设有家庭房、泳池和亲子设施，适合家庭度假。酒店预算：**500 元/晚以上**。
* **【三亚海棠湾仁恒皇冠假日度假酒店】**：位于海棠湾国际免税城附近，亲子设施丰富，适合家庭和一站式度假。酒店预算：**500 元/晚以上**。
* **【三亚海棠湾洲际度假酒店】**：位于海棠湾、国际免税城方向，适合购物、亲子及高端海滨度假。酒店预算：**500 元/晚以上**。
* **【三亚理文索菲特度假酒店】**：位于海棠湾中心区域，拥有热带园林、泳池和会议设施，适合亲子、婚礼及商务会展。酒店预算：**500 元/晚以上**。
* **【三亚海棠湾开维费尔蒙酒店】**：位于海棠湾，以海景、园林和水系景观为特色，适合高端家庭及休闲度假。酒店预算：**500 元/晚以上**。
* **【三亚海棠湾阳光壹酒店】**：位于海棠湾、后海村方向，强调设计、自然材料和亲子体验，适合年轻家庭及设计酒店爱好者。酒店预算：**500 元/晚以上**。
* **【三亚亚特兰蒂斯酒店】**：位于海棠湾，与水世界和失落的空间水族馆相连，适合亲子玩水和一站式度假。酒店预算：**500 元/晚以上**。
* **【三亚艾迪逊酒店】**：位于海棠湾、三亚国际免税城附近，强调设计、私密度和高端度假体验。酒店预算：**500 元/晚以上**。
* **【三亚保利瑰丽酒店】**：位于海棠湾，部分公共空间和房型具有高层海景，适合情侣、商务和高端度假。酒店预算：**500 元/晚以上**。
```

## 2. 切片后的非叶子层级节点

下面三个节点自身都有子节点，所以从广义的树结构术语看都属于“父节点”。但它们不是某个酒店叶子的三个并列父节点，而是一条逐级包含的祖先链：`document_root → section_parent → category_parent → hotel_entity_leaf`。对酒店叶子而言，`category_parent` 是唯一直接父节点，`section_parent` 是祖父层，`document_root` 是根祖先。第一阶段三个非叶子节点都不送入 Embedding 模型。

### 层级节点 1：document_root（根祖先）

```json
{
  "chunk_id": "epv1_8c7224265764862b",
  "text": "# 2026 三亚深度游玩全攻略",
  "embedding_text": null,
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 0,
    "chunk_type": "document_root",
    "entity_name": null,
    "section_title": null,
    "category_title": null,
    "parent_id": null,
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [
      "epv1_62e8d55be48a6a36"
    ],
    "source_line_start": 1,
    "source_line_end": 1,
    "is_embedded": false
  }
}
```

### 层级节点 2：section_parent（祖父层）

```json
{
  "chunk_id": "epv1_62e8d55be48a6a36",
  "text": "## 4. 住宿区域建议",
  "embedding_text": null,
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 1,
    "chunk_type": "section_parent",
    "entity_name": null,
    "section_title": "4. 住宿区域建议",
    "category_title": null,
    "parent_id": "epv1_8c7224265764862b",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [
      "epv1_7d8ef5b0fa16e6d2"
    ],
    "source_line_start": 217,
    "source_line_end": 217,
    "is_embedded": false
  }
}
```

### 层级节点 3：category_parent（酒店叶子的唯一直接父节点）

```json
{
  "chunk_id": "epv1_7d8ef5b0fa16e6d2",
  "text": "### 豪华型（500 元/晚以上）",
  "embedding_text": null,
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 2,
    "chunk_type": "category_parent",
    "entity_name": null,
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_62e8d55be48a6a36",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [
      "epv1_12859d6b67172e80",
      "epv1_4b54a1064fa538e3",
      "epv1_7e1951b5450bfa90",
      "epv1_5170cfe89742872b",
      "epv1_68869dc47086883a",
      "epv1_6c059aa830c181cf",
      "epv1_42cc299664fcc31b",
      "epv1_5da1dde0d2bb425b",
      "epv1_a2b369b981958025",
      "epv1_12b337e2e9422034",
      "epv1_c12f791eca4787b3",
      "epv1_2f740907e5bc8568",
      "epv1_95e7c9907a9cf774",
      "epv1_e41c7cb9cd2ab71a",
      "epv1_f1a0ff1539148965",
      "epv1_c87ec897d645e1a3",
      "epv1_2e03a92ca0d6d120",
      "epv1_798b6bf93bc67600",
      "epv1_31808b20976f40b8",
      "epv1_0e5c0cebab3d5da9",
      "epv1_ed20c5d64ff85241",
      "epv1_87b9dafd7ad72c11",
      "epv1_8ec7b59234173528",
      "epv1_9a7c6276bf317d18",
      "epv1_2c2c0871627eb808"
    ],
    "source_line_start": 254,
    "source_line_end": 281,
    "is_embedded": false
  }
}
```

## 3. 切片后的 25 个酒店叶子节点

每家酒店变成一个独立叶子 Chunk。`text` 保留原始 Markdown；`embedding_text` 是实际送给 Embedding 模型的完整文本；`metadata` 保存父子关系和来源位置。

### 叶子 Chunk 01：三亚阳光大酒店

#### 原始叶子正文

```markdown
* **【三亚阳光大酒店】**：位于三亚湾路、凤凰机场方向，适合航空中转、三亚湾日落及家庭度假。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚阳光大酒店
三亚阳光大酒店
位于三亚湾路、凤凰机场方向，适合航空中转、三亚湾日落及家庭度假。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_12859d6b67172e80",
  "text": "* **【三亚阳光大酒店】**：位于三亚湾路、凤凰机场方向，适合航空中转、三亚湾日落及家庭度假。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚阳光大酒店\n三亚阳光大酒店\n位于三亚湾路、凤凰机场方向，适合航空中转、三亚湾日落及家庭度假。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚阳光大酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 256,
    "source_line_end": 256,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 02：三亚福朋喜来登酒店

#### 原始叶子正文

```markdown
* **【三亚福朋喜来登酒店】**：位于三亚湾椰梦长廊，靠近沙滩和市区美食商圈，适合家庭、商务和海滨度假游客。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚福朋喜来登酒店
三亚福朋喜来登酒店
位于三亚湾椰梦长廊，靠近沙滩和市区美食商圈，适合家庭、商务和海滨度假游客。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_4b54a1064fa538e3",
  "text": "* **【三亚福朋喜来登酒店】**：位于三亚湾椰梦长廊，靠近沙滩和市区美食商圈，适合家庭、商务和海滨度假游客。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚福朋喜来登酒店\n三亚福朋喜来登酒店\n位于三亚湾椰梦长廊，靠近沙滩和市区美食商圈，适合家庭、商务和海滨度假游客。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚福朋喜来登酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 257,
    "source_line_end": 257,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 03：三亚海韵度假酒店

#### 原始叶子正文

```markdown
* **【三亚海韵度假酒店】**：位于三亚湾、海虹广场附近，设有亲子和度假设施，适合家庭及三亚湾日落行程。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚海韵度假酒店
三亚海韵度假酒店
位于三亚湾、海虹广场附近，设有亲子和度假设施，适合家庭及三亚湾日落行程。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_7e1951b5450bfa90",
  "text": "* **【三亚海韵度假酒店】**：位于三亚湾、海虹广场附近，设有亲子和度假设施，适合家庭及三亚湾日落行程。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚海韵度假酒店\n三亚海韵度假酒店\n位于三亚湾、海虹广场附近，设有亲子和度假设施，适合家庭及三亚湾日落行程。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚海韵度假酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 258,
    "source_line_end": 258,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 04：三亚天丽湾凯悦酒店

#### 原始叶子正文

```markdown
* **【三亚天丽湾凯悦酒店】**：位于天涯海角、西岛方向的海湾区域，适合亲子、安静海滨度假及西线景点行程。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚天丽湾凯悦酒店
三亚天丽湾凯悦酒店
位于天涯海角、西岛方向的海湾区域，适合亲子、安静海滨度假及西线景点行程。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_5170cfe89742872b",
  "text": "* **【三亚天丽湾凯悦酒店】**：位于天涯海角、西岛方向的海湾区域，适合亲子、安静海滨度假及西线景点行程。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚天丽湾凯悦酒店\n三亚天丽湾凯悦酒店\n位于天涯海角、西岛方向的海湾区域，适合亲子、安静海滨度假及西线景点行程。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚天丽湾凯悦酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 259,
    "source_line_end": 259,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 05：三亚绿发山海天 JW 万豪酒店

#### 原始叶子正文

```markdown
* **【三亚绿发山海天 JW 万豪酒店】**：位于大东海、鹿回头方向，依山面海，适合亲子、商务和高端海滨度假。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚绿发山海天 JW 万豪酒店
三亚绿发山海天 JW 万豪酒店
位于大东海、鹿回头方向，依山面海，适合亲子、商务和高端海滨度假。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_68869dc47086883a",
  "text": "* **【三亚绿发山海天 JW 万豪酒店】**：位于大东海、鹿回头方向，依山面海，适合亲子、商务和高端海滨度假。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚绿发山海天 JW 万豪酒店\n三亚绿发山海天 JW 万豪酒店\n位于大东海、鹿回头方向，依山面海，适合亲子、商务和高端海滨度假。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚绿发山海天 JW 万豪酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 260,
    "source_line_end": 260,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 06：三亚绿发山海天酒店·傲途格精选

#### 原始叶子正文

```markdown
* **【三亚绿发山海天酒店·傲途格精选】**：位于小东海片区，以设计和海景体验为特色，适合情侣、摄影和度假游客。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚绿发山海天酒店·傲途格精选
三亚绿发山海天酒店·傲途格精选
位于小东海片区，以设计和海景体验为特色，适合情侣、摄影和度假游客。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_6c059aa830c181cf",
  "text": "* **【三亚绿发山海天酒店·傲途格精选】**：位于小东海片区，以设计和海景体验为特色，适合情侣、摄影和度假游客。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚绿发山海天酒店·傲途格精选\n三亚绿发山海天酒店·傲途格精选\n位于小东海片区，以设计和海景体验为特色，适合情侣、摄影和度假游客。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚绿发山海天酒店·傲途格精选",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 261,
    "source_line_end": 261,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 07：三亚珊瑚湾文华东方酒店

#### 原始叶子正文

```markdown
* **【三亚珊瑚湾文华东方酒店】**：位于珊瑚湾、大东海方向，拥有相对私密的海湾环境，适合高端度假、情侣和潜水爱好者。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚珊瑚湾文华东方酒店
三亚珊瑚湾文华东方酒店
位于珊瑚湾、大东海方向，拥有相对私密的海湾环境，适合高端度假、情侣和潜水爱好者。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_42cc299664fcc31b",
  "text": "* **【三亚珊瑚湾文华东方酒店】**：位于珊瑚湾、大东海方向，拥有相对私密的海湾环境，适合高端度假、情侣和潜水爱好者。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚珊瑚湾文华东方酒店\n三亚珊瑚湾文华东方酒店\n位于珊瑚湾、大东海方向，拥有相对私密的海湾环境，适合高端度假、情侣和潜水爱好者。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚珊瑚湾文华东方酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 262,
    "source_line_end": 262,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 08：三亚悦榕庄

#### 原始叶子正文

```markdown
* **【三亚悦榕庄】**：位于鹿回头、小东海方向，以泳池别墅、私人海滩和水疗体验为特色，适合私密度假及纪念日行程。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚悦榕庄
三亚悦榕庄
位于鹿回头、小东海方向，以泳池别墅、私人海滩和水疗体验为特色，适合私密度假及纪念日行程。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_5da1dde0d2bb425b",
  "text": "* **【三亚悦榕庄】**：位于鹿回头、小东海方向，以泳池别墅、私人海滩和水疗体验为特色，适合私密度假及纪念日行程。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚悦榕庄\n三亚悦榕庄\n位于鹿回头、小东海方向，以泳池别墅、私人海滩和水疗体验为特色，适合私密度假及纪念日行程。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚悦榕庄",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 263,
    "source_line_end": 263,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 09：三亚亚龙湾红树林度假酒店

#### 原始叶子正文

```markdown
* **【三亚亚龙湾红树林度假酒店】**：位于亚龙湾一线海滨，适合亲子、沙滩休闲及综合度假。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚亚龙湾红树林度假酒店
三亚亚龙湾红树林度假酒店
位于亚龙湾一线海滨，适合亲子、沙滩休闲及综合度假。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_a2b369b981958025",
  "text": "* **【三亚亚龙湾红树林度假酒店】**：位于亚龙湾一线海滨，适合亲子、沙滩休闲及综合度假。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚亚龙湾红树林度假酒店\n三亚亚龙湾红树林度假酒店\n位于亚龙湾一线海滨，适合亲子、沙滩休闲及综合度假。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚亚龙湾红树林度假酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 264,
    "source_line_end": 264,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 10：三亚亚龙湾万豪度假酒店

#### 原始叶子正文

```markdown
* **【三亚亚龙湾万豪度假酒店】**：位于亚龙湾国家旅游度假区，拥有海滨和亲子设施，适合家庭及长住度假游客。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚亚龙湾万豪度假酒店
三亚亚龙湾万豪度假酒店
位于亚龙湾国家旅游度假区，拥有海滨和亲子设施，适合家庭及长住度假游客。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_12b337e2e9422034",
  "text": "* **【三亚亚龙湾万豪度假酒店】**：位于亚龙湾国家旅游度假区，拥有海滨和亲子设施，适合家庭及长住度假游客。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚亚龙湾万豪度假酒店\n三亚亚龙湾万豪度假酒店\n位于亚龙湾国家旅游度假区，拥有海滨和亲子设施，适合家庭及长住度假游客。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚亚龙湾万豪度假酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 265,
    "source_line_end": 265,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 11：三亚亚龙湾喜来登度假酒店

#### 原始叶子正文

```markdown
* **【三亚亚龙湾喜来登度假酒店】**：位于亚龙湾海滨，设有泳池、沙滩和亲子活动，适合家庭和休闲度假。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚亚龙湾喜来登度假酒店
三亚亚龙湾喜来登度假酒店
位于亚龙湾海滨，设有泳池、沙滩和亲子活动，适合家庭和休闲度假。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_c12f791eca4787b3",
  "text": "* **【三亚亚龙湾喜来登度假酒店】**：位于亚龙湾海滨，设有泳池、沙滩和亲子活动，适合家庭和休闲度假。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚亚龙湾喜来登度假酒店\n三亚亚龙湾喜来登度假酒店\n位于亚龙湾海滨，设有泳池、沙滩和亲子活动，适合家庭和休闲度假。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚亚龙湾喜来登度假酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 266,
    "source_line_end": 266,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 12：金茂三亚亚龙湾丽思卡尔顿酒店

#### 原始叶子正文

```markdown
* **【金茂三亚亚龙湾丽思卡尔顿酒店】**：位于亚龙湾，提供豪华海滨度假和别墅产品，适合高端家庭、情侣及纪念日行程。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 金茂三亚亚龙湾丽思卡尔顿酒店
金茂三亚亚龙湾丽思卡尔顿酒店
位于亚龙湾，提供豪华海滨度假和别墅产品，适合高端家庭、情侣及纪念日行程。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_2f740907e5bc8568",
  "text": "* **【金茂三亚亚龙湾丽思卡尔顿酒店】**：位于亚龙湾，提供豪华海滨度假和别墅产品，适合高端家庭、情侣及纪念日行程。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 金茂三亚亚龙湾丽思卡尔顿酒店\n金茂三亚亚龙湾丽思卡尔顿酒店\n位于亚龙湾，提供豪华海滨度假和别墅产品，适合高端家庭、情侣及纪念日行程。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "金茂三亚亚龙湾丽思卡尔顿酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 267,
    "source_line_end": 267,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 13：三亚亚龙湾希尔顿酒店

#### 原始叶子正文

```markdown
* **【三亚亚龙湾希尔顿酒店】**：位于亚龙湾国家旅游度假区，适合亲子、沙滩和品牌度假体验。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚亚龙湾希尔顿酒店
三亚亚龙湾希尔顿酒店
位于亚龙湾国家旅游度假区，适合亲子、沙滩和品牌度假体验。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_95e7c9907a9cf774",
  "text": "* **【三亚亚龙湾希尔顿酒店】**：位于亚龙湾国家旅游度假区，适合亲子、沙滩和品牌度假体验。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚亚龙湾希尔顿酒店\n三亚亚龙湾希尔顿酒店\n位于亚龙湾国家旅游度假区，适合亲子、沙滩和品牌度假体验。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚亚龙湾希尔顿酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 268,
    "source_line_end": 268,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 14：三亚亚龙湾美高梅度假酒店

#### 原始叶子正文

```markdown
* **【三亚亚龙湾美高梅度假酒店】**：位于亚龙湾中心区域，强调亲子娱乐、海滩和活动体验，适合家庭及年轻游客。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚亚龙湾美高梅度假酒店
三亚亚龙湾美高梅度假酒店
位于亚龙湾中心区域，强调亲子娱乐、海滩和活动体验，适合家庭及年轻游客。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_e41c7cb9cd2ab71a",
  "text": "* **【三亚亚龙湾美高梅度假酒店】**：位于亚龙湾中心区域，强调亲子娱乐、海滩和活动体验，适合家庭及年轻游客。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚亚龙湾美高梅度假酒店\n三亚亚龙湾美高梅度假酒店\n位于亚龙湾中心区域，强调亲子娱乐、海滩和活动体验，适合家庭及年轻游客。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚亚龙湾美高梅度假酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 269,
    "source_line_end": 269,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 15：三亚太阳湾柏悦酒店

#### 原始叶子正文

```markdown
* **【三亚太阳湾柏悦酒店】**：位于太阳湾，环境相对私密，适合艺术、安静海湾和高端度假体验。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚太阳湾柏悦酒店
三亚太阳湾柏悦酒店
位于太阳湾，环境相对私密，适合艺术、安静海湾和高端度假体验。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_f1a0ff1539148965",
  "text": "* **【三亚太阳湾柏悦酒店】**：位于太阳湾，环境相对私密，适合艺术、安静海湾和高端度假体验。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚太阳湾柏悦酒店\n三亚太阳湾柏悦酒店\n位于太阳湾，环境相对私密，适合艺术、安静海湾和高端度假体验。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚太阳湾柏悦酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 270,
    "source_line_end": 270,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 16：三亚海棠湾君悦酒店

#### 原始叶子正文

```markdown
* **【三亚海棠湾君悦酒店】**：位于海棠湾，靠近国际免税城方向，适合亲子、购物和海滨度假游客。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚海棠湾君悦酒店
三亚海棠湾君悦酒店
位于海棠湾，靠近国际免税城方向，适合亲子、购物和海滨度假游客。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_c87ec897d645e1a3",
  "text": "* **【三亚海棠湾君悦酒店】**：位于海棠湾，靠近国际免税城方向，适合亲子、购物和海滨度假游客。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚海棠湾君悦酒店\n三亚海棠湾君悦酒店\n位于海棠湾，靠近国际免税城方向，适合亲子、购物和海滨度假游客。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚海棠湾君悦酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 271,
    "source_line_end": 271,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 17：三亚海棠湾喜来登度假酒店

#### 原始叶子正文

```markdown
* **【三亚海棠湾喜来登度假酒店】**：位于海棠湾，设有家庭房、泳池和亲子设施，适合家庭度假。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚海棠湾喜来登度假酒店
三亚海棠湾喜来登度假酒店
位于海棠湾，设有家庭房、泳池和亲子设施，适合家庭度假。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_2e03a92ca0d6d120",
  "text": "* **【三亚海棠湾喜来登度假酒店】**：位于海棠湾，设有家庭房、泳池和亲子设施，适合家庭度假。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚海棠湾喜来登度假酒店\n三亚海棠湾喜来登度假酒店\n位于海棠湾，设有家庭房、泳池和亲子设施，适合家庭度假。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚海棠湾喜来登度假酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 272,
    "source_line_end": 272,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 18：三亚海棠湾仁恒皇冠假日度假酒店

#### 原始叶子正文

```markdown
* **【三亚海棠湾仁恒皇冠假日度假酒店】**：位于海棠湾国际免税城附近，亲子设施丰富，适合家庭和一站式度假。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚海棠湾仁恒皇冠假日度假酒店
三亚海棠湾仁恒皇冠假日度假酒店
位于海棠湾国际免税城附近，亲子设施丰富，适合家庭和一站式度假。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_798b6bf93bc67600",
  "text": "* **【三亚海棠湾仁恒皇冠假日度假酒店】**：位于海棠湾国际免税城附近，亲子设施丰富，适合家庭和一站式度假。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚海棠湾仁恒皇冠假日度假酒店\n三亚海棠湾仁恒皇冠假日度假酒店\n位于海棠湾国际免税城附近，亲子设施丰富，适合家庭和一站式度假。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚海棠湾仁恒皇冠假日度假酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 273,
    "source_line_end": 273,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 19：三亚海棠湾洲际度假酒店

#### 原始叶子正文

```markdown
* **【三亚海棠湾洲际度假酒店】**：位于海棠湾、国际免税城方向，适合购物、亲子及高端海滨度假。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚海棠湾洲际度假酒店
三亚海棠湾洲际度假酒店
位于海棠湾、国际免税城方向，适合购物、亲子及高端海滨度假。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_31808b20976f40b8",
  "text": "* **【三亚海棠湾洲际度假酒店】**：位于海棠湾、国际免税城方向，适合购物、亲子及高端海滨度假。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚海棠湾洲际度假酒店\n三亚海棠湾洲际度假酒店\n位于海棠湾、国际免税城方向，适合购物、亲子及高端海滨度假。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚海棠湾洲际度假酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 274,
    "source_line_end": 274,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 20：三亚理文索菲特度假酒店

#### 原始叶子正文

```markdown
* **【三亚理文索菲特度假酒店】**：位于海棠湾中心区域，拥有热带园林、泳池和会议设施，适合亲子、婚礼及商务会展。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚理文索菲特度假酒店
三亚理文索菲特度假酒店
位于海棠湾中心区域，拥有热带园林、泳池和会议设施，适合亲子、婚礼及商务会展。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_0e5c0cebab3d5da9",
  "text": "* **【三亚理文索菲特度假酒店】**：位于海棠湾中心区域，拥有热带园林、泳池和会议设施，适合亲子、婚礼及商务会展。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚理文索菲特度假酒店\n三亚理文索菲特度假酒店\n位于海棠湾中心区域，拥有热带园林、泳池和会议设施，适合亲子、婚礼及商务会展。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚理文索菲特度假酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 275,
    "source_line_end": 275,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 21：三亚海棠湾开维费尔蒙酒店

#### 原始叶子正文

```markdown
* **【三亚海棠湾开维费尔蒙酒店】**：位于海棠湾，以海景、园林和水系景观为特色，适合高端家庭及休闲度假。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚海棠湾开维费尔蒙酒店
三亚海棠湾开维费尔蒙酒店
位于海棠湾，以海景、园林和水系景观为特色，适合高端家庭及休闲度假。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_ed20c5d64ff85241",
  "text": "* **【三亚海棠湾开维费尔蒙酒店】**：位于海棠湾，以海景、园林和水系景观为特色，适合高端家庭及休闲度假。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚海棠湾开维费尔蒙酒店\n三亚海棠湾开维费尔蒙酒店\n位于海棠湾，以海景、园林和水系景观为特色，适合高端家庭及休闲度假。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚海棠湾开维费尔蒙酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 276,
    "source_line_end": 276,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 22：三亚海棠湾阳光壹酒店

#### 原始叶子正文

```markdown
* **【三亚海棠湾阳光壹酒店】**：位于海棠湾、后海村方向，强调设计、自然材料和亲子体验，适合年轻家庭及设计酒店爱好者。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚海棠湾阳光壹酒店
三亚海棠湾阳光壹酒店
位于海棠湾、后海村方向，强调设计、自然材料和亲子体验，适合年轻家庭及设计酒店爱好者。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_87b9dafd7ad72c11",
  "text": "* **【三亚海棠湾阳光壹酒店】**：位于海棠湾、后海村方向，强调设计、自然材料和亲子体验，适合年轻家庭及设计酒店爱好者。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚海棠湾阳光壹酒店\n三亚海棠湾阳光壹酒店\n位于海棠湾、后海村方向，强调设计、自然材料和亲子体验，适合年轻家庭及设计酒店爱好者。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚海棠湾阳光壹酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 277,
    "source_line_end": 277,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 23：三亚亚特兰蒂斯酒店

#### 原始叶子正文

```markdown
* **【三亚亚特兰蒂斯酒店】**：位于海棠湾，与水世界和失落的空间水族馆相连，适合亲子玩水和一站式度假。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚亚特兰蒂斯酒店
三亚亚特兰蒂斯酒店
位于海棠湾，与水世界和失落的空间水族馆相连，适合亲子玩水和一站式度假。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_8ec7b59234173528",
  "text": "* **【三亚亚特兰蒂斯酒店】**：位于海棠湾，与水世界和失落的空间水族馆相连，适合亲子玩水和一站式度假。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚亚特兰蒂斯酒店\n三亚亚特兰蒂斯酒店\n位于海棠湾，与水世界和失落的空间水族馆相连，适合亲子玩水和一站式度假。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚亚特兰蒂斯酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 278,
    "source_line_end": 278,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 24：三亚艾迪逊酒店

#### 原始叶子正文

```markdown
* **【三亚艾迪逊酒店】**：位于海棠湾、三亚国际免税城附近，强调设计、私密度和高端度假体验。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚艾迪逊酒店
三亚艾迪逊酒店
位于海棠湾、三亚国际免税城附近，强调设计、私密度和高端度假体验。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_9a7c6276bf317d18",
  "text": "* **【三亚艾迪逊酒店】**：位于海棠湾、三亚国际免税城附近，强调设计、私密度和高端度假体验。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚艾迪逊酒店\n三亚艾迪逊酒店\n位于海棠湾、三亚国际免税城附近，强调设计、私密度和高端度假体验。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚艾迪逊酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 279,
    "source_line_end": 279,
    "is_embedded": true
  }
}
```

### 叶子 Chunk 25：三亚保利瑰丽酒店

#### 原始叶子正文

```markdown
* **【三亚保利瑰丽酒店】**：位于海棠湾，部分公共空间和房型具有高层海景，适合情侣、商务和高端度假。酒店预算：**500 元/晚以上**。
```

#### 实际 Embedding 输入

```text
三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚保利瑰丽酒店
三亚保利瑰丽酒店
位于海棠湾，部分公共空间和房型具有高层海景，适合情侣、商务和高端度假。酒店预算：500 元/晚以上。
```

#### 完整存储对象

```json
{
  "chunk_id": "epv1_2c2c0871627eb808",
  "text": "* **【三亚保利瑰丽酒店】**：位于海棠湾，部分公共空间和房型具有高层海景，适合情侣、商务和高端度假。酒店预算：**500 元/晚以上**。",
  "embedding_text": "三亚 > 住宿区域建议 > 豪华型（500 元/晚以上） > 三亚保利瑰丽酒店\n三亚保利瑰丽酒店\n位于海棠湾，部分公共空间和房型具有高层海景，适合情侣、商务和高端度假。酒店预算：500 元/晚以上。",
  "metadata": {
    "strategy_name": "entity_parent_v1",
    "strategy_version": "1.0",
    "document_id": "sanya_guide",
    "document_title": "2026 三亚深度游玩全攻略",
    "destination": "三亚",
    "source": "sanya_guide.md",
    "chunk_level": 3,
    "chunk_type": "hotel_entity_leaf",
    "entity_name": "三亚保利瑰丽酒店",
    "section_title": "4. 住宿区域建议",
    "category_title": "豪华型（500 元/晚以上）",
    "parent_id": "epv1_7d8ef5b0fa16e6d2",
    "root_id": "epv1_8c7224265764862b",
    "child_ids": [],
    "source_line_start": 280,
    "source_line_end": 280,
    "is_embedded": true
  }
}
```

## 4. 切片前后数量变化

| 对比项 | 数量 |
|---|---:|
| 原策略下整个豪华型分类 | 1 个大 Chunk |
| 新策略的文档根节点（根祖先） | 1 |
| 新策略的章节节点（祖父层） | 1 |
| 新策略的分类节点（酒店的直接父节点） | 1 |
| 新策略的酒店叶子节点 | 25 |
| 本示例总节点数 | 28 |
| 实际生成 Embedding 的节点数 | 25 |

检索时，向量数据库比较的是 25 个独立酒店叶子的 `embedding_text`，而不是把 25 家酒店混在同一个大 Chunk 中。每个酒店对象只有一个 `parent_id`，它指向 `category_parent`；然后 `category_parent.parent_id` 再指向 `section_parent`，`section_parent.parent_id` 最后指向 `document_root`。因此数据结构是一条逐级祖先链，而不是一个酒店同时拥有三个并列父节点。