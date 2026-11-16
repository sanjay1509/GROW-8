"""LocalFileStorage: atomic writes, server-generated keys only (ADR 0007)."""

from pathlib import Path

import pytest

from app.storage import LocalFileStorage, StoredFileMissing, new_key


def test_round_trip(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    key = new_key("resumes")

    storage.save(key, [b"%PDF-", b"1.4 body"])

    with storage.open(key) as f:
        assert f.read() == b"%PDF-1.4 body"
    assert (tmp_path / key).is_file()


def test_keys_are_unique_and_shaped(tmp_path: Path) -> None:
    keys = {new_key("resumes") for _ in range(100)}
    assert len(keys) == 100
    assert all(k.startswith("resumes/") and len(k) == len("resumes/") + 32 for k in keys)


@pytest.mark.parametrize(
    "key",
    [
        "../outside",
        "resumes/../../etc/passwd",
        "/etc/passwd",
        "resumes/My CV.pdf",
        "resumes/" + "a" * 31,
        "Resumes/" + "a" * 32,
        "",
    ],
)
def test_only_generated_keys_are_accepted(tmp_path: Path, key: str) -> None:
    storage = LocalFileStorage(tmp_path)
    with pytest.raises(ValueError):
        storage.save(key, [b"x"])
    with pytest.raises(ValueError):
        storage.open(key)
    with pytest.raises(ValueError):
        storage.delete(key)


def test_a_failed_write_leaves_nothing_behind(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    key = new_key("resumes")

    def chunks():
        yield b"%PDF-partial"
        raise RuntimeError("upload too large")

    with pytest.raises(RuntimeError):
        storage.save(key, chunks())

    assert [p for p in tmp_path.rglob("*") if p.is_file()] == []


def test_saving_again_replaces_the_whole_file(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    key = new_key("resumes")
    storage.save(key, [b"first version, longer"])
    storage.save(key, [b"second"])

    with storage.open(key) as f:
        assert f.read() == b"second"


def test_missing_files(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)
    key = new_key("resumes")

    with pytest.raises(StoredFileMissing):
        storage.open(key)
    storage.delete(key)  # not an error
