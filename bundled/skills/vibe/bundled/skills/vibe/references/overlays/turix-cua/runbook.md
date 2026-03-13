# VCO Overlay — TuriX‑CUA Runbook（何时用 + 如何跑）

## 1) 触发条件（快速判断）

当满足任一条件时，优先考虑 CUA（否则优先 Playwright/API）：

- 需要真实 UI：验证码/2FA/人机验证/复杂拖拽/视觉状态判断
- 选择器不稳定：SPA/Shadow DOM/频繁改版导致 selector 维护成本极高
- 流程跨站：多域跳转 + 下载/上传 + 多次确认弹窗

## 2) 最小运行步骤（建议外置执行，不阻塞 VCO）

> VCO 侧只做“建议与验收”；CUA 作为外部执行器运行，产出 artifacts 后再回填结果。

1. 准备运行环境（推荐 Mac runner）
   - 具备屏幕录制权限（Screen Recording）
   - Python 3.12（上游 `requirements.txt` 标注 `mac_agent_env`）

2. 运行策略（先小后大）
   - 先跑“单步验证”：打开页面 → 定位一个按钮 → 截图确认
   - 再跑“最小闭环”：登录 → 进入目标页 → 完成一次操作 → 导出/下载结果

3. 观测与可复现（必须产出）
   - 每个阶段保存截图（before/after）
   - 保存动作日志（包含失败点与重试次数）

## 3) 与 Playwright 的协作方式（推荐）

- 能用 Playwright 做的步骤先用 Playwright（速度快、可回归）
- 仅把“卡在 UI 的最后一公里”交给 CUA：
  - 例如：验证码/2FA 完成后，把 cookie/session 回填到 Playwright 继续后续稳定步骤

## 4) 失败回退（不阻塞交付）

- CUA 失败（权限/依赖/网络/不稳定）：
  1) 降级为 Playwright（若 selector 可用）
  2) 再降级为 API/HTTP（若存在接口）
  3) 若必须人工：输出“最短人工 SOP + 验收 checklist”（并让测试 overlay 校验）

## 上游参考

- `https://github.com/TurixAI/TuriX-CUA`

