"""Resume upload rules that need no database (ADR 0008)."""

import io
from types import SimpleNamespace

import pytest

from app.core.exceptions import AppError
from app.services import resume_service
from app.services.resume_service import clean_file_name


@pytest.mark.parametrize(
    ("given", "stored"),
    [
        ("My CV.pdf", "My CV.pdf"),
        ("../../etc/passwd", "passwd.pdf"),
        (r"C:\Users\alex\Résumé 2026.PDF", "Résumé 2026.PDF"),
        ("bad\x00name\n.pdf", "badname.pdf"),
        ("   ", "resume.pdf"),
        (None, "resume.pdf"),
        ("...", "resume.pdf"),
    ],
)
def test_file_names_are_display_only(given: str | None, stored: str) -> None:
    assert clean_file_name(given) == stored


def test_long_file_names_are_cut_but_keep_the_extension() -> None:
    name = clean_file_name("x" * 400 + ".pdf")
    assert len(name) == 255
    assert name.endswith(".pdf")


class _RecordingStorage:
    def __init__(self) -> None:
        self.saved: dict[str, bytes] = {}
        self.deleted: list[str] = []

    def save(self, key, chunks):
        self.saved[key] = b"".join(chunks)

    def open(self, key):
        raise NotImplementedError

    def delete(self, key):
        self.deleted.append(key)


class _FailingCommitSession:
    def add(self, _obj) -> None:
        pass

    def commit(self) -> None:
        raise RuntimeError("database went away")

    def rollback(self) -> None:
        pass


def test_a_failed_commit_removes_the_new_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(resume_service.resume_repository, "lock_profile", lambda s, uid: object())
    monkeypatch.setattr(resume_service.resume_repository, "get", lambda s, uid: None)
    storage = _RecordingStorage()

    with pytest.raises(RuntimeError):
        resume_service.upload(
            _FailingCommitSession(),
            storage,
            SimpleNamespace(user_id=5),
            io.BytesIO(b"%PDF-1.4 hello"),
            "cv.pdf",
        )

    [key] = storage.saved
    assert storage.deleted == [key]


def test_size_limit_stops_the_copy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(resume_service, "MAX_BYTES", 10)
    monkeypatch.setattr(resume_service.resume_repository, "lock_profile", lambda s, uid: object())
    storage = _RecordingStorage()

    with pytest.raises(AppError) as exc_info:
        resume_service.upload(
            _FailingCommitSession(),
            storage,
            SimpleNamespace(user_id=5),
            io.BytesIO(b"%PDF-" + b"x" * 200_000),
            "cv.pdf",
        )

    assert exc_info.value.code == "RESUME_TOO_LARGE"
    assert exc_info.value.status_code == 413
