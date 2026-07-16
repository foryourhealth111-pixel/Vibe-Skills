# Data-ML Problem-First 收敛证据

> Historical / Retired Note: This document discusses retired or cleanup-context routing terminology. The current routing model is `skill_candidates -> skill_routing.selected -> module_skill_dispatch -> skill_usage`; old terms here are historical only and are not current runtime states.

日期：2026-04-27

## 结论先看

本轮只治理 `data-ml` pack。

收敛方式从“skill 列表导向”改为“用户问题导向”：

> 一个 skill 只有能独立解决一个清楚的机器学习问题，才继续留在 `data-ml`。

收敛结果：

| 指标 | 收敛前 | 收敛后 |
|---|---:|---:|
| `data-ml.skill_candidates` | 17 | 8 |
| `data-ml.route_authority_candidates` | 11 | 7 |
| `data-ml.stage_assistant_candidates` | 4 | 1 |

本轮没有直接删除带资产的 skill 目录。原因是这些目录仍有 scripts、references 或 assets，需要下一轮先迁移再删。

## 收敛后的 data-ml

| 问题类型 | 保留 skill | 角色 | 为什么保留 |
|---|---|---|---|
| 端到端 ML 流程 | `ml-pipeline-workflow` | route authority | 负责从数据到训练、验证、部署的整体流程规划。 |
| 传统表格分类/回归/聚类 | `scikit-learn` | route authority | 传统机器学习 coding/research 默认入口。 |
| 数据探索和质量理解 | `exploratory-data-analysis` | route authority | 负责数据质量、结构、分布、缺失和初步理解。 |
| 特征工程与预处理 | `preprocessing-data-with-automated-pipelines` | stage assistant | 只做阶段助手，负责清洗、编码、缩放、转换和验证。 |
| 模型评估 | `evaluating-machine-learning-models` | route authority | 负责指标、阈值、校准、模型比较和验证策略。 |
| 数据泄漏检查 | `ml-data-leakage-guard` | route authority | 数据泄漏是独立高风险问题，需要专门入口。 |
| 模型解释 | `shap` | route authority | 只在 SHAP、特征归因、模型解释问题中触发。 |
| 时间序列 ML | `aeon` | route authority | 时间序列分类、回归、聚类和异常检测不是普通表格 ML 能完全覆盖的场景。 |

## 移出 data-ml 但保留目录

这些 skill 不是没价值，而是不应该继续留在 `data-ml` 里抢普通机器学习主路由。

| skill | 处理 | 主要原因 |
|---|---|---|
| `creating-data-visualizations` | 移出 `data-ml` | 普通图表应由可视化/科研作图场景接管，不是 ML 主入口。 |
| `LQF_Machine_Learning_Expert_Guide` | 移出 `data-ml` | 适合批判式方案评审，但触发面太宽，容易压住普通 ML 路由。 |
| `statistical-analysis` | 移出 `data-ml` | 统计检验和研究统计有价值，但属于统计/科研设计语境。 |
| `statsmodels` | 移出 `data-ml` | OLS、GLM、ARIMA、计量模型应在明确统计建模场景中触发。 |
| `umap-learn` | 移出 `data-ml` | UMAP 是窄工具，应该只在明确 UMAP、流形学习、降维请求中触发。 |

## 合并迁移后再删除

这些 skill 和保留 skill 重叠明显，但本轮没有直接删除，因为它们还有资产。

| skill | 接管方向 | 资产情况 | 本轮处理 |
|---|---|---|---|
| `data-exploration-visualization` | `exploratory-data-analysis` | scripts=5; references=0; assets=0 | 先移出 `data-ml`，后续复核脚本再决定删除。 |
| `engineering-features-for-machine-learning` | `preprocessing-data-with-automated-pipelines` | scripts=5; references=1; assets=4 | 先移出 `data-ml`，后续迁移特征工程资产。 |
| `running-clustering-algorithms` | `scikit-learn` | scripts=6; references=1; assets=4 | 先移出 `data-ml`，后续复核聚类脚本是否迁入 scikit-learn。 |
| `training-machine-learning-models` | `scikit-learn` / `ml-pipeline-workflow` | scripts=6; references=1; assets=4 | 先移出 `data-ml`，后续迁移训练脚本或删除重复目录。 |

## 路由效果

本轮修改后的路由意图是：

- 宽泛“做一个机器学习模型”：优先 `scikit-learn` 或 `ml-pipeline-workflow`。
- “先看看数据怎么样”：优先 `exploratory-data-analysis`。
- “评估模型是否靠谱”：优先 `evaluating-machine-learning-models`。
- “担心数据泄漏”：优先 `ml-data-leakage-guard`。
- “做 SHAP/解释模型”：只命中 `shap`。
- “时间序列机器学习”：只命中 `aeon`。
- “预处理/编码/缩放”：作为阶段助手使用 `preprocessing-data-with-automated-pipelines`。

已补一条路由回归样例：`请检查这个机器学习流程是否存在数据泄漏，尤其是归一化是否在划分前fit了` 应命中 `ml-data-leakage-guard`，不能再被 `ml-pipeline-workflow` 抢走。

## 审计产物

本轮新增 problem-first 审计输出：

```text
outputs/skills-audit/data-ml-problem-map.json
outputs/skills-audit/data-ml-problem-map.csv
outputs/skills-audit/data-ml-problem-consolidation.md
```

审计摘要：

| 分类 | 数量 |
|---|---:|
| 保留为 route authority | 7 |
| 保留为 stage assistant | 1 |
| 移出 `data-ml` 但保留目录 | 5 |
| 合并迁移后可删除 | 4 |

## 后续建议

2026-04-28 后续处理：下面 4 个合并迁移对象已经物理删除。删除边界和资产复核记录见 `docs/governance/data-ml-physical-skill-deletion-2026-04-28.md`。

下一轮如果继续收敛实际目录数量，建议只处理 4 个合并迁移对象：

```text
data-exploration-visualization
engineering-features-for-machine-learning
running-clustering-algorithms
training-machine-learning-models
```

处理顺序应该是：

1. 逐个读取 scripts、references、assets。
2. 判断是否比目标 owner 现有内容更强。
3. 迁移可复用资产。
4. 清理引用。
5. 删除目录并刷新 `skills-lock.json`。
