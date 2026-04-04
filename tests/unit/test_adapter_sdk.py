from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
ADAPTER_SDK_SRC = ROOT / 'packages' / 'adapter-sdk' / 'src'
CONTRACTS_SRC = ROOT / 'packages' / 'contracts' / 'src'
for src in (ADAPTER_SDK_SRC, CONTRACTS_SRC):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from vgo_adapters.descriptor_loader import load_descriptor
from vgo_adapters.target_root_resolver import resolve_default_target_root


REGISTRY = json.loads((ROOT / 'config' / 'adapter-registry.json').read_text(encoding='utf-8'))


def test_adapter_sdk_descriptors_match_registry_default_target_roots() -> None:
    for adapter in REGISTRY['adapters']:
        descriptor = load_descriptor(adapter['id'])
        assert descriptor.id == adapter['id']
        assert descriptor.default_target_root == adapter['default_target_root']['rel']
        assert descriptor.default_target_root_env == adapter['default_target_root']['env']
        assert descriptor.default_target_root_kind == adapter['default_target_root']['kind']


def test_descriptor_loader_supports_registry_aliases() -> None:
    descriptor = load_descriptor('claude')
    assert descriptor.id == 'claude-code'
    assert descriptor.default_target_root == '.claude'
    assert descriptor.default_target_root_env == 'CLAUDE_HOME'
    assert descriptor.default_target_root_kind == 'host-home'


def test_target_root_resolver_uses_env_when_available() -> None:
    descriptor = load_descriptor('codex')
    resolved = resolve_default_target_root(descriptor, env={'CODEX_HOME': '/tmp/codex-home'}, home='/home/tester')
    assert resolved == '/tmp/codex-home'


def test_target_root_resolver_falls_back_to_home_relative_path() -> None:
    descriptor = load_descriptor('opencode')
    resolved = resolve_default_target_root(descriptor, env={}, home='/home/tester')
    assert resolved == '/home/tester/.config/opencode'
