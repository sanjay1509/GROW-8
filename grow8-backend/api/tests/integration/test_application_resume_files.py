"""Resume copies kept with applications never leave orphan files (#48, ADR 0020).

Files go to a temporary folder (`storage_dir`). Opportunity 1 is open; Alex (user 5)
applies, withdraws and applies again."""

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import ConflictError
from app.services import application_service

API = "/api/v1"
APPLY = f"{API}/opportunities/1/applications"


def _pdf(text: str) -> bytes:
    return b"%PDF-1.4\n% " + text.encode() + b"\n%%EOF\n"


def _files(storage_dir: Path) -> list[Path]:
    return sorted(p for p in storage_dir.rglob("*") if p.is_file())


def _apply(client: TestClient, headers: dict[str, str], resume: bytes | None = None) -> Any:
    files = {"resume": ("cv.pdf", resume, "application/pdf")} if resume else None
    return client.post(APPLY, data={}, files=files, headers=headers)


def _withdraw(client: TestClient, headers: dict[str, str], application_id: int) -> None:
    response = client.post(f"{API}/applications/{application_id}/withdraw", headers=headers)
    assert response.status_code == 200, response.text


def _download(client: TestClient, headers: dict[str, str], application_id: int) -> Any:
    return client.get(f"{API}/applications/{application_id}/resume", headers=headers)


def test_a_refused_apply_leaves_no_file(
    client: TestClient,
    contributor: dict[str, str],
    storage_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The database can still refuse the row after the copy is stored, for example when a
    race fills the last place; the copy must be deleted again."""

    def refuse(session: object) -> None:
        raise ConflictError("No places left", code="APPLICANT_LIMIT_REACHED")

    monkeypatch.setattr(application_service, "_commit", refuse)

    response = _apply(client, contributor, resume=_pdf("mine"))

    assert response.status_code == 409, response.text
    assert _files(storage_dir) == []


def test_reapplying_replaces_the_copy_and_deletes_the_old_one(
    client: TestClient, contributor: dict[str, str], bakery: dict[str, str], storage_dir: Path
) -> None:
    first = _apply(client, contributor, resume=_pdf("first"))
    application_id = first.json()["application_id"]
    [old_file] = _files(storage_dir)
    _withdraw(client, contributor, application_id)

    again = _apply(client, contributor, resume=_pdf("second"))

    assert again.status_code == 201, again.text
    assert again.json()["application_id"] == application_id
    [new_file] = _files(storage_dir)
    assert new_file != old_file
    assert _download(client, bakery, application_id).content == _pdf("second")


def test_reapplying_without_a_resume_deletes_the_old_copy(
    client: TestClient, contributor: dict[str, str], storage_dir: Path
) -> None:
    application_id = _apply(client, contributor, resume=_pdf("first")).json()["application_id"]
    _withdraw(client, contributor, application_id)

    again = _apply(client, contributor)

    assert again.status_code == 201, again.text
    assert again.json()["applicant"]["has_resume"] is False
    assert _files(storage_dir) == []


def test_a_missing_profile_resume_file_does_not_break_applying(
    client: TestClient, contributor: dict[str, str], storage_dir: Path
) -> None:
    upload = client.put(
        f"{API}/contributors/me/resume",
        files={"file": ("cv.pdf", _pdf("profile"), "application/pdf")},
        headers=contributor,
    )
    assert upload.status_code == 200, upload.text
    for path in _files(storage_dir):
        path.unlink()  # the row is there, the file is gone

    response = _apply(client, contributor)

    assert response.status_code == 201, response.text
    assert _files(storage_dir) == []


def test_applying_copies_the_profile_resume(
    client: TestClient, contributor: dict[str, str], bakery: dict[str, str], storage_dir: Path
) -> None:
    client.put(
        f"{API}/contributors/me/resume",
        files={"file": ("cv.pdf", _pdf("profile"), "application/pdf")},
        headers=contributor,
    )

    application_id = _apply(client, contributor).json()["application_id"]

    assert len(_files(storage_dir)) == 2  # the profile resume and the application's copy
    assert _download(client, bakery, application_id).content == _pdf("profile")
