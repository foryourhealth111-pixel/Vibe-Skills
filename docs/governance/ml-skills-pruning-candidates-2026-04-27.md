# ML Skills 第一轮瘦身候选清单

日期：2026-04-27

## 结论先看

本文件最初是删除前证据清单。作者确认后，下面 7 个 skill 已进入删除补丁。

- 本次审计识别出 40 个 ML 相关 skill。
- 第一轮建议删除 7 个通用模板型 stage assistant。
- 12 个专业工具型 skill 暂缓专项评估，本轮不删。
- 13 个 skill 标记为 `merge-into`，说明有重叠或边界问题，但证据还不足以直接删。
- 作者已确认下面的具体 skill ID 可以删除。

一句话解释：

> 这 7 个候选不是“完全没用”，而是太窄、太薄、没有脚本或参考资料，并且已有更强 skill 可以接管。

## 删除候选

| skill_id | 当前 pack | 当前角色 | 质量分 | 重复分 | 接管 skill | 风险 | 删除理由 |
|---|---|---:|---:|---:|---|---|---|
| `anomaly-detector` | `data-ml` | `stage_assistant` | 2 | 5 | `scikit-learn` | low | 异常检测说明较薄，无 scripts/references；异常检测可由 `scikit-learn` 的 classical ML 流程接管。 |
| `confusion-matrix-generator` | `data-ml` | `stage_assistant` | 2 | 5 | `scikit-learn` | low | 只覆盖混淆矩阵和分类错误分析，无独立资产；`scikit-learn` 已覆盖分类评估和指标输出。 |
| `correlation-analyzer` | `data-ml` | `stage_assistant` | 2 | 5 | `exploratory-data-analysis` | low | 只覆盖相关性筛查，无独立流程资产；可并入 EDA 主流程。 |
| `data-normalization-tool` | `data-ml` | `stage_assistant` | 2 | 5 | `preprocessing-data-with-automated-pipelines` | low | 只覆盖缩放/归一化，无独立资产；可由预处理 pipeline skill 接管。 |
| `data-quality-checker` | `data-ml` | `stage_assistant` | 2 | 5 | `exploratory-data-analysis` | low | 只覆盖基础数据质量检查，无独立资产；EDA 主流程已覆盖数据质量和完整性检查。 |
| `feature-importance-analyzer` | `data-ml` | `stage_assistant` | 2 | 5 | `shap` | low | 只覆盖特征重要性解释，无独立资产；更深入的解释性由 `shap` 接管。 |
| `regression-analysis-helper` | `data-ml` | `stage_assistant` | 2 | 5 | `scikit-learn` | low | 只覆盖轻量回归分析帮助，无独立资产；通用回归建模可由 `scikit-learn` 接管。 |

## 为什么是这些

这 7 个候选共同满足第一轮删除条件：

- 都在 `data-ml` pack。
- 都是 `stage_assistant`，不是主专家。
- 每个目录只有 `SKILL.md` 一个文件。
- 都没有 `scripts/`。
- 都没有 `references/`。
- 内容大约 40 行，主要是用途、边界和输出描述。
- 都有明确接管 skill。
- 风险等级都是 `low`。

## 合并但暂不删除

这些 skill 有重叠或边界问题，但本轮不直接删除。

| skill_id | 当前 pack | 当前动作 | 接管方向 | 备注 |
|---|---|---|---|---|
| `data-exploration-visualization` | `data-ml` | `merge-into` | 待定 | 和 EDA/可视化边界有重叠，需要人工比较。 |
| `engineering-features-for-machine-learning` | `data-ml` | `merge-into` | `preprocessing-data-with-automated-pipelines` | 有 scripts/references，先不删。 |
| `evaluating-machine-learning-models` | `data-ml` | `merge-into` | `scikit-learn` | 有更完整资产，先保留做人工比较。 |
| `explaining-machine-learning-models` | 空 | `merge-into` | 待定 | 名称上与解释性 ML 相关，但不在 `data-ml` pack，先不删。 |
| `performing-regression-analysis` | `research-design` | `merge-into` | 待定 | 属于 research-design，不能按 ML 第一刀直接删。 |
| `preprocessing-data-with-automated-pipelines` | `data-ml` | `merge-into` | 待定 | 是多个候选的接管方向之一，本轮不能删。 |
| `running-clustering-algorithms` | `data-ml` | `merge-into` | `scikit-learn` | 有 scripts/references，先不删。 |
| `senior-data-scientist` | 空 | `merge-into` | 待定 | 角色型 skill，需要另做角色类治理。 |
| `senior-ml-engineer` | 空 | `merge-into` | 待定 | 角色型 skill，需要另做角色类治理。 |
| `splitting-datasets` | 空 | `merge-into` | 待定 | 数据拆分可能是 ML 步骤，但不在本轮第一刀范围。 |
| `torch_geometric` | `ml-torch-geometric` | `merge-into` | 待定 | 疑似与 `torch-geometric` 命名重复，需要第二轮工具型专项。 |
| `training-machine-learning-models` | `data-ml` | `merge-into` | `scikit-learn` | 有 scripts/references，不能按薄模板直接删。 |
| `transformer-lens-interpretability` | `ai-llm` | `merge-into` | 待定 | LLM/解释性工具交叉项，第二轮处理。 |

## 专业工具型暂缓

这些是工具或框架绑定型 skill，第一轮不删。

| skill_id | 当前 pack | 当前角色 | 风险 | 本轮处理 |
|---|---|---|---|---|
| `deepchem` | `science-chem-drug` | `candidate` | medium | 暂缓，第二轮专项评估。 |
| `scikit-survival` | 空 | `candidate` | medium | 暂缓，第二轮专项评估。 |
| `shap` | `data-ml` | `candidate` | medium | 暂缓，且作为 `feature-importance-analyzer` 的接管 skill。 |
| `stable-baselines3` | `ml-stable-baselines3` | `default` | medium | 暂缓，第二轮专项评估。 |
| `statsmodels` | `data-ml` | `route_authority` | medium | 暂缓，先不动主路由。 |
| `tensorboard` | 空 | `candidate` | medium | 暂缓，第二轮专项评估。 |
| `timesfm-forecasting` | `science-timesfm-forecasting` | `default` | medium | 暂缓，第二轮专项评估。 |
| `torch-geometric` | `ml-torch-geometric` | `default` | medium | 暂缓，第二轮专项评估。 |
| `torchdrug` | 空 | `candidate` | medium | 暂缓，第二轮专项评估。 |
| `transformers` | `ai-llm` | `candidate` | medium | 暂缓，第二轮专项评估。 |
| `umap-learn` | `data-ml` | `candidate` | medium | 暂缓，第二轮专项评估。 |
| `weights-and-biases` | 空 | `candidate` | medium | 暂缓，第二轮专项评估。 |

## 迁移映射

| 原 skill | 删除后使用 |
|---|---|
| `anomaly-detector` | `scikit-learn` |
| `confusion-matrix-generator` | `scikit-learn` |
| `correlation-analyzer` | `exploratory-data-analysis` |
| `data-normalization-tool` | `preprocessing-data-with-automated-pipelines` |
| `data-quality-checker` | `exploratory-data-analysis` |
| `feature-importance-analyzer` | `shap` |
| `regression-analysis-helper` | `scikit-learn` |

## 人工复核记录

| skill_id | 是否读过 SKILL.md | 是否有 scripts | 是否有 references | 是否同意删除 | 复核备注 |
|---|---|---:|---:|---:|---|
| `anomaly-detector` | 是 | 否 | 否 | 是 | 内容是异常检测薄流程，边界清楚但没有独立资产。 |
| `confusion-matrix-generator` | 是 | 否 | 否 | 是 | 内容是分类错误分析薄流程，可由 `scikit-learn` 覆盖。 |
| `correlation-analyzer` | 是 | 否 | 否 | 是 | 内容是相关性筛查薄流程，可由 EDA 覆盖。 |
| `data-normalization-tool` | 是 | 否 | 否 | 是 | 内容是归一化薄流程，可由预处理 pipeline 覆盖。 |
| `data-quality-checker` | 是 | 否 | 否 | 是 | 内容是基础数据质量薄流程，可由 EDA 覆盖。 |
| `feature-importance-analyzer` | 是 | 否 | 否 | 是 | 内容是特征重要性薄流程，可由 `shap` 覆盖。 |
| `regression-analysis-helper` | 是 | 否 | 否 | 是 | 内容是轻量回归分析帮助，可由 `scikit-learn` 覆盖。 |

## 引用检查摘要

这些候选被全仓引用的位置主要分成四类：

- skill 自己的 `bundled/skills/<skill_id>/SKILL.md`。
- `config/pack-manifest.json` 和 `config/skills-lock.json`。
- 相邻 skill 的 Related Skills / Boundaries 文案。
- 本次新增的审计工具、测试和计划文档中的证据映射。

如果作者确认删除，下一步删除补丁必须同步处理：

- 从 `config/pack-manifest.json` 移除已删除 skill。
- 重新生成 `config/skills-lock.json`。
- 清理相邻 skill 文案里指向已删除 skill 的 Related Skills / Boundaries。
- 保留审计文档里的迁移映射，作为删除原因和历史证据。

## 删除后审计结果

作者确认后已删除上述 7 个目录，并重新运行 ML 审计 gate。

删除后结果：

- `delete` 行数：0
- `defer-specialist-review`：12
- `keep`：8
- `merge-into`：13

这表示第一轮已确认的薄模板删除候选已经从当前 bundled skills 面清掉。

## 作者确认区

作者已在 2026-04-27 确认可以删除下列目录。

确认删除名单：

```text
anomaly-detector
confusion-matrix-generator
correlation-analyzer
data-normalization-tool
data-quality-checker
feature-importance-analyzer
regression-analysis-helper
```
