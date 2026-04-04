from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ALLOWED_PATHS = {
    ROOT / 'scripts' / 'common' / 'Resolve-VgoAdapter.ps1',
    ROOT / 'scripts' / 'common' / 'resolve_vgo_adapter.py',
}
NEEDLES = (
    'Resolve-VgoAdapter.ps1',
    'resolve_vgo_adapter.py',
    'Resolve-VgoAdapterDescriptor',
    'Resolve-VgoAdapterRegistry',
)


def test_runtime_surfaces_do_not_depend_on_resolver_shims_outside_their_own_module() -> None:
    offenders: list[str] = []
    for file_path in ROOT.rglob('*'):
        if not file_path.is_file():
            continue
        if file_path in ALLOWED_PATHS:
            continue
        relative = file_path.relative_to(ROOT)
        if relative.parts[0] in {'tests', 'docs', '.git', '__pycache__'}:
            continue
        if file_path.suffix in {'.pyc'}:
            continue
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        if any(needle in content for needle in NEEDLES):
            offenders.append(str(relative))
    assert offenders == [], f'unexpected runtime resolver shim dependencies: {offenders}'
