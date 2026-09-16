"""Bounded reads and atomic replacement of regular, non-symlink files."""

from __future__ import annotations

import os
import secrets
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .limits import MAX_INPUT_BYTES, TemplateLimitError, check_size

# Anchor operations to open directories on platforms with no-follow/dir-fd support.
_DIR_FD = os.open in os.supports_dir_fd and hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY")


def reject_links(path: Path) -> None:
    """Also reject linked ancestors and Windows junction/reparse points."""
    for item in (*reversed(path.absolute().parents), path.absolute()):
        info = item.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise OSError(f"refusing symbolic link or reparse point: {item}")


@contextmanager
def _parent_directory(path: Path) -> Iterator[int | None]:
    reject_links(path.parent)
    if not _DIR_FD:
        yield None
        return
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(path.anchor, flags)
    try:
        for part in path.parent.parts[1:]:
            child = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        yield descriptor
    finally:
        os.close(descriptor)


def _fingerprint(info: os.stat_result) -> tuple[int, ...]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
        info.st_mode,
        info.st_uid,
        info.st_gid,
    )


@dataclass
class TemplateFile:
    path: Path
    parent_fd: int | None
    snapshot: os.stat_result | None = None

    def _target(self, name: str | None = None) -> str | Path:
        name = name or self.path.name
        return name if self.parent_fd is not None else self.path.parent / name

    def _stat(self) -> os.stat_result:
        if self.parent_fd is None:
            reject_links(self.path)
        return os.stat(self._target(), dir_fd=self.parent_fd, follow_symlinks=False)

    def read(self) -> str:
        before = self._stat()
        if not stat.S_ISREG(before.st_mode):
            raise OSError(f"not a regular file: {self.path}")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(self._target(), flags, dir_fd=self.parent_fd)
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if _fingerprint(opened) != _fingerprint(before):
                raise OSError("file changed while opening; refusing to read")
            if opened.st_size > MAX_INPUT_BYTES:
                raise TemplateLimitError(f"template exceeds the {MAX_INPUT_BYTES}-byte limit")
            data = stream.read(MAX_INPUT_BYTES + 1)
            if len(data) > MAX_INPUT_BYTES:
                raise TemplateLimitError(f"template exceeds the {MAX_INPUT_BYTES}-byte limit")
            if _fingerprint(os.fstat(stream.fileno())) != _fingerprint(opened):
                raise OSError("file changed while reading; please retry")
        self.snapshot = opened
        return data.decode("utf-8")

    def replace(self, text: str) -> None:
        check_size(text)
        if self.snapshot is None:
            raise OSError("file must be read before replacement")
        if not self.snapshot.st_mode & 0o222:
            raise PermissionError("refusing to replace a read-only file")
        if hasattr(os, "geteuid") and self.snapshot.st_uid != os.geteuid():
            raise PermissionError("refusing to change file ownership through replacement")
        temporary = f".j2fix-{secrets.token_hex(16)}.tmp"
        descriptor = os.open(
            self._target(temporary),
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
            dir_fd=self.parent_fd,
        )
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(text.encode("utf-8"))
                stream.flush()
                if hasattr(os, "fchown") and os.fstat(stream.fileno()).st_gid != self.snapshot.st_gid:
                    # Never expose content to a different group through replacement.
                    os.fchown(stream.fileno(), -1, self.snapshot.st_gid)
                if hasattr(os, "fchmod"):
                    # Do not propagate setuid/setgid bits to rewritten content.
                    os.fchmod(stream.fileno(), stat.S_IMODE(self.snapshot.st_mode) & 0o777)
                os.fsync(stream.fileno())
            if _fingerprint(self._stat()) != _fingerprint(self.snapshot):
                raise OSError("file changed during formatting; refusing to overwrite it")
            # Replaces the directory entry, never writes through a symlink/hardlink.
            os.replace(
                self._target(temporary),
                self._target(),
                src_dir_fd=self.parent_fd,
                dst_dir_fd=self.parent_fd,
            )
        finally:
            try:
                os.unlink(self._target(temporary), dir_fd=self.parent_fd)
            except FileNotFoundError:
                pass


@contextmanager
def open_template(path: Path) -> Iterator[TemplateFile]:
    path = path.absolute()
    with _parent_directory(path) as descriptor:
        yield TemplateFile(path, descriptor)
