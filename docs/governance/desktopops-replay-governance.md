# DesktopOps Replay Governance

## Purpose

Wave69 为 Agent-S 吸收面建立 replay suite，而不是默认执行权。
replay suite 的价值是：把 open-world desktop suggestions 变成 checkpointed evidence，而不是不可审计的即兴动作。

## Replay Surfaces

必须固定：
- checkpoint corpus
- failure taxonomy
- confirm checkpoints
- fallback to operator / deterministic tooling
- replay artifact naming

## Failure Taxonomy

至少区分：UI drift、selector ambiguity、window focus loss、unsafe side-effect boundary、credential / destructive action boundary。

## Guardrail

DesktopOps replay 仅证明 shadow contract 更可审计，不意味着 Agent-S 获得默认 desktop owner 身份。
