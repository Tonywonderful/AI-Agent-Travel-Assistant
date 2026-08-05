# RAG 测试问题与 qrels 答案打分明细（v4）

## 评分规则

- **3 分**：直接回答 Query 核心对象，或同时覆盖多个核心意图。
- **2 分**：直接满足一个重要子意图，可以支持旅行决策。
- **1 分**：背景、顺路、泛主题或弱相关；不计入正式正确答案。
- **0 分**：不能实质回答 Query。为避免报告过长，本报告不展开 1500 条 0 分记录；完整记录见 `backend/eval/rag_qrels_v4_annotations.json`。
- 正式相关阈值：`relevance >= 2`。

## 总览

| # | Case ID | 测试问题 | 3 分 | 2 分 | 1 分 | 正式相关 |
|---:|---|---|---:|---:|---:|---:|
| 1 | `dali_sunset_easy_photo` | 大理 洱海 日落 拍照 轻松 不早起 | 5 | 8 | 5 | 13 |
| 2 | `dali_culture_slow_trip` | 大理 白族文化 古镇 扎染 崇圣寺 慢节奏 | 7 | 15 | 8 | 22 |
| 3 | `dali_food_budget` | 大理 特色美食 小吃 餐厅 人均预算 | 15 | 5 | 2 | 20 |
| 4 | `chengdu_relax_food` | 成都 带父母 轻松 慢生活 美食 文化 | 6 | 47 | 10 | 53 |
| 5 | `chengdu_food_deep` | 成都 特色小吃 火锅 担担面 兔头 美食 | 10 | 28 | 4 | 38 |
| 6 | `chengdu_park_old_town_nature` | 成都 城市公园 古镇 自然风景 轻松 | 16 | 5 | 3 | 21 |
| 7 | `xian_history_culture` | 西安 历史文化 古迹 博物馆 遗址 深度游 | 8 | 3 | 6 | 11 |
| 8 | `xian_food_night` | 西安 特色小吃 夜市 本地餐馆 美食 | 7 | 16 | 5 | 23 |
| 9 | `xian_family_study` | 西安 亲子 研学 历史文化 轻松 | 5 | 8 | 7 | 13 |
| 10 | `xiamen_couple_relax` | 厦门 情侣 鼓浪屿 文艺 美食 轻松 | 8 | 29 | 2 | 37 |
| 11 | `xiamen_architecture_history` | 厦门 建筑 历史 南普陀寺 胡里山炮台 | 5 | 5 | 2 | 10 |
| 12 | `xiamen_bike_sea` | 厦门 海边骑行 海景 日落 休闲 | 1 | 2 | 2 | 3 |
| 13 | `sanya_beach_resort` | 三亚 海滩 度假 酒店 放松 | 28 | 18 | 4 | 46 |
| 14 | `sanya_family_relax` | 三亚 家庭游 海滩 文化景区 轻松活动 | 22 | 19 | 3 | 41 |
| 15 | `sanya_seafood_culture` | 三亚 新鲜海鲜 椰子鸡 南山寺 文化 | 14 | 10 | 1 | 24 |
| 16 | `beijing_history_palace` | 北京 第一次 故宫 天安门 皇家历史文化 | 5 | 13 | 6 | 18 |
| 17 | `beijing_food_local` | 北京 老北京美食 烤鸭 炸酱面 豆汁 小吃 | 18 | 22 | 2 | 40 |
| 18 | `beijing_family_study` | 北京 亲子 研学 天安门 故宫 历史文化 | 6 | 11 | 6 | 17 |

## 逐题 qrels 明细

### 1. `dali_sunset_easy_photo`

- **目的地**：大理
- **测试问题**：大理 洱海 日落 拍照 轻松 不早起
- **正式相关数量**：13（3 分 5 条，2 分 8 条）
- **弱相关数量**：5（1 分，不计入正式答案）

#### 3 分：核心答案（5 条）

- **3 分**｜`dali_guide.md::2.5 大理180度海景网红打卡地`｜类别：`guide`
- **3 分**｜`dali_guide.md::2.26 双廊古镇`｜类别：`guide`
- **3 分**｜`dali_guide.md::真美度假客栈（大理洱海悬崖海景店）`｜类别：`hotel`
- **3 分**｜`dali_guide.md::拾光映月·ShiGuang中古奢设计师海景度假美宿（大理双廊洱海店）`｜类别：`hotel`
- **3 分**｜`dali_guide.md::双廊露娜·蓝泊湾`｜类别：`hotel`

#### 2 分：正式相关答案（8 条）

- **2 分**｜`dali_guide.md::2.16 洱海生态廊道`｜类别：`guide`
- **2 分**｜`dali_guide.md::2.19 磻溪村S湾`｜类别：`guide`
- **2 分**｜`dali_guide.md::2.29 罗荃半岛旅游区`｜类别：`guide`
- **2 分**｜`dali_guide.md::2.30 洱海公园`｜类别：`guide`
- **2 分**｜`dali_guide.md::大理栖苑·蓝谷栖海景民宿（磻溪S湾店）`｜类别：`hotel`
- **2 分**｜`dali_guide.md::大理松云悬崖酒店`｜类别：`hotel`
- **2 分**｜`dali_guide.md::大理懒人吾舍·隐奢海景美宿`｜类别：`hotel`
- **2 分**｜`dali_guide.md::六阅·無所海景度假民宿（大理洱海双廊店）`｜类别：`hotel`

#### 1 分：弱相关答案（5 条）

- **1 分**｜`dali_guide.md::2.17 龙龛码头与龙龛村`｜类别：`guide`
- **1 分**｜`dali_guide.md::2.18 才村码头`｜类别：`guide`
- **1 分**｜`dali_guide.md::2.20 古生村与古生村廊桥`｜类别：`guide`
- **1 分**｜`dali_guide.md::2.24 海舌生态公园`｜类别：`guide`
- **1 分**｜`dali_guide.md::2.28 小普陀`｜类别：`guide`

### 2. `dali_culture_slow_trip`

- **目的地**：大理
- **测试问题**：大理 白族文化 古镇 扎染 崇圣寺 慢节奏
- **正式相关数量**：22（3 分 7 条，2 分 15 条）
- **弱相关数量**：8（1 分，不计入正式答案）

#### 3 分：核心答案（7 条）

- **3 分**｜`dali_guide.md::2.2 崇圣寺三塔文化旅游区`｜类别：`guide`
- **3 分**｜`dali_guide.md::2.21 喜洲古镇`｜类别：`guide`
- **3 分**｜`dali_guide.md::2.22 严家大院`｜类别：`guide`
- **3 分**｜`dali_guide.md::2.23 周城村与白族扎染体验`｜类别：`guide`
- **3 分**｜`dali_guide.md::2.31 大理白族自治州博物馆`｜类别：`guide`
- **3 分**｜`dali_guide.md::2.32 大理州非物质文化遗产博物馆`｜类别：`guide`
- **3 分**｜`dali_guide.md::2.41 剑川古城`｜类别：`guide`

#### 2 分：正式相关答案（15 条）

- **2 分**｜`dali_guide.md::2.1 大理古城-南门楼`｜类别：`guide`
- **2 分**｜`dali_guide.md::2.6 大理市博物馆（杜文秀帅府）`｜类别：`guide`
- **2 分**｜`dali_guide.md::2.7 大理文庙`｜类别：`guide`
- **2 分**｜`dali_guide.md::2.15 凤阳邑茶马古道`｜类别：`guide`
- **2 分**｜`dali_guide.md::2.20 古生村与古生村廊桥`｜类别：`guide`
- **2 分**｜`dali_guide.md::2.25 蝴蝶泉公园`｜类别：`guide`
- **2 分**｜`dali_guide.md::2.36 凤羽古镇`｜类别：`guide`
- **2 分**｜`dali_guide.md::2.38 沙溪古镇`｜类别：`guide`
- **2 分**｜`dali_guide.md::2.40 石钟山石窟`｜类别：`guide`
- **2 分**｜`dali_guide.md::2.42 巍山古城`｜类别：`guide`
- **2 分**｜`dali_guide.md::2.47 鹤庆新华银器小镇`｜类别：`guide`
- **2 分**｜`dali_guide.md::菜品：白族三道茶`｜类别：`dish`
- **2 分**｜`dali_guide.md::阿鹏金花客栈（大理古城人民路店）`｜类别：`hotel`
- **2 分**｜`dali_guide.md::Aurora·云岭之南白族风情文旅客栈（洱海才村店）`｜类别：`hotel`
- **2 分**｜`dali_guide.md::大理古城银峰酒店`｜类别：`hotel`

#### 1 分：弱相关答案（8 条）

- **1 分**｜`dali_guide.md::2.3 洋人街`｜类别：`guide`
- **1 分**｜`dali_guide.md::2.4 大理古城红龙井`｜类别：`guide`
- **1 分**｜`dali_guide.md::2.37 宾川鸡足山`｜类别：`guide`
- **1 分**｜`dali_guide.md::2.43 巍宝山`｜类别：`guide`
- **1 分**｜`dali_guide.md::2.44 东莲花村`｜类别：`guide`
- **1 分**｜`dali_guide.md::2.45 诺邓古村`｜类别：`guide`
- **1 分**｜`dali_guide.md::菜品：白族生皮`｜类别：`dish`
- **1 分**｜`dali_guide.md::菜品：喜洲粑粑`｜类别：`dish`

### 3. `dali_food_budget`

- **目的地**：大理
- **测试问题**：大理 特色美食 小吃 餐厅 人均预算
- **正式相关数量**：20（3 分 15 条，2 分 5 条）
- **弱相关数量**：2（1 分，不计入正式答案）

#### 3 分：核心答案（15 条）

- **3 分**｜`dali_guide.md::餐饮：大理乐客特色小吃`｜类别：`restaurant`
- **3 分**｜`dali_guide.md::餐饮：梅子井酒家`｜类别：`restaurant`
- **3 分**｜`dali_guide.md::餐饮：花与菌野生菌火锅（大理古城人民路店）`｜类别：`restaurant`
- **3 分**｜`dali_guide.md::菜品：酸辣鱼与砂锅鱼`｜类别：`dish`
- **3 分**｜`dali_guide.md::菜品：白族生皮`｜类别：`dish`
- **3 分**｜`dali_guide.md::菜品：白族三道茶`｜类别：`dish`
- **3 分**｜`dali_guide.md::菜品：喜洲粑粑`｜类别：`dish`
- **3 分**｜`dali_guide.md::菜品：乳扇`｜类别：`dish`
- **3 分**｜`dali_guide.md::菜品：饵丝、饵块和米线`｜类别：`dish`
- **3 分**｜`dali_guide.md::菜品：凉鸡米线、米凉虾与油粉`｜类别：`dish`
- **3 分**｜`dali_guide.md::菜品：巍山小吃与耙肉饵丝`｜类别：`dish`
- **3 分**｜`dali_guide.md::菜品：永平黄焖鸡`｜类别：`dish`
- **3 分**｜`dali_guide.md::菜品：云龙诺邓火腿`｜类别：`dish`
- **3 分**｜`dali_guide.md::菜品：剑川八大碗与鹤庆米糕`｜类别：`dish`
- **3 分**｜`dali_guide.md::餐饮提示：预算与选择原则`｜类别：`dining_advice`

#### 2 分：正式相关答案（5 条）

- **2 分**｜`dali_guide.md::餐饮：避风塘大理特色小吃`｜类别：`restaurant`
- **2 分**｜`dali_guide.md::餐饮：渝记酸萝卜乌江鱼（大理古城总店）`｜类别：`restaurant`
- **2 分**｜`dali_guide.md::餐饮：大理真美洱海悬崖酒店·海景网红餐厅`｜类别：`restaurant`
- **2 分**｜`dali_guide.md::菜品：洱源雕梅`｜类别：`dish`
- **2 分**｜`dali_guide.md::餐饮提示：野生菌食用安全`｜类别：`dining_advice`

#### 1 分：弱相关答案（2 条）

- **1 分**｜`dali_guide.md::2.21 喜洲古镇`｜类别：`guide`
- **1 分**｜`dali_guide.md::2.45 诺邓古村`｜类别：`guide`

### 4. `chengdu_relax_food`

- **目的地**：成都
- **测试问题**：成都 带父母 轻松 慢生活 美食 文化
- **正式相关数量**：53（3 分 6 条，2 分 47 条）
- **弱相关数量**：10（1 分，不计入正式答案）

#### 3 分：核心答案（6 条）

- **3 分**｜`chengdu_guide.md::2.1 宽窄巷子景区`｜类别：`guide`
- **3 分**｜`chengdu_guide.md::2.8 人民公园（城市生活）`｜类别：`guide`
- **3 分**｜`chengdu_guide.md::2.11 望江楼公园（园林与名人文化）`｜类别：`guide`
- **3 分**｜`chengdu_guide.md::餐饮：成都映象`｜类别：`restaurant`
- **3 分**｜`chengdu_guide.md::餐饮：顺兴老茶馆`｜类别：`restaurant`
- **3 分**｜`chengdu_guide.md::餐饮提示：成都小吃选择`｜类别：`dining_advice`

#### 2 分：正式相关答案（47 条）

- **2 分**｜`chengdu_guide.md::2.2 锦城公园`｜类别：`guide`
- **2 分**｜`chengdu_guide.md::2.5 成都武侯祠博物馆（历史文化）`｜类别：`guide`
- **2 分**｜`chengdu_guide.md::2.6 锦里古街（历史街区与夜游）`｜类别：`guide`
- **2 分**｜`chengdu_guide.md::2.7 成都杜甫草堂博物馆（历史文化）`｜类别：`guide`
- **2 分**｜`chengdu_guide.md::2.9 文殊院（历史文化与宗教场所）`｜类别：`guide`
- **2 分**｜`chengdu_guide.md::2.10 青羊宫（历史文化与宗教场所）`｜类别：`guide`
- **2 分**｜`chengdu_guide.md::2.12 大慈寺与成都远洋太古里（古今城市空间）`｜类别：`guide`
- **2 分**｜`chengdu_guide.md::2.14 奎星楼街（城市美食街区）`｜类别：`guide`
- **2 分**｜`chengdu_guide.md::2.15 玉林街区（城市漫步与夜生活）`｜类别：`guide`
- **2 分**｜`chengdu_guide.md::2.18 成都博物馆（博物馆与研学）`｜类别：`guide`
- **2 分**｜`chengdu_guide.md::2.19 四川博物院（博物馆与研学）`｜类别：`guide`
- **2 分**｜`chengdu_guide.md::2.20 成都金沙遗址博物馆（古蜀文明）`｜类别：`guide`
- **2 分**｜`chengdu_guide.md::2.25 成都蜀锦织绣博物馆（非遗与工艺）`｜类别：`guide`
- **2 分**｜`chengdu_guide.md::2.26 浣花溪公园（城市公园）`｜类别：`guide`
- **2 分**｜`chengdu_guide.md::2.27 天府艺术公园（城市公园与艺术）`｜类别：`guide`
- **2 分**｜`chengdu_guide.md::餐饮：老成都张妹特色小吃（现代大厦店）`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：龙抄手`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：钟水饺`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：赖汤圆`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：洞子口张老二凉粉`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：甘记肥肠粉`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：百年粉蒸牛肉`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：曾牛肉（青羊）`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：马旺子·川小馆（成都太古里店）`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：陶德砂锅（建设路店）`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：陈麻婆豆腐（青华路）`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：龙森园（青羊）`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：明婷饭店`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：饕林餐厅`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：皇城老妈`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：小龙坎老火锅`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：大龙燚火锅`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：蜀大侠火锅`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：冯校长老火锅（太古里总店）`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：玉芝兰`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：柴门荟`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：芳香景`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：芙蓉凰`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：马旺子（锦江）`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：银锅`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：许家菜`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：漾亚·雍雅合鲜（桐梓林东路）`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮提示：川菜入门`｜类别：`dining_advice`
- **2 分**｜`chengdu_guide.md::餐饮提示：火锅点餐与食用安全`｜类别：`dining_advice`
- **2 分**｜`chengdu_guide.md::餐饮街区：春熙路—太古里`｜类别：`food_district`
- **2 分**｜`chengdu_guide.md::餐饮街区：玉林—桐梓林`｜类别：`food_district`
- **2 分**｜`chengdu_guide.md::餐饮街区：建设路`｜类别：`food_district`

#### 1 分：弱相关答案（10 条）

- **1 分**｜`chengdu_guide.md::2.3 黄龙溪古镇`｜类别：`guide`
- **1 分**｜`chengdu_guide.md::2.13 东郊记忆（工业遗产与文创）`｜类别：`guide`
- **1 分**｜`chengdu_guide.md::2.16 九眼桥与锦江绿道（城市夜景）`｜类别：`guide`
- **1 分**｜`chengdu_guide.md::餐饮：魏斯理汉堡（成都金牛万达广场店）`｜类别：`restaurant`
- **1 分**｜`chengdu_guide.md::餐饮：陶陶居酒家（成都太古里店）`｜类别：`restaurant`
- **1 分**｜`chengdu_guide.md::餐饮：新荣记（成都）`｜类别：`restaurant`
- **1 分**｜`chengdu_guide.md::餐饮：谧寻茶室`｜类别：`restaurant`
- **1 分**｜`chengdu_guide.md::餐饮：蔻 Co-`｜类别：`restaurant`
- **1 分**｜`chengdu_guide.md::餐饮：福满楼`｜类别：`restaurant`
- **1 分**｜`chengdu_guide.md::餐饮：会馆 The Hall`｜类别：`restaurant`

### 5. `chengdu_food_deep`

- **目的地**：成都
- **测试问题**：成都 特色小吃 火锅 担担面 兔头 美食
- **正式相关数量**：38（3 分 10 条，2 分 28 条）
- **弱相关数量**：4（1 分，不计入正式答案）

#### 3 分：核心答案（10 条）

- **3 分**｜`chengdu_guide.md::2.14 奎星楼街（城市美食街区）`｜类别：`guide`
- **3 分**｜`chengdu_guide.md::餐饮：老成都张妹特色小吃（现代大厦店）`｜类别：`restaurant`
- **3 分**｜`chengdu_guide.md::餐饮：马旺子·川小馆（成都太古里店）`｜类别：`restaurant`
- **3 分**｜`chengdu_guide.md::餐饮：龙森园（青羊）`｜类别：`restaurant`
- **3 分**｜`chengdu_guide.md::餐饮：皇城老妈`｜类别：`restaurant`
- **3 分**｜`chengdu_guide.md::餐饮：小龙坎老火锅`｜类别：`restaurant`
- **3 分**｜`chengdu_guide.md::餐饮：大龙燚火锅`｜类别：`restaurant`
- **3 分**｜`chengdu_guide.md::餐饮：蜀大侠火锅`｜类别：`restaurant`
- **3 分**｜`chengdu_guide.md::餐饮：冯校长老火锅（太古里总店）`｜类别：`restaurant`
- **3 分**｜`chengdu_guide.md::餐饮提示：火锅点餐与食用安全`｜类别：`dining_advice`

#### 2 分：正式相关答案（28 条）

- **2 分**｜`chengdu_guide.md::2.6 锦里古街（历史街区与夜游）`｜类别：`guide`
- **2 分**｜`chengdu_guide.md::2.15 玉林街区（城市漫步与夜生活）`｜类别：`guide`
- **2 分**｜`chengdu_guide.md::餐饮：龙抄手`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：钟水饺`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：赖汤圆`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：洞子口张老二凉粉`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：甘记肥肠粉`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：百年粉蒸牛肉`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：曾牛肉（青羊）`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：陶德砂锅（建设路店）`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：陈麻婆豆腐（青华路）`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：明婷饭店`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：饕林餐厅`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：成都映象`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：顺兴老茶馆`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：玉芝兰`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：柴门荟`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：芳香景`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：芙蓉凰`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：马旺子（锦江）`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：银锅`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：许家菜`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮：漾亚·雍雅合鲜（桐梓林东路）`｜类别：`restaurant`
- **2 分**｜`chengdu_guide.md::餐饮提示：川菜入门`｜类别：`dining_advice`
- **2 分**｜`chengdu_guide.md::餐饮提示：成都小吃选择`｜类别：`dining_advice`
- **2 分**｜`chengdu_guide.md::餐饮街区：春熙路—太古里`｜类别：`food_district`
- **2 分**｜`chengdu_guide.md::餐饮街区：玉林—桐梓林`｜类别：`food_district`
- **2 分**｜`chengdu_guide.md::餐饮街区：建设路`｜类别：`food_district`

#### 1 分：弱相关答案（4 条）

- **1 分**｜`chengdu_guide.md::2.9 文殊院（历史文化与宗教场所）`｜类别：`guide`
- **1 分**｜`chengdu_guide.md::餐饮：陶陶居酒家（成都太古里店）`｜类别：`restaurant`
- **1 分**｜`chengdu_guide.md::餐饮：谧寻茶室`｜类别：`restaurant`
- **1 分**｜`chengdu_guide.md::餐饮：蔻 Co-`｜类别：`restaurant`

### 6. `chengdu_park_old_town_nature`

- **目的地**：成都
- **测试问题**：成都 城市公园 古镇 自然风景 轻松
- **正式相关数量**：21（3 分 16 条，2 分 5 条）
- **弱相关数量**：3（1 分，不计入正式答案）

#### 3 分：核心答案（16 条）

- **3 分**｜`chengdu_guide.md::2.2 锦城公园`｜类别：`guide`
- **3 分**｜`chengdu_guide.md::2.3 黄龙溪古镇`｜类别：`guide`
- **3 分**｜`chengdu_guide.md::2.8 人民公园（城市生活）`｜类别：`guide`
- **3 分**｜`chengdu_guide.md::2.11 望江楼公园（园林与名人文化）`｜类别：`guide`
- **3 分**｜`chengdu_guide.md::2.26 浣花溪公园（城市公园）`｜类别：`guide`
- **3 分**｜`chengdu_guide.md::2.27 天府艺术公园（城市公园与艺术）`｜类别：`guide`
- **3 分**｜`chengdu_guide.md::2.28 桂溪生态公园（城市公园）`｜类别：`guide`
- **3 分**｜`chengdu_guide.md::2.29 兴隆湖湿地公园（城市公园）`｜类别：`guide`
- **3 分**｜`chengdu_guide.md::2.30 东安湖公园（城市公园与体育地标）`｜类别：`guide`
- **3 分**｜`chengdu_guide.md::2.35 洛带古镇（古镇与客家文化）`｜类别：`guide`
- **3 分**｜`chengdu_guide.md::2.36 安仁古镇（古镇与博物馆）`｜类别：`guide`
- **3 分**｜`chengdu_guide.md::2.37 平乐古镇（古镇与山水）`｜类别：`guide`
- **3 分**｜`chengdu_guide.md::2.38 街子古镇（古镇与山水）`｜类别：`guide`
- **3 分**｜`chengdu_guide.md::2.39 元通古镇（古镇与建筑）`｜类别：`guide`
- **3 分**｜`chengdu_guide.md::2.40 五凤溪古镇（古镇与山水）`｜类别：`guide`
- **3 分**｜`chengdu_guide.md::2.41 新场古镇（古镇与川西生活）`｜类别：`guide`

#### 2 分：正式相关答案（5 条）

- **2 分**｜`chengdu_guide.md::2.31 成都植物园（植物与亲子）`｜类别：`guide`
- **2 分**｜`chengdu_guide.md::2.46 成都天台山旅游景区（山水与生态）`｜类别：`guide`
- **2 分**｜`chengdu_guide.md::2.47 龙泉山城市森林公园丹景台（城市远眺）`｜类别：`guide`
- **2 分**｜`chengdu_guide.md::2.48 石象湖景区（花卉与湖泊）`｜类别：`guide`
- **2 分**｜`chengdu_guide.md::2.50 花舞人间景区（花卉与亲子）`｜类别：`guide`

#### 1 分：弱相关答案（3 条）

- **1 分**｜`chengdu_guide.md::2.44 青城后山（山水徒步）`｜类别：`guide`
- **1 分**｜`chengdu_guide.md::2.45 西岭雪山（山地与冰雪）`｜类别：`guide`
- **1 分**｜`chengdu_guide.md::2.49 川西竹海景区（竹林徒步）`｜类别：`guide`

### 7. `xian_history_culture`

- **目的地**：西安
- **测试问题**：西安 历史文化 古迹 博物馆 遗址 深度游
- **正式相关数量**：11（3 分 8 条，2 分 3 条）
- **弱相关数量**：6（1 分，不计入正式答案）

#### 3 分：核心答案（8 条）

- **3 分**｜`xian_guide.md::2.2 大明宫国家遗址公园`｜类别：`guide`
- **3 分**｜`xian_guide.md::2.3 秦始皇帝陵博物院`｜类别：`guide`
- **3 分**｜`xian_guide.md::2.5 西安城墙`｜类别：`guide`
- **3 分**｜`xian_guide.md::2.7 陕西历史博物馆`｜类别：`guide`
- **3 分**｜`xian_guide.md::2.8 大慈恩寺与大雁塔`｜类别：`guide`
- **3 分**｜`xian_guide.md::2.11 华清宫`｜类别：`guide`
- **3 分**｜`xian_guide.md::2.14 西安碑林博物馆`｜类别：`guide`
- **3 分**｜`xian_guide.md::2.15 西安博物院与小雁塔`｜类别：`guide`

#### 2 分：正式相关答案（3 条）

- **2 分**｜`xian_guide.md::2.4 曲江池遗址公园`｜类别：`guide`
- **2 分**｜`xian_guide.md::2.6 西安钟楼与鼓楼`｜类别：`guide`
- **2 分**｜`xian_guide.md::2.13 骊山与骊山索道`｜类别：`guide`

#### 1 分：弱相关答案（6 条）

- **1 分**｜`xian_guide.md::2.1 西安千古情售票厅`｜类别：`guide`
- **1 分**｜`xian_guide.md::2.9 大唐不夜城`｜类别：`guide`
- **1 分**｜`xian_guide.md::2.10 大唐芙蓉园`｜类别：`guide`
- **1 分**｜`xian_guide.md::2.12 《长恨歌》实景演出`｜类别：`guide`
- **1 分**｜`xian_guide.md::2.16 长安十二时辰主题街区`｜类别：`guide`
- **1 分**｜`xian_guide.md::2.20 白鹿原·白鹿仓`｜类别：`guide`

### 8. `xian_food_night`

- **目的地**：西安
- **测试问题**：西安 特色小吃 夜市 本地餐馆 美食
- **正式相关数量**：23（3 分 7 条，2 分 16 条）
- **弱相关数量**：5（1 分，不计入正式答案）

#### 3 分：核心答案（7 条）

- **3 分**｜`xian_guide.md::餐饮：子午路张记肉夹馍（翠华路店）`｜类别：`restaurant`
- **3 分**｜`xian_guide.md::餐饮：刘信牛羊肉泡馍小炒（洒金桥店）`｜类别：`restaurant`
- **3 分**｜`xian_guide.md::餐饮：袁家村关中美食（曲江银泰城店）`｜类别：`restaurant`
- **3 分**｜`xian_guide.md::餐饮：同盛祥`｜类别：`restaurant`
- **3 分**｜`xian_guide.md::餐饮：老孙家饭庄`｜类别：`restaurant`
- **3 分**｜`xian_guide.md::餐饮：长安大牌档`｜类别：`restaurant`
- **3 分**｜`xian_guide.md::餐饮：西安菜馆·秦唐一号（钟楼店）`｜类别：`restaurant`

#### 2 分：正式相关答案（16 条）

- **2 分**｜`xian_guide.md::2.6 西安钟楼与鼓楼`｜类别：`guide`
- **2 分**｜`xian_guide.md::餐饮：魏家凉皮（西大街店）`｜类别：`restaurant`
- **2 分**｜`xian_guide.md::餐饮：樊记腊汁肉夹馍（竹笆市店）`｜类别：`restaurant`
- **2 分**｜`xian_guide.md::餐饮：柳巷面（吉庆巷店）`｜类别：`restaurant`
- **2 分**｜`xian_guide.md::餐饮：爱骅裤带面馆`｜类别：`restaurant`
- **2 分**｜`xian_guide.md::餐饮：贾三清真灌汤包子（北院门总店）`｜类别：`restaurant`
- **2 分**｜`xian_guide.md::餐饮：定家小酥肉（大皮院店）`｜类别：`restaurant`
- **2 分**｜`xian_guide.md::餐饮：陕拾叁`｜类别：`restaurant`
- **2 分**｜`xian_guide.md::餐饮：志亮灌汤蒸饺·清真`｜类别：`restaurant`
- **2 分**｜`xian_guide.md::餐饮：虎子水盆羊肉（翠华路总店）`｜类别：`restaurant`
- **2 分**｜`xian_guide.md::餐饮：西安饭庄`｜类别：`restaurant`
- **2 分**｜`xian_guide.md::餐饮：德发长饺子（钟楼店或大唐不夜城店）`｜类别：`restaurant`
- **2 分**｜`xian_guide.md::餐饮：八百里秦川陕菜`｜类别：`restaurant`
- **2 分**｜`xian_guide.md::餐饮：窄巷子陕菜馆`｜类别：`restaurant`
- **2 分**｜`xian_guide.md::餐饮：三原老黄家（文艺路店）`｜类别：`restaurant`
- **2 分**｜`xian_guide.md::餐饮：醉长安`｜类别：`restaurant`

#### 1 分：弱相关答案（5 条）

- **1 分**｜`xian_guide.md::2.9 大唐不夜城`｜类别：`guide`
- **1 分**｜`xian_guide.md::2.16 长安十二时辰主题街区`｜类别：`guide`
- **1 分**｜`xian_guide.md::餐饮：魏斯理汉堡（西安文艺路地铁站店）`｜类别：`restaurant`
- **1 分**｜`xian_guide.md::餐饮：肥肥虾庄（高新店）`｜类别：`restaurant`
- **1 分**｜`xian_guide.md::餐饮：幸福老火锅（总店）`｜类别：`restaurant`

### 9. `xian_family_study`

- **目的地**：西安
- **测试问题**：西安 亲子 研学 历史文化 轻松
- **正式相关数量**：13（3 分 5 条，2 分 8 条）
- **弱相关数量**：7（1 分，不计入正式答案）

#### 3 分：核心答案（5 条）

- **3 分**｜`xian_guide.md::2.2 大明宫国家遗址公园`｜类别：`guide`
- **3 分**｜`xian_guide.md::2.3 秦始皇帝陵博物院`｜类别：`guide`
- **3 分**｜`xian_guide.md::2.7 陕西历史博物馆`｜类别：`guide`
- **3 分**｜`xian_guide.md::2.14 西安碑林博物馆`｜类别：`guide`
- **3 分**｜`xian_guide.md::2.15 西安博物院与小雁塔`｜类别：`guide`

#### 2 分：正式相关答案（8 条）

- **2 分**｜`xian_guide.md::2.4 曲江池遗址公园`｜类别：`guide`
- **2 分**｜`xian_guide.md::2.5 西安城墙`｜类别：`guide`
- **2 分**｜`xian_guide.md::2.6 西安钟楼与鼓楼`｜类别：`guide`
- **2 分**｜`xian_guide.md::2.8 大慈恩寺与大雁塔`｜类别：`guide`
- **2 分**｜`xian_guide.md::2.11 华清宫`｜类别：`guide`
- **2 分**｜`xian_guide.md::2.17 陕西自然博物馆`｜类别：`guide`
- **2 分**｜`xian_guide.md::2.19 西影电影博物馆`｜类别：`guide`
- **2 分**｜`xian_guide.md::2.20 白鹿原·白鹿仓`｜类别：`guide`

#### 1 分：弱相关答案（7 条）

- **1 分**｜`xian_guide.md::2.1 西安千古情售票厅`｜类别：`guide`
- **1 分**｜`xian_guide.md::2.9 大唐不夜城`｜类别：`guide`
- **1 分**｜`xian_guide.md::2.10 大唐芙蓉园`｜类别：`guide`
- **1 分**｜`xian_guide.md::2.12 《长恨歌》实景演出`｜类别：`guide`
- **1 分**｜`xian_guide.md::2.13 骊山与骊山索道`｜类别：`guide`
- **1 分**｜`xian_guide.md::2.16 长安十二时辰主题街区`｜类别：`guide`
- **1 分**｜`xian_guide.md::2.18 曲江海洋极地公园`｜类别：`guide`

### 10. `xiamen_couple_relax`

- **目的地**：厦门
- **测试问题**：厦门 情侣 鼓浪屿 文艺 美食 轻松
- **正式相关数量**：37（3 分 8 条，2 分 29 条）
- **弱相关数量**：2（1 分，不计入正式答案）

#### 3 分：核心答案（8 条）

- **3 分**｜`xiamen_guide.md::2.1 鼓浪屿风景名胜区`｜类别：`guide`
- **3 分**｜`xiamen_guide.md::2.10 钟鼓索道（城市与山海观景）`｜类别：`guide`
- **3 分**｜`xiamen_guide.md::2.12 沙坡尾艺术西区（老港口与文创街区）`｜类别：`guide`
- **3 分**｜`xiamen_guide.md::2.14 曾厝垵文创村（小吃、民宿与夜间休闲）`｜类别：`guide`
- **3 分**｜`xiamen_guide.md::2.21 厦门之眼海上摩天轮（五缘湾夜景与亲子体验）`｜类别：`guide`
- **3 分**｜`xiamen_guide.md::餐饮提示：精品咖啡或海景咖啡馆`｜类别：`dining_advice`
- **3 分**｜`xiamen_guide.md::餐饮提示：鼓浪屿、西堤或沙坡尾休闲餐饮`｜类别：`dining_advice`
- **3 分**｜`xiamen_guide.md::餐饮街区：沙坡尾`｜类别：`food_district`

#### 2 分：正式相关答案（29 条）

- **2 分**｜`xiamen_guide.md::2.2 日光岩`｜类别：`guide`
- **2 分**｜`xiamen_guide.md::2.5 菽庄花园（鼓浪屿园林与钢琴文化）`｜类别：`guide`
- **2 分**｜`xiamen_guide.md::2.6 皓月园（鼓浪屿历史文化与海滨景观）`｜类别：`guide`
- **2 分**｜`xiamen_guide.md::2.7 八卦楼风琴博物馆（鼓浪屿建筑与音乐文化）`｜类别：`guide`
- **2 分**｜`xiamen_guide.md::2.8 鼓浪屿管风琴艺术中心（鼓浪屿音乐文化）`｜类别：`guide`
- **2 分**｜`xiamen_guide.md::2.11 厦门大学思明校区（校园建筑与人文）`｜类别：`guide`
- **2 分**｜`xiamen_guide.md::2.13 环岛路与黄厝海滩（海滨骑行与日出）`｜类别：`guide`
- **2 分**｜`xiamen_guide.md::2.15 中山路步行街（骑楼建筑与老字号小吃）`｜类别：`guide`
- **2 分**｜`xiamen_guide.md::2.20 云上厦门观光厅（高空城市观景）`｜类别：`guide`
- **2 分**｜`xiamen_guide.md::餐饮：局口拌面（中山路店）`｜类别：`restaurant`
- **2 分**｜`xiamen_guide.md::餐饮：醉壹号海鲜大排档·老厦门特色菜（厦门美食地标店）`｜类别：`restaurant`
- **2 分**｜`xiamen_guide.md::餐饮：阿忠食坊大排档·20年老店（万象城店）`｜类别：`restaurant`
- **2 分**｜`xiamen_guide.md::餐饮：荣誉·海上江南`｜类别：`restaurant`
- **2 分**｜`xiamen_guide.md::餐饮：临家闽南菜（环岛路店）`｜类别：`restaurant`
- **2 分**｜`xiamen_guide.md::餐饮提示：厦门特色小吃概览`｜类别：`dining_advice`
- **2 分**｜`xiamen_guide.md::菜品：沙茶面`｜类别：`dish`
- **2 分**｜`xiamen_guide.md::菜品：土笋冻`｜类别：`dish`
- **2 分**｜`xiamen_guide.md::菜品：花生汤与烧肉粽`｜类别：`dish`
- **2 分**｜`xiamen_guide.md::菜品：面线糊`｜类别：`dish`
- **2 分**｜`xiamen_guide.md::菜品：海蛎煎`｜类别：`dish`
- **2 分**｜`xiamen_guide.md::菜品：五香卷`｜类别：`dish`
- **2 分**｜`xiamen_guide.md::餐饮提示：家常闽南菜馆选择`｜类别：`dining_advice`
- **2 分**｜`xiamen_guide.md::餐饮提示：普通海鲜排档选择`｜类别：`dining_advice`
- **2 分**｜`xiamen_guide.md::餐饮提示：中高端海鲜餐厅选择`｜类别：`dining_advice`
- **2 分**｜`xiamen_guide.md::餐饮提示：海鲜点餐计价`｜类别：`dining_advice`
- **2 分**｜`xiamen_guide.md::餐饮提示：烧烤与夜宵`｜类别：`dining_advice`
- **2 分**｜`xiamen_guide.md::餐饮街区：八市`｜类别：`food_district`
- **2 分**｜`xiamen_guide.md::餐饮街区：中山路`｜类别：`food_district`
- **2 分**｜`xiamen_guide.md::餐饮街区：曾厝垵`｜类别：`food_district`

#### 1 分：弱相关答案（2 条）

- **1 分**｜`xiamen_guide.md::2.9 厦门园林植物园（自然生态与摄影）`｜类别：`guide`
- **1 分**｜`xiamen_guide.md::2.16 集美学村与龙舟池（嘉庚建筑与学村文化）`｜类别：`guide`

### 11. `xiamen_architecture_history`

- **目的地**：厦门
- **测试问题**：厦门 建筑 历史 南普陀寺 胡里山炮台
- **正式相关数量**：10（3 分 5 条，2 分 5 条）
- **弱相关数量**：2（1 分，不计入正式答案）

#### 3 分：核心答案（5 条）

- **3 分**｜`xiamen_guide.md::2.1 鼓浪屿风景名胜区`｜类别：`guide`
- **3 分**｜`xiamen_guide.md::2.3 南普陀寺`｜类别：`guide`
- **3 分**｜`xiamen_guide.md::2.4 胡里山炮台`｜类别：`guide`
- **3 分**｜`xiamen_guide.md::2.7 八卦楼风琴博物馆（鼓浪屿建筑与音乐文化）`｜类别：`guide`
- **3 分**｜`xiamen_guide.md::2.16 集美学村与龙舟池（嘉庚建筑与学村文化）`｜类别：`guide`

#### 2 分：正式相关答案（5 条）

- **2 分**｜`xiamen_guide.md::2.5 菽庄花园（鼓浪屿园林与钢琴文化）`｜类别：`guide`
- **2 分**｜`xiamen_guide.md::2.6 皓月园（鼓浪屿历史文化与海滨景观）`｜类别：`guide`
- **2 分**｜`xiamen_guide.md::2.11 厦门大学思明校区（校园建筑与人文）`｜类别：`guide`
- **2 分**｜`xiamen_guide.md::2.12 沙坡尾艺术西区（老港口与文创街区）`｜类别：`guide`
- **2 分**｜`xiamen_guide.md::2.15 中山路步行街（骑楼建筑与老字号小吃）`｜类别：`guide`

#### 1 分：弱相关答案（2 条）

- **1 分**｜`xiamen_guide.md::2.2 日光岩`｜类别：`guide`
- **1 分**｜`xiamen_guide.md::2.8 鼓浪屿管风琴艺术中心（鼓浪屿音乐文化）`｜类别：`guide`

### 12. `xiamen_bike_sea`

- **目的地**：厦门
- **测试问题**：厦门 海边骑行 海景 日落 休闲
- **正式相关数量**：3（3 分 1 条，2 分 2 条）
- **弱相关数量**：2（1 分，不计入正式答案）

#### 3 分：核心答案（1 条）

- **3 分**｜`xiamen_guide.md::2.13 环岛路与黄厝海滩（海滨骑行与日出）`｜类别：`guide`

#### 2 分：正式相关答案（2 条）

- **2 分**｜`xiamen_guide.md::2.10 钟鼓索道（城市与山海观景）`｜类别：`guide`
- **2 分**｜`xiamen_guide.md::5. 预约、交通、价格与安全提示`｜类别：`guide`

#### 1 分：弱相关答案（2 条）

- **1 分**｜`xiamen_guide.md::2.12 沙坡尾艺术西区（老港口与文创街区）`｜类别：`guide`
- **1 分**｜`xiamen_guide.md::2.14 曾厝垵文创村（小吃、民宿与夜间休闲）`｜类别：`guide`

### 13. `sanya_beach_resort`

- **目的地**：三亚
- **测试问题**：三亚 海滩 度假 酒店 放松
- **正式相关数量**：46（3 分 28 条，2 分 18 条）
- **弱相关数量**：4（1 分，不计入正式答案）

#### 3 分：核心答案（28 条）

- **3 分**｜`sanya_guide.md::2.9 亚龙湾公共海滩`｜类别：`guide`
- **3 分**｜`sanya_guide.md::2.10 大东海旅游区`｜类别：`guide`
- **3 分**｜`sanya_guide.md::2.11 三亚湾与椰梦长廊`｜类别：`guide`
- **3 分**｜`sanya_guide.md::三亚阳光大酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚福朋喜来登酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚海韵度假酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚天丽湾凯悦酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚绿发山海天 JW 万豪酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚绿发山海天酒店·傲途格精选`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚珊瑚湾文华东方酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚悦榕庄`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚亚龙湾红树林度假酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚亚龙湾万豪度假酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚亚龙湾喜来登度假酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::金茂三亚亚龙湾丽思卡尔顿酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚亚龙湾希尔顿酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚亚龙湾美高梅度假酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚太阳湾柏悦酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚海棠湾君悦酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚海棠湾喜来登度假酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚海棠湾仁恒皇冠假日度假酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚海棠湾洲际度假酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚理文索菲特度假酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚海棠湾开维费尔蒙酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚海棠湾阳光壹酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚亚特兰蒂斯酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚艾迪逊酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚保利瑰丽酒店`｜类别：`hotel`

#### 2 分：正式相关答案（18 条）

- **2 分**｜`sanya_guide.md::2.6 蜈支洲岛旅游区`｜类别：`guide`
- **2 分**｜`sanya_guide.md::2.7 西岛海洋文化旅游区`｜类别：`guide`
- **2 分**｜`sanya_guide.md::2.12 后海村与皇后湾`｜类别：`guide`
- **2 分**｜`sanya_guide.md::2.19 天涯小镇`｜类别：`guide`
- **2 分**｜`sanya_guide.md::鸿韵旅租（三亚湾店）`｜类别：`hotel`
- **2 分**｜`sanya_guide.md::找商机青年旅舍（三亚湾椰梦长廊店）`｜类别：`hotel`
- **2 分**｜`sanya_guide.md::伴海时光酒店（三亚湾椰梦长廊店）`｜类别：`hotel`
- **2 分**｜`sanya_guide.md::三亚海聆酒店（三亚湾中心医院店）`｜类别：`hotel`
- **2 分**｜`sanya_guide.md::嘉宁·东海临海臻境酒店（大东海沙滩店）`｜类别：`hotel`
- **2 分**｜`sanya_guide.md::尚客优连锁酒店（三亚亚龙湾博后路店）`｜类别：`hotel`
- **2 分**｜`sanya_guide.md::三亚玉阙宾馆（三亚湾店）`｜类别：`hotel`
- **2 分**｜`sanya_guide.md::ROYAL HOTEL 臻瑞庭酒店（三亚湾椰梦长廊店）`｜类别：`hotel`
- **2 分**｜`sanya_guide.md::三亚怡庭酒店（三亚湾椰梦长廊店）`｜类别：`hotel`
- **2 分**｜`sanya_guide.md::三亚柏瑞精品海景酒店（大东海广场店）`｜类别：`hotel`
- **2 分**｜`sanya_guide.md::三亚宝宏大酒店`｜类别：`hotel`
- **2 分**｜`sanya_guide.md::三亚南中国大酒店`｜类别：`hotel`
- **2 分**｜`sanya_guide.md::三亚微蓝民宿（大东海鹿回头景区店）`｜类别：`hotel`
- **2 分**｜`sanya_guide.md::三亚鹿回头蔚景温德姆酒店`｜类别：`hotel`

#### 1 分：弱相关答案（4 条）

- **1 分**｜`sanya_guide.md::2.8 亚龙湾热带天堂森林公园`｜类别：`guide`
- **1 分**｜`sanya_guide.md::2.13 亚特兰蒂斯水世界`｜类别：`guide`
- **1 分**｜`sanya_guide.md::2.14 亚特兰蒂斯失落的空间水族馆`｜类别：`guide`
- **1 分**｜`sanya_guide.md::2.20 凤凰岭海誓山盟景区`｜类别：`guide`

### 14. `sanya_family_relax`

- **目的地**：三亚
- **测试问题**：三亚 家庭游 海滩 文化景区 轻松活动
- **正式相关数量**：41（3 分 22 条，2 分 19 条）
- **弱相关数量**：3（1 分，不计入正式答案）

#### 3 分：核心答案（22 条）

- **3 分**｜`sanya_guide.md::2.7 西岛海洋文化旅游区`｜类别：`guide`
- **3 分**｜`sanya_guide.md::2.9 亚龙湾公共海滩`｜类别：`guide`
- **3 分**｜`sanya_guide.md::2.10 大东海旅游区`｜类别：`guide`
- **3 分**｜`sanya_guide.md::2.11 三亚湾与椰梦长廊`｜类别：`guide`
- **3 分**｜`sanya_guide.md::2.15 大小洞天旅游区`｜类别：`guide`
- **3 分**｜`sanya_guide.md::三亚海韵度假酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚天丽湾凯悦酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚绿发山海天 JW 万豪酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚亚龙湾红树林度假酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚亚龙湾万豪度假酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚亚龙湾喜来登度假酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::金茂三亚亚龙湾丽思卡尔顿酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚亚龙湾希尔顿酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚亚龙湾美高梅度假酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚海棠湾君悦酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚海棠湾喜来登度假酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚海棠湾仁恒皇冠假日度假酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚海棠湾洲际度假酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚理文索菲特度假酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚海棠湾开维费尔蒙酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚海棠湾阳光壹酒店`｜类别：`hotel`
- **3 分**｜`sanya_guide.md::三亚亚特兰蒂斯酒店`｜类别：`hotel`

#### 2 分：正式相关答案（19 条）

- **2 分**｜`sanya_guide.md::2.1 三亚千古情景区`｜类别：`guide`
- **2 分**｜`sanya_guide.md::2.3 南山寺`｜类别：`guide`
- **2 分**｜`sanya_guide.md::2.4 天涯海角游览区-天涯石`｜类别：`guide`
- **2 分**｜`sanya_guide.md::2.6 蜈支洲岛旅游区`｜类别：`guide`
- **2 分**｜`sanya_guide.md::2.8 亚龙湾热带天堂森林公园`｜类别：`guide`
- **2 分**｜`sanya_guide.md::2.12 后海村与皇后湾`｜类别：`guide`
- **2 分**｜`sanya_guide.md::2.13 亚特兰蒂斯水世界`｜类别：`guide`
- **2 分**｜`sanya_guide.md::2.14 亚特兰蒂斯失落的空间水族馆`｜类别：`guide`
- **2 分**｜`sanya_guide.md::2.16 崖州古城与崖州学宫`｜类别：`guide`
- **2 分**｜`sanya_guide.md::2.18 三亚海昌梦幻海洋不夜城`｜类别：`guide`
- **2 分**｜`sanya_guide.md::2.19 天涯小镇`｜类别：`guide`
- **2 分**｜`sanya_guide.md::2.21 亚龙湾国际玫瑰谷`｜类别：`guide`
- **2 分**｜`sanya_guide.md::2.22 白鹭公园`｜类别：`guide`
- **2 分**｜`sanya_guide.md::2.23 东岸湿地公园`｜类别：`guide`
- **2 分**｜`sanya_guide.md::三亚怡庭酒店（三亚湾椰梦长廊店）`｜类别：`hotel`
- **2 分**｜`sanya_guide.md::三亚宝宏大酒店`｜类别：`hotel`
- **2 分**｜`sanya_guide.md::三亚鹿回头蔚景温德姆酒店`｜类别：`hotel`
- **2 分**｜`sanya_guide.md::三亚阳光大酒店`｜类别：`hotel`
- **2 分**｜`sanya_guide.md::三亚福朋喜来登酒店`｜类别：`hotel`

#### 1 分：弱相关答案（3 条）

- **1 分**｜`sanya_guide.md::2.2 鹿回头风景区`｜类别：`guide`
- **1 分**｜`sanya_guide.md::2.17 临春岭森林公园`｜类别：`guide`
- **1 分**｜`sanya_guide.md::2.20 凤凰岭海誓山盟景区`｜类别：`guide`

### 15. `sanya_seafood_culture`

- **目的地**：三亚
- **测试问题**：三亚 新鲜海鲜 椰子鸡 南山寺 文化
- **正式相关数量**：24（3 分 14 条，2 分 10 条）
- **弱相关数量**：1（1 分，不计入正式答案）

#### 3 分：核心答案（14 条）

- **3 分**｜`sanya_guide.md::2.3 南山寺`｜类别：`guide`
- **3 分**｜`sanya_guide.md::餐饮：嗲嗲的椰子鸡（椰梦长廊店）`｜类别：`restaurant`
- **3 分**｜`sanya_guide.md::餐饮：海南椰子鸡饭店`｜类别：`restaurant`
- **3 分**｜`sanya_guide.md::餐饮：太琼百年糟粕醋海鲜火锅（明珠广场店）`｜类别：`restaurant`
- **3 分**｜`sanya_guide.md::餐饮：太琼糟粕醋海鲜火锅（百花谷店）`｜类别：`restaurant`
- **3 分**｜`sanya_guide.md::餐饮：琼小琼糟粕醋（亚龙湾店）`｜类别：`restaurant`
- **3 分**｜`sanya_guide.md::餐饮：阿浪海鲜（第一市场店）`｜类别：`restaurant`
- **3 分**｜`sanya_guide.md::餐饮：小胡子川味海鲜（第一市场店）`｜类别：`restaurant`
- **3 分**｜`sanya_guide.md::餐饮：不仔客海鲜270度海景餐厅`｜类别：`restaurant`
- **3 分**｜`sanya_guide.md::餐饮：小海豚海鲜广场（三亚湾店）`｜类别：`restaurant`
- **3 分**｜`sanya_guide.md::餐饮：东海龙宫（大东海店）`｜类别：`restaurant`
- **3 分**｜`sanya_guide.md::餐饮：三亚亚特兰蒂斯酒店·松鹤楼中餐厅`｜类别：`restaurant`
- **3 分**｜`sanya_guide.md::餐饮：三亚海棠湾洲际度假酒店·涛·海底餐厅`｜类别：`restaurant`
- **3 分**｜`sanya_guide.md::餐饮：三亚亚龙湾瑞吉度假酒店·宴悦 Driftwood`｜类别：`restaurant`

#### 2 分：正式相关答案（10 条）

- **2 分**｜`sanya_guide.md::2.1 三亚千古情景区`｜类别：`guide`
- **2 分**｜`sanya_guide.md::2.7 西岛海洋文化旅游区`｜类别：`guide`
- **2 分**｜`sanya_guide.md::2.15 大小洞天旅游区`｜类别：`guide`
- **2 分**｜`sanya_guide.md::2.16 崖州古城与崖州学宫`｜类别：`guide`
- **2 分**｜`sanya_guide.md::餐饮：阖冯记铺前糟粕醋`｜类别：`restaurant`
- **2 分**｜`sanya_guide.md::餐饮：创味·民间海南菜·海鲜（林旺店）`｜类别：`restaurant`
- **2 分**｜`sanya_guide.md::餐饮：琼乡阁海南菜餐厅（机场路店）`｜类别：`restaurant`
- **2 分**｜`sanya_guide.md::餐饮：应天承海南特色美食（乐天城店）`｜类别：`restaurant`
- **2 分**｜`sanya_guide.md::餐饮：朱家酒店`｜类别：`restaurant`
- **2 分**｜`sanya_guide.md::餐饮：三亚亚特兰蒂斯酒店·蟹餐厅`｜类别：`restaurant`

#### 1 分：弱相关答案（1 条）

- **1 分**｜`sanya_guide.md::2.4 天涯海角游览区-天涯石`｜类别：`guide`

### 16. `beijing_history_palace`

- **目的地**：北京
- **测试问题**：北京 第一次 故宫 天安门 皇家历史文化
- **正式相关数量**：18（3 分 5 条，2 分 13 条）
- **弱相关数量**：6（1 分，不计入正式答案）

#### 3 分：核心答案（5 条）

- **3 分**｜`beijing_guide.md::2.1 天安门广场`｜类别：`guide`
- **3 分**｜`beijing_guide.md::2.2 故宫博物院`｜类别：`guide`
- **3 分**｜`beijing_guide.md::2.3 颐和园`｜类别：`guide`
- **3 分**｜`beijing_guide.md::2.5 天坛公园（历史文化与中轴线）`｜类别：`guide`
- **3 分**｜`beijing_guide.md::2.6 景山公园（历史文化与中轴线）`｜类别：`guide`

#### 2 分：正式相关答案（13 条）

- **2 分**｜`beijing_guide.md::2.7 北海公园（历史文化与中轴线）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.8 恭王府博物馆（历史文化与中轴线）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.10 钟鼓楼（历史文化与中轴线）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.11 雍和宫（历史文化与中轴线）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.12 孔庙和国子监博物馆（历史文化与中轴线）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.13 正阳门与前门大街（历史文化与中轴线）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.15 北京古代建筑博物馆（先农坛）（历史文化与中轴线）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.17 白塔寺（妙应寺）（历史文化与中轴线）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.19 明十三陵（历史文化与中轴线）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.20 圆明园遗址公园（皇家园林与城市公园）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.24 中山公园（皇家园林与城市公园）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.30 中国国家博物馆（博物馆、艺术与研学）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.31 首都博物馆（博物馆、艺术与研学）`｜类别：`guide`

#### 1 分：弱相关答案（6 条）

- **1 分**｜`beijing_guide.md::2.9 什刹海历史文化街区（历史文化与中轴线）`｜类别：`guide`
- **1 分**｜`beijing_guide.md::2.14 大栅栏历史文化街区（历史文化与中轴线）`｜类别：`guide`
- **1 分**｜`beijing_guide.md::2.16 法源寺（历史文化与中轴线）`｜类别：`guide`
- **1 分**｜`beijing_guide.md::2.18 卢沟桥与宛平城（历史文化与中轴线）`｜类别：`guide`
- **1 分**｜`beijing_guide.md::2.21 香山公园（皇家园林与城市公园）`｜类别：`guide`
- **1 分**｜`beijing_guide.md::2.41 周口店北京人遗址博物馆（博物馆、艺术与研学）`｜类别：`guide`

### 17. `beijing_food_local`

- **目的地**：北京
- **测试问题**：北京 老北京美食 烤鸭 炸酱面 豆汁 小吃
- **正式相关数量**：40（3 分 18 条，2 分 22 条）
- **弱相关数量**：2（1 分，不计入正式答案）

#### 3 分：核心答案（18 条）

- **3 分**｜`beijing_guide.md::餐饮：尹三豆汁（前门旗舰店）`｜类别：`restaurant`
- **3 分**｜`beijing_guide.md::餐饮：方砖厂69号炸酱面（前门大街店）`｜类别：`restaurant`
- **3 分**｜`beijing_guide.md::餐饮：护国寺小吃`｜类别：`restaurant`
- **3 分**｜`beijing_guide.md::餐饮：锦芳小吃`｜类别：`restaurant`
- **3 分**｜`beijing_guide.md::餐饮：宝记豆汁店`｜类别：`restaurant`
- **3 分**｜`beijing_guide.md::餐饮：方砖厂69号炸酱面`｜类别：`restaurant`
- **3 分**｜`beijing_guide.md::餐饮：海碗居`｜类别：`restaurant`
- **3 分**｜`beijing_guide.md::餐饮：四季民福烤鸭店（王府井东安门店）`｜类别：`restaurant`
- **3 分**｜`beijing_guide.md::餐饮：全聚德`｜类别：`restaurant`
- **3 分**｜`beijing_guide.md::餐饮：便宜坊`｜类别：`restaurant`
- **3 分**｜`beijing_guide.md::餐饮：四季民福`｜类别：`restaurant`
- **3 分**｜`beijing_guide.md::餐饮：大董`｜类别：`restaurant`
- **3 分**｜`beijing_guide.md::餐饮：1949全鸭季`｜类别：`restaurant`
- **3 分**｜`beijing_guide.md::餐饮：利群烤鸭店`｜类别：`restaurant`
- **3 分**｜`beijing_guide.md::餐饮：四季民福烤鸭店（翠微店）`｜类别：`restaurant`
- **3 分**｜`beijing_guide.md::餐饮街区：牛街`｜类别：`food_district`
- **3 分**｜`beijing_guide.md::餐饮街区：护国寺街`｜类别：`food_district`
- **3 分**｜`beijing_guide.md::餐饮街区：前门—大栅栏—鲜鱼口`｜类别：`food_district`

#### 2 分：正式相关答案（22 条）

- **2 分**｜`beijing_guide.md::餐饮：黑窑厂街糖油饼`｜类别：`restaurant`
- **2 分**｜`beijing_guide.md::餐饮：牛街白记年糕`｜类别：`restaurant`
- **2 分**｜`beijing_guide.md::餐饮：门框胡同百年卤煮`｜类别：`restaurant`
- **2 分**｜`beijing_guide.md::餐饮：都一处烧麦馆`｜类别：`restaurant`
- **2 分**｜`beijing_guide.md::餐饮：庆丰包子铺`｜类别：`restaurant`
- **2 分**｜`beijing_guide.md::餐饮：河沿肉饼`｜类别：`restaurant`
- **2 分**｜`beijing_guide.md::餐饮：小肠陈`｜类别：`restaurant`
- **2 分**｜`beijing_guide.md::餐饮：东来顺`｜类别：`restaurant`
- **2 分**｜`beijing_guide.md::餐饮：聚宝源`｜类别：`restaurant`
- **2 分**｜`beijing_guide.md::餐饮：南门涮肉`｜类别：`restaurant`
- **2 分**｜`beijing_guide.md::餐饮：满恒记`｜类别：`restaurant`
- **2 分**｜`beijing_guide.md::餐饮：阳坊大都涮羊肉`｜类别：`restaurant`
- **2 分**｜`beijing_guide.md::餐饮：鸿宾楼`｜类别：`restaurant`
- **2 分**｜`beijing_guide.md::餐饮：紫光园`｜类别：`restaurant`
- **2 分**｜`beijing_guide.md::餐饮：丰泽园饭店`｜类别：`restaurant`
- **2 分**｜`beijing_guide.md::餐饮：砂锅居`｜类别：`restaurant`
- **2 分**｜`beijing_guide.md::餐饮：萃华楼`｜类别：`restaurant`
- **2 分**｜`beijing_guide.md::餐饮：仿膳饭庄`｜类别：`restaurant`
- **2 分**｜`beijing_guide.md::餐饮：白家大院`｜类别：`restaurant`
- **2 分**｜`beijing_guide.md::餐饮：小吊梨汤`｜类别：`restaurant`
- **2 分**｜`beijing_guide.md::餐饮：局气`｜类别：`restaurant`
- **2 分**｜`beijing_guide.md::餐饮：京季`｜类别：`restaurant`

#### 1 分：弱相关答案（2 条）

- **1 分**｜`beijing_guide.md::餐饮提示：宴乐主题餐饮体验`｜类别：`dining_advice`
- **1 分**｜`beijing_guide.md::餐饮街区：簋街`｜类别：`food_district`

### 18. `beijing_family_study`

- **目的地**：北京
- **测试问题**：北京 亲子 研学 天安门 故宫 历史文化
- **正式相关数量**：17（3 分 6 条，2 分 11 条）
- **弱相关数量**：6（1 分，不计入正式答案）

#### 3 分：核心答案（6 条）

- **3 分**｜`beijing_guide.md::2.1 天安门广场`｜类别：`guide`
- **3 分**｜`beijing_guide.md::2.2 故宫博物院`｜类别：`guide`
- **3 分**｜`beijing_guide.md::2.12 孔庙和国子监博物馆（历史文化与中轴线）`｜类别：`guide`
- **3 分**｜`beijing_guide.md::2.15 北京古代建筑博物馆（先农坛）（历史文化与中轴线）`｜类别：`guide`
- **3 分**｜`beijing_guide.md::2.30 中国国家博物馆（博物馆、艺术与研学）`｜类别：`guide`
- **3 分**｜`beijing_guide.md::2.31 首都博物馆（博物馆、艺术与研学）`｜类别：`guide`

#### 2 分：正式相关答案（11 条）

- **2 分**｜`beijing_guide.md::2.5 天坛公园（历史文化与中轴线）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.6 景山公园（历史文化与中轴线）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.7 北海公园（历史文化与中轴线）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.8 恭王府博物馆（历史文化与中轴线）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.10 钟鼓楼（历史文化与中轴线）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.13 正阳门与前门大街（历史文化与中轴线）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.18 卢沟桥与宛平城（历史文化与中轴线）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.19 明十三陵（历史文化与中轴线）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.20 圆明园遗址公园（皇家园林与城市公园）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.24 中山公园（皇家园林与城市公园）`｜类别：`guide`
- **2 分**｜`beijing_guide.md::2.41 周口店北京人遗址博物馆（博物馆、艺术与研学）`｜类别：`guide`

#### 1 分：弱相关答案（6 条）

- **1 分**｜`beijing_guide.md::2.32 国家自然博物馆（博物馆、艺术与研学）`｜类别：`guide`
- **1 分**｜`beijing_guide.md::2.33 中国科学技术馆（博物馆、艺术与研学）`｜类别：`guide`
- **1 分**｜`beijing_guide.md::2.34 北京天文馆（博物馆、艺术与研学）`｜类别：`guide`
- **1 分**｜`beijing_guide.md::2.35 中国航空博物馆（博物馆、艺术与研学）`｜类别：`guide`
- **1 分**｜`beijing_guide.md::2.42 中国园林博物馆（博物馆、艺术与研学）`｜类别：`guide`
- **1 分**｜`beijing_guide.md::2.43 北京大运河博物馆（博物馆、艺术与研学）`｜类别：`guide`

