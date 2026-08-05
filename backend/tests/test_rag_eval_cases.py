import json
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
CASES_PATH = BACKEND_DIR / "eval" / "rag_eval_cases.json"
QRELS_PATH = BACKEND_DIR / "eval" / "rag_qrels.json"
QRELS_V4_PATH = BACKEND_DIR / "eval" / "rag_qrels_v4.json"
ANNOTATIONS_V4_PATH = BACKEND_DIR / "eval" / "rag_qrels_v4_annotations.json"
CITY_GUIDES = {
    "大理": "dali_guide.md",
    "成都": "chengdu_guide.md",
    "西安": "xian_guide.md",
    "厦门": "xiamen_guide.md",
    "三亚": "sanya_guide.md",
    "北京": "beijing_guide.md",
}


def _load_cases() -> list[dict]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def _load_qrels() -> dict[str, dict[str, int]]:
    return json.loads(QRELS_PATH.read_text(encoding="utf-8"))


def test_eval_cases_contain_only_fixed_top5_inputs() -> None:
    cases = _load_cases()
    assert cases
    assert len({case["id"] for case in cases}) == len(cases)
    for case in cases:
        assert set(case) == {"id", "destination", "query", "top_k"}
        assert case["id"].strip()
        assert case["destination"] in CITY_GUIDES
        assert case["query"].strip()
        assert case["top_k"] == 5


def test_qrels_cover_all_cases_and_reference_existing_destination_chunks() -> None:
    cases = _load_cases()
    qrels = _load_qrels()
    all_chunk_keys_by_guide: dict[str, set[str]] = {}

    for guide_name in CITY_GUIDES.values():
        guide_text = (BACKEND_DIR / "data" / guide_name).read_text(encoding="utf-8")
        titles = {
            line.lstrip("#").strip()
            for line in guide_text.splitlines()
            if line.startswith("## ") or line.startswith("### ")
        }
        all_chunk_keys_by_guide[guide_name] = {
            f"{guide_name}::{title}" for title in titles
        }

    assert set(qrels) == {case["id"] for case in cases}
    for case in cases:
        judgments = qrels[case["id"]]
        guide_name = CITY_GUIDES[case["destination"]]
        assert any(int(relevance) >= 2 for relevance in judgments.values())
        assert set(judgments) <= all_chunk_keys_by_guide[guide_name]


def test_qrels_use_supported_grades() -> None:
    qrels = _load_qrels()
    all_grades: set[int] = set()
    for judgments in qrels.values():
        assert set(map(int, judgments.values())) <= {0, 1, 2, 3}
        all_grades.update(map(int, judgments.values()))

    assert all_grades == {1, 2, 3}


def test_qrels_preserve_core_semantic_anchors() -> None:
    qrels = _load_qrels()
    expected = {
        "dali_sunset_easy_photo": {
            "dali_guide.md::2.5 大理180度海景网红打卡地": 3,
            "dali_guide.md::双廊露娜·蓝泊湾": 3,
        },
        "chengdu_food_deep": {
            "chengdu_guide.md::餐饮：老成都张妹特色小吃（现代大厦店）": 3,
            "chengdu_guide.md::餐饮：马旺子·川小馆（成都太古里店）": 3,
            "chengdu_guide.md::餐饮：小龙坎老火锅": 3,
            "chengdu_guide.md::餐饮提示：火锅点餐与食用安全": 3,
        },
        "sanya_seafood_culture": {
            "sanya_guide.md::2.3 南山寺": 3,
            "sanya_guide.md::餐饮：嗲嗲的椰子鸡（椰梦长廊店）": 3,
            "sanya_guide.md::餐饮：阿浪海鲜（第一市场店）": 3,
        },
        "beijing_food_local": {
            "beijing_guide.md::餐饮：尹三豆汁（前门旗舰店）": 3,
            "beijing_guide.md::餐饮：方砖厂69号炸酱面（前门大街店）": 3,
            "beijing_guide.md::餐饮：全聚德": 3,
        },
    }

    for case_id, anchors in expected.items():
        for chunk_key, grade in anchors.items():
            assert qrels[case_id][chunk_key] == grade


def test_canonical_qrels_match_semantic_audit_v4() -> None:
    qrels = _load_qrels()
    assert qrels == json.loads(QRELS_V4_PATH.read_text(encoding="utf-8"))

    annotations = json.loads(ANNOTATIONS_V4_PATH.read_text(encoding="utf-8"))
    assert (
        annotations["qrels_version"]
        == "v5-semantic-undergrading-review-2026-08-04"
    )
    methodology = annotations["methodology"]
    assert methodology["semantic_only"] is True
    assert methodology["candidate_pool_used"] is False
    assert methodology["vector_similarity_used_for_judging"] is False
    assert methodology["embedding_results_used_for_judging"] is False
    assert methodology["current_entity_chunks_manually_reviewed"] is True
    assert annotations["coverage"]["guide_chunk_count"] == 676
    assert annotations["coverage"]["reviewed_query_chunk_pairs"] == 2028
    assert (
        annotations["coverage"]["reviewed_query_chunk_pairs"]
        == annotations["coverage"]["expected_query_chunk_pairs"]
    )

    for case_id, case_audit in annotations["cases"].items():
        audited_nonzero = {
            judgment["chunk_key"]: judgment["relevance"]
            for judgment in case_audit["judgments"]
            if judgment["relevance"] > 0
        }
        assert qrels[case_id] == audited_nonzero
