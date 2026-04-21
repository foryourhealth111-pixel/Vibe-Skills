from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CORE_UTILS = REPO_ROOT / "scripts" / "router" / "modules" / "00-core-utils.ps1"
OPENAI_RESPONSES = REPO_ROOT / "scripts" / "router" / "modules" / "01-openai-responses.ps1"
OVERLAY_MODULE = REPO_ROOT / "scripts" / "router" / "modules" / "48-llm-acceleration-overlay.ps1"
MAIN_FIXTURE_PATH = REPO_ROOT / "scripts" / "verify" / "fixtures" / "llm-acceleration.mock.json"
MAIN_FIXTURE_TEXT = MAIN_FIXTURE_PATH.read_text(encoding="utf-8")


def resolve_powershell() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        r"C:\Program Files\PowerShell\7-preview\pwsh.exe",
        shutil.which("powershell"),
        shutil.which("powershell.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


class LlmAccelerationOverlayProviderPathTests(unittest.TestCase):
    maxDiff = None

    def run_powershell_json(self, lines: list[str]) -> dict[str, object]:
        powershell = resolve_powershell()
        if powershell is None:
            self.skipTest("PowerShell executable not available in PATH")

        with tempfile.TemporaryDirectory() as tempdir:
            script_path = Path(tempdir) / "probe-provider-paths.ps1"
            script_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            result = subprocess.run(
                [
                    powershell,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script_path),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

        self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
        stdout = result.stdout.strip()
        self.assertTrue(stdout, msg=result.stderr)
        return json.loads(stdout.splitlines()[-1])

    def base_script(self) -> list[str]:
        return [
            "$ErrorActionPreference = 'Stop'",
            f"$repoRoot = '{REPO_ROOT.as_posix()}'",
            f". '{CORE_UTILS.as_posix()}'",
            f". '{OPENAI_RESPONSES.as_posix()}'",
            f". '{OVERLAY_MODULE.as_posix()}'",
            "[Environment]::SetEnvironmentVariable('TEST_ADVICE_KEY', 'sk-test-provider-paths')",
            "$policy = Get-LlmAccelerationPolicyDefaults",
            "$policy.provider.model = 'claude-test'",
            "$policy.provider.api_key_env = 'TEST_ADVICE_KEY'",
            "$policy.provider.timeout_ms = 1200",
            "$policy.provider.max_output_tokens = 600",
            "$policy.provider.temperature = 0.0",
            "$policy.provider.store = $false",
        ]

    def test_anthropic_compatible_main_provider_uses_messages_api(self) -> None:
        payload = self.run_powershell_json(
            self.base_script()
            + [
                "$policy.provider.type = 'anthropic-compatible'",
                "$policy.provider.base_url = 'https://anthropic-gateway.example'",
                "function Invoke-OpenAiResponsesCreate { throw 'responses should not be called for anthropic-compatible provider' }",
                "function Invoke-OpenAiChatCompletionsCreate { throw 'chat_completions should not be called for anthropic-compatible provider' }",
                "function Invoke-AnthropicMessagesCreate {",
                "    param(",
                "        [string]$Model,",
                "        [object[]]$Messages,",
                "        [string]$System,",
                "        [int]$MaxTokens,",
                "        [double]$Temperature,",
                "        [double]$TopP,",
                "        [int]$TimeoutMs,",
                "        [string]$ApiKey,",
                "        [string]$ApiKeyEnv,",
                "        [string]$BaseUrl,",
                "        [string[]]$BaseUrlEnvCandidates,",
                "        [string]$AnthropicVersion",
                "    )",
                "    return [pscustomobject]@{",
                "        ok = $true",
                "        abstained = $false",
                "        reason = 'ok'",
                "        status_code = 200",
                "        latency_ms = 17",
                "        output_text = @'",
                MAIN_FIXTURE_TEXT,
                "'@",
                "        response = $null",
                "        error = $null",
                "    }",
                "}",
                "$result = Invoke-LlmAccelerationProvider -PolicyResolved (Get-LlmAccelerationPolicy -Policy $policy) -RepoRoot $repoRoot -InputText 'route this request'",
                "[pscustomobject]@{",
                "    ok = [bool]$result.ok",
                "    abstained = [bool]$result.abstained",
                "    reason = [string]$result.reason",
                "    api = [string]$result.api",
                "} | ConvertTo-Json -Compress",
            ]
        )

        self.assertTrue(payload["ok"])
        self.assertFalse(payload["abstained"])
        self.assertEqual("ok", payload["reason"])
        self.assertEqual("anthropic_messages", payload["api"])

    def test_custom_gateway_openai_provider_can_fallback_to_anthropic_messages(self) -> None:
        payload = self.run_powershell_json(
            self.base_script()
            + [
                "$policy.provider.type = 'openai'",
                "$policy.provider.base_url = 'https://anthropic-gateway.example'",
                "$script:attempts = @()",
                "function Invoke-OpenAiResponsesCreate {",
                "    $script:attempts += 'responses'",
                "    return [pscustomobject]@{ ok = $false; abstained = $true; reason = 'openai_http_error'; status_code = 503; latency_ms = 9; output_text = $null; response = $null; error = '503' }",
                "}",
                "function Invoke-OpenAiChatCompletionsCreate {",
                "    $script:attempts += 'chat_completions'",
                "    return [pscustomobject]@{ ok = $false; abstained = $true; reason = 'openai_http_error'; status_code = 503; latency_ms = 11; output_text = $null; response = $null; error = '503' }",
                "}",
                "function Invoke-AnthropicMessagesCreate {",
                "    $script:attempts += 'anthropic_messages'",
                "    return [pscustomobject]@{",
                "        ok = $true",
                "        abstained = $false",
                "        reason = 'ok'",
                "        status_code = 200",
                "        latency_ms = 23",
                "        output_text = @'",
                MAIN_FIXTURE_TEXT,
                "'@",
                "        response = $null",
                "        error = $null",
                "    }",
                "}",
                "$result = Invoke-LlmAccelerationProvider -PolicyResolved (Get-LlmAccelerationPolicy -Policy $policy) -RepoRoot $repoRoot -InputText 'route this request'",
                "[pscustomobject]@{",
                "    ok = [bool]$result.ok",
                "    abstained = [bool]$result.abstained",
                "    api = [string]$result.api",
                "    attempts = @($script:attempts)",
                "} | ConvertTo-Json -Depth 8 -Compress",
            ]
        )

        self.assertTrue(payload["ok"])
        self.assertFalse(payload["abstained"])
        self.assertEqual("anthropic_messages", payload["api"])
        self.assertEqual(["chat_completions", "responses", "anthropic_messages"], payload["attempts"])

    def test_anthropic_compatible_diff_digest_provider_uses_messages_api(self) -> None:
        payload = self.run_powershell_json(
            self.base_script()
            + [
                "$policy.provider.type = 'anthropic-compatible'",
                "$policy.provider.base_url = 'https://anthropic-gateway.example'",
                "function Invoke-OpenAiResponsesCreate { throw 'responses should not be called for anthropic-compatible digest provider' }",
                "function Invoke-OpenAiChatCompletionsCreate { throw 'chat_completions should not be called for anthropic-compatible digest provider' }",
                "function Invoke-AnthropicMessagesCreate {",
                "    return [pscustomobject]@{",
                "        ok = $true",
                "        abstained = $false",
                "        reason = 'ok'",
                "        status_code = 200",
                "        latency_ms = 19",
                "        output_text = '{\"digest\":\"tight summary\"}'",
                "        response = $null",
                "        error = $null",
                "    }",
                "}",
                "$result = Invoke-LlmDiffDigestProvider -PolicyResolved (Get-LlmAccelerationPolicy -Policy $policy) -RepoRoot $repoRoot -InputText 'summarize the diff' -MaxDigestChars 120",
                "[pscustomobject]@{",
                "    ok = [bool]$result.ok",
                "    abstained = [bool]$result.abstained",
                "    reason = [string]$result.reason",
                "    api = [string]$result.api",
                "    digest = [string]$result.digest",
                "} | ConvertTo-Json -Compress",
            ]
        )

        self.assertTrue(payload["ok"])
        self.assertFalse(payload["abstained"])
        self.assertEqual("ok", payload["reason"])
        self.assertEqual("anthropic_messages", payload["api"])
        self.assertEqual("tight summary", payload["digest"])

    def test_anthropic_compatible_confirm_booster_uses_messages_api(self) -> None:
        payload = self.run_powershell_json(
            self.base_script()
            + [
                "$policy.provider.type = 'anthropic-compatible'",
                "$policy.provider.base_url = 'https://anthropic-gateway.example'",
                "function Invoke-OpenAiResponsesCreate { throw 'responses should not be called for anthropic-compatible confirm booster' }",
                "function Invoke-OpenAiChatCompletionsCreate { throw 'chat_completions should not be called for anthropic-compatible confirm booster' }",
                "function Invoke-AnthropicMessagesCreate {",
                "    return [pscustomobject]@{",
                "        ok = $true",
                "        abstained = $false",
                "        reason = 'ok'",
                "        status_code = 200",
                "        latency_ms = 21",
                "        output_text = '{\"confirm_questions\":[\"What repo should I touch?\",\"What output do you expect?\",\"What constraints matter most?\",\"How should success be verified?\"]}'",
                "        response = $null",
                "        error = $null",
                "    }",
                "}",
                "$result = Invoke-LlmConfirmQuestionBoosterProvider -PolicyResolved (Get-LlmAccelerationPolicy -Policy $policy) -RepoRoot $repoRoot -InputText 'improve confirm questions' -MaxQuestions 6",
                "[pscustomobject]@{",
                "    ok = [bool]$result.ok",
                "    abstained = [bool]$result.abstained",
                "    reason = [string]$result.reason",
                "    api = [string]$result.api",
                "    confirm_questions = @($result.confirm_questions)",
                "} | ConvertTo-Json -Depth 8 -Compress",
            ]
        )

        self.assertTrue(payload["ok"])
        self.assertFalse(payload["abstained"])
        self.assertEqual("ok", payload["reason"])
        self.assertEqual("anthropic_messages", payload["api"])
        self.assertEqual(
            [
                "What repo should I touch?",
                "What output do you expect?",
                "What constraints matter most?",
                "How should success be verified?",
            ],
            payload["confirm_questions"],
        )


if __name__ == "__main__":
    unittest.main()
