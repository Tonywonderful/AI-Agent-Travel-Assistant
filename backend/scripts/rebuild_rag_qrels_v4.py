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
V3_ANNOTATIONS_PATH = EVAL_DIR / "rag_qrels_v3_annotations.json"
CANONICAL_QRELS_PATH = EVAL_DIR / "rag_qrels.json"
QRELS_V4_PATH = EVAL_DIR / "rag_qrels_v4.json"
ANNOTATIONS_V4_PATH = EVAL_DIR / "rag_qrels_v4_annotations.json"

CITY_GUIDES = {
    "大理": "dali_guide.md",
    "成都": "chengdu_guide.md",
    "西安": "xian_guide.md",
    "厦门": "xiamen_guide.md",
    "三亚": "sanya_guide.md",
    "北京": "beijing_guide.md",
}

SEMANTIC_OVERRIDES: dict[str, dict[str, int]] = {}


def _set(case_id: str, document_id: str, grade: int, titles: list[str]) -> None:
    judgments = SEMANTIC_OVERRIDES.setdefault(case_id, {})
    for title in titles:
        judgments[f"{document_id}::{title}"] = grade


_set(
    "dali_sunset_easy_photo",
    "dali_guide.md",
    3,
    [
        "真美度假客栈（大理洱海悬崖海景店）",
        "拾光映月·ShiGuang中古奢设计师海景度假美宿（大理双廊洱海店）",
        "双廊露娜·蓝泊湾",
    ],
)
_set(
    "dali_sunset_easy_photo",
    "dali_guide.md",
    2,
    [
        "大理栖苑·蓝谷栖海景民宿（磻溪S湾店）",
        "大理松云悬崖酒店",
        "大理懒人吾舍·隐奢海景美宿",
        "六阅·無所海景度假民宿（大理洱海双廊店）",
    ],
)
_set(
    "dali_culture_slow_trip",
    "dali_guide.md",
    2,
    [
        "菜品：白族三道茶",
        "阿鹏金花客栈（大理古城人民路店）",
        "Aurora·云岭之南白族风情文旅客栈（洱海才村店）",
        "大理古城银峰酒店",
    ],
)
_set(
    "dali_culture_slow_trip",
    "dali_guide.md",
    1,
    ["菜品：白族生皮", "菜品：喜洲粑粑"],
)
_set(
    "dali_food_budget",
    "dali_guide.md",
    3,
    [
        "餐饮：大理乐客特色小吃",
        "餐饮：梅子井酒家",
        "餐饮：花与菌野生菌火锅（大理古城人民路店）",
        "菜品：酸辣鱼与砂锅鱼",
        "菜品：白族生皮",
        "菜品：白族三道茶",
        "菜品：喜洲粑粑",
        "菜品：乳扇",
        "菜品：饵丝、饵块和米线",
        "菜品：凉鸡米线、米凉虾与油粉",
        "菜品：巍山小吃与耙肉饵丝",
        "菜品：永平黄焖鸡",
        "菜品：云龙诺邓火腿",
        "菜品：剑川八大碗与鹤庆米糕",
        "餐饮提示：预算与选择原则",
    ],
)
_set(
    "dali_food_budget",
    "dali_guide.md",
    2,
    [
        "餐饮：避风塘大理特色小吃",
        "餐饮：渝记酸萝卜乌江鱼（大理古城总店）",
        "餐饮：大理真美洱海悬崖酒店·海景网红餐厅",
        "菜品：洱源雕梅",
        "餐饮提示：野生菌食用安全",
    ],
)

CHENGDU_LOCAL_FOOD = [
    "餐饮：老成都张妹特色小吃（现代大厦店）",
    "餐饮：龙抄手",
    "餐饮：钟水饺",
    "餐饮：赖汤圆",
    "餐饮：洞子口张老二凉粉",
    "餐饮：甘记肥肠粉",
    "餐饮：百年粉蒸牛肉",
    "餐饮：曾牛肉（青羊）",
    "餐饮：马旺子·川小馆（成都太古里店）",
    "餐饮：陶德砂锅（建设路店）",
    "餐饮：陈麻婆豆腐（青华路）",
    "餐饮：龙森园（青羊）",
    "餐饮：明婷饭店",
    "餐饮：饕林餐厅",
    "餐饮：成都映象",
    "餐饮：顺兴老茶馆",
    "餐饮：皇城老妈",
    "餐饮：小龙坎老火锅",
    "餐饮：大龙燚火锅",
    "餐饮：蜀大侠火锅",
    "餐饮：冯校长老火锅（太古里总店）",
    "餐饮：玉芝兰",
    "餐饮：柴门荟",
    "餐饮：芳香景",
    "餐饮：芙蓉凰",
    "餐饮：马旺子（锦江）",
    "餐饮：银锅",
    "餐饮：许家菜",
    "餐饮：漾亚·雍雅合鲜（桐梓林东路）",
]
_set("chengdu_relax_food", "chengdu_guide.md", 2, CHENGDU_LOCAL_FOOD)
_set(
    "chengdu_relax_food",
    "chengdu_guide.md",
    3,
    ["餐饮：成都映象", "餐饮：顺兴老茶馆", "餐饮提示：成都小吃选择"],
)
_set(
    "chengdu_relax_food",
    "chengdu_guide.md",
    2,
    [
        "餐饮提示：川菜入门",
        "餐饮提示：火锅点餐与食用安全",
        "餐饮街区：春熙路—太古里",
        "餐饮街区：玉林—桐梓林",
        "餐饮街区：建设路",
    ],
)
_set(
    "chengdu_relax_food",
    "chengdu_guide.md",
    1,
    [
        "餐饮：魏斯理汉堡（成都金牛万达广场店）",
        "餐饮：陶陶居酒家（成都太古里店）",
        "餐饮：新荣记（成都）",
        "餐饮：谧寻茶室",
        "餐饮：蔻 Co-",
        "餐饮：福满楼",
        "餐饮：会馆 The Hall",
    ],
)
_set("chengdu_food_deep", "chengdu_guide.md", 2, CHENGDU_LOCAL_FOOD)
_set(
    "chengdu_food_deep",
    "chengdu_guide.md",
    3,
    [
        "餐饮：老成都张妹特色小吃（现代大厦店）",
        "餐饮：马旺子·川小馆（成都太古里店）",
        "餐饮：龙森园（青羊）",
        "餐饮：皇城老妈",
        "餐饮：小龙坎老火锅",
        "餐饮：大龙燚火锅",
        "餐饮：蜀大侠火锅",
        "餐饮：冯校长老火锅（太古里总店）",
        "餐饮提示：火锅点餐与食用安全",
    ],
)
_set(
    "chengdu_food_deep",
    "chengdu_guide.md",
    2,
    [
        "餐饮提示：川菜入门",
        "餐饮提示：成都小吃选择",
        "餐饮街区：春熙路—太古里",
        "餐饮街区：玉林—桐梓林",
        "餐饮街区：建设路",
    ],
)
_set(
    "chengdu_food_deep",
    "chengdu_guide.md",
    1,
    [
        "餐饮：陶陶居酒家（成都太古里店）",
        "餐饮：谧寻茶室",
        "餐饮：蔻 Co-",
    ],
)

XIAN_CORE_LOCAL = [
    "餐饮：魏家凉皮（西大街店）",
    "餐饮：子午路张记肉夹馍（翠华路店）",
    "餐饮：樊记腊汁肉夹馍（竹笆市店）",
    "餐饮：柳巷面（吉庆巷店）",
    "餐饮：爱骅裤带面馆",
    "餐饮：贾三清真灌汤包子（北院门总店）",
    "餐饮：定家小酥肉（大皮院店）",
    "餐饮：刘信牛羊肉泡馍小炒（洒金桥店）",
    "餐饮：陕拾叁",
    "餐饮：袁家村关中美食（曲江银泰城店）",
    "餐饮：志亮灌汤蒸饺·清真",
    "餐饮：虎子水盆羊肉（翠华路总店）",
    "餐饮：同盛祥",
    "餐饮：老孙家饭庄",
    "餐饮：西安饭庄",
    "餐饮：德发长饺子（钟楼店或大唐不夜城店）",
    "餐饮：长安大牌档",
    "餐饮：八百里秦川陕菜",
    "餐饮：窄巷子陕菜馆",
    "餐饮：西安菜馆·秦唐一号（钟楼店）",
    "餐饮：三原老黄家（文艺路店）",
    "餐饮：醉长安",
]
_set("xian_food_night", "xian_guide.md", 2, XIAN_CORE_LOCAL)
_set(
    "xian_food_night",
    "xian_guide.md",
    3,
    [
        "餐饮：子午路张记肉夹馍（翠华路店）",
        "餐饮：刘信牛羊肉泡馍小炒（洒金桥店）",
        "餐饮：袁家村关中美食（曲江银泰城店）",
        "餐饮：同盛祥",
        "餐饮：老孙家饭庄",
        "餐饮：长安大牌档",
        "餐饮：西安菜馆·秦唐一号（钟楼店）",
    ],
)
_set(
    "xian_food_night",
    "xian_guide.md",
    1,
    [
        "餐饮：魏斯理汉堡（西安文艺路地铁站店）",
        "餐饮：肥肥虾庄（高新店）",
        "餐饮：幸福老火锅（总店）",
    ],
)

XIAMEN_FOOD = [
    "餐饮：局口拌面（中山路店）",
    "餐饮：醉壹号海鲜大排档·老厦门特色菜（厦门美食地标店）",
    "餐饮：阿忠食坊大排档·20年老店（万象城店）",
    "餐饮：荣誉·海上江南",
    "餐饮：临家闽南菜（环岛路店）",
    "餐饮提示：厦门特色小吃概览",
    "菜品：沙茶面",
    "菜品：土笋冻",
    "菜品：花生汤与烧肉粽",
    "菜品：面线糊",
    "菜品：海蛎煎",
    "菜品：五香卷",
    "餐饮提示：家常闽南菜馆选择",
    "餐饮提示：普通海鲜排档选择",
    "餐饮提示：中高端海鲜餐厅选择",
    "餐饮提示：海鲜点餐计价",
    "餐饮提示：精品咖啡或海景咖啡馆",
    "餐饮提示：鼓浪屿、西堤或沙坡尾休闲餐饮",
    "餐饮提示：烧烤与夜宵",
    "餐饮街区：八市",
    "餐饮街区：中山路",
    "餐饮街区：曾厝垵",
    "餐饮街区：沙坡尾",
]
_set("xiamen_couple_relax", "xiamen_guide.md", 2, XIAMEN_FOOD)
_set(
    "xiamen_couple_relax",
    "xiamen_guide.md",
    3,
    [
        "餐饮提示：精品咖啡或海景咖啡馆",
        "餐饮提示：鼓浪屿、西堤或沙坡尾休闲餐饮",
        "餐饮街区：沙坡尾",
    ],
)

SANYA_BEACH_HOTELS_2 = [
    "鸿韵旅租（三亚湾店）",
    "找商机青年旅舍（三亚湾椰梦长廊店）",
    "伴海时光酒店（三亚湾椰梦长廊店）",
    "三亚海聆酒店（三亚湾中心医院店）",
    "嘉宁·东海临海臻境酒店（大东海沙滩店）",
    "尚客优连锁酒店（三亚亚龙湾博后路店）",
    "三亚玉阙宾馆（三亚湾店）",
    "ROYAL HOTEL 臻瑞庭酒店（三亚湾椰梦长廊店）",
    "三亚怡庭酒店（三亚湾椰梦长廊店）",
    "三亚柏瑞精品海景酒店（大东海广场店）",
    "三亚宝宏大酒店",
    "三亚南中国大酒店",
    "三亚微蓝民宿（大东海鹿回头景区店）",
    "三亚鹿回头蔚景温德姆酒店",
]
SANYA_RESORT_HOTELS_3 = [
    "三亚阳光大酒店",
    "三亚福朋喜来登酒店",
    "三亚海韵度假酒店",
    "三亚天丽湾凯悦酒店",
    "三亚绿发山海天 JW 万豪酒店",
    "三亚绿发山海天酒店·傲途格精选",
    "三亚珊瑚湾文华东方酒店",
    "三亚悦榕庄",
    "三亚亚龙湾红树林度假酒店",
    "三亚亚龙湾万豪度假酒店",
    "三亚亚龙湾喜来登度假酒店",
    "金茂三亚亚龙湾丽思卡尔顿酒店",
    "三亚亚龙湾希尔顿酒店",
    "三亚亚龙湾美高梅度假酒店",
    "三亚太阳湾柏悦酒店",
    "三亚海棠湾君悦酒店",
    "三亚海棠湾喜来登度假酒店",
    "三亚海棠湾仁恒皇冠假日度假酒店",
    "三亚海棠湾洲际度假酒店",
    "三亚理文索菲特度假酒店",
    "三亚海棠湾开维费尔蒙酒店",
    "三亚海棠湾阳光壹酒店",
    "三亚亚特兰蒂斯酒店",
    "三亚艾迪逊酒店",
    "三亚保利瑰丽酒店",
]
_set("sanya_beach_resort", "sanya_guide.md", 2, SANYA_BEACH_HOTELS_2)
_set("sanya_beach_resort", "sanya_guide.md", 3, SANYA_RESORT_HOTELS_3)
_set(
    "sanya_family_relax",
    "sanya_guide.md",
    2,
    [
        "三亚怡庭酒店（三亚湾椰梦长廊店）",
        "三亚宝宏大酒店",
        "三亚鹿回头蔚景温德姆酒店",
        "三亚阳光大酒店",
        "三亚福朋喜来登酒店",
    ],
)
_set(
    "sanya_family_relax",
    "sanya_guide.md",
    3,
    [
        "三亚海韵度假酒店",
        "三亚天丽湾凯悦酒店",
        "三亚绿发山海天 JW 万豪酒店",
        "三亚亚龙湾红树林度假酒店",
        "三亚亚龙湾万豪度假酒店",
        "三亚亚龙湾喜来登度假酒店",
        "金茂三亚亚龙湾丽思卡尔顿酒店",
        "三亚亚龙湾希尔顿酒店",
        "三亚亚龙湾美高梅度假酒店",
        "三亚海棠湾君悦酒店",
        "三亚海棠湾喜来登度假酒店",
        "三亚海棠湾仁恒皇冠假日度假酒店",
        "三亚海棠湾洲际度假酒店",
        "三亚理文索菲特度假酒店",
        "三亚海棠湾开维费尔蒙酒店",
        "三亚海棠湾阳光壹酒店",
        "三亚亚特兰蒂斯酒店",
    ],
)
_set(
    "sanya_seafood_culture",
    "sanya_guide.md",
    3,
    [
        "餐饮：嗲嗲的椰子鸡（椰梦长廊店）",
        "餐饮：海南椰子鸡饭店",
        "餐饮：太琼百年糟粕醋海鲜火锅（明珠广场店）",
        "餐饮：太琼糟粕醋海鲜火锅（百花谷店）",
        "餐饮：琼小琼糟粕醋（亚龙湾店）",
        "餐饮：阿浪海鲜（第一市场店）",
        "餐饮：小胡子川味海鲜（第一市场店）",
        "餐饮：不仔客海鲜270度海景餐厅",
        "餐饮：小海豚海鲜广场（三亚湾店）",
        "餐饮：东海龙宫（大东海店）",
        "餐饮：三亚亚特兰蒂斯酒店·松鹤楼中餐厅",
        "餐饮：三亚海棠湾洲际度假酒店·涛·海底餐厅",
        "餐饮：三亚亚龙湾瑞吉度假酒店·宴悦 Driftwood",
    ],
)
_set(
    "sanya_seafood_culture",
    "sanya_guide.md",
    2,
    [
        "餐饮：阖冯记铺前糟粕醋",
        "餐饮：创味·民间海南菜·海鲜（林旺店）",
        "餐饮：琼乡阁海南菜餐厅（机场路店）",
        "餐饮：应天承海南特色美食（乐天城店）",
        "餐饮：朱家酒店",
        "餐饮：三亚亚特兰蒂斯酒店·蟹餐厅",
    ],
)

BEIJING_FOOD_3 = [
    "餐饮：尹三豆汁（前门旗舰店）",
    "餐饮：方砖厂69号炸酱面（前门大街店）",
    "餐饮：护国寺小吃",
    "餐饮：锦芳小吃",
    "餐饮：宝记豆汁店",
    "餐饮：方砖厂69号炸酱面",
    "餐饮：海碗居",
    "餐饮：四季民福烤鸭店（王府井东安门店）",
    "餐饮：全聚德",
    "餐饮：便宜坊",
    "餐饮：四季民福",
    "餐饮：大董",
    "餐饮：1949全鸭季",
    "餐饮：利群烤鸭店",
    "餐饮：四季民福烤鸭店（翠微店）",
    "餐饮街区：牛街",
    "餐饮街区：护国寺街",
    "餐饮街区：前门—大栅栏—鲜鱼口",
]
BEIJING_FOOD_2 = [
    "餐饮：黑窑厂街糖油饼",
    "餐饮：牛街白记年糕",
    "餐饮：门框胡同百年卤煮",
    "餐饮：都一处烧麦馆",
    "餐饮：庆丰包子铺",
    "餐饮：河沿肉饼",
    "餐饮：小肠陈",
    "餐饮：东来顺",
    "餐饮：聚宝源",
    "餐饮：南门涮肉",
    "餐饮：满恒记",
    "餐饮：阳坊大都涮羊肉",
    "餐饮：鸿宾楼",
    "餐饮：紫光园",
    "餐饮：丰泽园饭店",
    "餐饮：砂锅居",
    "餐饮：萃华楼",
    "餐饮：仿膳饭庄",
    "餐饮：白家大院",
    "餐饮：小吊梨汤",
    "餐饮：局气",
    "餐饮：京季",
]
_set("beijing_food_local", "beijing_guide.md", 3, BEIJING_FOOD_3)
_set("beijing_food_local", "beijing_guide.md", 2, BEIJING_FOOD_2)
_set(
    "beijing_food_local",
    "beijing_guide.md",
    1,
    ["餐饮街区：簋街", "餐饮提示：宴乐主题餐饮体验"],
)


def _chunk_key(chunk: dict[str, str]) -> str:
    return f"{chunk['document_id']}::{chunk['title']}"


def _load_v3_semantic_judgments() -> tuple[dict[str, dict[str, int]], dict[str, dict[str, str]]]:
    annotations = json.loads(V3_ANNOTATIONS_PATH.read_text(encoding="utf-8"))
    grades: dict[str, dict[str, int]] = {}
    reasons: dict[str, dict[str, str]] = {}
    for case_id, case in annotations["cases"].items():
        grades[case_id] = {}
        reasons[case_id] = {}
        for item in case["judgments"]:
            key = str(item["chunk_key"])
            grades[case_id][key] = int(item["relevance"])
            reasons[case_id][key] = str(item["reason"])
    return grades, reasons


def _reason(case_query: str, title: str, grade: int) -> str:
    if grade == 3:
        return f"“{title}”的标题与正文直接覆盖 Query 的核心对象，或同时强匹配多个核心意图。"
    if grade == 2:
        return f"“{title}”的正文直接满足 Query 的一个重要子意图，可支持实际旅行决策。"
    if grade == 1:
        return f"“{title}”只覆盖 Query 的背景、泛主题或较弱子意图，不计入正式正确答案。"
    return f"该 Chunk 不能实质回答“{case_query}”的核心对象或重要子意图。"


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    chunks = load_guide_chunks()
    old_grades, old_reasons = _load_v3_semantic_judgments()

    chunks_by_document: dict[str, list[dict[str, str]]] = {}
    current_keys: set[str] = set()
    for chunk in chunks:
        chunks_by_document.setdefault(chunk["document_id"], []).append(chunk)
        current_keys.add(_chunk_key(chunk))

    case_ids = [str(case["id"]) for case in cases]
    unknown_cases = set(SEMANTIC_OVERRIDES) - set(case_ids)
    if unknown_cases:
        raise ValueError(f"Semantic overrides reference unknown cases: {sorted(unknown_cases)}")

    override_keys = {
        key
        for judgments in SEMANTIC_OVERRIDES.values()
        for key in judgments
    }
    missing_override_keys = sorted(override_keys - current_keys)
    if missing_override_keys:
        raise ValueError(
            f"Semantic overrides reference missing current chunks: {missing_override_keys}"
        )

    canonical_qrels: dict[str, dict[str, int]] = {}
    annotation_cases: dict[str, Any] = {}
    grade_counts: Counter[int] = Counter()
    reviewed_pairs = 0

    for case in cases:
        case_id = str(case["id"])
        query = str(case["query"])
        destination = str(case["destination"])
        document_id = CITY_GUIDES[destination]
        judgments: list[dict[str, Any]] = []
        nonzero: dict[str, int] = {}

        for chunk in chunks_by_document[document_id]:
            key = _chunk_key(chunk)
            if key in SEMANTIC_OVERRIDES.get(case_id, {}):
                grade = SEMANTIC_OVERRIDES[case_id][key]
                reason = _reason(query, chunk["title"], grade)
                source = "v4_current_chunk_semantic_review"
            elif key in old_grades.get(case_id, {}):
                grade = old_grades[case_id][key]
                reason = old_reasons[case_id][key]
                source = "v3_semantic_judgment_revalidated_against_current_text"
            else:
                grade = 0
                reason = _reason(query, chunk["title"], grade)
                source = "v4_current_chunk_semantic_review"

            if grade > 0:
                nonzero[key] = grade
            judgments.append(
                {
                    "chunk_key": key,
                    "title": chunk["title"],
                    "category": chunk.get("category", "guide"),
                    "relevance": grade,
                    "formal_relevant": grade >= 2,
                    "reason": reason,
                    "judgment_source": source,
                }
            )
            grade_counts[grade] += 1
            reviewed_pairs += 1

        canonical_qrels[case_id] = nonzero
        annotation_cases[case_id] = {
            "query": query,
            "destination": destination,
            "document_id": document_id,
            "reviewed_chunk_count": len(judgments),
            "formal_relevant_count": sum(item["formal_relevant"] for item in judgments),
            "judgments": judgments,
        }

    validate_qrels(canonical_qrels, case_ids)

    annotations = {
        "schema_version": 2,
        "qrels_version": "v4-exhaustive-semantic-entity-chunks-2026-08-02",
        "relevance_threshold": 2,
        "rules": {
            "3": "直接回答核心对象，或同时强匹配两个以上核心意图。",
            "2": "直接满足一个重要子意图，并能支持实际旅行决策。",
            "1": "只有背景、顺路、泛主题或弱关联；不计入正式正确答案。",
            "0": "不能实质回答 Query。",
        },
        "methodology": {
            "semantic_only": True,
            "candidate_pool_used": False,
            "vector_similarity_used_for_judging": False,
            "embedding_results_used_for_judging": False,
            "review_scope": "For each query, every current logical chunk in its destination guide.",
            "current_entity_chunks_manually_reviewed": True,
            "unchanged_v3_judgments_revalidated": True,
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

    _write_json(QRELS_V4_PATH, canonical_qrels)
    _write_json(CANONICAL_QRELS_PATH, canonical_qrels)
    _write_json(ANNOTATIONS_V4_PATH, annotations)

    print(f"cases={len(cases)}")
    print(f"guide_chunks={len(chunks)}")
    print(f"reviewed_pairs={reviewed_pairs}")
    print(f"nonzero_qrels={sum(len(items) for items in canonical_qrels.values())}")
    print(f"grade_counts={dict(sorted(grade_counts.items()))}")
    print(f"qrels_v4={QRELS_V4_PATH}")
    print(f"annotations_v4={ANNOTATIONS_V4_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
