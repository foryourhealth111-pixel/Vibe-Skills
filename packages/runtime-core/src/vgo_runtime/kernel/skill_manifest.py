from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import re


REQUIRED_LIST_FIELDS = ("when_to_use", "not_for", "inputs", "outputs")
REQUIRED_STRING_FIELDS = ("id", "name", "description")
OPTIONAL_LIST_FIELDS = ("plan_hints", "verify_hints", "tags")
ALLOWED_FIELDS = frozenset(
    REQUIRED_STRING_FIELDS
    + REQUIRED_LIST_FIELDS
    + OPTIONAL_LIST_FIELDS
    + ("enabled", "priority")
)
INTEGER_PATTERN = re.compile(r"^-?\d+$")
BODY_HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+?)\s*$")
BODY_GUIDANCE_ITEM_PATTERN = re.compile(r"^(?:[-*+]\s+|\d+[.)]\s+)(.+)$")
BODY_GUIDANCE_SECTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^(?:inputs?|prerequisites?|输入|前置条件)$", re.IGNORECASE), "inputs"),
    (re.compile(r"^(?:outputs?|deliverables?|输出|交付物)$", re.IGNORECASE), "outputs"),
    (
        re.compile(
            r"^(?:workflow(?:\s*\([^)]*\))?|process|work steps?|steps?|plan|implementation plan|工作流|流程|步骤|计划)$",
            re.IGNORECASE,
        ),
        "plan_hints",
    ),
    (
        re.compile(
            r"^(?:verification|validation|checks?|exit criteria|acceptance criteria|验证|检查|验收标准)$",
            re.IGNORECASE,
        ),
        "verify_hints",
    ),
)


@dataclass(frozen=True, slots=True)
class SkillManifest:
    id: str
    name: str
    description: str
    when_to_use: tuple[str, ...]
    not_for: tuple[str, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    plan_hints: tuple[str, ...] = ()
    verify_hints: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    enabled: bool = True
    priority: int = 50
    root_dir: str = ""
    skill_file: str = ""

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class InstalledSkillManifest:
    skill_id: str
    name: str
    description: str
    capabilities: tuple[str, ...] = ()
    not_for: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    headings: tuple[str, ...] = ()
    root_dir: str = ""
    skill_file: str = ""
    content_sha256: str = ""
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    plan_hints: tuple[str, ...] = ()
    verify_hints: tuple[str, ...] = ()

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _parse_scalar(value: str) -> object:
    normalized = value.strip()
    lowered = normalized.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if INTEGER_PATTERN.match(normalized):
        return int(normalized)
    return _strip_quotes(normalized)


def _extract_frontmatter_lines(skill_file: Path) -> list[str]:
    lines = skill_file.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"skill file missing frontmatter start: {skill_file}")
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[1:index]
    raise ValueError(f"skill file missing frontmatter end: {skill_file}")


def _parse_frontmatter(frontmatter_lines: list[str], *, skill_file: Path) -> dict[str, object]:
    payload: dict[str, object] = {}
    index = 0
    while index < len(frontmatter_lines):
        raw_line = frontmatter_lines[index]
        stripped = raw_line.strip()
        if not stripped:
            index += 1
            continue
        if raw_line[:1].isspace():
            raise ValueError(f"unexpected indentation in skill frontmatter: {skill_file}")
        if ":" not in raw_line:
            raise ValueError(f"invalid frontmatter line in {skill_file}: {raw_line}")
        key, remainder = raw_line.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"empty frontmatter key in {skill_file}")
        if key not in ALLOWED_FIELDS:
            raise ValueError(f"unsupported frontmatter field {key!r} in {skill_file}")
        value_text = remainder.strip()
        if value_text:
            payload[key] = _parse_scalar(value_text)
            index += 1
            continue
        items: list[str] = []
        index += 1
        while index < len(frontmatter_lines):
            candidate = frontmatter_lines[index]
            if not candidate.strip():
                index += 1
                continue
            if not candidate[:1].isspace():
                break
            stripped_candidate = candidate.lstrip()
            if not stripped_candidate.startswith("- "):
                raise ValueError(f"invalid list item in {skill_file}: {candidate}")
            item_value = stripped_candidate[2:].strip()
            if not item_value:
                raise ValueError(f"empty list item in {skill_file}: {candidate}")
            items.append(_strip_quotes(item_value))
            index += 1
        payload[key] = items
    return payload


def _extract_frontmatter_and_body(skill_file: Path) -> tuple[list[str], list[str]]:
    lines = skill_file.read_text(encoding="utf-8-sig").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"skill file missing frontmatter start: {skill_file}")
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[1:index], lines[index + 1 :]
    raise ValueError(f"skill file missing frontmatter end: {skill_file}")


def _parse_loose_frontmatter(frontmatter_lines: list[str], *, skill_file: Path) -> dict[str, object]:
    payload: dict[str, object] = {}
    index = 0
    while index < len(frontmatter_lines):
        raw_line = frontmatter_lines[index]
        stripped = raw_line.strip()
        if not stripped:
            index += 1
            continue
        if raw_line[:1].isspace():
            raise ValueError(f"unexpected indentation in skill frontmatter: {skill_file}")
        if ":" not in raw_line:
            raise ValueError(f"invalid frontmatter line in {skill_file}: {raw_line}")
        key, remainder = raw_line.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"empty frontmatter key in {skill_file}")
        value_text = remainder.strip()
        if value_text in {">", "|", ">-", "|-"}:
            parts: list[str] = []
            index += 1
            while index < len(frontmatter_lines):
                candidate = frontmatter_lines[index]
                if candidate.strip() and not candidate[:1].isspace():
                    break
                parts.append(candidate.strip())
                index += 1
            payload[key] = " ".join(part for part in parts if part).strip()
            continue
        if value_text:
            payload[key] = _parse_scalar(value_text)
            index += 1
            continue
        items: list[str] = []
        index += 1
        while index < len(frontmatter_lines):
            candidate = frontmatter_lines[index]
            if not candidate.strip():
                index += 1
                continue
            if not candidate[:1].isspace():
                break
            stripped_candidate = candidate.lstrip()
            if stripped_candidate.startswith("- "):
                item_value = stripped_candidate[2:].strip()
                if not item_value:
                    raise ValueError(f"empty list item in {skill_file}: {candidate}")
                items.append(_strip_quotes(item_value))
            index += 1
        payload[key] = items
    return payload


def _coerce_string_field(frontmatter: dict[str, object], field_name: str, skill_file: Path) -> str:
    value = frontmatter.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing required frontmatter field {field_name!r} in {skill_file}")
    return value.strip()


def _coerce_string_list(value: object) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, str) and value.strip():
        return tuple(part.strip() for part in value.split(",") if part.strip())
    return ()


def _extract_heading_lines(body_lines: list[str], *, limit: int = 8) -> tuple[str, ...]:
    headings: list[str] = []
    for line in body_lines:
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        marker, _, title = stripped.partition(" ")
        if not title.strip() or len(marker) > 3:
            continue
        headings.append(title.strip())
        if len(headings) >= limit:
            break
    return tuple(headings)


def _dedupe_non_empty(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        deduped.append(text)
        seen.add(text)
    return tuple(deduped)


def _body_guidance_section(line: str) -> str | None:
    heading_match = BODY_HEADING_PATTERN.match(line.strip())
    if heading_match is None:
        return None
    heading = heading_match.group(1).strip()
    for pattern, section in BODY_GUIDANCE_SECTIONS:
        if pattern.fullmatch(heading):
            return section
    return ""


def _extract_body_guidance(body_lines: list[str], *, limit_per_section: int = 12) -> dict[str, tuple[str, ...]]:
    values: dict[str, list[str]] = {
        "inputs": [],
        "outputs": [],
        "plan_hints": [],
        "verify_hints": [],
    }
    active_section = ""
    code_fence: str | None = None
    for line in body_lines:
        stripped = line.strip()
        fence_match = re.match(r"^(`{3,}|~{3,})", stripped)
        if code_fence is None and fence_match is not None:
            code_fence = fence_match.group(1)
            continue
        if code_fence is not None:
            if (
                fence_match is not None
                and fence_match.group(1)[0] == code_fence[0]
                and len(fence_match.group(1)) >= len(code_fence)
                and len(fence_match.group(1)) == len(stripped)
            ):
                code_fence = None
            continue
        section = _body_guidance_section(stripped)
        if section is not None:
            active_section = section
            continue
        if not active_section or len(values[active_section]) >= limit_per_section:
            continue
        item_match = BODY_GUIDANCE_ITEM_PATTERN.match(stripped)
        if item_match is None:
            continue
        item = item_match.group(1).strip()
        if item:
            values[active_section].append(item)
    return {key: _dedupe_non_empty(tuple(items)) for key, items in values.items()}


def _extract_body_not_for_lines(body_lines: list[str]) -> tuple[str, ...]:
    items: list[str] = []
    in_not_for_section = False
    for line in body_lines:
        stripped = line.strip()
        lowered = stripped.casefold()
        if not in_not_for_section:
            if lowered.startswith("do not use this skill for") or lowered.startswith("do not use for"):
                in_not_for_section = True
            continue
        if not stripped:
            if items:
                break
            continue
        if stripped.startswith("#"):
            break
        if not stripped.startswith("- "):
            if items:
                break
            continue
        item = stripped[2:].strip()
        if item:
            items.append(item)
    return _dedupe_non_empty(tuple(items))


def validate_skill_manifest(manifest: SkillManifest) -> None:
    for field_name in REQUIRED_STRING_FIELDS:
        value = getattr(manifest, field_name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"skill manifest field {field_name!r} must be a non-empty string")
    for field_name in REQUIRED_LIST_FIELDS + OPTIONAL_LIST_FIELDS:
        value = getattr(manifest, field_name)
        if not isinstance(value, tuple) or any(not isinstance(item, str) or not item.strip() for item in value):
            raise ValueError(f"skill manifest field {field_name!r} must be a list of non-empty strings")
    if not isinstance(manifest.enabled, bool):
        raise ValueError("skill manifest field 'enabled' must be boolean")
    if not isinstance(manifest.priority, int):
        raise ValueError("skill manifest field 'priority' must be an integer")


def parse_skill_manifest(skill_file: Path) -> SkillManifest:
    resolved_file = skill_file.resolve()
    frontmatter = _parse_frontmatter(_extract_frontmatter_lines(resolved_file), skill_file=resolved_file)
    for field_name in REQUIRED_STRING_FIELDS:
        if field_name not in frontmatter:
            raise ValueError(f"missing required skill field {field_name!r} in {resolved_file}")
        if not isinstance(frontmatter[field_name], str):
            raise ValueError(f"skill field {field_name!r} must be a string in {resolved_file}")
    for field_name in REQUIRED_LIST_FIELDS:
        if field_name not in frontmatter:
            raise ValueError(f"missing required skill field {field_name!r} in {resolved_file}")
        if not isinstance(frontmatter[field_name], list):
            raise ValueError(f"skill field {field_name!r} must be a list in {resolved_file}")
    enabled = frontmatter.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError(f"skill field 'enabled' must be boolean in {resolved_file}")
    priority = frontmatter.get("priority", 50)
    if not isinstance(priority, int):
        raise ValueError(f"skill field 'priority' must be an integer in {resolved_file}")
    manifest = SkillManifest(
        id=str(frontmatter["id"]).strip(),
        name=str(frontmatter["name"]).strip(),
        description=str(frontmatter["description"]).strip(),
        when_to_use=tuple(frontmatter["when_to_use"]),
        not_for=tuple(frontmatter["not_for"]),
        inputs=tuple(frontmatter["inputs"]),
        outputs=tuple(frontmatter["outputs"]),
        plan_hints=tuple(frontmatter.get("plan_hints", [])),
        verify_hints=tuple(frontmatter.get("verify_hints", [])),
        tags=tuple(frontmatter.get("tags", [])),
        enabled=enabled,
        priority=priority,
        root_dir=str(resolved_file.parent),
        skill_file=str(resolved_file),
    )
    validate_skill_manifest(manifest)
    return manifest


def parse_installed_skill_manifest(skill_file: Path, *, skill_id: str | None = None) -> InstalledSkillManifest:
    resolved_file = skill_file.resolve()
    frontmatter_lines, body_lines = _extract_frontmatter_and_body(resolved_file)
    frontmatter = _parse_loose_frontmatter(frontmatter_lines, skill_file=resolved_file)
    resolved_skill_id = str(skill_id or resolved_file.parent.name).strip()
    if not resolved_skill_id:
        raise ValueError(f"skill id cannot be empty for {resolved_file}")
    name = _coerce_string_field(frontmatter, "name", resolved_file)
    description = _coerce_string_field(frontmatter, "description", resolved_file)
    not_for = _dedupe_non_empty(
        _coerce_string_list(frontmatter.get("not_for")) + _extract_body_not_for_lines(body_lines)
    )
    body_guidance = _extract_body_guidance(body_lines)
    return InstalledSkillManifest(
        skill_id=resolved_skill_id,
        name=name,
        description=description,
        capabilities=_coerce_string_list(frontmatter.get("capabilities")),
        not_for=not_for,
        inputs=_dedupe_non_empty(_coerce_string_list(frontmatter.get("inputs")) + body_guidance["inputs"]),
        outputs=_dedupe_non_empty(_coerce_string_list(frontmatter.get("outputs")) + body_guidance["outputs"]),
        plan_hints=_dedupe_non_empty(
            _coerce_string_list(frontmatter.get("plan_hints")) + body_guidance["plan_hints"]
        ),
        verify_hints=_dedupe_non_empty(
            _coerce_string_list(frontmatter.get("verify_hints")) + body_guidance["verify_hints"]
        ),
        tags=_coerce_string_list(frontmatter.get("tags")),
        headings=_extract_heading_lines(body_lines),
        root_dir=str(resolved_file.parent),
        skill_file=str(resolved_file),
        content_sha256=hashlib.sha256(resolved_file.read_bytes()).hexdigest(),
    )
