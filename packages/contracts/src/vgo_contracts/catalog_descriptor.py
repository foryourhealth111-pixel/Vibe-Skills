from dataclasses import dataclass, field


@dataclass(slots=True)
class CatalogDescriptor:
    catalog_root: str
    profiles_manifest: str | None = None
    groups_manifest: str | None = None
    owners: list[str] = field(default_factory=list)
