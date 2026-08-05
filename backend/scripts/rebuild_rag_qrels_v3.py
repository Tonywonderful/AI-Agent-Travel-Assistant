from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag.evaluation_metrics import validate_qrels
from app.rag.vector_db import load_guide_chunks


EVAL_DIR = BACKEND_DIR / "eval"
CASES_PATH = EVAL_DIR / "rag_eval_cases.json"
CANONICAL_QRELS_PATH = EVAL_DIR / "rag_qrels.json"
QRELS_V3_PATH = EVAL_DIR / "rag_qrels_v3.json"
ANNOTATIONS_PATH = EVAL_DIR / "rag_qrels_v3_annotations.json"


def _chunk_key(chunk: dict[str, str]) -> str:
    return f"{chunk['document_id']}::{chunk['title']}"

CITY_GUIDES = {
    "大理": "dali_guide.md",
    "成都": "chengdu_guide.md",
    "西安": "xian_guide.md",
    "厦门": "xiamen_guide.md",
    "三亚": "sanya_guide.md",
    "北京": "beijing_guide.md",
}

# This mapping is the manually reviewed positive set after reading every logical
# chunk in the corresponding city guide. Grades below 2 stay in the audit file
# and do not enter the formal qrels used by retrieval metrics.
REVIEWED_QRELS: dict[str, dict[str, int]] = {
    "dali_sunset_easy_photo": {
        "dali_guide.md::2.5 大理180度海景网红打卡地": 3,
        "dali_guide.md::2.16 洱海生态廊道": 2,
        "dali_guide.md::2.19 磻溪村S湾": 2,
        "dali_guide.md::2.26 双廊古镇": 3,
        "dali_guide.md::2.29 罗荃半岛旅游区": 2,
        "dali_guide.md::2.30 洱海公园": 2,
    },
    "dali_culture_slow_trip": {
        "dali_guide.md::2.1 大理古城-南门楼": 2,
        "dali_guide.md::2.2 崇圣寺三塔文化旅游区": 3,
        "dali_guide.md::2.6 大理市博物馆（杜文秀帅府）": 2,
        "dali_guide.md::2.7 大理文庙": 2,
        "dali_guide.md::2.15 凤阳邑茶马古道": 2,
        "dali_guide.md::2.20 古生村与古生村廊桥": 2,
        "dali_guide.md::2.21 喜洲古镇": 3,
        "dali_guide.md::2.22 严家大院": 3,
        "dali_guide.md::2.23 周城村与白族扎染体验": 3,
        "dali_guide.md::2.25 蝴蝶泉公园": 2,
        "dali_guide.md::2.31 大理白族自治州博物馆": 3,
        "dali_guide.md::2.32 大理州非物质文化遗产博物馆": 3,
        "dali_guide.md::2.36 凤羽古镇": 2,
        "dali_guide.md::2.38 沙溪古镇": 2,
        "dali_guide.md::2.40 石钟山石窟": 2,
        "dali_guide.md::2.41 剑川古城": 3,
        "dali_guide.md::2.42 巍山古城": 2,
        "dali_guide.md::2.47 鹤庆新华银器小镇": 2,
    },
    "dali_food_budget": {
        "dali_guide.md::经济实惠（人均 30 元以下）": 3,
        "dali_guide.md::中档特色（人均 50-150 元）": 3,
        "dali_guide.md::高端体验（人均 200 元以上）": 3,
        "dali_guide.md::白族家常菜与苍洱风味": 3,
        "dali_guide.md::大理小吃与早餐": 3,
        "dali_guide.md::大理州各县代表性风味": 2,
        "dali_guide.md::野生菌用餐提示": 2,
        "dali_guide.md::餐饮预算与选择原则": 3,
    },
    "chengdu_relax_food": {
        "chengdu_guide.md::2.1 宽窄巷子景区": 3,
        "chengdu_guide.md::2.2 锦城公园": 2,
        "chengdu_guide.md::2.5 成都武侯祠博物馆（历史文化）": 2,
        "chengdu_guide.md::2.6 锦里古街（历史街区与夜游）": 2,
        "chengdu_guide.md::2.7 成都杜甫草堂博物馆（历史文化）": 2,
        "chengdu_guide.md::2.8 人民公园（城市生活）": 3,
        "chengdu_guide.md::2.9 文殊院（历史文化与宗教场所）": 2,
        "chengdu_guide.md::2.10 青羊宫（历史文化与宗教场所）": 2,
        "chengdu_guide.md::2.11 望江楼公园（园林与名人文化）": 3,
        "chengdu_guide.md::2.12 大慈寺与成都远洋太古里（古今城市空间）": 2,
        "chengdu_guide.md::2.14 奎星楼街（城市美食街区）": 2,
        "chengdu_guide.md::2.15 玉林街区（城市漫步与夜生活）": 2,
        "chengdu_guide.md::2.18 成都博物馆（博物馆与研学）": 2,
        "chengdu_guide.md::2.19 四川博物院（博物馆与研学）": 2,
        "chengdu_guide.md::2.20 成都金沙遗址博物馆（古蜀文明）": 2,
        "chengdu_guide.md::2.25 成都蜀锦织绣博物馆（非遗与工艺）": 2,
        "chengdu_guide.md::2.26 浣花溪公园（城市公园）": 2,
        "chengdu_guide.md::2.27 天府艺术公园（城市公园与艺术）": 2,
        "chengdu_guide.md::经济实惠（人均 30 元以下）": 2,
        "chengdu_guide.md::成都传统小吃与必比登平价餐厅": 3,
        "chengdu_guide.md::中档特色（人均 50-150 元）": 2,
        "chengdu_guide.md::中档川菜与茶馆": 3,
        "chengdu_guide.md::中档火锅品牌": 2,
        "chengdu_guide.md::高端体验（人均 200 元以上）": 2,
        "chengdu_guide.md::2026成都米其林一星川菜餐厅": 2,
        "chengdu_guide.md::美食类型与街区选择": 3,
    },
    "chengdu_food_deep": {
        "chengdu_guide.md::2.6 锦里古街（历史街区与夜游）": 2,
        "chengdu_guide.md::2.14 奎星楼街（城市美食街区）": 3,
        "chengdu_guide.md::2.15 玉林街区（城市漫步与夜生活）": 2,
        "chengdu_guide.md::经济实惠（人均 30 元以下）": 3,
        "chengdu_guide.md::成都传统小吃与必比登平价餐厅": 3,
        "chengdu_guide.md::中档特色（人均 50-150 元）": 3,
        "chengdu_guide.md::中档川菜与茶馆": 3,
        "chengdu_guide.md::中档火锅品牌": 3,
        "chengdu_guide.md::高端体验（人均 200 元以上）": 2,
        "chengdu_guide.md::2026成都米其林二星餐厅": 2,
        "chengdu_guide.md::2026成都米其林一星川菜餐厅": 2,
        "chengdu_guide.md::美食类型与街区选择": 3,
    },
    "chengdu_park_old_town_nature": {
        "chengdu_guide.md::2.2 锦城公园": 3,
        "chengdu_guide.md::2.3 黄龙溪古镇": 3,
        "chengdu_guide.md::2.8 人民公园（城市生活）": 3,
        "chengdu_guide.md::2.11 望江楼公园（园林与名人文化）": 3,
        "chengdu_guide.md::2.26 浣花溪公园（城市公园）": 3,
        "chengdu_guide.md::2.27 天府艺术公园（城市公园与艺术）": 3,
        "chengdu_guide.md::2.28 桂溪生态公园（城市公园）": 3,
        "chengdu_guide.md::2.29 兴隆湖湿地公园（城市公园）": 3,
        "chengdu_guide.md::2.30 东安湖公园（城市公园与体育地标）": 3,
        "chengdu_guide.md::2.31 成都植物园（植物与亲子）": 2,
        "chengdu_guide.md::2.35 洛带古镇（古镇与客家文化）": 3,
        "chengdu_guide.md::2.36 安仁古镇（古镇与博物馆）": 3,
        "chengdu_guide.md::2.37 平乐古镇（古镇与山水）": 3,
        "chengdu_guide.md::2.38 街子古镇（古镇与山水）": 3,
        "chengdu_guide.md::2.39 元通古镇（古镇与建筑）": 3,
        "chengdu_guide.md::2.40 五凤溪古镇（古镇与山水）": 3,
        "chengdu_guide.md::2.41 新场古镇（古镇与川西生活）": 3,
        "chengdu_guide.md::2.46 成都天台山旅游景区（山水与生态）": 2,
        "chengdu_guide.md::2.47 龙泉山城市森林公园丹景台（城市远眺）": 2,
        "chengdu_guide.md::2.48 石象湖景区（花卉与湖泊）": 2,
        "chengdu_guide.md::2.50 花舞人间景区（花卉与亲子）": 2,
    },
    "xian_history_culture": {
        "xian_guide.md::2.2 大明宫国家遗址公园": 3,
        "xian_guide.md::2.3 秦始皇帝陵博物院": 3,
        "xian_guide.md::2.4 曲江池遗址公园": 2,
        "xian_guide.md::2.5 西安城墙": 3,
        "xian_guide.md::2.6 西安钟楼与鼓楼": 2,
        "xian_guide.md::2.7 陕西历史博物馆": 3,
        "xian_guide.md::2.8 大慈恩寺与大雁塔": 3,
        "xian_guide.md::2.11 华清宫": 3,
        "xian_guide.md::2.13 骊山与骊山索道": 2,
        "xian_guide.md::2.14 西安碑林博物馆": 3,
        "xian_guide.md::2.15 西安博物院与小雁塔": 3,
    },
    "xian_food_night": {
        "xian_guide.md::2.6 西安钟楼与鼓楼": 2,
        "xian_guide.md::经济实惠（人均 30 元以下）": 2,
        "xian_guide.md::小吃、早餐与面食（人均约10-60元）": 3,
        "xian_guide.md::中档特色（人均 50-150 元）": 3,
        "xian_guide.md::泡馍、陕菜与老字号（人均约35-200元）": 3,
    },
    "xian_family_study": {
        "xian_guide.md::2.2 大明宫国家遗址公园": 3,
        "xian_guide.md::2.3 秦始皇帝陵博物院": 3,
        "xian_guide.md::2.4 曲江池遗址公园": 2,
        "xian_guide.md::2.5 西安城墙": 2,
        "xian_guide.md::2.6 西安钟楼与鼓楼": 2,
        "xian_guide.md::2.7 陕西历史博物馆": 3,
        "xian_guide.md::2.8 大慈恩寺与大雁塔": 2,
        "xian_guide.md::2.11 华清宫": 2,
        "xian_guide.md::2.14 西安碑林博物馆": 3,
        "xian_guide.md::2.15 西安博物院与小雁塔": 3,
        "xian_guide.md::2.17 陕西自然博物馆": 2,
        "xian_guide.md::2.19 西影电影博物馆": 2,
        "xian_guide.md::2.20 白鹿原·白鹿仓": 2,
    },
    "xiamen_couple_relax": {
        "xiamen_guide.md::2.1 鼓浪屿风景名胜区": 3,
        "xiamen_guide.md::2.2 日光岩": 2,
        "xiamen_guide.md::2.5 菽庄花园（鼓浪屿园林与钢琴文化）": 2,
        "xiamen_guide.md::2.6 皓月园（鼓浪屿历史文化与海滨景观）": 2,
        "xiamen_guide.md::2.7 八卦楼风琴博物馆（鼓浪屿建筑与音乐文化）": 2,
        "xiamen_guide.md::2.8 鼓浪屿管风琴艺术中心（鼓浪屿音乐文化）": 2,
        "xiamen_guide.md::2.10 钟鼓索道（城市与山海观景）": 3,
        "xiamen_guide.md::2.11 厦门大学思明校区（校园建筑与人文）": 2,
        "xiamen_guide.md::2.12 沙坡尾艺术西区（老港口与文创街区）": 3,
        "xiamen_guide.md::2.13 环岛路与黄厝海滩（海滨骑行与日出）": 2,
        "xiamen_guide.md::2.14 曾厝垵文创村（小吃、民宿与夜间休闲）": 3,
        "xiamen_guide.md::2.15 中山路步行街（骑楼建筑与老字号小吃）": 2,
        "xiamen_guide.md::2.20 云上厦门观光厅（高空城市观景）": 2,
        "xiamen_guide.md::2.21 厦门之眼海上摩天轮（五缘湾夜景与亲子体验）": 3,
        "xiamen_guide.md::经济实惠（人均 30 元以下）": 2,
        "xiamen_guide.md::厦门传统小吃（人均约15-50元）": 2,
        "xiamen_guide.md::中档特色（人均 50-150 元）": 2,
        "xiamen_guide.md::闽南菜与海鲜（人均约60-350元）": 2,
        "xiamen_guide.md::高端体验（人均 200 元以上）": 2,
        "xiamen_guide.md::咖啡、甜品与夜宵（人均约25-150元）": 3,
        "xiamen_guide.md::美食街区与选择建议": 3,
    },
    "xiamen_architecture_history": {
        "xiamen_guide.md::2.1 鼓浪屿风景名胜区": 3,
        "xiamen_guide.md::2.3 南普陀寺": 3,
        "xiamen_guide.md::2.4 胡里山炮台": 3,
        "xiamen_guide.md::2.5 菽庄花园（鼓浪屿园林与钢琴文化）": 2,
        "xiamen_guide.md::2.6 皓月园（鼓浪屿历史文化与海滨景观）": 2,
        "xiamen_guide.md::2.7 八卦楼风琴博物馆（鼓浪屿建筑与音乐文化）": 3,
        "xiamen_guide.md::2.11 厦门大学思明校区（校园建筑与人文）": 2,
        "xiamen_guide.md::2.12 沙坡尾艺术西区（老港口与文创街区）": 2,
        "xiamen_guide.md::2.15 中山路步行街（骑楼建筑与老字号小吃）": 2,
        "xiamen_guide.md::2.16 集美学村与龙舟池（嘉庚建筑与学村文化）": 3,
    },
    "xiamen_bike_sea": {
        "xiamen_guide.md::2.10 钟鼓索道（城市与山海观景）": 2,
        "xiamen_guide.md::2.13 环岛路与黄厝海滩（海滨骑行与日出）": 3,
        "xiamen_guide.md::5. 预约、交通、价格与安全提示": 2,
    },
    "sanya_beach_resort": {
        "sanya_guide.md::2.6 蜈支洲岛旅游区": 2,
        "sanya_guide.md::2.7 西岛海洋文化旅游区": 2,
        "sanya_guide.md::2.9 亚龙湾公共海滩": 3,
        "sanya_guide.md::2.10 大东海旅游区": 3,
        "sanya_guide.md::2.11 三亚湾与椰梦长廊": 3,
        "sanya_guide.md::2.12 后海村与皇后湾": 2,
        "sanya_guide.md::2.19 天涯小镇": 2,
        "sanya_guide.md::经济型（200 元/晚以下）": 2,
        "sanya_guide.md::舒适型（200-500 元/晚）": 3,
        "sanya_guide.md::豪华型（500 元/晚以上）": 3,
    },
    "sanya_family_relax": {
        "sanya_guide.md::2.1 三亚千古情景区": 2,
        "sanya_guide.md::2.3 南山寺": 2,
        "sanya_guide.md::2.4 天涯海角游览区-天涯石": 2,
        "sanya_guide.md::2.6 蜈支洲岛旅游区": 2,
        "sanya_guide.md::2.7 西岛海洋文化旅游区": 3,
        "sanya_guide.md::2.8 亚龙湾热带天堂森林公园": 2,
        "sanya_guide.md::2.9 亚龙湾公共海滩": 3,
        "sanya_guide.md::2.10 大东海旅游区": 3,
        "sanya_guide.md::2.11 三亚湾与椰梦长廊": 3,
        "sanya_guide.md::2.12 后海村与皇后湾": 2,
        "sanya_guide.md::2.13 亚特兰蒂斯水世界": 2,
        "sanya_guide.md::2.14 亚特兰蒂斯失落的空间水族馆": 2,
        "sanya_guide.md::2.15 大小洞天旅游区": 3,
        "sanya_guide.md::2.16 崖州古城与崖州学宫": 2,
        "sanya_guide.md::2.18 三亚海昌梦幻海洋不夜城": 2,
        "sanya_guide.md::2.19 天涯小镇": 2,
        "sanya_guide.md::2.21 亚龙湾国际玫瑰谷": 2,
        "sanya_guide.md::2.22 白鹭公园": 2,
        "sanya_guide.md::2.23 东岸湿地公园": 2,
    },
    "sanya_seafood_culture": {
        "sanya_guide.md::2.1 三亚千古情景区": 2,
        "sanya_guide.md::2.3 南山寺": 3,
        "sanya_guide.md::2.7 西岛海洋文化旅游区": 2,
        "sanya_guide.md::2.15 大小洞天旅游区": 2,
        "sanya_guide.md::2.16 崖州古城与崖州学宫": 2,
        "sanya_guide.md::中档特色（人均 50-150 元）": 3,
        "sanya_guide.md::高端体验（人均 200 元以上）": 2,
    },
    "beijing_history_palace": {
        "beijing_guide.md::2.1 天安门广场": 3,
        "beijing_guide.md::2.2 故宫博物院": 3,
        "beijing_guide.md::2.3 颐和园": 3,
        "beijing_guide.md::2.5 天坛公园（历史文化与中轴线）": 3,
        "beijing_guide.md::2.6 景山公园（历史文化与中轴线）": 3,
        "beijing_guide.md::2.7 北海公园（历史文化与中轴线）": 2,
        "beijing_guide.md::2.8 恭王府博物馆（历史文化与中轴线）": 2,
        "beijing_guide.md::2.10 钟鼓楼（历史文化与中轴线）": 2,
        "beijing_guide.md::2.11 雍和宫（历史文化与中轴线）": 2,
        "beijing_guide.md::2.12 孔庙和国子监博物馆（历史文化与中轴线）": 2,
        "beijing_guide.md::2.13 正阳门与前门大街（历史文化与中轴线）": 2,
        "beijing_guide.md::2.15 北京古代建筑博物馆（先农坛）（历史文化与中轴线）": 2,
        "beijing_guide.md::2.17 白塔寺（妙应寺）（历史文化与中轴线）": 2,
        "beijing_guide.md::2.19 明十三陵（历史文化与中轴线）": 2,
        "beijing_guide.md::2.20 圆明园遗址公园（皇家园林与城市公园）": 2,
        "beijing_guide.md::2.24 中山公园（皇家园林与城市公园）": 2,
        "beijing_guide.md::2.30 中国国家博物馆（博物馆、艺术与研学）": 2,
        "beijing_guide.md::2.31 首都博物馆（博物馆、艺术与研学）": 2,
    },
    "beijing_food_local": {
        "beijing_guide.md::经济实惠（人均 30 元以下）": 3,
        "beijing_guide.md::老北京早餐与小吃（人均约20-60元）": 3,
        "beijing_guide.md::炸酱面、包子与北京家常（人均约30-100元）": 3,
        "beijing_guide.md::中档特色（人均 50-150 元）": 2,
        "beijing_guide.md::北京烤鸭（人均约100-350元）": 3,
        "beijing_guide.md::铜锅涮肉与清真美食（人均约80-250元）": 3,
        "beijing_guide.md::京菜、鲁菜与宫廷风味（人均约100-500元）": 3,
        "beijing_guide.md::高端体验（人均 200 元以上）": 2,
        "beijing_guide.md::美食街区与选择建议": 2,
    },
    "beijing_family_study": {
        "beijing_guide.md::2.1 天安门广场": 3,
        "beijing_guide.md::2.2 故宫博物院": 3,
        "beijing_guide.md::2.5 天坛公园（历史文化与中轴线）": 2,
        "beijing_guide.md::2.6 景山公园（历史文化与中轴线）": 2,
        "beijing_guide.md::2.7 北海公园（历史文化与中轴线）": 2,
        "beijing_guide.md::2.8 恭王府博物馆（历史文化与中轴线）": 2,
        "beijing_guide.md::2.10 钟鼓楼（历史文化与中轴线）": 2,
        "beijing_guide.md::2.12 孔庙和国子监博物馆（历史文化与中轴线）": 3,
        "beijing_guide.md::2.13 正阳门与前门大街（历史文化与中轴线）": 2,
        "beijing_guide.md::2.15 北京古代建筑博物馆（先农坛）（历史文化与中轴线）": 3,
        "beijing_guide.md::2.18 卢沟桥与宛平城（历史文化与中轴线）": 2,
        "beijing_guide.md::2.19 明十三陵（历史文化与中轴线）": 2,
        "beijing_guide.md::2.20 圆明园遗址公园（皇家园林与城市公园）": 2,
        "beijing_guide.md::2.24 中山公园（皇家园林与城市公园）": 2,
        "beijing_guide.md::2.30 中国国家博物馆（博物馆、艺术与研学）": 3,
        "beijing_guide.md::2.31 首都博物馆（博物馆、艺术与研学）": 3,
        "beijing_guide.md::2.41 周口店北京人遗址博物馆（博物馆、艺术与研学）": 2,
    },
}

# Explicitly documented borderline exclusions. Every remaining chunk is still
# emitted as grade 0 in the exhaustive annotation file.
WEAK_RELEVANCE: dict[str, dict[str, str]] = {
    "dali_sunset_easy_photo": {
        "dali_guide.md::2.17 龙龛码头与龙龛村": "正文明确偏日出，与“不早起、日落”方向相反。",
        "dali_guide.md::2.18 才村码头": "正文明确偏日出，仅满足洱海散步，未满足日落摄影。",
        "dali_guide.md::2.20 古生村与古生村廊桥": "有洱海村落景观，但没有日落或摄影决策信息。",
        "dali_guide.md::2.24 海舌生态公园": "有洱海湿地景观，但没有日落或摄影决策信息。",
        "dali_guide.md::2.28 小普陀": "位于洱海且停留轻松，但正文没有日落或摄影信息。",
    },
    "dali_culture_slow_trip": {
        "dali_guide.md::2.3 洋人街": "适合古城慢行，但正文没有白族文化、扎染或古镇历史信息。",
        "dali_guide.md::2.4 大理古城红龙井": "适合文艺慢行，但只弱关联古城文化。",
        "dali_guide.md::2.37 宾川鸡足山": "佛教文化相关，但全天山地行程不符合慢节奏古镇与白族文化主线。",
        "dali_guide.md::2.43 巍宝山": "道教与古建文化相关，但偏山地游览且不直接回答白族、扎染或古镇意图。",
        "dali_guide.md::2.44 东莲花村": "体现多民族和马帮文化，但主体是回族村落，不是白族文化主线。",
        "dali_guide.md::2.45 诺邓古村": "古村慢游相关，但距离远且正文未覆盖白族、扎染或崇圣寺。",
    },
    "dali_food_budget": {
        "dali_guide.md::2.21 喜洲古镇": "正文只顺带提到喜洲粑粑，主体仍是古镇景点。",
        "dali_guide.md::2.45 诺邓古村": "正文只顺带提到诺邓火腿，缺少餐厅和预算决策信息。",
    },
    "chengdu_relax_food": {
        "chengdu_guide.md::2.3 黄龙溪古镇": "有小吃和文化，但往返半日且节假日拥挤，对带父母轻松慢游仅弱相关。",
        "chengdu_guide.md::2.13 东郊记忆（工业遗产与文创）": "有文化和城市休闲属性，但与慢生活、传统美食及父母友好主线较弱。",
        "chengdu_guide.md::2.16 九眼桥与锦江绿道（城市夜景）": "适合散步，但夜生活属性与带父母的文化美食慢游只部分相关。",
        "chengdu_guide.md::2026成都米其林二星餐厅": "属于成都餐饮，但预算和正式用餐定位不是该 Query 的主要慢生活体验。",
        "chengdu_guide.md::2026成都米其林一星多元菜系餐厅": "位于成都但以非本地菜系为主，只弱关联美食意图。",
    },
    "chengdu_food_deep": {
        "chengdu_guide.md::2.9 文殊院（历史文化与宗教场所）": "周边有小吃和茶饮，但正文主体是寺院。",
        "chengdu_guide.md::2026成都米其林一星多元菜系餐厅": "是高端餐饮信息，但以非川菜为主，不覆盖火锅、担担面或兔头。",
    },
    "chengdu_park_old_town_nature": {
        "chengdu_guide.md::2.44 青城后山（山水徒步）": "自然风景明确，但路滑、坡陡和半日至一天徒步不符合“轻松”。",
        "chengdu_guide.md::2.45 西岭雪山（山地与冰雪）": "自然主题明确，但高海拔、索道和全天行程不属于轻松城市休闲。",
        "chengdu_guide.md::2.49 川西竹海景区（竹林徒步）": "自然景观相关，但峡谷步道和坡路削弱了轻松意图。",
    },
    "xian_history_culture": {
        "xian_guide.md::2.1 西安千古情售票厅": "以商业演出呈现历史，缺少古迹、博物馆或遗址本体信息。",
        "xian_guide.md::2.9 大唐不夜城": "唐风街景与夜游相关，但不是历史遗存或博物馆。",
        "xian_guide.md::2.10 大唐芙蓉园": "唐文化主题园林与演艺相关，但历史遗存和深度研究价值较弱。",
        "xian_guide.md::2.12 《长恨歌》实景演出": "历史题材演出相关，但不是古迹、遗址或博物馆本体。",
        "xian_guide.md::2.16 长安十二时辰主题街区": "唐文化主题体验相关，但历史遗存和研究价值较弱。",
        "xian_guide.md::2.20 白鹿原·白鹿仓": "有关中文化和民俗，但更偏商业街区与游乐项目。",
    },
    "xian_food_night": {
        "xian_guide.md::2.9 大唐不夜城": "夜游属性明确，但正文没有本地小吃、夜市或餐馆信息。",
        "xian_guide.md::2.16 长安十二时辰主题街区": "可能包含餐饮体验，但正文主体是付费唐文化主题街区。",
    },
    "xian_family_study": {
        "xian_guide.md::2.18 曲江海洋极地公园": "适合亲子，但不属于历史文化研学。",
        "xian_guide.md::2.1 西安千古情售票厅": "历史演出适合家庭，但商业表演的研学深度有限。",
        "xian_guide.md::2.9 大唐不夜城": "适合家庭夜游，但历史研学价值有限。",
        "xian_guide.md::2.10 大唐芙蓉园": "唐文化主题可辅助体验，但不是历史遗存。",
        "xian_guide.md::2.12 《长恨歌》实景演出": "历史题材可辅助理解，但偏夜间演出且不够轻松。",
        "xian_guide.md::2.13 骊山与骊山索道": "有历史遗迹，但台阶、气温和体力要求削弱轻松亲子意图。",
        "xian_guide.md::2.16 长安十二时辰主题街区": "适合亲子体验，但研学深度有限。",
    },
    "xiamen_couple_relax": {
        "xiamen_guide.md::2.9 厦门园林植物园（自然生态与摄影）": "适合摄影，但游览时间和步行量较大，与情侣轻松美食主线只部分相关。",
        "xiamen_guide.md::2.16 集美学村与龙舟池（嘉庚建筑与学村文化）": "有文艺建筑和散步空间，但不覆盖鼓浪屿或美食核心。",
    },
    "xiamen_architecture_history": {
        "xiamen_guide.md::2.2 日光岩": "位于鼓浪屿并可看整体风貌，但正文主要是登高观景。",
        "xiamen_guide.md::2.8 鼓浪屿管风琴艺术中心（鼓浪屿音乐文化）": "有文化价值，但正文没有建筑或历史信息。",
    },
    "xiamen_bike_sea": {
        "xiamen_guide.md::2.14 曾厝垵文创村（小吃、民宿与夜间休闲）": "邻近环岛路且可休息，但正文没有骑行、海景或日落路线信息。",
        "xiamen_guide.md::2.12 沙坡尾艺术西区（老港口与文创街区）": "有傍晚滨水散步氛围，但没有骑行或日落路线信息。",
    },
    "sanya_beach_resort": {
        "sanya_guide.md::2.8 亚龙湾热带天堂森林公园": "属于亚龙湾度假区域，但正文主体是雨林观景，不是海滩或酒店。",
        "sanya_guide.md::2.13 亚特兰蒂斯水世界": "位于度假区并适合玩水，但不是放松型海滩或住宿信息。",
        "sanya_guide.md::2.14 亚特兰蒂斯失落的空间水族馆": "位于度假酒店综合体，但正文主体是室内水族馆。",
        "sanya_guide.md::2.20 凤凰岭海誓山盟景区": "可看海湾夕阳，但不直接提供海滩或酒店度假信息。",
    },
    "sanya_family_relax": {
        "sanya_guide.md::2.2 鹿回头风景区": "适合家庭观景，但没有海滩、文化研学或明确轻松活动信息。",
        "sanya_guide.md::2.17 临春岭森林公园": "免费自然活动相关，但台阶和高温因素削弱轻松家庭意图。",
        "sanya_guide.md::2.20 凤凰岭海誓山盟景区": "可轻松乘索道观景，但更偏情侣和摄影。",
    },
    "sanya_seafood_culture": {
        "sanya_guide.md::经济实惠（人均 30 元以下）": "主要是粉面、甜品和小吃，没有直接覆盖新鲜海鲜或椰子鸡。",
        "sanya_guide.md::2.4 天涯海角游览区-天涯石": "有地方文化象征，但与南山寺、海鲜和椰子鸡主线关联较弱。",
    },
    "beijing_history_palace": {
        "beijing_guide.md::2.9 什刹海历史文化街区（历史文化与中轴线）": "属于老城历史空间，但不直接覆盖皇家宫殿或天安门核心。",
        "beijing_guide.md::2.14 大栅栏历史文化街区（历史文化与中轴线）": "有商业史和街区文化，但不属于皇家历史主线。",
        "beijing_guide.md::2.16 法源寺（历史文化与中轴线）": "历史悠久，但与故宫、天安门和皇家制度只弱相关。",
        "beijing_guide.md::2.18 卢沟桥与宛平城（历史文化与中轴线）": "历史教育价值高，但不属于皇家宫殿或首次中轴线核心。",
        "beijing_guide.md::2.21 香山公园（皇家园林与城市公园）": "有皇家园林渊源，但正文重点是山林和红叶。",
        "beijing_guide.md::2.41 周口店北京人遗址博物馆（博物馆、艺术与研学）": "历史研究价值高，但属于史前文明，偏离皇家历史主线。",
    },
    "beijing_food_local": {
        "beijing_guide.md::素食与高端特色体验（人均约200元以上）": "包含一家现代京菜，但该块多数是素食或非北京菜系。",
    },
    "beijing_family_study": {
        "beijing_guide.md::2.32 国家自然博物馆（博物馆、艺术与研学）": "适合亲子研学，但主题是自然史，不回答天安门、故宫与历史文化主线。",
        "beijing_guide.md::2.33 中国科学技术馆（博物馆、艺术与研学）": "适合亲子研学，但主题是科学技术，不回答历史文化核心。",
        "beijing_guide.md::2.34 北京天文馆（博物馆、艺术与研学）": "适合亲子研学，但主题是天文学，不回答历史文化核心。",
        "beijing_guide.md::2.35 中国航空博物馆（博物馆、艺术与研学）": "兼具航空史，但与天安门、故宫和古都历史主线距离较远。",
        "beijing_guide.md::2.42 中国园林博物馆（博物馆、艺术与研学）": "适合建筑和园林研学，但与天安门、故宫历史主线距离较远。",
        "beijing_guide.md::2.43 北京大运河博物馆（博物馆、艺术与研学）": "属于历史研学，但不直接服务天安门—故宫主线。",
    },
}


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _positive_reason(grade: int) -> str:
    if grade == 3:
        return "标题与正文直接覆盖 Query 的核心对象，或同时强匹配多个核心意图。"
    return "正文直接满足 Query 的重要子意图，可用于景点、餐饮、路线或预算决策。"


def main() -> int:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    chunks = load_guide_chunks()
    chunks_by_document: dict[str, list[dict[str, str]]] = {}
    for chunk in chunks:
        chunks_by_document.setdefault(chunk["document_id"], []).append(chunk)

    case_ids = [str(case["id"]) for case in cases]
    if set(REVIEWED_QRELS) != set(case_ids):
        raise ValueError("Reviewed qrels do not exactly cover evaluation cases")

    graded_qrels = {
        case_id: dict(judgments)
        for case_id, judgments in REVIEWED_QRELS.items()
    }
    for case_id, weak_judgments in WEAK_RELEVANCE.items():
        if case_id not in graded_qrels:
            raise ValueError(f"Weak relevance references unknown case: {case_id}")
        overlap = set(graded_qrels[case_id]) & set(weak_judgments)
        if overlap:
            raise ValueError(
                f"Weak and formal judgments overlap for {case_id}: {sorted(overlap)}"
            )
        graded_qrels[case_id].update(
            {chunk_key: 1 for chunk_key in weak_judgments}
        )
    validate_qrels(graded_qrels, case_ids)

    all_chunk_keys = {_chunk_key(chunk) for chunk in chunks}
    qrels_keys = {
        chunk_key
        for judgments in graded_qrels.values()
        for chunk_key in judgments
    }
    missing_keys = sorted(qrels_keys - all_chunk_keys)
    if missing_keys:
        raise ValueError(f"Reviewed qrels reference missing chunks: {missing_keys}")

    annotation_cases: dict[str, Any] = {}
    grade_counts: Counter[int] = Counter()
    reviewed_pairs = 0
    for case in cases:
        case_id = str(case["id"])
        destination = str(case["destination"])
        document_id = CITY_GUIDES[destination]
        judgments: list[dict[str, Any]] = []
        for chunk in chunks_by_document[document_id]:
            chunk_key = _chunk_key(chunk)
            grade = int(graded_qrels[case_id].get(chunk_key, 0))
            if chunk_key in WEAK_RELEVANCE.get(case_id, {}):
                reason = WEAK_RELEVANCE[case_id][chunk_key]
            elif grade >= 2:
                reason = _positive_reason(grade)
            else:
                reason = "该 Chunk 的正文不能实质回答本 Query 的核心对象或重要子意图。"

            judgments.append(
                {
                    "chunk_key": chunk_key,
                    "title": chunk["title"],
                    "relevance": grade,
                    "formal_relevant": grade >= 2,
                    "reason": reason,
                }
            )
            grade_counts[grade] += 1
            reviewed_pairs += 1

        formal_count = len(REVIEWED_QRELS[case_id])
        annotation_cases[case_id] = {
            "query": case["query"],
            "destination": destination,
            "document_id": document_id,
            "reviewed_chunk_count": len(judgments),
            "formal_relevant_count": formal_count,
            "judgments": judgments,
        }

    annotations = {
        "schema_version": 1,
        "qrels_version": "v3-exhaustive-semantic-2026-08-02",
        "relevance_threshold": 2,
        "rules": {
            "3": "直接回答核心对象，或同时强匹配两个以上核心意图。",
            "2": "直接满足一个重要子意图，并能支持实际旅行决策。",
            "1": "只有背景、顺路、泛主题或弱关联；不计入正式正确答案。",
            "0": "不能实质回答 Query。",
        },
        "methodology": {
            "candidate_pool_used": False,
            "vector_similarity_used_for_judging": False,
            "review_scope": "For each query, every logical chunk in its destination guide.",
            "canonical_qrels_contains_grades": [1, 2, 3],
            "formal_relevance_grades": [2, 3],
        },
        "coverage": {
            "case_count": len(cases),
            "guide_chunk_count": len(chunks),
            "reviewed_query_chunk_pairs": reviewed_pairs,
            "expected_query_chunk_pairs": sum(
                len(chunks_by_document[CITY_GUIDES[str(case["destination"])]])
                for case in cases
            ),
            "grade_counts": {str(grade): grade_counts[grade] for grade in range(4)},
        },
        "cases": annotation_cases,
    }

    _write_json(QRELS_V3_PATH, graded_qrels)
    _write_json(CANONICAL_QRELS_PATH, graded_qrels)
    _write_json(ANNOTATIONS_PATH, annotations)

    print(f"cases={len(cases)}")
    print(f"guide_chunks={len(chunks)}")
    print(f"reviewed_pairs={reviewed_pairs}")
    print(f"formal_qrels={sum(len(items) for items in REVIEWED_QRELS.values())}")
    print(f"grade_counts={dict(sorted(grade_counts.items()))}")
    print(f"qrels_v3={QRELS_V3_PATH}")
    print(f"annotations={ANNOTATIONS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
