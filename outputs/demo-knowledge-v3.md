# 云岚市旅游知识库

## 1. 地理实体

### 地理实体：示例省（place_example_province）

- 实体 ID：place_example_province
- 实体类型：省级行政区
- 包含地点：place_yunlan_city

示例省是云岚市所属的上级行政区，仅用于展示地点的父级关系。

### 地理实体：云岚市（place_yunlan_city）

- 实体 ID：place_yunlan_city
- 实体类型：旅游目的地 / 城市
- 标准名称：云岚市
- 别名：云岚、镜湖之城
- 上级地点：place_example_province
- 包含区域：place_yunlan_old_town、place_jinghu_east_bank、place_nanxi_district、place_qinglan_mountain
- 适合旅行主题：湖景休闲、古城漫步、轻量徒步、地方文化、美食体验

云岚市是一座依山临湖的旅游城市，主要游览区域由云岚古城、镜湖东岸、南溪街区和青岚山组成。城市内部的古城、湖边和餐饮街区距离较近，适合安排 2 至 4 天的慢节奏旅行。第一次到访时，可以以古城、镜湖和南溪街区为主；希望加入轻量徒步和自然体验时，再安排青岚山。

### 地理实体：云岚古城片区（place_yunlan_old_town）

- 实体 ID：place_yunlan_old_town
- 实体类型：旅游片区 / 历史街区
- 所属地点：place_yunlan_city
- 邻近区域：place_nanxi_district、place_jinghu_east_bank
- 包含实体：attraction_yunlan_old_town、service_old_town_visitor_center、food_nanxi_small_bistro

云岚古城片区位于云岚市中心，保留青石街巷、临水码头和传统店铺。片区适合步行游览，街巷内机动车通行有限。带大件行李的游客适合先在古城外办理入住，再步行进入古城。

### 地理实体：镜湖东岸（place_jinghu_east_bank）

- 实体 ID：place_jinghu_east_bank
- 实体类型：湖畔旅游片区
- 所属地点：place_yunlan_city
- 邻近区域：place_nanxi_district、attraction_jinghu_wetland_park
- 包含实体：attraction_jinghu_viewpoint、activity_jinghu_slow_route、food_lakeside_fish_house、accommodation_jinghu_youth_hostel、accommodation_jinghu_yunqi_hotel

镜湖东岸以日落、慢行和湖畔休闲为主要特点。沿湖路段平缓，适合老人、亲子游客和不希望长距离爬坡的旅行者。晴朗天气下，傍晚的湖面倒影和远山景观是该区域的主要看点。

### 地理实体：南溪街区（place_nanxi_district）

- 实体 ID：place_nanxi_district
- 实体类型：文化与餐饮街区
- 所属地点：place_yunlan_city
- 邻近区域：place_yunlan_old_town、place_jinghu_east_bank
- 包含实体：activity_nanxi_handicraft_street、food_nanxi_small_bistro、accommodation_nanxi_lane_hotel

南溪街区连接古城与镜湖，是云岚市适合晚餐、手作体验和夜间散步的区域。街区内店铺密集，步行即可到达部分古城入口和镜湖慢行道。

### 地理实体：青岚山南麓（place_qinglan_mountain）

- 实体 ID：place_qinglan_mountain
- 实体类型：山地自然景区
- 所属地点：place_yunlan_city
- 包含实体：activity_qinglan_summit_trail、food_bamboo_creek_restaurant、accommodation_qinglan_summit_resort

青岚山南麓是云岚市的山地活动区域，适合安排半日或一日轻量徒步。该区域距离市中心较远，但环境安静，适合把徒步与度假住宿组合安排。

## 2. 交通与服务实体

### 交通实体：云岚站（transport_yunlan_railway_station）

- 实体 ID：transport_yunlan_railway_station
- 实体类型：铁路客运站
- 所属地点：place_yunlan_city
- 所在区域：城北新区
- 可到达区域：place_yunlan_old_town、place_jinghu_east_bank、place_nanxi_district
- 关联服务：service_old_town_visitor_center

云岚站是云岚市主要铁路客运站。首次到访且携带行李的游客，适合先从车站前往住宿区域，再开始游览。前往古城时，公共交通耗时较长；携带较多行李或同行人数较多时，短途出租车或网约车更方便。

### 服务实体：云岚古城游客中心（service_old_town_visitor_center）

- 实体 ID：service_old_town_visitor_center
- 实体类型：旅游信息与行李服务
- 所属地点：place_yunlan_old_town
- 提供服务：咨询、临时行李寄存、饮水点、公共卫生间
- 邻近实体：attraction_yunlan_old_town、food_nanxi_small_bistro

云岚古城游客中心位于古城南门外，适合作为抵达古城后的第一站。需要寄存行李、确认步行路线或了解当日体验项目时，可以优先在这里完成准备。

### 活动实体：镜湖环湖慢行道（activity_jinghu_slow_route）

- 实体 ID：activity_jinghu_slow_route
- 实体类型：步行与骑行路线
- 所属地点：place_jinghu_east_bank
- 起点：attraction_jinghu_viewpoint
- 途经区域：place_jinghu_east_bank、attraction_jinghu_wetland_park、place_nanxi_district
- 全程长度：约 12 公里
- 推荐方式：步行、公共自行车、短途网约车分段衔接
- 适合人群：亲子游客、老人、轻量骑行者、日落摄影爱好者

镜湖环湖慢行道串联镜湖东岸、湿地和南溪街区。东岸路段平缓，适合观看日落；北侧湿地树荫较多，适合亲子散步；靠近南溪的一段餐饮较集中，适合在傍晚安排晚餐。

## 3. 景点与活动实体

### 景点：云岚古城（attraction_yunlan_old_town）

- 实体 ID：attraction_yunlan_old_town
- 实体类型：历史街区 / 旅游景点
- 所属地点：place_yunlan_old_town
- 建议停留：2 至 3 小时
- 推荐方式：步行
- 适合人群：首次到访者、摄影爱好者、亲子游客、文化爱好者
- 关联实体：service_old_town_visitor_center、activity_nanxi_handicraft_street、food_nanxi_small_bistro
- 旅行标签：古城漫步、街景摄影、地方文化、低强度游览

云岚古城以青石路、木构店铺和临水巷道为主要特色。古城南门、望湖巷和西平码头适合拍摄街景；城内民俗馆适合了解当地节庆、服饰和手工艺。古城的游览价值主要在于慢走和观察街区细节，而不是快速打卡多个单点景观。

### 景点：镜湖东岸观景台（attraction_jinghu_viewpoint）

- 实体 ID：attraction_jinghu_viewpoint
- 实体类型：湖畔观景点
- 所属地点：place_jinghu_east_bank
- 建议停留：1 至 1.5 小时
- 推荐方式：步行、短途网约车
- 适合人群：摄影爱好者、情侣、老人、亲子游客、不想长距离爬坡者
- 关联实体：activity_jinghu_slow_route、attraction_jinghu_wetland_park、food_lakeside_fish_house
- 旅行标签：日落、湖景、低强度、亲子友好、轮椅可达区域附近

镜湖东岸观景台面向湖面开阔区域，是云岚市观看日落的主要地点。步行前往湖边不需要长距离爬坡，附近有长椅、公共卫生间和饮水点。晴朗天气下，日落前半小时可以看到湖面与远山的倒影。

### 景点：镜湖湿地公园（attraction_jinghu_wetland_park）

- 实体 ID：attraction_jinghu_wetland_park
- 实体类型：城市湿地公园
- 所属地点：place_jinghu_east_bank
- 建议停留：约 2 小时
- 适合人群：亲子游客、老人、自然爱好者、雨后散步者
- 关联实体：activity_jinghu_slow_route、attraction_jinghu_viewpoint
- 旅行标签：观鸟、散步、自然摄影、低强度

镜湖湿地公园包含浅水湿地、木栈道和观鸟平台。公园地势平缓，适合老人和儿童进行低强度散步。春季和初秋适合观察水鸟，夏季午后日照较强，宜避开正午。

### 活动：青岚山云顶步道（activity_qinglan_summit_trail）

- 实体 ID：activity_qinglan_summit_trail
- 实体类型：山地徒步路线
- 所属地点：place_qinglan_mountain
- 往返长度：约 4.5 公里
- 常规耗时：2.5 至 3.5 小时
- 适合人群：有轻量徒步经验的旅行者、自然爱好者
- 不适合：行动不便者、婴儿车出行者、连续降雨后的当天游览
- 关联实体：food_bamboo_creek_restaurant、accommodation_qinglan_summit_resort
- 旅行标签：徒步、山景、中等强度、自然体验

青岚山云顶步道从山南麓进入，终点为云顶观景台。体力一般的游客可以只走到半山茶亭，不必完成全程。该路线的体验重点是山地步行和视野，不适合在天气不稳定或天色较晚时进入。

### 景点：云岚自然博物馆（attraction_yunlan_nature_museum）

- 实体 ID：attraction_yunlan_nature_museum
- 实体类型：自然科普场馆
- 所属地点：place_yunlan_city
- 所在区域：城北新区
- 建议停留：1.5 至 2 小时
- 适合人群：亲子游客、学生、雨天出行者、炎热天气出行者
- 关联实体：transport_yunlan_railway_station、attraction_jinghu_wetland_park
- 旅行标签：室内替代行程、自然科普、亲子友好

云岚自然博物馆围绕当地山地生态、湖泊湿地和传统农耕展开，设有标本展区、儿童互动区和短时科普讲解。它适合替代雨天无法进行的户外行程，也适合与城北新区的抵达或返程安排在同一天。

### 活动：南溪手作街（activity_nanxi_handicraft_street）

- 实体 ID：activity_nanxi_handicraft_street
- 实体类型：文化体验街区
- 所属地点：place_nanxi_district
- 建议停留：1.5 至 2 小时
- 适合人群：喜欢地方文化、伴手礼和慢节奏游览的旅行者
- 关联实体：food_nanxi_small_bistro、attraction_yunlan_old_town、activity_jinghu_slow_route
- 旅行标签：手作体验、地方文化、夜游、伴手礼

南溪手作街沿旧南溪码头展开，集中分布木雕、染布、陶器和地方茶点店铺。街区适合与晚餐或夜间散步组合。购买较大的手工艺品前，应先确认包装、运输和快递安排。

## 4. 餐饮实体

### 餐饮：湖畔鱼馆（food_lakeside_fish_house）

- 实体 ID：food_lakeside_fish_house
- 实体类型：地方菜餐厅
- 所属地点：place_jinghu_east_bank
- 人均预算：80 至 120 元
- 推荐菜品：酸汤鱼、清蒸白鱼、山野时蔬
- 适合人群：家庭用餐、朋友聚餐、日落后晚餐者
- 关联实体：attraction_jinghu_viewpoint、activity_jinghu_slow_route
- 旅行标签：本地菜、湖景附近、多人用餐

湖畔鱼馆位于镜湖东岸步行区，适合在观景台看完日落后步行前往用餐。鱼类菜品通常按整条点单，2 人用餐时应先确认分量。希望在靠窗位置用餐的游客，适合避开晚餐高峰或提前预约。

### 餐饮：南溪小馆（food_nanxi_small_bistro）

- 实体 ID：food_nanxi_small_bistro
- 实体类型：地方小吃与简餐
- 所属地点：place_nanxi_district
- 人均预算：25 至 45 元
- 推荐菜品：云岚米线、豆花、腌菜炒肉
- 适合人群：预算有限者、独自旅行者、亲子游客
- 关联实体：activity_nanxi_handicraft_street、attraction_yunlan_old_town
- 旅行标签：地方小吃、快捷用餐、预算友好

南溪小馆位于南溪手作街入口，出餐较快，适合作为古城和手作街之间的简餐选择。不能吃辣时，应在点餐时说明选择清淡汤底或不加辣椒。

### 餐饮：青岚山脚竹溪餐馆（food_bamboo_creek_restaurant）

- 实体 ID：food_bamboo_creek_restaurant
- 实体类型：山地风味餐厅
- 所属地点：place_qinglan_mountain
- 人均预算：60 至 90 元
- 推荐菜品：竹筒饭、菌菇汤、腊味拼盘
- 适合人群：徒步游客、多人同行游客
- 关联实体：activity_qinglan_summit_trail、accommodation_qinglan_summit_resort
- 旅行标签：徒步补给、山地风味、多人用餐

竹溪餐馆位于云顶步道南门附近，适合作为徒步结束后的正餐。部分菜品制作时间较长，赶返程的游客可以优先选择现成小菜和汤品。

## 5. 住宿区域建议

### 经济型（200 元/晚以下）

#### 住宿：云岚古城北门客栈（accommodation_old_town_north_gate_inn）

- 实体 ID：accommodation_old_town_north_gate_inn
- 实体类型：客栈
- 住宿预算分类：经济型（200 元/晚以下）
- 所属地点：place_yunlan_old_town
- 每晚预算：120 至 180 元
- 适合人群：学生、独自旅行者、短住游客
- 关联实体：attraction_yunlan_old_town、service_old_town_visitor_center
- 旅行标签：古城附近、预算友好、短住

云岚古城北门客栈位于古城北门外，步行到古城主街约 8 分钟。房间面积较小，但出行方便。对清晨车辆声音敏感的游客，应在预订时确认是否临街。

#### 住宿：镜湖东岸青年旅舍（accommodation_jinghu_youth_hostel）

- 实体 ID：accommodation_jinghu_youth_hostel
- 实体类型：青年旅舍
- 住宿预算分类：经济型（200 元/晚以下）
- 所属地点：place_jinghu_east_bank
- 每晚预算：90 至 160 元
- 适合人群：背包客、年轻旅行者、短途骑行者
- 关联实体：activity_jinghu_slow_route、attraction_jinghu_viewpoint
- 旅行标签：湖边、多人间、骑行友好

镜湖东岸青年旅舍提供多人间和少量单人房，公共区域有简单厨房和行李寄存服务。旅舍夜间公共区域较活跃，对睡眠敏感者应选择远离客厅的房间，并自行保管贵重物品。

### 舒适型（200-500 元/晚）

#### 住宿：南溪巷里酒店（accommodation_nanxi_lane_hotel）

- 实体 ID：accommodation_nanxi_lane_hotel
- 实体类型：城市酒店
- 住宿预算分类：舒适型（200-500 元/晚）
- 所属地点：place_nanxi_district
- 每晚预算：280 至 420 元
- 适合人群：情侣、家庭游客、首次到访者
- 关联实体：activity_nanxi_handicraft_street、food_nanxi_small_bistro、attraction_yunlan_old_town
- 旅行标签：古城与餐饮方便、夜游、家庭友好

南溪巷里酒店靠近南溪手作街，适合希望兼顾古城、餐饮和夜游的游客。靠街区一侧的房间可能听到餐饮店声音，预订时可备注安静房。自驾游客需要提前确认停车位。

#### 住宿：镜湖东岸云栖酒店（accommodation_jinghu_yunqi_hotel）

- 实体 ID：accommodation_jinghu_yunqi_hotel
- 实体类型：湖畔酒店
- 住宿预算分类：舒适型（200-500 元/晚）
- 所属地点：place_jinghu_east_bank
- 每晚预算：360 至 480 元
- 适合人群：情侣、亲子游客、喜欢湖畔休闲的游客
- 关联实体：attraction_jinghu_viewpoint、activity_jinghu_slow_route
- 旅行标签：湖景、日落、慢行道附近

镜湖东岸云栖酒店靠近观景台和慢行道，适合计划在镜湖周边停留两天的游客。部分房间可以看到湖景，但预订时需确认房型名称是否明确包含湖景；低楼层视野可能被绿化遮挡。

### 豪华型（500 元/晚以上）

#### 住宿：青岚山云顶度假酒店（accommodation_qinglan_summit_resort）

- 实体 ID：accommodation_qinglan_summit_resort
- 实体类型：度假酒店
- 住宿预算分类：豪华型（500 元/晚以上）
- 所属地点：place_qinglan_mountain
- 每晚预算：680 至 980 元
- 适合人群：度假游客、多人家庭、重视环境与服务的游客
- 关联实体：activity_qinglan_summit_trail、food_bamboo_creek_restaurant
- 旅行标签：山景、度假、徒步附近、安静

青岚山云顶度假酒店距离云顶步道入口约 1 公里，适合把徒步和休闲住宿结合安排。酒店离市中心较远，入住期间应提前规划前往古城和镜湖的交通；雨季前应确认山路和接驳安排。

## 6. 动态事实记录

### 动态事实：云岚古城开放安排（fact_old_town_opening_hours）

- 事实 ID：fact_old_town_opening_hours
- 关联实体 ID：attraction_yunlan_old_town
- 事实类型：开放安排
- 当前值：古城公共街区全天可步行游览；民俗馆开放时间以现场公告为准
- 核验时间：2026-08-02
- 生效时间：2026-08-02
- 有效期至：2026-10-31
- 置信等级：高

古城公共街区与民俗馆的开放规则不同。行程规划时，古城步行可按全天安排；需要参观馆内展览时，应在出发前再次确认当日开放情况。

### 动态事实：镜湖东岸日落体验条件（fact_jinghu_sunset_conditions）

- 事实 ID：fact_jinghu_sunset_conditions
- 关联实体 ID：attraction_jinghu_viewpoint
- 事实类型：季节与天气建议
- 当前值：晴朗或少云天气更适合日落摄影；湖边傍晚风力通常强于市区
- 核验时间：2026-08-02
- 生效时间：2026-08-02
- 有效期至：2026-09-30
- 置信等级：中

镜湖东岸的体验质量受云量、能见度和风力影响。带老人或儿童在傍晚停留时，应准备薄外套，并在天气变化明显时缩短湖边停留时间。

### 动态事实：青岚山云顶步道安全条件（fact_qinglan_trail_safety）

- 事实 ID：fact_qinglan_trail_safety
- 关联实体 ID：activity_qinglan_summit_trail
- 事实类型：安全与开放条件
- 当前值：连续降雨、雷雨预警或石阶湿滑时不建议进入；应在天黑前完成下山
- 核验时间：2026-08-02
- 生效时间：2026-08-02
- 有效期至：2026-12-31
- 置信等级：高

步道安全条件会直接影响是否适合纳入行程。下雨天或体力不确定时，可使用云岚自然博物馆作为室内替代实体，而不是勉强完成徒步。

### 动态事实：住宿价格变动说明（fact_accommodation_price_variation）

- 事实 ID：fact_accommodation_price_variation
- 关联实体 ID：accommodation_old_town_north_gate_inn、accommodation_jinghu_youth_hostel、accommodation_nanxi_lane_hotel、accommodation_jinghu_yunqi_hotel、accommodation_qinglan_summit_resort
- 事实类型：价格波动
- 当前值：每晚预算为常规区间；节假日、周末和热门活动期间可能上浮
- 核验时间：2026-08-02
- 生效时间：2026-08-02
- 有效期至：2026-08-31
- 置信等级：中

住宿预算用于初步筛选，不应被理解为实时成交价。需要预订时，应根据实际入住日期再次确认价格、取消政策和停车条件。
