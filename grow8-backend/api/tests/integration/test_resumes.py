"""Contributor resumes: upload, replace, download, delete, and creator access through
an application (ADRs 0007, 0008). Files go to a temporary folder (`storage_dir`)."""

from pathlib import Path
from typing import Any

import pymysql
import pytest
from fastapi.testclient import TestClient

ME = "/api/v1/contributors/me/resume"
PDF = b"%PDF-1.4\n% GROW8 test resume\n" + b"0" * 2_000 + b"\n%%EOF\n"


def _upload(
    client: TestClient,
    headers: dict[str, str],
    content: bytes = PDF,
    name: str = "Alex Chen CV.pdf",
    content_type: str = "application/pdf",
) -> Any:
    return client.put(ME, files={"file": (name, content, content_type)}, headers=headers)


def _stored_files(storage_dir: Path) -> list[Path]:
    return sorted(p for p in storage_dir.rglob("*") if p.is_file())


def _error(response: Any, status: int) -> str:
    assert response.status_code == status, response.text
    return response.json()["error"]["code"]


# --- the contributor's own resume ---------------------------------------------


def test_upload_then_read_metadata_and_download(
    client: TestClient, contributor: dict[str, str], storage_dir: Path
) -> None:
    response = _upload(client, contributor)

    assert response.status_code == 200, response.text
    assert response.json() == {
        "file_name": "Alex Chen CV.pdf",
        "content_type": "application/pdf",
        "size_bytes": len(PDF),
        "uploaded_at": "2026-10-16T12:00:00Z",
    }
    assert client.get(ME, headers=contributor).json() == response.json()

    download = client.get(f"{ME}/file", headers=contributor)
    assert download.status_code == 200
    assert download.content == PDF
    assert download.headers["content-type"] == "application/pdf"
    assert download.headers["content-disposition"].startswith(
        'attachment; filename="Alex Chen CV.pdf"'
    )
    assert download.headers["x-content-type-options"] == "nosniff"

    [stored] = _stored_files(storage_dir)
    assert stored.parent.name == "resumes"
    assert "Alex" not in stored.name  # the key never comes from the file name


def test_uploading_again_replaces_the_file(
    client: TestClient, contributor: dict[str, str], storage_dir: Path
) -> None:
    _upload(client, contributor)
    [first] = _stored_files(storage_dir)

    second = PDF + b"% version 2\n"
    response = _upload(client, contributor, content=second, name="CV v2.pdf")

    assert response.status_code == 200
    assert response.json()["file_name"] == "CV v2.pdf"
    [stored] = _stored_files(storage_dir)
    assert stored != first
    assert client.get(f"{ME}/file", headers=contributor).content == second


def test_delete_removes_row_and_file(
    client: TestClient, contributor: dict[str, str], storage_dir: Path
) -> None:
    _upload(client, contributor)

    assert client.delete(ME, headers=contributor).status_code == 204

    assert _stored_files(storage_dir) == []
    assert _error(client.get(ME, headers=contributor), 404) == "RESUME_NOT_FOUND"
    assert _error(client.get(f"{ME}/file", headers=contributor), 404) == "RESUME_NOT_FOUND"
    assert _error(client.delete(ME, headers=contributor), 404) == "RESUME_NOT_FOUND"


def test_file_names_are_cleaned_and_non_ascii_names_survive_the_download(
    client: TestClient, contributor: dict[str, str]
) -> None:
    response = _upload(client, contributor, name="../../secret/Résumé")

    assert response.json()["file_name"] == "Résumé.pdf"
    disposition = client.get(f"{ME}/file", headers=contributor).headers["content-disposition"]
    assert "filename*=UTF-8''R%C3%A9sum%C3%A9.pdf" in disposition
    assert 'filename="Resume.pdf"' in disposition  # ASCII fallback keeps the letters


# --- validation ---------------------------------------------------------------


def test_only_pdfs_are_accepted_whatever_the_name_or_type_claims(
    client: TestClient, contributor: dict[str, str], storage_dir: Path
) -> None:
    fake = b"PK\x03\x04 a zip, renamed"
    response = _upload(client, contributor, content=fake, name="cv.pdf")

    assert _error(response, 415) == "UNSUPPORTED_FILE_TYPE"
    assert _stored_files(storage_dir) == []


def test_empty_file_is_rejected(client: TestClient, contributor: dict[str, str]) -> None:
    assert _error(_upload(client, contributor, content=b""), 422) == "EMPTY_FILE"


def test_missing_file_field_is_a_validation_error(
    client: TestClient, contributor: dict[str, str]
) -> None:
    response = client.put(ME, data={"not_file": "x"}, headers=contributor)

    assert _error(response, 422) == "VALIDATION_ERROR"


def test_over_10_mb_is_refused_before_the_body_is_read(
    client: TestClient, contributor: dict[str, str], storage_dir: Path
) -> None:
    too_big = b"%PDF-" + b"0" * (10 * 1024 * 1024 + 70 * 1024)

    response = _upload(client, contributor, content=too_big)

    assert _error(response, 413) == "RESUME_TOO_LARGE"
    assert _stored_files(storage_dir) == []


def test_file_just_over_the_limit_inside_the_envelope_is_caught_while_copying(
    client: TestClient,
    contributor: dict[str, str],
    storage_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The middleware allows room for multipart overhead, so the service checks the real
    size too. A lower service limit stands in for a file a few KB over 10 MB."""
    monkeypatch.setattr("app.services.resume_service.MAX_BYTES", 1_000)

    response = _upload(client, contributor)  # ~2 KB

    assert _error(response, 413) == "RESUME_TOO_LARGE"
    assert _stored_files(storage_dir) == []
    assert _error(client.get(ME, headers=contributor), 404) == "RESUME_NOT_FOUND"


def test_upload_without_content_length_is_refused(
    client: TestClient, contributor: dict[str, str]
) -> None:
    def chunked():  # httpx sends an iterator body chunked, without Content-Length
        yield b"--x\r\n"

    response = client.put(
        ME,
        content=chunked(),
        headers={**contributor, "Content-Type": "multipart/form-data; boundary=x"},
    )

    assert _error(response, 411) == "LENGTH_REQUIRED"


def test_only_contributors_have_a_resume(
    client: TestClient, bakery: dict[str, str], contributor: dict[str, str]
) -> None:
    assert _error(_upload(client, bakery), 403) == "ROLE_FORBIDDEN"
    assert _error(client.get(ME), 401) == "AUTH_REQUIRED"
    assert _error(client.put(ME, files={"file": ("cv.pdf", PDF)}), 401) == "AUTH_REQUIRED"


def test_row_whose_file_disappeared_is_reported_as_missing(
    client: TestClient, contributor: dict[str, str], storage_dir: Path
) -> None:
    _upload(client, contributor)
    for path in _stored_files(storage_dir):
        path.unlink()

    assert _error(client.get(f"{ME}/file", headers=contributor), 404) == "RESUME_NOT_FOUND"


# --- creators, through an application ------------------------------------------


def _apply(client: TestClient, headers: dict[str, str], opportunity_id: int = 1) -> int:
    response = client.post(
        f"/api/v1/opportunities/{opportunity_id}/applications", json={}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()["application_id"]


def test_owning_creator_downloads_the_applicants_resume(
    client: TestClient, contributor: dict[str, str], bakery: dict[str, str]
) -> None:
    _upload(client, contributor)
    application_id = _apply(client, contributor)

    application = client.get(f"/api/v1/applications/{application_id}", headers=bakery).json()
    assert application["applicant"]["has_resume"] is True

    download = client.get(f"/api/v1/applications/{application_id}/resume", headers=bakery)
    assert download.status_code == 200
    assert download.content == PDF


def test_creator_sees_the_current_resume_even_after_a_withdrawal(
    client: TestClient, contributor: dict[str, str], bakery: dict[str, str]
) -> None:
    application_id = _apply(client, contributor)
    client.post(f"/api/v1/applications/{application_id}/withdraw", headers=contributor)
    _upload(client, contributor)

    download = client.get(f"/api/v1/applications/{application_id}/resume", headers=bakery)

    assert download.content == PDF


def test_has_resume_is_false_and_download_404_without_one(
    client: TestClient, contributor: dict[str, str], bakery: dict[str, str]
) -> None:
    application_id = _apply(client, contributor)

    listing = client.get("/api/v1/opportunities/1/applications", headers=bakery).json()
    assert listing["items"][0]["applicant"]["has_resume"] is False
    response = client.get(f"/api/v1/applications/{application_id}/resume", headers=bakery)
    assert _error(response, 404) == "RESUME_NOT_FOUND"


def test_nobody_else_can_open_it(
    client: TestClient,
    contributor: dict[str, str],
    jordan: dict[str, str],
    events_org: dict[str, str],
) -> None:
    _upload(client, contributor)
    application_id = _apply(client, contributor)
    url = f"/api/v1/applications/{application_id}/resume"

    assert _error(client.get(url, headers=events_org), 404) == "APPLICATION_NOT_FOUND"
    assert _error(client.get(url, headers=jordan), 404) == "APPLICATION_NOT_FOUND"
    assert _error(client.get(url), 401) == "AUTH_REQUIRED"


def test_contributor_without_a_profile_cannot_upload(
    client: TestClient, sam: dict[str, str], seeded_db: pymysql.Connection, storage_dir: Path
) -> None:
    with seeded_db.cursor() as cur:  # sign-up always creates one; remove it directly
        cur.execute("DELETE FROM contributor_profile WHERE user_id = 7")

    assert _error(_upload(client, sam), 409) == "CONTRIBUTOR_PROFILE_REQUIRED"
    assert _stored_files(storage_dir) == []  # checked before anything is written
