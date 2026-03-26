from __future__ import annotations

import importlib.util
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
                        "base_url": "https://api.openai.com/v1",
                        "timeout_ms": 12000,
                    },
                    "context": {
                        "vector_diff": {
                            "enabled": False,
                            "embedding_model": "",
                            "embedding_provider": {
                                "type": "openai",
                                "base_url": "https://api.openai.com/v1",
                                "endpoint_path": "/embeddings",
                                "api_key_env": "OPENAI_API_KEY",
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
                                "abstain_reason": "missing_openai_api_key",
                                "required_env_any": ["OPENAI_API_KEY"],
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
        self._write_settings({"OPENAI_API_KEY": "sk-test"})
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
        self._write_settings({"OPENAI_API_KEY": "sk-test"})
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
        self._write_settings({"OPENAI_API_KEY": "sk-test"})

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

    def test_parse_error_is_classified(self) -> None:
        self._write_settings({"OPENAI_API_KEY": "sk-test"})

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
        self._write_settings({"OPENAI_API_KEY": "sk-test"})

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
        self._write_settings({"OPENAI_API_KEY": "sk-test"})

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
        self._write_settings({"OPENAI_API_KEY": "sk-test"})

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


if __name__ == "__main__":
    unittest.main()
