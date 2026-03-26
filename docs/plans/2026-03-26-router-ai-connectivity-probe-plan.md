# Router AI 连通性探针执行计划

**日期**: 2026-03-26
**需求文档**: [2026-03-26-router-ai-connectivity-probe.md](../requirements/2026-03-26-router-ai-connectivity-probe.md)
**对应议题**: `#33`
**执行级别**: L
**执行模式**: 设计冻结 + 分波实现 + 分层证明

---

## 总体设计

### 设计定位

本功能是一个 **Router AI advice connectivity probe**，不是第二套路由器，也不是 host 总健康检查。

它只回答一个问题：

> “当前这套 AI advice / 意图分析增强层，是否真的连通并可用？”

### 设计原则

1. **Advice-only**
   - 不拥有 canonical route authority
   - 不修改 selected pack / skill
2. **Truth-first**
   - 区分 `configured`、`reachable`、`invokable`、`gated`
3. **User-readable**
   - 普通用户无需理解 router 内部结构也能看懂结果
4. **Proof-first**
   - mock / offline / live 三层证据必须可分离

---

## 实现架构

### 入口层

建议新增：

1. `scripts/verify/vibe-router-ai-connectivity-gate.ps1`
2. `scripts/verify/runtime_neutral/router_ai_connectivity_probe.py`

建议采用与 `bootstrap doctor` 相似的结构：

1. Python runtime-neutral core 负责状态分类、artifact 生成
2. PowerShell gate 负责当前仓库生态接入、统一 CLI surface

理由：

1. 便于跨平台
2. 便于与当前 runtime-neutral verify family 对齐
3. 便于后续 shell / check surface 复用

### 数据输入层

Probe 读取：

1. `config/llm-acceleration-policy.json`
2. `config/router-provider-registry.json`
3. target root 的 `settings.json`（如果宿主存在）
4. 运行时环境变量
5. 当前 router provider helper 的最小调用结果

### 执行层

Probe 分两步：

1. **配置/作用域判定**
   - policy 是否启用
   - `/vibe` gating 是否生效
   - provider/model/base_url/key 是否齐备
2. **最小真实调用**
   - 对 advice provider 发起最小结构化探测
   - 对 `vector_diff` embeddings 发起可选最小探测

### 输出层

终端输出：

1. 一行主结论
2. 一行 `vector_diff` 结论
3. 一组 `next_steps`

Artifact 输出：

1. `outputs/verify/vibe-router-ai-connectivity-gate.json`
2. `outputs/verify/vibe-router-ai-connectivity-gate.md`

---

## 状态模型

### 主 advice 状态

1. `disabled_by_policy`
2. `prefix_required`
3. `scope_not_applicable`
4. `missing_credentials`
5. `missing_model`
6. `missing_base_url`
7. `provider_unreachable`
8. `provider_rejected_request`
9. `parse_error`
10. `ok`
11. `ok_with_offline_degrade`

### vector diff / embeddings 状态

1. `vector_diff_disabled`
2. `vector_diff_not_configured`
3. `vector_diff_missing_credentials`
4. `vector_diff_provider_unreachable`
5. `vector_diff_provider_rejected_request`
6. `vector_diff_parse_error`
7. `vector_diff_ok`

### next_step 规则

每个非 `ok` 状态都必须给出单句 next step，例如：

1. `Set OPENAI_API_KEY in local settings or environment.`
2. `Run this probe with a /vibe-scoped scenario.`
3. `Check provider base_url reachability and model id.`

---

## 执行波次

### Wave 1: Contract Freeze

目标：

1. 冻结 probe 的定位、非目标、状态模型
2. 冻结 artifact schema
3. 冻结终端输出口径

产物：

1. 本需求文档
2. 本执行计划
3. JSON artifact schema 草案

### Wave 2: Core Probe Design

目标：

1. 设计 runtime-neutral core 输入/输出
2. 定义最小 advice provider 探测负载
3. 定义最小 vector embeddings 探测负载

注意事项：

1. 真实 probe 必须足够小，不能像正常 routing 那样带大 diff
2. 不得把 probe 结果回灌正式 routing decision
3. `/vibe` gating 与 provider failure 必须分开判断

### Wave 3: PowerShell Gate Integration

目标：

1. 接入仓库现有 verify family
2. 补齐 artifact 输出
3. 与现有 `bootstrap doctor` 风格对齐

注意事项：

1. 不把本 probe 混入 install/check 的强制 green 条件
2. 不改变 install/check 现有 truth 边界

### Wave 4: Verification Matrix

目标：

1. 增加 deterministic fixture tests
2. 增加 mock provider tests
3. 增加 live optional proof 路径

### Wave 5: Documentation Freeze

目标：

1. 更新安装/配置文档
2. 增加 probe 使用说明
3. 增加状态解释表
4. 增加 FAQ

### Wave 6: Final Proof and Cleanup

目标：

1. 产出最终 proof artifacts
2. 审核 temp artifacts
3. 清理临时目录
4. 审计僵尸 node

---

## 测试矩阵

### A. 配置缺失类

1. policy disabled
2. missing `OPENAI_API_KEY`
3. missing `model`
4. missing `base_url` when required by configured provider

### B. 作用域类

1. no `/vibe` prefix or equivalent scope
2. route mode outside allowed scope
3. task type outside allowed scope

### C. Provider 连通类

1. provider reachable and returns valid JSON
2. provider unreachable
3. provider returns HTTP error
4. provider returns non-parseable body

### D. Embeddings 子能力类

1. `vector_diff` disabled
2. `vector_diff` enabled but credential missing
3. embeddings endpoint unreachable
4. embeddings returns malformed data
5. embeddings success

### E. 不回归类

1. probe does not mutate route result
2. probe does not elevate confirm_required
3. probe does not write to router config
4. probe output schema remains stable

---

## 稳定性证明方案

### 1. Deterministic Fixture Proof

使用固定 fixture / mock response，证明：

1. 相同输入得到相同状态
2. artifact 字段不漂移
3. `next_step` 不随机变化

### 2. No-Mutation Proof

在测试里断言：

1. probe 前后 route result 一致
2. probe 前后 config 文件内容一致
3. probe 只写入 `outputs/verify/`

### 3. Cross-Surface Proof

证明 PowerShell gate 与 runtime-neutral core 的状态模型一致。

---

## 可用性证明方案

### 1. Operator Output Proof

至少提供以下样例输出：

1. 正常连通
2. 缺 key
3. prefix gating
4. embeddings 未配置

### 2. Minimal Command Proof

用户只需运行一条命令即可得到结论。

### 3. Documentation Proof

文档中必须提供：

1. 一条最小命令
2. 结果解释
3. 下一步操作建议

---

## 智能性证明方案

这里的智能性定义为“分类正确、诊断有用”，不是生成能力 benchmark。

### 1. Classification Coverage Proof

要有一个状态覆盖表，证明主要失败模式都能被明确归类。

### 2. Root-Cause Precision Proof

对以下相似但不同的问题给出不同结果：

1. `missing_credentials` vs `provider_unreachable`
2. `prefix_required` vs `scope_not_applicable`
3. `provider_rejected_request` vs `parse_error`

### 3. Advice Honesty Proof

probe 不得把：

1. 作用域未触发
2. policy disabled
3. offline degrade

误报成“AI 已在线可用”。

---

## 文档固化清单

至少更新：

1. `docs/install/configuration-guide.md`
2. `docs/install/configuration-guide.en.md`
3. `scripts/verify/README.md`
4. 新增 `docs/router-ai-connectivity-probe.md` 或等价说明页

文档必须解释：

1. 这个 probe 检查的是什么
2. 不检查什么
3. 结果状态如何理解
4. 如何安全贴出 artifact 而不暴露密钥

---

## 验证命令（规划态）

```bash
python3 scripts/verify/runtime_neutral/router_ai_connectivity_probe.py --repo-root . --target-root <target> --write-artifacts
pwsh -NoProfile -File scripts/verify/vibe-router-ai-connectivity-gate.ps1 -TargetRoot <target> -WriteArtifacts
pwsh -NoProfile -File scripts/verify/vibe-llm-acceleration-overlay-gate.ps1
pytest -q tests/runtime_neutral/test_router_ai_connectivity_probe.py
```

如增加 live optional proof，再补：

```bash
pwsh -NoProfile -File scripts/verify/vibe-router-ai-connectivity-gate.ps1 -TargetRoot <target> -LiveProbe -WriteArtifacts
```

---

## 风险与控制

### 风险 1: 把 probe 做成第二套路由器

控制：

1. 仅 probe provider advice
2. 不返回可应用的 selected override
3. 明确 no-mutation gate

### 风险 2: 只测配置，不测真实可调用性

控制：

1. provider 侧必须有最小真实调用
2. mock 与 live 分开记录

### 风险 3: 把 scope gating 误诊为 provider 故障

控制：

1. 先 scope 判定，后 provider 调用
2. 状态模型显式区分 `prefix_required`

### 风险 4: 输出太复杂，用户还是看不懂

控制：

1. 终端摘要限制在少量行
2. artifact 才放细节

### 风险 5: 文档口径夸大

控制：

1. 文档统一使用 `router AI advice connectivity`
2. 不用“full online readiness”来替代 probe 结论

---

## 完成定义（Definition of Done）

满足以下条件才算完成：

1. 用户可运行 probe 并看懂结论
2. probe 可区分主 advice 与 vector diff 子能力状态
3. probe 不修改 routing truth
4. mock / fixture / optional live proof 三层证据齐备
5. 文档已更新
6. 本轮产生的临时文件、临时输出、僵尸 node 已清理
