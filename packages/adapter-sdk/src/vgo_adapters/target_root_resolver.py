from pathlib import Path


def resolve_default_target_root(descriptor, *, env: dict[str, str] | None = None, home: str | None = None) -> str:
    env = env or {}
    home = home or str(Path.home())
    env_name = str(getattr(descriptor, 'default_target_root_env', '') or '').strip()
    if env_name and env.get(env_name):
        return env[env_name]
    rel = str(getattr(descriptor, 'default_target_root', '') or '').strip()
    if not rel:
        raise ValueError(f'missing default target root for {descriptor.id}')
    if rel.startswith('/'):
        return rel
    return str(Path(home) / rel)
