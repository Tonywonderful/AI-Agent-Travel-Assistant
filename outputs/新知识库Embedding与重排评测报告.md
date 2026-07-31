# 新知识库 Embedding 与重排评测报告

评测时间：2026-07-31

## 1. Embedding 结果

- 知识库目录：`backend/data`
- 文档数：6
- 目的地：北京、成都、大理、三亚、厦门、西安
- Embedding 模型：`qwen3-embedding:4b`（本地 Ollama）
- 向量维度：2560
- Chroma Collection：`travel_guides_ollama_qwen3_4b`
- 当前知识库切分数：321 chunks
- 索引核验数：321 vectors

首次增量写入后发现 collection 中有 353 条，说明旧知识内容修改后遗留了 32 个旧 chunk ID。为避免历史脏数据污染评测，已删除并重建当前 collection，最终索引数与当前知识库 chunk 数严格一致（321 = 321）。

## 2. 评测方法

- 评测集：`backend/eval/rag_eval_cases.json`
- 样本数：18 条
- 每条查询先用同一个向量索引召回 10 个候选（`candidate_k = max(top_k * 2, 6)`）。
- 模型重排与规则重排共享完全相同的候选集，最终均输出 Top5。
- 模型重排：`nvidia/llama-nemotron-rerank-vl-1b-v2:free`
- 规则重排：项目内 `_score_chunk_for_rerank`，综合 query 关键词、标题/正文命中、噪声降权、领域规则与目的地规则。
- 相关性判定：结果标题包含任一 `expected_title_keywords` 即视为命中。
- Top1：首条结果命中的查询占比。
- Top5：前 5 条任一结果命中的查询占比。
- MRR：每条查询首个命中排名倒数的均值；未命中记为 0。
- 模型重排调用成功：18/18，无静默 fallback。

## 3. 核心结果

| 重排方式 | Top1 命中率 | Top5 命中率 | MRR | 平均重排耗时 |
|---|---:|---:|---:|---:|
| Rerank 模型 | 2/18（11.1%） | 15/18（83.3%） | 0.356 | 3297.9 ms |
| 规则重排 | 4/18（22.2%） | 12/18（66.7%） | 0.394 | 0.142 ms |

向量召回平均耗时：549.0 ms。

## 4. 对比结论

1. **模型重排更擅长保证候选覆盖**：Top5 为 83.3%，比规则重排高 16.6 个百分点（15/18 对 12/18）。
2. **规则重排更擅长把当前评测口径下的正确标题推到前面**：Top1 为 22.2%，比模型高 11.1 个百分点；MRR 为 0.394，比模型高 0.038。
3. **规则重排速度优势极大**：规则重排约 0.142 ms，模型重排约 3297.9 ms。模型重排额外增加约 3.3 秒查询延迟。
4. 若业务只消费 Top1，当前评测集上优先使用规则重排更合适；若下游会综合使用 Top5 上下文，模型重排的覆盖率更好。
5. 更推荐后续测试“模型分数 + 规则分数”的混合重排：利用模型提高 Top5 覆盖，再用规则抑制住宿/餐饮误升和强化标题关键词，以兼顾 Top1、MRR 与 Top5。

## 5. 结果产物

- 完整逐案例 JSON：`outputs/rerank_comparison_results.json`
- 可复现评测脚本：`backend/scripts/compare_rerank_methods.py`
- 验证：脚本通过 Python 编译检查；`backend/tests/test_rag_retriever.py` 共 5 项测试全部通过。

> 注：Chroma 输出的 telemetry 报错属于遥测兼容警告，不影响索引写入、查询或本次指标计算。
