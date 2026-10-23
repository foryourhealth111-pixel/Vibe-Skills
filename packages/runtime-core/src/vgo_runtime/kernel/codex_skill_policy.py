from __future__ import annotations

import ast
from pathlib import Path

from .host_skill_roots import resolve_codex_home
from .skill_manifest import _parse_scalar, _strip_frontmatter_comment


def _split_fields(text: str, separator: str, *, yaml: bool = False) -> list[str]:
    """Split policy syntax outside strings/containers, including multiline TOML."""
    parts: list[str] = []
    current: list[str] = []
    quote = ""
    depth = 0
    index = 0
    while index < len(text):
        character = text[index]
        if quote:
            if quote.startswith('"') and character == "\\":
                current.append(text[index:index + 2])
                index += 2
                continue
            if text.startswith(quote, index):
                current.append(quote)
                index += len(quote)
                quote = ""
                continue
        elif character in "\"'" and (not "".join(current).strip() or "".join(current).rstrip()[-1:] in "=:[{,."):
            quote = character * (3 if text.startswith(character * 3, index) else 1)
            current.append(quote)
            index += len(quote)
            continue
        elif character == "#" and (not yaml or index == 0 or text[index - 1].isspace()):
            end = text.find("\n", index)
            if end == -1:
                break
            index = end
            continue
        elif character in "[{":
            depth += 1
        elif character in "]}":
            depth -= 1
        elif character == separator and depth == 0:
            parts.append("".join(current).strip())
            current = []
            index += 1
            continue
        current.append(character)
        index += 1
    if quote or depth != 0:
        raise ValueError("Unterminated Codex policy string or container")
    parts.append("".join(current).strip())
    return parts


def _toml_string(value: str) -> str:
    if value.startswith("'") and value.endswith("'"):
        width = 3 if value.startswith("'''") else 1
        return value[width:-width].removeprefix("\n") if width == 3 else value[1:-1]
    if value.startswith('"'):
        try:
            result = ast.literal_eval(value)
        except (ValueError, SyntaxError) as exc:
            raise ValueError("Invalid quoted Codex Skill path") from exc
        if isinstance(result, str):
            return result
    raise ValueError("Codex Skill path must be a quoted string")


def _toml_key(value: str) -> tuple[str, ...]:
    return tuple(_toml_string(part) if part[:1] in {"'", '"'} else part.strip() for part in _split_fields(value, "."))


def _inline_fields(value: str, delimiter: str) -> dict[str, str]:
    if not value.startswith("{") or not value.endswith("}"):
        raise ValueError("Codex policy must be a mapping")
    fields: dict[str, str] = {}
    for part in _split_fields(value[1:-1], ",", yaml=delimiter == ":"):
        if not part:
            continue
        pieces = _split_fields(part, delimiter, yaml=delimiter == ":")
        key = pieces[0].strip().strip("\"'")
        scalar = delimiter.join(pieces[1:])
        if len(pieces) < 2 or key in fields:
            raise ValueError("Invalid or duplicate Codex policy field")
        fields[key] = scalar.strip()
    return fields


def _config_entries(text: str) -> list[dict[str, str]]:
    """Project documented Skill overrides without interpreting unrelated settings."""
    records: list[dict[str, str]] = []
    section: tuple[str, ...] = ()
    record: dict[str, str] | None = None
    for statement in _split_fields(text, "\n"):
        if not statement:
            continue
        if statement.startswith("["):
            array = statement.startswith("[[")
            width = 2 if array else 1
            section = _toml_key(statement[width:-width].strip())
            record = {} if array and section == ("skills", "config") else None
            if record is not None:
                records.append(record)
            continue
        assignment = _split_fields(statement, "=")
        if len(assignment) < 2:
            continue
        key_path = _toml_key(assignment[0])
        value = "=".join(assignment[1:]).strip()
        if record is not None:
            if key_path in {("path",), ("enabled",)}:
                if key_path[0] in record:
                    raise ValueError("Duplicate Codex Skill override field")
                record[key_path[0]] = value
            continue
        full_key = (*section, *key_path)
        if full_key == ("skills",):
            value = _inline_fields(value, "=").get("config", "[]")
        elif full_key != ("skills", "config"):
            continue
        if not value.startswith("[") or not value.endswith("]"):
            raise ValueError("Codex skills.config must be an array")
        records.extend(_inline_fields(part, "=") for part in _split_fields(value[1:-1], ",") if part)
    return records


def _skill_overrides(agent_root: Path) -> tuple[set[Path], set[Path]]:
    home = resolve_codex_home(agent_root)
    config = home / "config.toml"
    if not config.is_file():
        return set(), set()
    disabled: set[Path] = set()
    invalid: set[Path] = set()
    for entry in _config_entries(config.read_text(encoding="utf-8-sig")):
        path = Path(_toml_string(entry.get("path", ""))).expanduser()
        if not path.is_absolute():
            path = config.parent / path
        if path.name.casefold() != "skill.md" or path.is_dir():
            path = path / "SKILL.md"
        if entry.get("enabled", "true") not in {"true", "false"}:
            invalid.add(path.resolve())
        elif entry.get("enabled") == "false":
            disabled.add(path.resolve())
    return disabled, invalid


def _implicit_invocation_allowed(skill_file: Path) -> bool:
    metadata = skill_file.parent / "agents/openai.yaml"
    if not metadata.is_file():
        return True
    text = metadata.read_text(encoding="utf-8-sig")
    values: list[str] = []
    if text.lstrip().startswith("{"):
        policy = _inline_fields(text.strip(), ":").get("policy", "{}")
        fields = _inline_fields(policy, ":")
        values = [fields["allow_implicit_invocation"]] if "allow_implicit_invocation" in fields else []
    else:
        in_policy = False
        policy_indent: int | None = None
        for line in text.splitlines():
            stripped = _strip_frontmatter_comment(line).strip()
            if not stripped or stripped in {"---", "..."}:
                continue
            key, separator, value = stripped.partition(":")
            key = key.strip().strip("\"'")
            indent = len(line) - len(line.lstrip())
            if not line[:1].isspace():
                in_policy = bool(separator) and key == "policy"
                policy_indent = None
                if in_policy and value.strip():
                    if value.strip() in {"null", "~"}:
                        continue
                    fields = _inline_fields(value.strip(), ":")
                    if "allow_implicit_invocation" in fields:
                        values.append(fields["allow_implicit_invocation"])
            elif in_policy:
                policy_indent = min(policy_indent, indent) if policy_indent is not None else indent
                if indent != policy_indent:
                    continue
                if key == "allow_implicit_invocation" and separator:
                    values.append(value.strip())
                elif key == "<<":
                    raise ValueError("Codex policy merges require an explicit allow_implicit_invocation boolean")
    if len(values) > 1:
        raise ValueError("Duplicate Codex allow_implicit_invocation policy")
    if not values:
        return True
    allowed = _parse_scalar(values[0])
    if not isinstance(allowed, bool):
        raise ValueError("Codex allow_implicit_invocation must be a boolean")
    return allowed


def apply_codex_skill_policy(entries: list[dict[str, object]], *, agent_root: Path) -> list[tuple[dict[str, object], str]]:
    """Apply one configuration snapshot to active host sources; retain precedence."""
    errors: list[tuple[dict[str, object], str]] = []
    config_error = ""
    try:
        disabled, invalid = _skill_overrides(agent_root)
    except (OSError, UnicodeError, ValueError) as exc:
        disabled, invalid = set(), set()
        config_error = str(exc)
    for entry in entries:
        if not entry["active"] or entry["source_kind"] != "host_installed":
            continue
        try:
            if config_error:
                raise ValueError(config_error)
            descriptor = Path(str(entry["resolved_skill_file"]))
            if descriptor in invalid:
                raise ValueError("Codex Skill override enabled must be a boolean")
            entry["enabled"] = bool(entry["enabled"]) and descriptor not in disabled
            entry["explicit_only"] = bool(entry["explicit_only"]) or not _implicit_invocation_allowed(descriptor)
        except (OSError, UnicodeError, ValueError) as exc:
            entry["enabled"] = False
            entry["host_policy_error"] = str(exc)
            errors.append((entry, str(exc)))
    return errors
