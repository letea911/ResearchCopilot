import shutil
import uuid
from pathlib import Path
from config.model import StorageConfig
from storage.interfaces import BaseFileStore


class LocalFileStore(BaseFileStore):
    """Filesystem-backed file store."""

    def __init__(self, config: StorageConfig):
        self._root = Path(config.file_store_root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def save(self, source: Path, category: str) -> str:
        category_dir = self._root / category
        category_dir.mkdir(parents=True, exist_ok=True)

        stem = source.stem
        suffix = source.suffix
        unique_name = f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"
        dest = category_dir / unique_name

        shutil.copy2(source, dest)
        return dest.relative_to(self._root).as_posix()

    def get_path(self, relative_path: str) -> Path:
        return self._root / relative_path

    def list(self, category: str) -> list[str]:
        category_dir = self._root / category
        if not category_dir.exists():
            return []
        return [
            p.relative_to(self._root).as_posix()
            for p in category_dir.iterdir()
            if p.is_file()
        ]

    def delete(self, relative_path: str) -> None:
        target = self._root / relative_path
        if target.exists():
            target.unlink()
