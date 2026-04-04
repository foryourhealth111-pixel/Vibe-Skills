from __future__ import annotations

from vgo_contracts.adapter_descriptor import AdapterDescriptor
from vgo_contracts.adapter_registry_support import load_adapter_registry, resolve_adapter_entry


def load_descriptor_payload(host_id: str) -> dict:
    try:
        registry = load_adapter_registry(__file__)
        return resolve_adapter_entry(registry, host_id)
    except ValueError as exc:
        raise ValueError(f'unsupported adapter id: {host_id}') from exc
    except RuntimeError as exc:
        raise RuntimeError('VGO adapter registry not found for adapter-sdk descriptor loading') from exc


def load_descriptor(host_id: str) -> AdapterDescriptor:
    payload = load_descriptor_payload(host_id)
    target_root = dict(payload.get('default_target_root') or {})
    return AdapterDescriptor(
        id=str(payload['id']),
        default_target_root=str(target_root['rel']),
        default_target_root_env=str(target_root.get('env') or ''),
        default_target_root_kind=str(target_root.get('kind') or ''),
    )
