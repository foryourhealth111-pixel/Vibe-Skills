# AI LLM Pack Consolidation

Date: 2026-04-29

## Summary

This pass shrinks `ai-llm` into a focused AI/LLM routing pack. It keeps only official OpenAI API/docs work, prompt lookup and prompt optimization, embedding/RAG strategy, similarity-search implementation patterns, and LLM evaluation harnesses.

The six-stage Vibe runtime is unchanged, and skill usage remains binary:

```text
skill_candidates -> skill_routing.selected -> skill_usage.used / unused
```

No advisory, consult, primary/secondary, or stage-assistant execution model is introduced.

## Counts

| Field | Before | After |
| --- | ---: | ---: |
| `skill_candidates` | 11 | 5 |
| `route_authority_candidates` | 0 | 5 |
| `stage_assistant_candidates` | 0 | 0 |
| physical directory deletion | 0 | 0 |

`route_authority_candidates` is retained only as a compatibility mirror of `skill_candidates`. It is not a second execution model.

## Kept AI/LLM Owners

| User problem | Skill |
| --- | --- |
| OpenAI official API/docs/model-limit lookup and implementation guidance | `openai-docs` |
| Prompt template lookup, prompt search, and prompt optimization | `prompt-lookup` |
| Embedding model selection, chunking, semantic retrieval, and RAG strategy | `embedding-strategies` |
| Vector database, nearest-neighbor, similarity-search, and semantic-search implementation patterns | `similarity-search-patterns` |
| LLM benchmark/evaluation harnesses such as MMLU, GSM8K, and TruthfulQA | `evaluating-llms-harness` |

## Moved Out Of AI LLM

| Skill | Action | Rationale |
| --- | --- | --- |
| `documentation-lookup` | Removed from `ai-llm` routing surface | Generic framework documentation is not AI/LLM ownership. |
| `openai-knowledge` | Removed from `ai-llm` routing surface | This overlaps with `openai-docs`; `openai-docs` is the retained owner. |
| `evaluating-code-models` | Removed from `ai-llm` routing surface | HumanEval/MBPP code-model evaluation is narrow and should not own default AI/LLM routing. |
| `nowait-reasoning-optimizer` | Removed from `ai-llm` routing surface | NOWAIT/thinking-token optimization is cold and narrow, not a core pack owner. |
| `transformer-lens-interpretability` | Removed from `ai-llm` routing surface | TransformerLens circuit/activation analysis is specialized research tooling, not a default AI/LLM route owner. |
| `transformers` | Removed from `ai-llm` routing surface | Hugging Face Transformers fine-tuning is broad deep-learning tooling, not the core AI/LLM routing surface in this pack. |

## No Physical Deletion

No bundled skill directory is physically deleted in this pass. Moved-out skills remain on disk and can be handled by a later migration or pruning pass if their quality and target ownership are reviewed separately.

## Protected Boundaries

| Prompt | Expected route |
| --- | --- |
| `query OpenAI official docs for Responses API and model limits` | `ai-llm / openai-docs` |
| `帮我检索提示词模板并优化prompt` | `ai-llm / prompt-lookup` |
| `设计向量嵌入策略用于语义检索` | `ai-llm / embedding-strategies` |
| `设计vector database nearest neighbor similarity search方案` | `ai-llm / similarity-search-patterns` |
| `用MMLU和GSM8K做大模型评测` | `ai-llm / evaluating-llms-harness` |
| `查询React 19官方文档并给出useEffect示例` | not `ai-llm` |
| `用HumanEval和MBPP评测代码生成模型` | not `ai-llm` |
| `优化DeepSeek-R1推理，减少thinking tokens和反思token` | not `ai-llm` |
| `用TransformerLens做activation patching和circuit analysis` | not `ai-llm` |
| `用Hugging Face Transformers微调BERT文本分类模型` | not `ai-llm` |

## Verification

Required focused and broader checks:

```powershell
python -m pytest tests/runtime_neutral/test_ai_llm_pack_consolidation.py -q
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-skill-index-routing-audit.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-regression-matrix.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-keyword-precision-audit.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-pack-routing-smoke.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-generate-skills-lock.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-offline-skills-gate.ps1
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-config-parity-gate.ps1 -WriteArtifacts
git diff --check
```
