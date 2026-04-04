# DesktopOps Soft Rollout Governance

## Goal

Wave70 把 DesktopOps 从 shadow plan 推进到 soft candidate，但仍禁止默认 takeover。
只有 operator-confirmed、高证据的场景才允许进入 soft candidate execution path。
这是一条 operator-supervised soft candidate path，而不是默认桌面执行面。

## Soft Candidate Rules

- no default takeover
- no second default GUI owner
- replay required before promotion
- confirm required for side effects
- rollback path must restore human / baseline ownership

## Evidence

软候选必须同时具备 replay suite、checkpoint corpus、failure taxonomy、operator SOP 四项证据。
