from dataclasses import dataclass, field


@dataclass(slots=True)
class CatalogDescriptor:
    catalog_root: str
    skill_source_root: str | None = None
    profiles_manifest: str | None = None
    groups_manifest: str | None = None
    metadata_manifest: str | None = None
    owner: str = 'skill-catalog'
    owners: list[str] = field(default_factory=list)
