from __future__ import annotations

from contextlib import contextmanager
import errno
from functools import wraps
import hashlib
import json
import os
import secrets
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
import shutil
import stat
import tempfile
import threading
import time
from typing import Callable, Iterator, NoReturn, ParamSpec, TypeVar, cast

from ._bootstrap import ensure_contracts_src_on_path

ensure_contracts_src_on_path()

from vgo_contracts.runtime_surface_contract import load_json_file, resolve_packaging_contract


RUNTIME_SURFACE_PREFIXES = (
    "SKILL.md",
    "core/skill-contracts/",
    "config/",
    "protocols/",
    "apps/vgo-cli/",
    "packages/contracts/",
    "packages/runtime-core/",
    "packages/verification-core/",
    "scripts/common/",
    "scripts/runtime/",
    "scripts/router/",
    "scripts/verify/",
)
PACKAGE_EXCLUDED_FILES = {
    "apps/vgo-cli/src/vgo_cli/install_gates.py",
    "apps/vgo-cli/src/vgo_cli/install_support.py",
    "apps/vgo-cli/src/vgo_cli/installer_bridge.py",
    "apps/vgo-cli/src/vgo_cli/upgrade_service.py",
    "packages/verification-core/src/vgo_verify/bio_science_pack_consolidation_audit.py",
    "packages/verification-core/src/vgo_verify/code_quality_pack_consolidation_audit.py",
    "packages/verification-core/src/vgo_verify/global_pack_consolidation_audit.py",
    "packages/verification-core/src/vgo_verify/ml_skills_pruning_audit.py",
}
PACKAGE_RUNTIME_TEST_ENTRYPOINTS = {
    "packages/verification-core/src/vgo_verify/test_baseline_audit.py",
}
RECEIPT_RELPATH = ".vibeskills/install-receipt.json"
OPERATION_LOCK_RELPATH = ".vibeskills/vibe-operation.lock"
OPERATION_LOCK_TIMEOUT_SECONDS = 30.0
INSTALL_STATE_RELPATH = ".vibeskills/vibe-install-state.json"
INSTALL_STATE_KIND = "vibe-skill-install-transaction"
INSTALL_STATE_PREPARING = "preparing"
INSTALL_STATE_PREPARED = "prepared"
INSTALL_RECOVERY_COMMITTED = "committed"
INSTALL_RECOVERY_ROLLED_BACK = "rolled_back"
UNINSTALL_STATE_RELPATH = ".vibeskills/vibe-uninstall-state.json"
UNINSTALL_STATE_KIND = "vibe-skill-uninstall-state"
UNINSTALL_STATE_MANAGED_FILES_REMOVED = "managed_files_removed"
UNINSTALL_COMPLETE_RELPATH = ".vibeskills/vibe-uninstall-complete.json"
UNINSTALL_COMPLETE_KIND = "vibe-skill-uninstall-completion"
UNINSTALL_COMPLETE_STATUS = "completed"


@dataclass
class _InstallFileChange:
    relpath: str
    destination: Path
    staged_path: Path | None
    backup_path: Path | None = None
    destination_existed: bool = False
    old_sha256: str = ""
    new_sha256: str = ""


@dataclass(frozen=True)
class _InstallRecovery:
    disposition: str
    receipt_existed: bool


@dataclass(frozen=True)
class _InstallOperationFailure:
    detail: str
    error: Exception


@dataclass(frozen=True)
class _InstallTreeEntry:
    path: Path
    is_directory: bool
    is_link: bool


@dataclass(frozen=True)
class _UninstallCompletionCommitFailure:
    relpath: str
    error: OSError


class _FileChangedDuringReadError(RuntimeError):
    pass


_P = ParamSpec("_P")
_R = TypeVar("_R")
_PROCESS_OPERATION_LOCK = threading.RLock()
_PROCESS_OPERATION_LOCK_DEPTH = 0
_PROCESS_OPERATION_LOCK_PATH: Path | None = None


def _open_windows_file_no_follow(path: Path) -> int:
    import ctypes
    from ctypes import wintypes
    import msvcrt

    class _FileAttributeTagInfo(ctypes.Structure):
        _fields_ = [
            ("file_attributes", wintypes.DWORD),
            ("reparse_tag", wintypes.DWORD),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    get_file_information = kernel32.GetFileInformationByHandleEx
    get_file_information.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    ]
    get_file_information.restype = wintypes.BOOL
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    generic_read = 0x80000000
    share_read_write_delete = 0x00000001 | 0x00000002 | 0x00000004
    open_existing = 3
    file_attribute_normal = 0x00000080
    file_attribute_directory = 0x00000010
    file_attribute_reparse_point = 0x00000400
    file_flag_backup_semantics = 0x02000000
    file_flag_open_reparse_point = 0x00200000
    file_attribute_tag_info = 9
    invalid_handle = ctypes.c_void_p(-1).value

    handle = create_file(
        str(path),
        generic_read,
        share_read_write_delete,
        None,
        open_existing,
        file_attribute_normal | file_flag_backup_semantics | file_flag_open_reparse_point,
        None,
    )
    if handle == invalid_handle:
        raise ctypes.WinError(ctypes.get_last_error())

    try:
        file_info = _FileAttributeTagInfo()
        if not get_file_information(
            handle,
            file_attribute_tag_info,
            ctypes.byref(file_info),
            ctypes.sizeof(file_info),
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        if file_info.file_attributes & (
            file_attribute_directory | file_attribute_reparse_point
        ):
            raise _FileChangedDuringReadError(
                f"File changed to a link, junction, or non-file before hashing: {path}"
            )
        file_descriptor = msvcrt.open_osfhandle(
            int(handle),
            os.O_RDONLY | os.O_BINARY,
        )
    except BaseException:
        close_handle(handle)
        raise
    return file_descriptor


def _open_file_no_follow(path: Path) -> int:
    if os.name == "nt":
        return _open_windows_file_no_follow(path)

    no_follow = getattr(os, "O_NOFOLLOW", 0)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | no_follow
    try:
        return os.open(path, flags)
    except OSError as exc:
        if no_follow and exc.errno == errno.ELOOP:
            raise _FileChangedDuringReadError(
                f"File changed to a symbolic link before hashing: {path}"
            ) from exc
        raise


def _hash_path_status(path: Path) -> os.stat_result:
    try:
        return path.stat(follow_symlinks=False)
    except FileNotFoundError as exc:
        raise _FileChangedDuringReadError(
            f"File disappeared while preparing to hash it: {path}"
        ) from exc


def _validate_hash_file_identity(
    path: Path,
    *,
    descriptor_status: os.stat_result,
    path_status: os.stat_result,
) -> None:
    if (
        _is_link_or_reparse_point(path_status)
        or not stat.S_ISREG(descriptor_status.st_mode)
        or not stat.S_ISREG(path_status.st_mode)
        or not os.path.samestat(descriptor_status, path_status)
    ):
        raise _FileChangedDuringReadError(
            f"File changed identity or type while hashing: {path}"
        )


def _sha256_file(path: Path) -> str:
    file_descriptor = _open_file_no_follow(path)
    try:
        initial_descriptor_status = os.fstat(file_descriptor)
        _validate_hash_file_identity(
            path,
            descriptor_status=initial_descriptor_status,
            path_status=_hash_path_status(path),
        )
        digest = hashlib.sha256()
        for chunk in iter(lambda: os.read(file_descriptor, 1024 * 1024), b""):
            digest.update(chunk)
        final_descriptor_status = os.fstat(file_descriptor)
        _validate_hash_file_identity(
            path,
            descriptor_status=final_descriptor_status,
            path_status=_hash_path_status(path),
        )
        initial_snapshot = (
            initial_descriptor_status.st_size,
            initial_descriptor_status.st_mtime_ns,
            initial_descriptor_status.st_ctime_ns,
        )
        final_snapshot = (
            final_descriptor_status.st_size,
            final_descriptor_status.st_mtime_ns,
            final_descriptor_status.st_ctime_ns,
        )
        if initial_snapshot != final_snapshot:
            raise _FileChangedDuringReadError(f"File changed while hashing: {path}")
        return digest.hexdigest()
    finally:
        os.close(file_descriptor)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    temporary_path = _stage_text_file(_json_content(payload), path)
    try:
        os.replace(temporary_path, path)
    except BaseException:
        try:
            temporary_path.unlink()
        except OSError:
            pass
        raise


def _temporary_file_prefix(destination: Path, transaction_id: str = "") -> str:
    transaction_segment = f"{transaction_id}." if transaction_id else ""
    return f".{destination.name}.{transaction_segment}"


def _stage_text_file(
    content: str,
    destination: Path,
    *,
    transaction_id: str = "",
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=_temporary_file_prefix(destination, transaction_id),
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            os.close(file_descriptor)
        except OSError:
            pass
        try:
            temporary_path.unlink()
        except OSError:
            pass
        raise
    return temporary_path


def _json_content(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return payload


def _raise_install_operation_failures(
    summary: str,
    failures: list[_InstallOperationFailure],
) -> NoReturn:
    if not failures:
        raise RuntimeError(summary)

    message = f"{summary}: {'; '.join(failure.detail for failure in failures)}"
    timeout_failure = next(
        (
            failure.error
            for failure in failures
            if isinstance(failure.error, TimeoutError)
        ),
        None,
    )
    if timeout_failure is not None:
        raise TimeoutError(message) from timeout_failure

    permission_failure = next(
        (
            failure.error
            for failure in failures
            if isinstance(failure.error, PermissionError)
        ),
        None,
    )
    if permission_failure is not None:
        raise PermissionError(message) from permission_failure

    io_failure = next(
        (
            failure.error
            for failure in failures
            if isinstance(failure.error, OSError)
        ),
        None,
    )
    if io_failure is not None:
        raise OSError(message) from io_failure
    raise RuntimeError(message) from failures[0].error


def _stage_file_copy(
    source: Path,
    destination: Path,
    *,
    transaction_id: str = "",
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=_temporary_file_prefix(destination, transaction_id),
        suffix=".tmp",
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)
    try:
        shutil.copy2(source, temporary_path)
    except BaseException:
        try:
            temporary_path.unlink()
        except OSError:
            pass
        raise
    return temporary_path


def _matches_surface_prefix(relpath: str) -> bool:
    if relpath == "SKILL.md":
        return True
    return any(relpath.startswith(prefix) for prefix in RUNTIME_SURFACE_PREFIXES if prefix != "SKILL.md")


def _is_package_development_test(relpath: str) -> bool:
    if relpath in PACKAGE_RUNTIME_TEST_ENTRYPOINTS:
        return False
    if not relpath.startswith(("packages/runtime-core/", "packages/verification-core/")):
        return False
    return Path(relpath).name.startswith("test_") and relpath.endswith(".py")


def _should_copy_runtime_surface_file(relpath: str) -> bool:
    normalized = Path(relpath).as_posix()
    if "__pycache__" in Path(normalized).parts or normalized.endswith(".pyc"):
        return False
    if normalized in PACKAGE_EXCLUDED_FILES:
        return False
    if _is_package_development_test(normalized):
        return False
    return _matches_surface_prefix(normalized)


def _validate_packaging_paths(
    governance: dict[str, object],
    *,
    source_root: Path,
    governance_path: Path,
) -> None:
    raw_packaging = governance.get("packaging")
    if raw_packaging is None:
        return
    if not isinstance(raw_packaging, dict):
        raise RuntimeError(f"Invalid runtime packaging contract: {governance_path}")

    raw_payload = raw_packaging.get("runtime_payload")
    if raw_payload is None:
        raw_payload = raw_packaging.get("mirror")
    if raw_payload is not None:
        if not isinstance(raw_payload, dict):
            raise RuntimeError(f"Invalid runtime packaging payload: {governance_path}")
        for field_name in ("files", "directories"):
            raw_paths = raw_payload.get(field_name)
            if raw_paths is None:
                continue
            if not isinstance(raw_paths, list):
                raise RuntimeError(f"Invalid runtime packaging {field_name}: {governance_path}")
            for raw_path in raw_paths:
                _canonical_packaging_relpath(
                    raw_path,
                    artifact_path=governance_path,
                    label=f"package {field_name[:-1]}",
                )

    raw_manifests = raw_packaging.get("manifests")
    if raw_manifests is None:
        return
    manifest_paths: list[object] = []
    if isinstance(raw_manifests, list):
        for raw_manifest in raw_manifests:
            if not isinstance(raw_manifest, dict):
                raise RuntimeError(f"Invalid runtime packaging manifest: {governance_path}")
            manifest_paths.append(raw_manifest.get("path"))
    elif isinstance(raw_manifests, dict):
        for raw_manifest in raw_manifests.values():
            manifest_paths.append(
                raw_manifest.get("path") if isinstance(raw_manifest, dict) else raw_manifest
            )
    else:
        raise RuntimeError(f"Invalid runtime packaging manifests: {governance_path}")

    for raw_path in manifest_paths:
        manifest_relpath = _canonical_packaging_relpath(
            raw_path,
            artifact_path=governance_path,
            label="package manifest",
        )
        manifest_path = source_root.joinpath(*PurePosixPath(manifest_relpath).parts)
        _assert_source_path_is_local(source_root, manifest_path)


def runtime_surface_relpaths(source_root: Path) -> list[str]:
    governance_path = source_root / "config" / "version-governance.json"
    _assert_source_path_is_local(source_root, governance_path)
    if not governance_path.is_file():
        raise RuntimeError(f"Missing runtime governance contract: {governance_path}")

    try:
        governance = load_json_file(governance_path)
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"Unreadable runtime packaging contract: {governance_path}") from exc
    if not isinstance(governance, dict):
        raise RuntimeError(f"Expected JSON object: {governance_path}")
    _validate_packaging_paths(
        governance,
        source_root=source_root,
        governance_path=governance_path,
    )
    try:
        packaging = resolve_packaging_contract(governance, source_root)
        mirror = packaging["mirror"]
        files = mirror["files"]
        directories = mirror["directories"]
    except (AttributeError, KeyError, OSError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Invalid runtime packaging contract: {governance_path}") from exc
    if not isinstance(files, list) or not isinstance(directories, list):
        raise RuntimeError(f"Invalid runtime packaging contract: {governance_path}")

    relpaths: set[str] = set()
    for relpath in files:
        if not isinstance(relpath, str):
            raise RuntimeError(f"Invalid package file path in runtime contract: {governance_path}")
        normalized = Path(relpath).as_posix()
        _canonical_owned_relpath(normalized, artifact_path=governance_path, label="package")
        source = source_root / normalized
        _assert_source_path_is_local(source_root, source)
        if source.is_file() and _should_copy_runtime_surface_file(normalized):
            relpaths.add(normalized)

    for relpath in directories:
        if not isinstance(relpath, str):
            raise RuntimeError(f"Invalid package directory path in runtime contract: {governance_path}")
        _canonical_owned_relpath(relpath, artifact_path=governance_path, label="package")
        source = source_root / relpath
        _assert_source_path_is_local(source_root, source)
        if not source.exists():
            continue
        for file_path in sorted(path for path in source.rglob("*") if path.is_file()):
            _assert_source_path_is_local(source_root, file_path)
            installed_relpath = file_path.relative_to(source_root).as_posix()
            if _should_copy_runtime_surface_file(installed_relpath):
                relpaths.add(installed_relpath)

    return sorted(relpaths)


def _package_file_relpaths(source_root: Path) -> list[str]:
    relpaths: list[str] = []
    for relpath in runtime_surface_relpaths(source_root):
        source = source_root / relpath
        _assert_source_path_is_local(source_root, source)
        if not source.exists():
            continue
        relpaths.append(relpath)
    return sorted(set(relpaths))


def _prepare_install_file_changes(
    source_root: Path,
    install_root: Path,
    relpaths: list[str],
    *,
    retired_relpaths: set[str],
    transaction_id: str,
) -> list[_InstallFileChange]:
    changes: list[_InstallFileChange] = []
    try:
        for relpath in relpaths:
            source = source_root / relpath
            _assert_source_path_is_local(source_root, source)
            if not source.is_file():
                raise RuntimeError(f"Package source file is missing: {source}")
            destination = _owned_file_path(install_root, relpath)
            destination_is_link = _path_is_link_or_reparse_point(destination)
            destination_existed = destination.is_file() and not destination_is_link
            if destination_is_link or (destination.exists() and not destination_existed):
                raise RuntimeError(f"Install path is not a regular file: {destination}")
            change = _InstallFileChange(
                relpath=relpath,
                destination=destination,
                staged_path=_stage_file_copy(
                    source,
                    destination,
                    transaction_id=transaction_id,
                ),
                destination_existed=destination_existed,
            )
            changes.append(change)
            change.new_sha256 = _sha256_file(cast(Path, change.staged_path))
            if destination_existed:
                change.backup_path = _stage_file_copy(
                    destination,
                    destination,
                    transaction_id=transaction_id,
                )
                change.old_sha256 = _sha256_file(change.backup_path)

        for relpath in sorted(retired_relpaths, reverse=True):
            destination = _owned_file_path(install_root, relpath)
            destination_is_link = _path_is_link_or_reparse_point(destination)
            if not destination.exists() and not destination_is_link:
                continue
            if destination_is_link or not destination.is_file():
                raise RuntimeError(f"Retired install path is not a regular file: {destination}")
            change = _InstallFileChange(
                relpath=relpath,
                destination=destination,
                staged_path=None,
                destination_existed=True,
            )
            changes.append(change)
            change.backup_path = _stage_file_copy(
                destination,
                destination,
                transaction_id=transaction_id,
            )
            change.old_sha256 = _sha256_file(change.backup_path)
    except BaseException:
        cleanup_failures = _discard_install_file_changes(
            changes,
        )
        if cleanup_failures:
            _raise_install_operation_failures(
                "Failed to prepare Vibe install transaction and remove temporary files",
                cleanup_failures,
            )
        raise
    return changes


def _apply_install_file_changes(changes: list[_InstallFileChange]) -> None:
    for change in changes:
        if change.staged_path is None:
            change.destination.unlink()
        else:
            os.replace(change.staged_path, change.destination)
            change.staged_path = None


def _discard_install_file_changes(
    changes: list[_InstallFileChange],
) -> list[_InstallOperationFailure]:
    failures: list[_InstallOperationFailure] = []
    for change in changes:
        for temporary_path in (change.staged_path, change.backup_path):
            if temporary_path is None:
                continue
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError as exc:
                failures.append(
                    _InstallOperationFailure(
                        detail=f"{temporary_path}: {exc}",
                        error=exc,
                    )
                )
    return failures


def _assert_source_path_is_local(source_root: Path, source: Path) -> None:
    try:
        resolved_root = source_root.resolve(strict=False)
        resolved_source = source.resolve(strict=False)
        resolved_source.relative_to(resolved_root)
    except ValueError as exc:
        raise RuntimeError(f"Package path escapes the source root: {source}") from exc


def _canonical_owned_relpath(
    value: object,
    *,
    artifact_path: Path,
    label: str = "owned file",
) -> str:
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"Invalid {label} path in {artifact_path}")
    if "\\" in value or "\x00" in value:
        raise RuntimeError(f"Non-canonical {label} path in {artifact_path}: {value}")

    posix_path = PurePosixPath(value)
    windows_path = PureWindowsPath(value)
    if (
        posix_path.is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or not posix_path.parts
        or ".." in posix_path.parts
        or posix_path.as_posix() != value
        or posix_path.parts[0].casefold() == ".vibeskills"
        or any(part.rstrip(" .") != part for part in posix_path.parts)
        or any(PureWindowsPath(part).is_reserved() for part in posix_path.parts)
        or ":" in value
    ):
        raise RuntimeError(f"Unsafe {label} path in {artifact_path}: {value}")
    return value


def _canonical_packaging_relpath(
    value: object,
    *,
    artifact_path: Path,
    label: str,
) -> str:
    if not isinstance(value, str):
        raise RuntimeError(f"Invalid {label} path in {artifact_path}")
    return _canonical_owned_relpath(
        value.replace("\\", "/"),
        artifact_path=artifact_path,
        label=label,
    )


def _assert_install_root_is_local(skills_dir: Path, install_root: Path) -> None:
    expected_install_root = skills_dir.resolve(strict=False) / "vibe"
    if install_root.absolute() != expected_install_root:
        raise RuntimeError(f"Vibe install root is outside the Skills directory: {install_root}")
    if install_root.resolve(strict=False) != expected_install_root:
        raise RuntimeError(
            f"Vibe install root must not be a symbolic link or junction: {install_root}"
        )


def _assert_local_destination(
    install_root: Path,
    destination: Path,
    *,
    reject_destination_symlink: bool,
    root_label: str = "Vibe install root",
    path_label: str = "Install path",
) -> None:
    if install_root.is_symlink():
        raise RuntimeError(f"{root_label} must not be a symbolic link: {install_root}")

    try:
        resolved_root = install_root.resolve(strict=False)
        if reject_destination_symlink:
            resolved_destination = destination.resolve(strict=False)
        else:
            resolved_destination = destination.parent.resolve(strict=False) / destination.name
        resolved_destination.relative_to(resolved_root)
    except ValueError as exc:
        raise RuntimeError(f"{path_label} escapes the {root_label}: {destination}") from exc

    if reject_destination_symlink and _path_is_link_or_reparse_point(destination):
        raise RuntimeError(f"{path_label} traverses a link or junction: {destination}")

    current = destination.parent
    while current != install_root:
        if current.is_symlink() or current.resolve(strict=False) != current:
            raise RuntimeError(f"{path_label} traverses a link or junction: {destination}")
        parent = current.parent
        if parent == current:
            raise RuntimeError(f"{path_label} escapes the {root_label}: {destination}")
        current = parent


def _assert_install_destination_is_local(install_root: Path, destination: Path) -> None:
    _assert_local_destination(
        install_root,
        destination,
        reject_destination_symlink=True,
    )


def _owned_file_path(install_root: Path, relpath: str) -> Path:
    destination = install_root.joinpath(*PurePosixPath(relpath).parts)
    _assert_local_destination(
        install_root,
        destination,
        reject_destination_symlink=False,
    )
    metadata_root = (install_root / ".vibeskills").absolute()
    try:
        destination.absolute().relative_to(metadata_root)
    except ValueError:
        pass
    else:
        raise RuntimeError(f"Install path targets Vibe installer metadata: {destination}")
    return destination


def _destination_key(destination: Path) -> str:
    local_destination = destination.parent.resolve(strict=False) / destination.name
    return os.path.normcase(str(local_destination))


def _is_link_or_reparse_point(file_status: os.stat_result) -> bool:
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    file_attributes = getattr(file_status, "st_file_attributes", 0)
    return stat.S_ISLNK(file_status.st_mode) or bool(file_attributes & reparse_flag)


def _path_is_link_or_reparse_point(path: Path) -> bool:
    try:
        file_status = path.stat(follow_symlinks=False)
    except FileNotFoundError:
        return False
    return _is_link_or_reparse_point(file_status)


def _install_tree_entries(install_root: Path) -> Iterator[_InstallTreeEntry]:
    pending_directories = [install_root]
    while pending_directories:
        directory = pending_directories.pop()
        with os.scandir(directory) as scanner:
            raw_entries = sorted(scanner, key=lambda entry: entry.name)

        child_directories: list[Path] = []
        for raw_entry in raw_entries:
            file_status = raw_entry.stat(follow_symlinks=False)
            is_link = _is_link_or_reparse_point(file_status)
            is_directory = stat.S_ISDIR(file_status.st_mode) and not is_link
            path = Path(raw_entry.path)
            yield _InstallTreeEntry(
                path=path,
                is_directory=is_directory,
                is_link=is_link,
            )
            if is_directory:
                child_directories.append(path)
        pending_directories.extend(reversed(child_directories))


def _relpaths_by_destination(
    install_root: Path,
    relpaths: list[str] | set[str],
    *,
    artifact_path: Path,
    label: str,
) -> dict[str, str]:
    relpaths_by_destination: dict[str, str] = {}
    for relpath in sorted(relpaths):
        destination = _owned_file_path(install_root, relpath)
        destination_key = _destination_key(destination)
        previous = relpaths_by_destination.get(destination_key)
        if previous is not None:
            raise RuntimeError(
                f"Duplicate {label} paths target the same install file in {artifact_path}: "
                f"{previous}, {relpath}"
            )
        relpaths_by_destination[destination_key] = relpath
    return relpaths_by_destination


def _validated_file_entries(
    payload: dict[str, object],
    *,
    artifact_path: Path,
    install_root: Path,
) -> list[dict[str, str]]:
    raw_entries = payload.get("files")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise RuntimeError(f"Invalid Vibe owned-files list: {artifact_path}")

    entries: list[dict[str, str]] = []
    destinations: set[str] = set()
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict):
            raise RuntimeError(f"Invalid Vibe owned-file entry: {artifact_path}")
        relpath = _canonical_owned_relpath(raw_entry.get("path"), artifact_path=artifact_path)
        expected_sha = raw_entry.get("sha256")
        if not isinstance(expected_sha, str) or not expected_sha:
            raise RuntimeError(f"Invalid Vibe owned-file hash for {relpath}: {artifact_path}")
        expected_sha = expected_sha.lower()
        destination = _owned_file_path(install_root, relpath)
        destination_key = _destination_key(destination)
        if destination_key in destinations:
            raise RuntimeError(f"Duplicate Vibe owned-file path: {relpath}")
        destinations.add(destination_key)
        entries.append({"path": relpath, "sha256": expected_sha})
    return entries


def _file_entry_paths(entries: list[dict[str, str]]) -> set[str]:
    return {entry["path"] for entry in entries}


def _recorded_path_matches(value: object, expected: Path) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        recorded = Path(value)
        return recorded.is_absolute() and recorded.resolve(strict=False) == expected.resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return False


def _operation_lock_path(skills_dir: Path) -> Path:
    resolved_skills_dir = skills_dir.resolve()
    lock_path = resolved_skills_dir.joinpath(*PurePosixPath(OPERATION_LOCK_RELPATH).parts)
    _assert_local_destination(
        resolved_skills_dir,
        lock_path,
        reject_destination_symlink=True,
        root_label="Skills directory",
        path_label="Vibe operation lock path",
    )
    return lock_path


def _is_platform_lock_contention(exc: OSError) -> bool:
    if exc.errno in {errno.EACCES, errno.EAGAIN}:
        return True
    return os.name == "nt" and getattr(exc, "winerror", None) in {32, 33}


def _acquire_platform_file_lock(file_descriptor: int, lock_path: Path) -> None:
    deadline = time.monotonic() + OPERATION_LOCK_TIMEOUT_SECONDS
    while True:
        try:
            os.lseek(file_descriptor, 0, os.SEEK_SET)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(file_descriptor, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(file_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except OSError as exc:
            if not _is_platform_lock_contention(exc):
                raise
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Timed out waiting for another Vibe lifecycle operation: {lock_path}"
                ) from exc
            time.sleep(0.05)


def _release_platform_file_lock(file_descriptor: int) -> None:
    os.lseek(file_descriptor, 0, os.SEEK_SET)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(file_descriptor, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(file_descriptor, fcntl.LOCK_UN)


@contextmanager
def _cross_process_operation_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = _operation_lock_path(lock_path.parent.parent)
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    file_descriptor = os.open(lock_path, flags, 0o600)
    acquired = False
    try:
        file_status = os.fstat(file_descriptor)
        if not stat.S_ISREG(file_status.st_mode):
            raise RuntimeError(f"Vibe operation lock is not a regular file: {lock_path}")
        if file_status.st_nlink != 1:
            raise RuntimeError(f"Vibe operation lock must not be a hard link: {lock_path}")
        if file_status.st_size == 0:
            os.write(file_descriptor, b"\0")
            os.fsync(file_descriptor)
        _acquire_platform_file_lock(file_descriptor, lock_path)
        acquired = True
        yield
    finally:
        try:
            if acquired:
                _release_platform_file_lock(file_descriptor)
        finally:
            os.close(file_descriptor)


@contextmanager
def _vibe_operation_lock(skills_dir: Path) -> Iterator[None]:
    global _PROCESS_OPERATION_LOCK_DEPTH
    global _PROCESS_OPERATION_LOCK_PATH

    lock_path = _operation_lock_path(skills_dir)
    with _PROCESS_OPERATION_LOCK:
        if _PROCESS_OPERATION_LOCK_DEPTH:
            if _PROCESS_OPERATION_LOCK_PATH != lock_path:
                raise RuntimeError("Nested Vibe lifecycle operations use different Skills directories")
            _PROCESS_OPERATION_LOCK_DEPTH += 1
            try:
                yield
            finally:
                _PROCESS_OPERATION_LOCK_DEPTH -= 1
            return

        with _cross_process_operation_lock(lock_path):
            _PROCESS_OPERATION_LOCK_PATH = lock_path
            _PROCESS_OPERATION_LOCK_DEPTH = 1
            try:
                yield
            finally:
                _PROCESS_OPERATION_LOCK_DEPTH = 0
                _PROCESS_OPERATION_LOCK_PATH = None


def _locked_vibe_operation(function: Callable[_P, _R]) -> Callable[_P, _R]:
    @wraps(function)
    def locked(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        raw_skills_dir = kwargs.get("skills_dir")
        if raw_skills_dir is None:
            raise TypeError("Vibe lifecycle operation requires skills_dir")
        with _vibe_operation_lock(cast(Path, raw_skills_dir)):
            return function(*args, **kwargs)

    return locked


def _read_install_receipt(
    receipt_path: Path,
    *,
    skills_dir: Path,
    install_root: Path,
) -> dict[str, object]:
    try:
        receipt = _read_json(receipt_path)
    except ValueError as exc:
        raise RuntimeError(f"Unreadable Vibe install receipt: {receipt_path}") from exc

    if receipt.get("schema_version") != 1:
        raise RuntimeError(f"Unsupported Vibe install receipt schema: {receipt_path}")
    if receipt.get("receipt_kind") != "vibe-skill-install" or receipt.get("skill_id") != "vibe":
        raise RuntimeError(f"Invalid Vibe install receipt: {receipt_path}")
    if not _recorded_path_matches(receipt.get("skills_dir"), skills_dir):
        raise RuntimeError(f"Vibe install receipt Skills directory mismatch: {receipt_path}")
    if not _recorded_path_matches(receipt.get("install_root"), install_root):
        raise RuntimeError(f"Vibe install receipt install root mismatch: {receipt_path}")

    receipt["files"] = _validated_file_entries(
        receipt,
        artifact_path=receipt_path,
        install_root=install_root,
    )
    return receipt


def _install_state_path(skills_dir: Path) -> Path:
    resolved_skills_dir = skills_dir.resolve()
    state_path = resolved_skills_dir.joinpath(*PurePosixPath(INSTALL_STATE_RELPATH).parts)
    _assert_local_destination(
        resolved_skills_dir,
        state_path,
        reject_destination_symlink=True,
        root_label="Skills directory",
        path_label="Vibe install state path",
    )
    return state_path


def _validated_transaction_id(value: object, *, state_path: Path) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 32
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RuntimeError(f"Invalid transaction ID in Vibe install state: {state_path}")
    return value


def _validate_install_state_header(
    state: dict[str, object],
    *,
    state_path: Path,
    skills_dir: Path,
    install_root: Path,
) -> tuple[str, str]:
    if state.get("schema_version") != 1:
        raise RuntimeError(f"Unsupported Vibe install state schema: {state_path}")
    if state.get("state_kind") != INSTALL_STATE_KIND or state.get("skill_id") != "vibe":
        raise RuntimeError(f"Invalid Vibe install state: {state_path}")
    status = state.get("status")
    if status not in {INSTALL_STATE_PREPARING, INSTALL_STATE_PREPARED}:
        raise RuntimeError(f"Invalid Vibe install state status: {state_path}")
    if not _recorded_path_matches(state.get("skills_dir"), skills_dir):
        raise RuntimeError(f"Vibe install state Skills directory mismatch: {state_path}")
    if not _recorded_path_matches(state.get("install_root"), install_root):
        raise RuntimeError(f"Vibe install state install root mismatch: {state_path}")
    transaction_id = _validated_transaction_id(
        state.get("transaction_id"),
        state_path=state_path,
    )
    return cast(str, status), transaction_id


def _validated_transaction_sha256(
    value: object,
    *,
    state_path: Path,
    label: str,
    required: bool,
) -> str:
    if value is None and not required:
        return ""
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RuntimeError(f"Invalid {label} hash in Vibe install state: {state_path}")
    return value


def _validated_transaction_temp_path(
    value: object,
    *,
    state_path: Path,
    install_root: Path,
    destination: Path,
    transaction_id: str,
    label: str,
) -> Path:
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"Invalid {label} path in Vibe install state: {state_path}")
    temporary_path = Path(value)
    if not temporary_path.is_absolute():
        raise RuntimeError(f"Relative {label} path in Vibe install state: {state_path}")
    _assert_local_destination(
        install_root,
        temporary_path,
        reject_destination_symlink=True,
        path_label=f"Vibe install transaction {label} path",
    )
    if _destination_key(temporary_path.parent) != _destination_key(destination.parent):
        raise RuntimeError(f"Misplaced {label} path in Vibe install state: {state_path}")
    expected_prefix = _temporary_file_prefix(destination, transaction_id)
    if (
        not temporary_path.name.startswith(expected_prefix)
        or not temporary_path.name.endswith(".tmp")
        or len(temporary_path.name) <= len(expected_prefix) + len(".tmp")
    ):
        raise RuntimeError(f"Unexpected {label} name in Vibe install state: {state_path}")
    if (temporary_path.exists() or temporary_path.is_symlink()) and not temporary_path.is_file():
        raise RuntimeError(f"Vibe install transaction {label} is not a file: {temporary_path}")
    return temporary_path


def _build_preparing_install_state(
    *,
    skills_dir: Path,
    install_root: Path,
    transaction_id: str,
    receipt_existed: bool,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "state_kind": INSTALL_STATE_KIND,
        "skill_id": "vibe",
        "skills_dir": str(skills_dir.resolve()),
        "install_root": str(install_root.resolve(strict=False)),
        "transaction_id": transaction_id,
        "status": INSTALL_STATE_PREPARING,
        "receipt_existed": receipt_existed,
    }


def _build_install_state(
    *,
    skills_dir: Path,
    install_root: Path,
    transaction_id: str,
    changes: list[_InstallFileChange],
) -> dict[str, object]:
    receipt_change = changes[-1]
    if receipt_change.relpath != RECEIPT_RELPATH or not receipt_change.new_sha256:
        raise RuntimeError("Vibe install transaction has no receipt commit marker")
    return {
        "schema_version": 1,
        "state_kind": INSTALL_STATE_KIND,
        "skill_id": "vibe",
        "skills_dir": str(skills_dir.resolve()),
        "install_root": str(install_root.resolve()),
        "transaction_id": transaction_id,
        "status": INSTALL_STATE_PREPARED,
        "receipt_sha256": receipt_change.new_sha256,
        "changes": [
            {
                "relpath": change.relpath,
                "destination": str(change.destination.resolve(strict=False)),
                "staged_path": (
                    str(change.staged_path.resolve(strict=False))
                    if change.staged_path is not None
                    else None
                ),
                "backup_path": (
                    str(change.backup_path.resolve(strict=False))
                    if change.backup_path is not None
                    else None
                ),
                "destination_existed": change.destination_existed,
                "old_sha256": change.old_sha256 or None,
                "new_sha256": change.new_sha256 or None,
            }
            for change in changes
        ],
    }


def _read_install_state(
    state_path: Path,
    *,
    skills_dir: Path,
    install_root: Path,
    state: dict[str, object] | None = None,
) -> list[_InstallFileChange]:
    if state is None:
        try:
            state = _read_json(state_path)
        except ValueError as exc:
            raise RuntimeError(f"Unreadable Vibe install state: {state_path}") from exc
    status, transaction_id = _validate_install_state_header(
        state,
        state_path=state_path,
        skills_dir=skills_dir,
        install_root=install_root,
    )
    if status != INSTALL_STATE_PREPARED:
        raise RuntimeError(f"Invalid Vibe install state status: {state_path}")

    raw_changes = state.get("changes")
    if not isinstance(raw_changes, list) or not raw_changes:
        raise RuntimeError(f"Invalid Vibe install changes list: {state_path}")

    changes: list[_InstallFileChange] = []
    destination_keys: set[str] = set()
    temporary_keys: set[str] = set()
    receipt_count = 0
    for raw_change in raw_changes:
        if not isinstance(raw_change, dict):
            raise RuntimeError(f"Invalid Vibe install change entry: {state_path}")
        relpath_value = raw_change.get("relpath")
        is_receipt = relpath_value == RECEIPT_RELPATH
        if is_receipt:
            receipt_count += 1
            relpath = RECEIPT_RELPATH
            destination = install_root.joinpath(*PurePosixPath(RECEIPT_RELPATH).parts)
            _assert_install_destination_is_local(install_root, destination)
        else:
            relpath = _canonical_owned_relpath(
                relpath_value,
                artifact_path=state_path,
                label="install transaction",
            )
            destination = _owned_file_path(install_root, relpath)

        if not _recorded_path_matches(raw_change.get("destination"), destination):
            raise RuntimeError(
                f"Vibe install state destination mismatch for {relpath}: {state_path}"
            )
        destination_key = _destination_key(destination)
        if destination_key in destination_keys or destination_key in temporary_keys:
            raise RuntimeError(f"Duplicate Vibe install transaction destination: {state_path}")
        destination_keys.add(destination_key)

        destination_existed = raw_change.get("destination_existed")
        if type(destination_existed) is not bool:
            raise RuntimeError(f"Invalid destination state for {relpath}: {state_path}")
        old_sha256 = _validated_transaction_sha256(
            raw_change.get("old_sha256"),
            state_path=state_path,
            label=f"old {relpath}",
            required=destination_existed,
        )
        if not destination_existed and raw_change.get("old_sha256") is not None:
            raise RuntimeError(f"Unexpected old hash for {relpath}: {state_path}")

        raw_staged_path = raw_change.get("staged_path")
        has_staged_path = raw_staged_path is not None
        if is_receipt and not has_staged_path:
            raise RuntimeError(f"Missing staged receipt in Vibe install state: {state_path}")
        new_sha256 = _validated_transaction_sha256(
            raw_change.get("new_sha256"),
            state_path=state_path,
            label=f"new {relpath}",
            required=has_staged_path,
        )
        if not has_staged_path and raw_change.get("new_sha256") is not None:
            raise RuntimeError(f"Unexpected new hash for {relpath}: {state_path}")

        staged_path = None
        if has_staged_path:
            staged_path = _validated_transaction_temp_path(
                raw_staged_path,
                state_path=state_path,
                install_root=install_root,
                destination=destination,
                transaction_id=transaction_id,
                label="staged file",
            )
        raw_backup_path = raw_change.get("backup_path")
        if destination_existed:
            backup_path = _validated_transaction_temp_path(
                raw_backup_path,
                state_path=state_path,
                install_root=install_root,
                destination=destination,
                transaction_id=transaction_id,
                label="backup file",
            )
        else:
            if raw_backup_path is not None:
                raise RuntimeError(f"Unexpected backup path for {relpath}: {state_path}")
            backup_path = None

        for temporary_path in (staged_path, backup_path):
            if temporary_path is None:
                continue
            temporary_key = _destination_key(temporary_path)
            if temporary_key in temporary_keys or temporary_key in destination_keys:
                raise RuntimeError(f"Duplicate Vibe install transaction path: {state_path}")
            temporary_keys.add(temporary_key)

        changes.append(
            _InstallFileChange(
                relpath=relpath,
                destination=destination,
                staged_path=staged_path,
                backup_path=backup_path,
                destination_existed=destination_existed,
                old_sha256=old_sha256,
                new_sha256=new_sha256,
            )
        )

    if receipt_count != 1 or changes[-1].relpath != RECEIPT_RELPATH:
        raise RuntimeError(f"Vibe install state receipt must be the final change: {state_path}")
    receipt_sha256 = _validated_transaction_sha256(
        state.get("receipt_sha256"),
        state_path=state_path,
        label="receipt commit marker",
        required=True,
    )
    if receipt_sha256 != changes[-1].new_sha256:
        raise RuntimeError(f"Vibe install state receipt marker mismatch: {state_path}")
    return changes


def _current_install_file_sha256(path: Path, *, relpath: str) -> str | None:
    if _path_is_link_or_reparse_point(path):
        raise RuntimeError(f"Vibe install transaction path became a link or junction: {relpath}")
    if not path.exists():
        return None
    if not path.is_file():
        raise RuntimeError(f"Vibe install transaction path is not a file: {relpath}")
    return _sha256_file(path)


def _install_change_state(change: _InstallFileChange) -> str:
    current_sha256 = _current_install_file_sha256(
        change.destination,
        relpath=change.relpath,
    )
    if change.new_sha256 and current_sha256 == change.new_sha256:
        return "new"
    if change.destination_existed and current_sha256 == change.old_sha256:
        return "old"
    if current_sha256 is None:
        if not change.new_sha256:
            return "new"
        if not change.destination_existed:
            return "old"
    raise RuntimeError(
        f"Vibe install transaction destination drifted during recovery: {change.relpath}"
    )


def _validated_existing_transaction_file(
    path: Path,
    *,
    expected_sha256: str,
    label: str,
) -> bool:
    if _path_is_link_or_reparse_point(path):
        raise RuntimeError(f"Vibe install transaction {label} became a link or junction: {path}")
    if not path.exists():
        return False
    if not path.is_file():
        raise RuntimeError(f"Vibe install transaction {label} is not a file: {path}")
    if _sha256_file(path) != expected_sha256:
        raise RuntimeError(f"Vibe install transaction {label} hash mismatch: {path}")
    return True


def _cleanup_install_transaction_files(
    changes: list[_InstallFileChange],
) -> list[_InstallOperationFailure]:
    failures: list[_InstallOperationFailure] = []
    for change in changes:
        temporary_files = (
            (change.staged_path, change.new_sha256, "staged file"),
            (change.backup_path, change.old_sha256, "backup file"),
        )
        for temporary_path, expected_sha256, label in temporary_files:
            if temporary_path is None:
                continue
            try:
                exists = _validated_existing_transaction_file(
                    temporary_path,
                    expected_sha256=expected_sha256,
                    label=label,
                )
                if exists:
                    temporary_path.unlink()
            except (OSError, RuntimeError) as exc:
                failures.append(
                    _InstallOperationFailure(
                        detail=(
                            f"{temporary_path}: {exc}"
                            if isinstance(exc, OSError)
                            else str(exc)
                        ),
                        error=exc,
                    )
                )
    return failures


def _rollback_persisted_install_changes(
    changes: list[_InstallFileChange],
) -> list[_InstallOperationFailure]:
    try:
        change_states = [_install_change_state(change) for change in changes]
        for change, change_state in zip(changes, change_states):
            if change_state != "new" or not change.destination_existed:
                continue
            if change.old_sha256 == change.new_sha256:
                continue
            if change.backup_path is None or not _validated_existing_transaction_file(
                change.backup_path,
                expected_sha256=change.old_sha256,
                label="rollback backup",
            ):
                raise RuntimeError(f"Missing Vibe install rollback backup: {change.relpath}")
    except (OSError, RuntimeError) as exc:
        return [_InstallOperationFailure(detail=str(exc), error=exc)]

    failures: list[_InstallOperationFailure] = []
    for change, change_state in reversed(list(zip(changes, change_states))):
        if change_state != "new" or change.old_sha256 == change.new_sha256:
            continue
        try:
            if change.destination_existed:
                if change.backup_path is None:
                    raise RuntimeError(f"Missing rollback backup for {change.destination}")
                os.replace(change.backup_path, change.destination)
            else:
                change.destination.unlink()
            if _install_change_state(change) != "old":
                raise RuntimeError(f"Rollback verification failed for {change.destination}")
        except (OSError, RuntimeError) as exc:
            failures.append(
                _InstallOperationFailure(
                    detail=f"{change.destination}: {exc}",
                    error=exc,
                )
            )
    return failures


def _remove_install_state_file(
    state_path: Path,
    *,
    failure_summary: str,
) -> None:
    try:
        state_path.unlink()
    except OSError as exc:
        _raise_install_operation_failures(
            failure_summary,
            [
                _InstallOperationFailure(
                    detail=f"recovery journal retained at {state_path}; {state_path}: {exc}",
                    error=exc,
                )
            ],
        )


def _cleanup_preparing_install_transaction(
    *,
    install_root: Path,
    transaction_id: str,
) -> list[_InstallOperationFailure]:
    if not install_root.exists():
        return []
    marker = f".{transaction_id}."
    failures: list[_InstallOperationFailure] = []
    try:
        candidates = [
            entry.path
            for entry in _install_tree_entries(install_root)
            if not entry.is_directory
            and not entry.is_link
            and entry.path.name.endswith(".tmp")
        ]
    except OSError as exc:
        return [
            _InstallOperationFailure(
                detail=f"{install_root}: {exc}",
                error=exc,
            )
        ]
    for candidate in candidates:
        if marker not in candidate.name:
            continue
        try:
            _assert_local_destination(
                install_root,
                candidate,
                reject_destination_symlink=True,
                path_label="Vibe preparing transaction temporary path",
            )
            if not candidate.is_file():
                raise RuntimeError(
                    f"Vibe preparing transaction temporary path is not a file: {candidate}"
                )
            candidate.unlink()
        except (OSError, RuntimeError) as exc:
            failures.append(
                _InstallOperationFailure(
                    detail=f"{candidate}: {exc}",
                    error=exc,
                )
            )
    return failures


def _recover_install_transaction(
    *,
    state_path: Path,
    skills_dir: Path,
    install_root: Path,
) -> _InstallRecovery:
    try:
        state = _read_json(state_path)
    except ValueError as exc:
        raise RuntimeError(f"Unreadable Vibe install state: {state_path}") from exc
    status, transaction_id = _validate_install_state_header(
        state,
        state_path=state_path,
        skills_dir=skills_dir,
        install_root=install_root,
    )
    if status == INSTALL_STATE_PREPARING:
        receipt_existed = state.get("receipt_existed")
        if type(receipt_existed) is not bool:
            raise RuntimeError(f"Invalid preparing Vibe install state: {state_path}")
        cleanup_failures = _cleanup_preparing_install_transaction(
            install_root=install_root,
            transaction_id=transaction_id,
        )
        if cleanup_failures:
            _raise_install_operation_failures(
                "Vibe install preparation cleanup was incomplete; "
                f"recovery journal retained at {state_path}; "
                "cleanup failures",
                cleanup_failures,
            )
        _remove_install_state_file(
            state_path,
            failure_summary="Vibe install preparation journal cleanup was incomplete",
        )
        return _InstallRecovery(
            disposition=INSTALL_RECOVERY_ROLLED_BACK,
            receipt_existed=receipt_existed,
        )

    changes = _read_install_state(
        state_path,
        skills_dir=skills_dir,
        install_root=install_root,
        state=state,
    )
    receipt_change = changes[-1]
    receipt_state = _install_change_state(receipt_change)
    if receipt_state == "new":
        for change in changes:
            if _install_change_state(change) != "new":
                raise RuntimeError(
                    "Vibe install receipt was committed before every payload change completed; "
                    f"recovery journal retained at {state_path}"
                )
        cleanup_failures = _cleanup_install_transaction_files(changes)
        if cleanup_failures:
            _raise_install_operation_failures(
                "Vibe install transaction cleanup was incomplete; "
                f"recovery journal retained at {state_path}; "
                "cleanup failures",
                cleanup_failures,
            )
        _remove_install_state_file(
            state_path,
            failure_summary="Vibe install transaction cleanup was incomplete",
        )
        return _InstallRecovery(
            disposition=INSTALL_RECOVERY_COMMITTED,
            receipt_existed=receipt_change.destination_existed,
        )

    rollback_failures = _rollback_persisted_install_changes(changes)
    if rollback_failures:
        retained_backups = sorted(
            str(change.backup_path)
            for change in changes
            if change.backup_path is not None and change.backup_path.exists()
        )
        backup_detail = ", ".join(retained_backups) or "none"
        _raise_install_operation_failures(
            "Vibe install failed and rollback was incomplete; "
            f"recovery journal retained at {state_path}; "
            f"recovery backups retained at: {backup_detail}; rollback failures",
            rollback_failures,
        )

    cleanup_failures = _cleanup_install_transaction_files(changes)
    if cleanup_failures:
        _raise_install_operation_failures(
            "Vibe install rollback completed and temporary-file cleanup was incomplete; "
            f"recovery journal retained at {state_path}; "
            "cleanup failures",
            cleanup_failures,
        )
    _remove_install_state_file(
        state_path,
        failure_summary="Vibe install rollback completed and journal cleanup was incomplete",
    )
    return _InstallRecovery(
        disposition=INSTALL_RECOVERY_ROLLED_BACK,
        receipt_existed=receipt_change.destination_existed,
    )


def _recover_pending_install_transaction(
    *,
    skills_dir: Path,
    install_root: Path,
) -> _InstallRecovery | None:
    state_path = _install_state_path(skills_dir)
    if not state_path.exists() and not state_path.is_symlink():
        return None
    if not state_path.is_file():
        raise RuntimeError(f"Vibe install state is not a regular file: {state_path}")
    return _recover_install_transaction(
        state_path=state_path,
        skills_dir=skills_dir,
        install_root=install_root,
    )


def _uninstall_state_path(skills_dir: Path) -> Path:
    resolved_skills_dir = skills_dir.resolve()
    state_path = resolved_skills_dir.joinpath(*PurePosixPath(UNINSTALL_STATE_RELPATH).parts)
    _assert_local_destination(
        resolved_skills_dir,
        state_path,
        reject_destination_symlink=True,
        root_label="Skills directory",
        path_label="Vibe uninstall state path",
    )
    return state_path


def _uninstall_completion_path(skills_dir: Path) -> Path:
    resolved_skills_dir = skills_dir.resolve()
    completion_path = resolved_skills_dir.joinpath(
        *PurePosixPath(UNINSTALL_COMPLETE_RELPATH).parts
    )
    _assert_local_destination(
        resolved_skills_dir,
        completion_path,
        reject_destination_symlink=True,
        root_label="Skills directory",
        path_label="Vibe uninstall completion path",
    )
    return completion_path


def _read_uninstall_state(
    state_path: Path,
    *,
    skills_dir: Path,
    install_root: Path,
) -> dict[str, object]:
    try:
        state = _read_json(state_path)
    except ValueError as exc:
        raise RuntimeError(f"Unreadable Vibe uninstall state: {state_path}") from exc
    expected_skills_dir = skills_dir.resolve()
    expected_install_root = install_root.resolve()
    if state.get("schema_version") != 1:
        raise RuntimeError(f"Unsupported Vibe uninstall state schema: {state_path}")
    if state.get("state_kind") != UNINSTALL_STATE_KIND or state.get("skill_id") != "vibe":
        raise RuntimeError(f"Invalid Vibe uninstall state: {state_path}")
    if not _recorded_path_matches(state.get("skills_dir"), expected_skills_dir):
        raise RuntimeError(f"Vibe uninstall state Skills directory mismatch: {state_path}")
    if not _recorded_path_matches(state.get("install_root"), expected_install_root):
        raise RuntimeError(f"Vibe uninstall state install root mismatch: {state_path}")
    if state.get("status") != UNINSTALL_STATE_MANAGED_FILES_REMOVED:
        raise RuntimeError(f"Invalid Vibe uninstall state status: {state_path}")
    return state


def _read_uninstall_completion(
    completion_path: Path,
    *,
    skills_dir: Path,
    install_root: Path,
) -> dict[str, object]:
    try:
        completion = _read_json(completion_path)
    except ValueError as exc:
        raise RuntimeError(f"Unreadable Vibe uninstall completion: {completion_path}") from exc
    if completion.get("schema_version") != 1:
        raise RuntimeError(f"Unsupported Vibe uninstall completion schema: {completion_path}")
    if (
        completion.get("completion_kind") != UNINSTALL_COMPLETE_KIND
        or completion.get("skill_id") != "vibe"
    ):
        raise RuntimeError(f"Invalid Vibe uninstall completion: {completion_path}")
    if not _recorded_path_matches(completion.get("skills_dir"), skills_dir):
        raise RuntimeError(f"Vibe uninstall completion Skills directory mismatch: {completion_path}")
    if not _recorded_path_matches(completion.get("install_root"), install_root):
        raise RuntimeError(f"Vibe uninstall completion install root mismatch: {completion_path}")
    if completion.get("status") != UNINSTALL_COMPLETE_STATUS:
        raise RuntimeError(f"Invalid Vibe uninstall completion status: {completion_path}")
    return completion


def _validate_uninstall_completion(
    completion_path: Path,
    *,
    skills_dir: Path,
    install_root: Path,
) -> bool:
    if not completion_path.exists() and not completion_path.is_symlink():
        return False
    if not completion_path.is_file():
        raise RuntimeError(f"Vibe uninstall completion is not a regular file: {completion_path}")
    _read_uninstall_completion(
        completion_path,
        skills_dir=skills_dir,
        install_root=install_root,
    )
    return True


def _clear_uninstall_completion(
    completion_path: Path,
    *,
    skills_dir: Path,
    install_root: Path,
) -> None:
    if not _validate_uninstall_completion(
        completion_path,
        skills_dir=skills_dir,
        install_root=install_root,
    ):
        return
    completion_path.unlink()


def _is_recoverable_empty_install_root(install_root: Path) -> bool:
    if not install_root.is_dir() or install_root.is_symlink():
        return False
    try:
        entries = list(_install_tree_entries(install_root))
    except OSError:
        return False
    for entry in entries:
        if not entry.is_directory:
            return False
    return True


def _preserved_file_relpaths(install_root: Path, *, owned_files: set[str]) -> list[str]:
    internal_files = {RECEIPT_RELPATH}
    preserved: list[str] = []
    for entry in _install_tree_entries(install_root):
        if entry.is_directory:
            continue
        path = entry.path
        relpath = path.relative_to(install_root).as_posix()
        if relpath not in internal_files and relpath not in owned_files:
            preserved.append(relpath)
    return sorted(set(preserved))


def _prune_empty_directories(
    install_root: Path,
) -> tuple[list[str], list[str], list[str]]:
    metadata_dir = install_root / ".vibeskills"
    try:
        directories = sorted(
            (
                entry.path
                for entry in _install_tree_entries(install_root)
                if entry.is_directory
            ),
            key=lambda path: len(path.parts),
            reverse=True,
        )
    except OSError as exc:
        permission_denied = ["."] if isinstance(exc, PermissionError) else []
        unavailable = ["."] if isinstance(exc, TimeoutError) else []
        return ["."], permission_denied, unavailable

    failed: list[str] = []
    permission_denied: list[str] = []
    unavailable: list[str] = []
    for directory in directories:
        if directory == metadata_dir or metadata_dir in directory.parents:
            continue
        try:
            directory.rmdir()
        except TimeoutError:
            relpath = directory.relative_to(install_root).as_posix()
            failed.append(relpath)
            unavailable.append(relpath)
        except PermissionError:
            relpath = directory.relative_to(install_root).as_posix()
            failed.append(relpath)
            permission_denied.append(relpath)
        except OSError:
            try:
                is_empty = next(directory.iterdir(), None) is None
            except TimeoutError:
                is_empty = True
                unavailable.append(directory.relative_to(install_root).as_posix())
            except PermissionError:
                is_empty = True
                permission_denied.append(directory.relative_to(install_root).as_posix())
            except OSError:
                is_empty = True
            if is_empty:
                failed.append(directory.relative_to(install_root).as_posix())
    return (
        sorted(set(failed)),
        sorted(set(permission_denied)),
        sorted(set(unavailable)),
    )


def _uninstall_result(
    *,
    ok: bool,
    status: str,
    removed_files: list[str],
    failed_files: list[str] | None = None,
    failed_directories: list[str] | None = None,
    permission_denied_files: list[str] | None = None,
    permission_denied_directories: list[str] | None = None,
    unavailable_files: list[str] | None = None,
    unavailable_directories: list[str] | None = None,
    preserved_files: list[str] | None = None,
    recovery_state: str = "",
) -> dict[str, object]:
    return {
        "ok": ok,
        "status": status,
        "removed_files": sorted(set(removed_files)),
        "failed_files": sorted(set(failed_files or [])),
        "failed_directories": sorted(set(failed_directories or [])),
        "permission_denied_files": sorted(set(permission_denied_files or [])),
        "permission_denied_directories": sorted(set(permission_denied_directories or [])),
        "unavailable_files": sorted(set(unavailable_files or [])),
        "unavailable_directories": sorted(set(unavailable_directories or [])),
        "preserved_files": sorted(set(preserved_files or [])),
        "recovery_state": recovery_state,
    }


def _build_recovery_state(
    *,
    skills_dir: Path,
    install_root: Path,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "state_kind": UNINSTALL_STATE_KIND,
        "skill_id": "vibe",
        "skills_dir": str(skills_dir.resolve()),
        "install_root": str(install_root.resolve()),
        "status": UNINSTALL_STATE_MANAGED_FILES_REMOVED,
    }


def _remove_uninstall_state_file(state_path: Path) -> None:
    state_path.unlink(missing_ok=True)


def _commit_uninstall_completion(
    *,
    state_path: Path,
    state: dict[str, object],
) -> _UninstallCompletionCommitFailure | None:
    completion_path = _uninstall_completion_path(state_path.parent.parent)
    completion = {
        "schema_version": 1,
        "completion_kind": UNINSTALL_COMPLETE_KIND,
        "skill_id": "vibe",
        "skills_dir": state["skills_dir"],
        "install_root": state["install_root"],
        "status": UNINSTALL_COMPLETE_STATUS,
    }
    try:
        _write_json(completion_path, completion)
    except OSError as exc:
        return _UninstallCompletionCommitFailure(
            relpath=UNINSTALL_COMPLETE_RELPATH,
            error=exc,
        )
    try:
        state_path.unlink()
    except OSError as exc:
        return _UninstallCompletionCommitFailure(
            relpath=UNINSTALL_STATE_RELPATH,
            error=exc,
        )
    return None


def _uninstall_completion_commit_failure_result(
    failure: _UninstallCompletionCommitFailure,
    *,
    removed_files: list[str],
) -> dict[str, object]:
    permission_denied_files = (
        [failure.relpath] if isinstance(failure.error, PermissionError) else []
    )
    unavailable_files = (
        [failure.relpath] if isinstance(failure.error, TimeoutError) else []
    )
    return _uninstall_result(
        ok=False,
        status="partial_failure",
        removed_files=removed_files,
        failed_files=[failure.relpath],
        permission_denied_files=permission_denied_files,
        unavailable_files=unavailable_files,
        recovery_state=UNINSTALL_STATE_RELPATH,
    )


def _scoped_check_result(payload: dict[str, object]) -> dict[str, object]:
    ok = bool(payload.get("ok"))
    return {
        **payload,
        "scope": "installed_vibe_skill",
        "result": "passed" if ok else "failed",
        "proves": [
            "Vibe install receipt exists",
            "receipt-owned files are present",
            "receipt-owned file hashes match",
        ],
        "does_not_prove": [
            "task completion",
            "material skill execution",
            "runtime coherent",
            "delivery accepted",
        ],
    }


@_locked_vibe_operation
def install_vibe_skill(
    *,
    repo_root: Path,
    skills_dir: Path,
    installed_at_utc: str,
    source_kind: str = "developer_repo",
    source_git_commit: str = "",
    source_git_dirty: bool = False,
    release_version: str = "",
    release_asset_name: str = "",
    release_asset_digest: str = "",
    installer_version: str = "0.1.0",
    package_version: str = "0.1.0",
) -> dict[str, object]:
    source_root = repo_root.resolve()
    resolved_skills_dir = skills_dir.resolve()
    install_root = resolved_skills_dir / "vibe"
    receipt_path = install_root / RECEIPT_RELPATH
    install_state_path = _install_state_path(resolved_skills_dir)
    uninstall_state_path = _uninstall_state_path(resolved_skills_dir)
    uninstall_completion_path = _uninstall_completion_path(resolved_skills_dir)
    _assert_install_root_is_local(resolved_skills_dir, install_root)
    _assert_install_destination_is_local(install_root, receipt_path)
    _recover_pending_install_transaction(
        skills_dir=resolved_skills_dir,
        install_root=install_root,
    )
    _validate_uninstall_completion(
        uninstall_completion_path,
        skills_dir=resolved_skills_dir,
        install_root=install_root,
    )

    normalized_source_kind = str(source_kind or "").strip() or "developer_repo"
    release_payload: dict[str, object] | None = None
    if normalized_source_kind == "public_release":
        version = str(release_version or "").strip()
        asset_name = str(release_asset_name or "").strip()
        if not version or not asset_name:
            raise RuntimeError("Public release install requires release version and asset name.")
        release_payload = {
            "version": version,
            "asset_name": asset_name,
        }
        digest = str(release_asset_digest or "").strip()
        if digest:
            release_payload["asset_digest_sha256"] = digest

    has_receipt = receipt_path.is_file()
    has_uninstall_state = uninstall_state_path.is_file()
    if has_uninstall_state and not has_receipt:
        _read_uninstall_state(
            uninstall_state_path,
            skills_dir=resolved_skills_dir,
            install_root=install_root,
        )
    if (
        install_root.exists()
        and not has_receipt
        and not has_uninstall_state
        and not _is_recoverable_empty_install_root(install_root)
    ):
        raise RuntimeError(f"Install root already exists without a Vibe install receipt: {install_root}")

    install_root.mkdir(parents=True, exist_ok=True)
    governance_path = source_root / "config" / "version-governance.json"
    next_owned: list[str] = []
    for relpath in _package_file_relpaths(source_root):
        destination = install_root / relpath
        _assert_install_destination_is_local(install_root, destination)
        next_owned.append(_canonical_owned_relpath(relpath, artifact_path=governance_path, label="package"))
    if not next_owned:
        raise RuntimeError(f"Runtime packaging contract selects no installable files: {governance_path}")
    next_owned_by_destination = _relpaths_by_destination(
        install_root,
        next_owned,
        artifact_path=governance_path,
        label="package",
    )
    old_owned: set[str] = set()
    old_owned_by_destination: dict[str, str] = {}
    if has_receipt:
        receipt = _read_install_receipt(
            receipt_path,
            skills_dir=resolved_skills_dir,
            install_root=install_root,
        )
        old_owned = _file_entry_paths(cast(list[dict[str, str]], receipt["files"]))
        old_owned_by_destination = _relpaths_by_destination(
            install_root,
            old_owned,
            artifact_path=receipt_path,
            label="receipt-owned",
        )
    for destination_key, relpath in next_owned_by_destination.items():
        destination = _owned_file_path(install_root, relpath)
        if (
            destination.exists() or destination.is_symlink()
        ) and destination_key not in old_owned_by_destination:
            raise RuntimeError(f"Install path exists but is not owned by the Vibe receipt: {destination}")

    transaction_id = secrets.token_hex(16)
    preparing_state = _build_preparing_install_state(
        skills_dir=resolved_skills_dir,
        install_root=install_root,
        transaction_id=transaction_id,
        receipt_existed=has_receipt,
    )
    if install_state_path.exists() or install_state_path.is_symlink():
        raise RuntimeError(f"Vibe install transaction already exists: {install_state_path}")
    _write_json(install_state_path, preparing_state)

    try:
        payload_changes = _prepare_install_file_changes(
            source_root,
            install_root,
            next_owned,
            retired_relpaths={
                relpath
                for destination_key, relpath in old_owned_by_destination.items()
                if destination_key not in next_owned_by_destination
            },
            transaction_id=transaction_id,
        )
    except BaseException:
        _recover_install_transaction(
            state_path=install_state_path,
            skills_dir=resolved_skills_dir,
            install_root=install_root,
        )
        raise
    payload_changes_by_relpath = {
        change.relpath: change
        for change in payload_changes
        if change.new_sha256
    }
    files = [
        {
            "path": relpath,
            "sha256": payload_changes_by_relpath[relpath].new_sha256,
        }
        for relpath in next_owned
    ]
    package_digest = hashlib.sha256(
        json.dumps(files, sort_keys=True).encode("utf-8")
    ).hexdigest()
    receipt: dict[str, object] = {
        "schema_version": 1,
        "receipt_kind": "vibe-skill-install",
        "skill_id": "vibe",
        "source_kind": normalized_source_kind,
        "skills_dir": str(resolved_skills_dir),
        "install_root": str(install_root.resolve()),
        "installed_at_utc": installed_at_utc,
        "installer_version": installer_version,
        "package_version": package_version,
        "package_digest_sha256": package_digest,
        "files": files,
    }
    if release_payload is not None:
        receipt["release"] = release_payload
    else:
        receipt["source_path"] = str(source_root)
        receipt["source_git_commit"] = source_git_commit
        receipt["source_git_dirty"] = bool(source_git_dirty)
    receipt_content = _json_content(receipt)
    receipt_change = _InstallFileChange(
        relpath=RECEIPT_RELPATH,
        destination=receipt_path,
        staged_path=None,
        destination_existed=has_receipt,
        new_sha256=_sha256_text(receipt_content),
    )
    try:
        if has_receipt:
            receipt_change.backup_path = _stage_file_copy(
                receipt_path,
                receipt_path,
                transaction_id=transaction_id,
            )
            receipt_change.old_sha256 = _sha256_file(receipt_change.backup_path)
        receipt_change.staged_path = _stage_text_file(
            receipt_content,
            receipt_path,
            transaction_id=transaction_id,
        )
    except BaseException:
        _recover_install_transaction(
            state_path=install_state_path,
            skills_dir=resolved_skills_dir,
            install_root=install_root,
        )
        raise
    changes = [*payload_changes, receipt_change]

    try:
        install_state = _build_install_state(
            skills_dir=resolved_skills_dir,
            install_root=install_root,
            transaction_id=transaction_id,
            changes=changes,
        )
        _write_json(install_state_path, install_state)
    except BaseException:
        _recover_install_transaction(
            state_path=install_state_path,
            skills_dir=resolved_skills_dir,
            install_root=install_root,
        )
        raise

    try:
        _apply_install_file_changes(changes)
    except BaseException:
        recovery = _recover_install_transaction(
            state_path=install_state_path,
            skills_dir=resolved_skills_dir,
            install_root=install_root,
        )
        if recovery.disposition != INSTALL_RECOVERY_COMMITTED:
            raise
    else:
        recovery = _recover_install_transaction(
            state_path=install_state_path,
            skills_dir=resolved_skills_dir,
            install_root=install_root,
        )
        if recovery.disposition != INSTALL_RECOVERY_COMMITTED:
            raise RuntimeError("Vibe install receipt did not commit")

    if uninstall_state_path.is_file():
        _remove_uninstall_state_file(uninstall_state_path)
    _clear_uninstall_completion(
        uninstall_completion_path,
        skills_dir=resolved_skills_dir,
        install_root=install_root,
    )
    return receipt


def check_vibe_skill(*, skills_dir: Path) -> dict[str, object]:
    resolved_skills_dir = skills_dir.resolve()
    install_root = resolved_skills_dir / "vibe"
    receipt_path = install_root / RECEIPT_RELPATH
    _assert_install_root_is_local(resolved_skills_dir, install_root)
    _assert_install_destination_is_local(install_root, receipt_path)
    if not receipt_path.is_file():
        return _scoped_check_result({"ok": False, "missing_receipt": str(receipt_path)})

    receipt = _read_install_receipt(
        receipt_path,
        skills_dir=resolved_skills_dir,
        install_root=install_root,
    )
    entries = cast(list[dict[str, str]], receipt["files"])
    missing_files: list[str] = []
    drifted_files: list[str] = []
    receipt_files: set[str] = set()
    for entry in entries:
        relpath = entry["path"]
        receipt_files.add(relpath)
        expected_sha = entry["sha256"]
        file_path = _owned_file_path(install_root, relpath)
        if _path_is_link_or_reparse_point(file_path):
            drifted_files.append(relpath)
            continue
        if not file_path.is_file():
            missing_files.append(relpath)
            continue
        try:
            actual_sha = _sha256_file(file_path)
        except _FileChangedDuringReadError:
            drifted_files.append(relpath)
            continue
        if actual_sha != expected_sha:
            drifted_files.append(relpath)

    actual_files = {
        entry.path.relative_to(install_root).as_posix()
        for entry in _install_tree_entries(install_root)
        if not entry.is_directory
        and entry.path.relative_to(install_root).as_posix() != RECEIPT_RELPATH
    }
    extra_files = sorted(actual_files - receipt_files)

    return _scoped_check_result({
        "ok": not missing_files and not drifted_files,
        "missing_files": missing_files,
        "drifted_files": drifted_files,
        "extra_files": extra_files,
    })


@_locked_vibe_operation
def update_vibe_skill(
    *,
    repo_root: Path,
    skills_dir: Path,
    installed_at_utc: str,
    source_kind: str = "developer_repo",
    source_git_commit: str = "",
    source_git_dirty: bool = False,
    release_version: str = "",
    release_asset_name: str = "",
    release_asset_digest: str = "",
    installer_version: str = "0.1.0",
    package_version: str = "0.1.0",
) -> dict[str, object]:
    resolved_skills_dir = skills_dir.resolve()
    install_root = resolved_skills_dir / "vibe"
    _assert_install_root_is_local(resolved_skills_dir, install_root)
    _recover_pending_install_transaction(
        skills_dir=resolved_skills_dir,
        install_root=install_root,
    )
    check_result = check_vibe_skill(skills_dir=skills_dir)
    if not check_result.get("ok"):
        raise RuntimeError(f"Refusing to update drifted Vibe install: {check_result}")
    return install_vibe_skill(
        repo_root=repo_root,
        skills_dir=skills_dir,
        installed_at_utc=installed_at_utc,
        source_kind=source_kind,
        source_git_commit=source_git_commit,
        source_git_dirty=source_git_dirty,
        release_version=release_version,
        release_asset_name=release_asset_name,
        release_asset_digest=release_asset_digest,
        installer_version=installer_version,
        package_version=package_version,
    )


def _remove_owned_files(
    install_root: Path,
    entries: list[dict[str, str]],
) -> tuple[list[str], list[str], list[str], list[str]]:
    removed_files: list[str] = []
    failed_files: list[str] = []
    permission_denied_files: list[str] = []
    unavailable_files: list[str] = []
    for entry in entries:
        relpath = entry["path"]
        file_path = _owned_file_path(install_root, relpath)
        try:
            file_status = file_path.stat(follow_symlinks=False)
        except FileNotFoundError:
            continue
        is_link = _is_link_or_reparse_point(file_status)
        if not is_link and not stat.S_ISREG(file_status.st_mode):
            continue
        try:
            if is_link and stat.S_ISDIR(file_status.st_mode) and not stat.S_ISLNK(
                file_status.st_mode
            ):
                file_path.rmdir()
            else:
                file_path.unlink()
        except OSError as exc:
            failed_files.append(relpath)
            if isinstance(exc, PermissionError):
                permission_denied_files.append(relpath)
            if isinstance(exc, TimeoutError):
                unavailable_files.append(relpath)
        else:
            removed_files.append(relpath)
    return removed_files, failed_files, permission_denied_files, unavailable_files


def _finalize_uninstall_state(
    *,
    install_root: Path,
    state_path: Path,
    state: dict[str, object],
    removed_files: list[str],
) -> dict[str, object]:
    if state.get("status") != UNINSTALL_STATE_MANAGED_FILES_REMOVED:
        raise RuntimeError(f"Invalid Vibe uninstall state status: {state_path}")

    if not install_root.exists():
        commit_failure = _commit_uninstall_completion(
            state_path=state_path,
            state=state,
        )
        if commit_failure is not None:
            return _uninstall_completion_commit_failure_result(
                commit_failure,
                removed_files=removed_files,
            )
        return _uninstall_result(
            ok=True,
            status="uninstalled",
            removed_files=removed_files,
        )

    (
        failed_directories,
        permission_denied_directories,
        unavailable_directories,
    ) = _prune_empty_directories(install_root)
    preserved_files = _preserved_file_relpaths(install_root, owned_files=set())
    if failed_directories:
        return _uninstall_result(
            ok=False,
            status="partial_failure",
            removed_files=removed_files,
            failed_directories=failed_directories,
            permission_denied_directories=permission_denied_directories,
            unavailable_directories=unavailable_directories,
            preserved_files=preserved_files,
            recovery_state=UNINSTALL_STATE_RELPATH,
        )
    if preserved_files:
        return _uninstall_result(
            ok=True,
            status="uninstalled_with_preserved_files",
            removed_files=removed_files,
            preserved_files=preserved_files,
            recovery_state=UNINSTALL_STATE_RELPATH,
        )

    metadata_dir = install_root / ".vibeskills"
    if metadata_dir.exists():
        try:
            metadata_dir.rmdir()
        except OSError as exc:
            preserved_files = _preserved_file_relpaths(install_root, owned_files=set())
            if preserved_files:
                return _uninstall_result(
                    ok=True,
                    status="uninstalled_with_preserved_files",
                    removed_files=removed_files,
                    preserved_files=preserved_files,
                    recovery_state=UNINSTALL_STATE_RELPATH,
                )
            relpath = metadata_dir.relative_to(install_root).as_posix()
            permission_denied = [relpath] if isinstance(exc, PermissionError) else []
            unavailable = [relpath] if isinstance(exc, TimeoutError) else []
            return _uninstall_result(
                ok=False,
                status="partial_failure",
                removed_files=removed_files,
                failed_directories=[relpath],
                permission_denied_directories=permission_denied,
                unavailable_directories=unavailable,
                recovery_state=UNINSTALL_STATE_RELPATH,
            )

    try:
        install_root.rmdir()
    except OSError as exc:
        preserved_files = _preserved_file_relpaths(install_root, owned_files=set())
        if preserved_files:
            return _uninstall_result(
                ok=True,
                status="uninstalled_with_preserved_files",
                removed_files=removed_files,
                preserved_files=preserved_files,
                recovery_state=UNINSTALL_STATE_RELPATH,
            )
        permission_denied = ["."] if isinstance(exc, PermissionError) else []
        unavailable = ["."] if isinstance(exc, TimeoutError) else []
        return _uninstall_result(
            ok=False,
            status="partial_failure",
            removed_files=removed_files,
            failed_directories=["."],
            permission_denied_directories=permission_denied,
            unavailable_directories=unavailable,
            recovery_state=UNINSTALL_STATE_RELPATH,
        )

    commit_failure = _commit_uninstall_completion(
        state_path=state_path,
        state=state,
    )
    if commit_failure is not None:
        return _uninstall_completion_commit_failure_result(
            commit_failure,
            removed_files=removed_files,
        )

    return _uninstall_result(
        ok=True,
        status="uninstalled",
        removed_files=removed_files,
    )


def _finalize_interrupted_new_install(install_root: Path) -> dict[str, object]:
    if not install_root.exists():
        return _uninstall_result(
            ok=True,
            status="uninstalled",
            removed_files=[],
        )

    (
        failed_directories,
        permission_denied_directories,
        unavailable_directories,
    ) = _prune_empty_directories(install_root)
    preserved_files = _preserved_file_relpaths(install_root, owned_files=set())
    if failed_directories:
        return _uninstall_result(
            ok=False,
            status="partial_failure",
            removed_files=[],
            failed_directories=failed_directories,
            permission_denied_directories=permission_denied_directories,
            unavailable_directories=unavailable_directories,
            preserved_files=preserved_files,
        )
    if preserved_files:
        return _uninstall_result(
            ok=True,
            status="uninstalled_with_preserved_files",
            removed_files=[],
            preserved_files=preserved_files,
        )

    metadata_dir = install_root / ".vibeskills"
    if metadata_dir.exists():
        try:
            metadata_dir.rmdir()
        except OSError as exc:
            relpath = metadata_dir.relative_to(install_root).as_posix()
            permission_denied = [relpath] if isinstance(exc, PermissionError) else []
            unavailable = [relpath] if isinstance(exc, TimeoutError) else []
            return _uninstall_result(
                ok=False,
                status="partial_failure",
                removed_files=[],
                failed_directories=[relpath],
                permission_denied_directories=permission_denied,
                unavailable_directories=unavailable,
            )
    try:
        install_root.rmdir()
    except OSError as exc:
        permission_denied = ["."] if isinstance(exc, PermissionError) else []
        unavailable = ["."] if isinstance(exc, TimeoutError) else []
        return _uninstall_result(
            ok=False,
            status="partial_failure",
            removed_files=[],
            failed_directories=["."],
            permission_denied_directories=permission_denied,
            unavailable_directories=unavailable,
        )
    return _uninstall_result(
        ok=True,
        status="uninstalled",
        removed_files=[],
    )


@_locked_vibe_operation
def uninstall_vibe_skill(*, skills_dir: Path) -> dict[str, object]:
    resolved_skills_dir = skills_dir.resolve()
    install_root = resolved_skills_dir / "vibe"
    receipt_path = install_root / RECEIPT_RELPATH
    state_path = _uninstall_state_path(resolved_skills_dir)
    completion_path = _uninstall_completion_path(resolved_skills_dir)
    _assert_install_root_is_local(resolved_skills_dir, install_root)
    _assert_install_destination_is_local(install_root, receipt_path)
    install_recovery = _recover_pending_install_transaction(
        skills_dir=resolved_skills_dir,
        install_root=install_root,
    )
    if not receipt_path.is_file():
        if state_path.is_file():
            state = _read_uninstall_state(
                state_path,
                skills_dir=resolved_skills_dir,
                install_root=install_root,
            )
            return _finalize_uninstall_state(
                install_root=install_root,
                state_path=state_path,
                state=state,
                removed_files=[],
            )
        if completion_path.exists() or completion_path.is_symlink():
            if not completion_path.is_file():
                raise RuntimeError(
                    f"Vibe uninstall completion is not a regular file: {completion_path}"
                )
            _read_uninstall_completion(
                completion_path,
                skills_dir=resolved_skills_dir,
                install_root=install_root,
            )
            preserved_files = (
                _preserved_file_relpaths(install_root, owned_files=set())
                if install_root.exists()
                else []
            )
            return _uninstall_result(
                ok=True,
                status=(
                    "uninstalled_with_preserved_files"
                    if preserved_files
                    else "uninstalled"
                ),
                removed_files=[],
                preserved_files=preserved_files,
            )
        if (
            install_recovery is not None
            and install_recovery.disposition == INSTALL_RECOVERY_ROLLED_BACK
            and not install_recovery.receipt_existed
        ):
            return _finalize_interrupted_new_install(install_root)
        raise RuntimeError(f"Vibe install receipt is missing: {receipt_path}")

    receipt = _read_install_receipt(
        receipt_path,
        skills_dir=resolved_skills_dir,
        install_root=install_root,
    )
    entries = cast(list[dict[str, str]], receipt["files"])
    owned_files = _file_entry_paths(entries)
    (
        removed_files,
        failed_files,
        permission_denied_files,
        unavailable_files,
    ) = _remove_owned_files(
        install_root,
        entries,
    )

    preserved_files = _preserved_file_relpaths(install_root, owned_files=owned_files)
    if failed_files:
        return _uninstall_result(
            ok=False,
            status="partial_failure",
            removed_files=removed_files,
            failed_files=failed_files,
            permission_denied_files=permission_denied_files,
            unavailable_files=unavailable_files,
            preserved_files=preserved_files,
        )

    (
        failed_directories,
        permission_denied_directories,
        unavailable_directories,
    ) = _prune_empty_directories(install_root)
    if failed_directories:
        return _uninstall_result(
            ok=False,
            status="partial_failure",
            removed_files=removed_files,
            failed_directories=failed_directories,
            permission_denied_directories=permission_denied_directories,
            unavailable_directories=unavailable_directories,
            preserved_files=preserved_files,
        )

    state = _build_recovery_state(
        skills_dir=resolved_skills_dir,
        install_root=install_root,
    )
    _write_json(state_path, state)
    try:
        receipt_path.unlink()
    except OSError as exc:
        permission_denied_files = [RECEIPT_RELPATH] if isinstance(exc, PermissionError) else []
        unavailable_files = [RECEIPT_RELPATH] if isinstance(exc, TimeoutError) else []
        return _uninstall_result(
            ok=False,
            status="partial_failure",
            removed_files=removed_files,
            failed_files=[RECEIPT_RELPATH],
            permission_denied_files=permission_denied_files,
            unavailable_files=unavailable_files,
            preserved_files=preserved_files,
            recovery_state=UNINSTALL_STATE_RELPATH,
        )

    return _finalize_uninstall_state(
        install_root=install_root,
        state_path=state_path,
        state=state,
        removed_files=removed_files,
    )


__all__ = [
    "check_vibe_skill",
    "install_vibe_skill",
    "runtime_surface_relpaths",
    "uninstall_vibe_skill",
    "update_vibe_skill",
]
