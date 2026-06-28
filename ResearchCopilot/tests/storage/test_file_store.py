import pytest
import tempfile
import shutil
from pathlib import Path
from config.model import StorageConfig
from storage.file_store import LocalFileStore


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d)


@pytest.fixture
def config(temp_dir):
    return StorageConfig(file_store_root=str(temp_dir))


@pytest.fixture
def store(config):
    return LocalFileStore(config)


def test_save_copies_file(store, temp_dir):
    """save() should copy the source file into the store under the right category."""
    src = temp_dir / "source.txt"
    src.write_text("hello world")

    rel_path = store.save(src, "papers")
    assert rel_path.startswith("papers/")
    assert Path(temp_dir / rel_path).exists()
    assert Path(temp_dir / rel_path).read_text() == "hello world"


def test_save_preserves_extension(store, temp_dir):
    src = temp_dir / "paper.pdf"
    src.write_text("pdf content")
    rel_path = store.save(src, "papers")
    assert rel_path.endswith(".pdf")


def test_save_avoids_name_collision(store, temp_dir):
    """If a file with the same name exists, save should not overwrite."""
    src1 = temp_dir / "doc.pdf"
    src1.write_text("version 1")
    src2 = temp_dir / "doc.pdf"  # same name, different temp location
    # We simulate this: create a second source file
    alt_dir = temp_dir / "alt"
    alt_dir.mkdir()
    src2_alt = alt_dir / "doc.pdf"
    src2_alt.write_text("version 2")

    p1 = store.save(src1, "papers")
    p2 = store.save(src2_alt, "papers")

    assert p1 != p2
    assert Path(temp_dir / p1).read_text() == "version 1"
    assert Path(temp_dir / p2).read_text() == "version 2"


def test_get_path_returns_absolute(store, temp_dir):
    src = temp_dir / "test.txt"
    src.write_text("data")
    rel = store.save(src, "notes")

    abs_path = store.get_path(rel)
    assert abs_path.is_absolute()
    assert abs_path.exists()


def test_list_returns_files_in_category(store, temp_dir):
    src = temp_dir / "a.txt"
    src.write_text("a")
    store.save(src, "papers")

    files = store.list("papers")
    assert len(files) == 1
    assert files[0].startswith("papers/")


def test_list_empty_category(store):
    assert store.list("nonexistent") == []


def test_delete_removes_file(store, temp_dir):
    src = temp_dir / "to_delete.txt"
    src.write_text("delete me")
    rel = store.save(src, "papers")

    assert Path(temp_dir / rel).exists()
    store.delete(rel)
    assert not Path(temp_dir / rel).exists()
