from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "verify" / "runtime_neutral" / "router_ai_connectivity_probe.py"


def load_module():
    spec = importlib.util.spec_from_file_location("runtime_neutral_router_ai_connectivity_probe", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RouterAiConnectivityProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "config").mkdir(parents=True, exist_ok=True)
        self.target_root = self.root / "target"
        self.target_root.mkdir(parents=True, exist_ok=True)

        (self.root / "config" / "llm-acceleration-policy.json").write_text(
            json.dumps(
                {
                    "enabled": True,
                    "mode": "soft",
                    "activation": {"explicit_vibe_only": True},
                    "scope": {
                        "grade_allow": ["M", "L", "XL"],
                        "task_allow": ["planning", "coding", "review", "debug", "research"],
                        "route_mode_allow": ["legacy_fallback", "confirm_required", "pack_overlay"],
                    },
                    "provider": {
                        "type": "openai",
                        "model": "gpt-4.1-mini",
                        "model_env": "VCO_INTENT_ADVICE_MODEL",
                        "base_url": "https://api.openai.com/v1",
                        "base_url_env_candidates": ["VCO_INTENT_ADVICE_BASE_URL"],
                        "api_key_env": "VCO_INTENT_ADVICE_API_KEY",
                        "timeout_ms": 12000,
                    },
                    "context": {
                        "vector_diff": {
                            "enabled": False,
                            "embedding_model": "",
                            "embedding_model_env": "VCO_VECTOR_DIFF_MODEL",
                            "embedding_provider": {
                                "type": "openai",
                                "base_url": "https://api.openai.com/v1",
                                "base_url_env_candidates": ["VCO_VECTOR_DIFF_BASE_URL"],
                                "endpoint_path": "/embeddings",
                                "api_key_env": "VCO_VECTOR_DIFF_API_KEY",
                                "timeout_ms": 6000,
                            },
                        }
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (self.root / "config" / "router-provider-registry.json").write_text(
            json.dumps(
                {
                    "providers": [
                        {
                            "id": "openai-compatible",
                            "offline_contract": {
                                "abstain_reason": "missing_intent_advice_api_key",
                                "required_env_any": ["VCO_INTENT_ADVICE_API_KEY"],
                            },
                        }
                    ]
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_settings(self, env: dict[str, str]) -> None:
        (self.target_root / "settings.json").write_text(
            json.dumps({"env": env}, indent=2) + "\n",
            encoding="utf-8",
        )

    def _policy(self) -> dict:
        return json.loads((self.root / "config" / "llm-acceleration-policy.json").read_text(encoding="utf-8"))

    def _write_policy(self, policy: dict) -> None:
        (self.root / "config" / "llm-acceleration-policy.json").write_text(
            json.dumps(policy, indent=2) + "\n", encoding="utf-8"
        )

    def test_prefix_required_is_classified_without_network_probe(self) -> None:
        self._write_settings({"VCO_INTENT_ADVICE_API_KEY": "sk-test"})
        transport_calls: list[dict] = []

        def transport(req: dict) -> dict:
            transport_calls.append(req)
            return {"ok": False, "error_kind": "network", "status_code": None, "error": "should_not_be_called"}

        with mock.patch.dict(os.environ, {}, clear=True):
            artifact = self.module.evaluate(
                self.root,
                self.target_root,
                probe_context=self.module.ProbeContext(prefix_detected=False),
                transport=transport,
            )

        self.assertEqual("prefix_required", artifact["summary"]["advice_status"])
        self.assertEqual([], transport_calls)

    def test_missing_credentials_is_classified(self) -> None:
        self._write_settings({})

        with mock.patch.dict(os.environ, {}, clear=True):
            artifact = self.module.evaluate(
                self.root,
                self.target_root,
                probe_context=self.module.ProbeContext(prefix_detected=True),
            )

        self.assertEqual("missing_credentials", artifact["summary"]["advice_status"])
        self.assertEqual("FAIL", artifact["summary"]["gate_result"])

    def test_scope_not_applicable_is_distinct_from_provider_failure(self) -> None:
        self._write_settings({"VCO_INTENT_ADVICE_API_KEY": "sk-test"})
        transport_calls: list[dict] = []

        def transport(req: dict) -> dict:
            transport_calls.append(req)
            return {"ok": False, "error_kind": "network", "status_code": None, "error": "unexpected"}

        with mock.patch.dict(os.environ, {}, clear=True):
            artifact = self.module.evaluate(
                self.root,
                self.target_root,
                probe_context=self.module.ProbeContext(prefix_detected=True, task_type="ops"),
                transport=transport,
            )

        self.assertEqual("scope_not_applicable", artifact["summary"]["advice_status"])
        self.assertEqual([], transport_calls)

    def test_provider_rejected_request_is_classified(self) -> None:
        self._write_settings({"VCO_INTENT_ADVICE_API_KEY": "sk-test"})

        def transport(_req: dict) -> dict:
            return {
                "ok": False,
                "status_code": 401,
                "error_kind": "http",
                "error": "401 unauthorized",
                "body_text": '{"error":"unauthorized"}',
                "json": {"error": "unauthorized"},
                "latency_ms": 3,
            }

        with mock.patch.dict(os.environ, {}, clear=True):
            artifact = self.module.evaluate(
                self.root,
                self.target_root,
                probe_context=self.module.ProbeContext(prefix_detected=True),
                transport=transport,
            )

        self.assertEqual("provider_rejected_request", artifact["summary"]["advice_status"])

    def test_plain_chat_completion_fallback_is_classified_ok(self) -> None:
        self._write_settings({"VCO_INTENT_ADVICE_API_KEY": "sk-test"})

        def transport(req: dict) -> dict:
            if req["endpoint_kind"] == "responses":
                return {
                    "ok": False,
                    "status_code": 404,
                    "error_kind": "http",
                    "error": "responses unsupported",
                    "body_text": '{"error":"not found"}',
                    "json": {"error": "not found"},
                    "latency_ms": 4,
                }
            if req["endpoint_kind"] == "chat_completions":
                return {
                    "ok": False,
                    "status_code": 400,
                    "error_kind": "http",
                    "error": "response_format unsupported",
                    "body_text": '{"error":"bad request"}',
                    "json": {"error": "bad request"},
                    "latency_ms": 5,
                }
            if req["endpoint_kind"] == "chat_completions_plain":
                return {
                    "ok": True,
                    "status_code": 200,
                    "error_kind": None,
                    "error": None,
                    "body_text": '{"choices":[{"message":{"content":"{\\"ok\\":true}"}}]}',
                    "json": {"choices": [{"message": {"content": '{"ok":true}'}}]},
                    "latency_ms": 6,
                }
            raise AssertionError(f"unexpected endpoint_kind: {req['endpoint_kind']}")

        with mock.patch.dict(os.environ, {}, clear=True):
            artifact = self.module.evaluate(
                self.root,
                self.target_root,
                probe_context=self.module.ProbeContext(prefix_detected=True),
                transport=transport,
            )

        self.assertEqual("ok", artifact["summary"]["advice_status"])
        self.assertEqual("chat_completions_plain", artifact["advice"]["endpoint_used"])
        self.assertEqual(
            ["responses", "chat_completions", "chat_completions_plain"],
            [attempt["endpoint_kind"] for attempt in artifact["advice"]["attempts"]],
        )

    def test_parse_error_is_classified(self) -> None:
        self._write_settings({"VCO_INTENT_ADVICE_API_KEY": "sk-test"})

        def transport(_req: dict) -> dict:
            return {
                "ok": True,
                "status_code": 200,
                "error_kind": None,
                "error": None,
                "body_text": "{}",
                "json": {},
                "latency_ms": 5,
            }

        with mock.patch.dict(os.environ, {}, clear=True):
            artifact = self.module.evaluate(
                self.root,
                self.target_root,
                probe_context=self.module.ProbeContext(prefix_detected=True),
                transport=transport,
            )

        self.assertEqual("parse_error", artifact["summary"]["advice_status"])

    def test_ok_with_vector_not_configured_passes(self) -> None:
        self._write_settings({"VCO_INTENT_ADVICE_API_KEY": "sk-test"})

        def transport(req: dict) -> dict:
            if req["endpoint_kind"] == "responses":
                return {
                    "ok": True,
                    "status_code": 200,
                    "error_kind": None,
                    "error": None,
                    "body_text": '{"output_text":"{\\"ok\\":true}"}',
                    "json": {"output_text": '{"ok":true}'},
                    "latency_ms": 3,
                }
            return {
                "ok": False,
                "status_code": 405,
                "error_kind": "http",
                "error": "not used",
                "body_text": "",
                "json": None,
                "latency_ms": 1,
            }

        with mock.patch.dict(os.environ, {}, clear=True):
            artifact = self.module.evaluate(
                self.root,
                self.target_root,
                probe_context=self.module.ProbeContext(prefix_detected=True),
                transport=transport,
            )

        self.assertEqual("ok", artifact["summary"]["advice_status"])
        self.assertEqual("vector_diff_not_configured", artifact["summary"]["vector_diff_status"])
        self.assertEqual("PASS", artifact["summary"]["gate_result"])

    def test_vector_diff_unreachable_is_reported(self) -> None:
        policy = self._policy()
        policy["context"]["vector_diff"]["enabled"] = True
        policy["context"]["vector_diff"]["embedding_model"] = "text-embedding-3-small"
        self._write_policy(policy)
        self._write_settings({"VCO_INTENT_ADVICE_API_KEY": "sk-test", "VCO_VECTOR_DIFF_API_KEY": "sk-vector"})

        def transport(req: dict) -> dict:
            if req["purpose"] == "advice":
                return {
                    "ok": True,
                    "status_code": 200,
                    "error_kind": None,
                    "error": None,
                    "body_text": '{"output_text":"{\\"ok\\":true}"}',
                    "json": {"output_text": '{"ok":true}'},
                    "latency_ms": 2,
                }
            return {
                "ok": False,
                "status_code": None,
                "error_kind": "network",
                "error": "connection timeout",
                "body_text": None,
                "json": None,
                "latency_ms": 10,
            }

        with mock.patch.dict(os.environ, {}, clear=True):
            artifact = self.module.evaluate(
                self.root,
                self.target_root,
                probe_context=self.module.ProbeContext(prefix_detected=True),
                transport=transport,
            )

        self.assertEqual("ok", artifact["summary"]["advice_status"])
        self.assertEqual("vector_diff_provider_unreachable", artifact["summary"]["vector_diff_status"])
        self.assertEqual("WARN", artifact["summary"]["gate_result"])

    def test_vector_diff_ok_is_reported(self) -> None:
        policy = self._policy()
        policy["context"]["vector_diff"]["enabled"] = True
        policy["context"]["vector_diff"]["embedding_model"] = "text-embedding-3-small"
        self._write_policy(policy)
        self._write_settings({"VCO_INTENT_ADVICE_API_KEY": "sk-test", "VCO_VECTOR_DIFF_API_KEY": "sk-vector"})

        def transport(req: dict) -> dict:
            if req["purpose"] == "advice":
                return {
                    "ok": True,
                    "status_code": 200,
                    "error_kind": None,
                    "error": None,
                    "body_text": '{"output_text":"{\\"ok\\":true}"}',
                    "json": {"output_text": '{"ok":true}'},
                    "latency_ms": 2,
                }
            return {
                "ok": True,
                "status_code": 200,
                "error_kind": None,
                "error": None,
                "body_text": '{"data":[{"index":0,"embedding":[0.1,0.2]}]}',
                "json": {"data": [{"index": 0, "embedding": [0.1, 0.2]}]},
                "latency_ms": 3,
            }

        with mock.patch.dict(os.environ, {}, clear=True):
            artifact = self.module.evaluate(
                self.root,
                self.target_root,
                probe_context=self.module.ProbeContext(prefix_detected=True),
                transport=transport,
            )

        self.assertEqual("ok", artifact["summary"]["advice_status"])
        self.assertEqual("vector_diff_ok", artifact["summary"]["vector_diff_status"])
        self.assertEqual("PASS", artifact["summary"]["gate_result"])

    def test_old_openai_key_does_not_backfill_intent_advice_credentials(self) -> None:
        self._write_settings({"OPENAI_API_KEY": "sk-legacy"})

        with mock.patch.dict(os.environ, {}, clear=True):
            artifact = self.module.evaluate(
                self.root,
                self.target_root,
                probe_context=self.module.ProbeContext(prefix_detected=True),
            )

        self.assertEqual("missing_credentials", artifact["summary"]["advice_status"])

    def test_old_openai_key_does_not_backfill_vector_diff_credentials(self) -> None:
        policy = self._policy()
        policy["context"]["vector_diff"]["enabled"] = True
        policy["context"]["vector_diff"]["embedding_model"] = "text-embedding-3-small"
        self._write_policy(policy)
        self._write_settings({"VCO_INTENT_ADVICE_API_KEY": "sk-intent", "OPENAI_API_KEY": "sk-legacy"})

        def transport(req: dict) -> dict:
            if req["purpose"] == "advice":
                return {
                    "ok": True,
                    "status_code": 200,
                    "error_kind": None,
                    "error": None,
                    "body_text": '{"output_text":"{\\"ok\\":true}"}',
                    "json": {"output_text": '{"ok":true}'},
                    "latency_ms": 2,
                }
            raise AssertionError("vector diff transport should not run without VCO_VECTOR_DIFF_API_KEY")

        with mock.patch.dict(os.environ, {}, clear=True):
            artifact = self.module.evaluate(
                self.root,
                self.target_root,
                probe_context=self.module.ProbeContext(prefix_detected=True),
                transport=transport,
            )

        self.assertEqual("ok", artifact["summary"]["advice_status"])
        self.assertEqual("vector_diff_missing_credentials", artifact["summary"]["vector_diff_status"])

    def test_evaluate_does_not_mutate_router_policy_files(self) -> None:
        self._write_settings({})
        policy_before = (self.root / "config" / "llm-acceleration-policy.json").read_text(encoding="utf-8")
        registry_before = (self.root / "config" / "router-provider-registry.json").read_text(encoding="utf-8")

        with mock.patch.dict(os.environ, {}, clear=True):
            _ = self.module.evaluate(
                self.root,
                self.target_root,
                probe_context=self.module.ProbeContext(prefix_detected=True),
            )

        self.assertEqual(policy_before, (self.root / "config" / "llm-acceleration-policy.json").read_text(encoding="utf-8"))
        self.assertEqual(
            registry_before, (self.root / "config" / "router-provider-registry.json").read_text(encoding="utf-8")
        )

    def test_main_prints_attempt_diagnostics(self) -> None:
        artifact = {
            "summary": {
                "advice_status": "provider_rejected_request",
                "vector_diff_status": "vector_diff_not_configured",
                "gate_result": "FAIL",
            },
            "next_steps": ["Verify API key validity."],
            "advice": {
                "attempts": [
                    {
                        "endpoint_kind": "responses",
                        "status_code": 404,
                        "error_kind": "http",
                        "latency_ms": 3,
                        "outcome": "http_error",
                    },
                    {
                        "endpoint_kind": "chat_completions",
                        "status_code": 400,
                        "error_kind": "http",
                        "latency_ms": 4,
                        "outcome": "http_error",
                    },
                ]
            },
            "vector_diff": {"attempts": []},
        }

        with mock.patch.dict(self.module.main.__globals__, {"evaluate": mock.Mock(return_value=artifact)}):
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                exit_code = self.module.main(["--repo-root", str(self.root), "--target-root", str(self.target_root)])

        self.assertEqual(1, exit_code)
        output = stream.getvalue()
        self.assertIn("[INFO] advice_status=provider_rejected_request", output)
        self.assertIn("[INFO] advice_attempt endpoint=responses status=404 outcome=http_error", output)
        self.assertIn("[INFO] advice_attempt endpoint=chat_completions status=400 outcome=http_error", output)


if __name__ == "__main__":
    unittest.main()
