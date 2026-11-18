"""Case-catalog coverage for the proposal-aligned contributor resume workflow."""

from pathlib import Path

import pytest

from .conftest import current_parameters, expect

RESUME_URL = "/api/v1/contributors/me/resume"
APPLICATIONS_URL = "/api/v1/applications"
OPPORTUNITIES_URL = "/api/v1/opportunities"
PDF = b"%PDF-1.4\n% GROW8 QA resume\n" + b"0" * 2048 + b"\n%%EOF\n"


def _upload(api, headers, content: bytes = PDF, name: str = "Contributor CV.pdf",
            content_type: str = "application/pdf"):
    return api.put(
        RESUME_URL,
        files={"file": (name, content, content_type)},
        headers=headers,
    )


def _stored_files(storage_dir: Path) -> list[Path]:
    return sorted(path for path in storage_dir.rglob("*") if path.is_file())


def _error(response, status: int, code: str):
    expect(response, status, code)


def _apply(api, contributor, opportunity_id: int = 1) -> int:
    body = expect(api.post(
        f"{OPPORTUNITIES_URL}/{opportunity_id}/applications",
        json={},
        headers=contributor,
    ), 201)
    return body["application_id"]


@pytest.mark.parametrize("case_id", current_parameters("CUR-RESUPLOAD-"))
def test_upload_resume(
    case_id, api, contributor, bakery, storage_dir, monkeypatch,
):
    if case_id.endswith("001"):
        response = expect(_upload(api, contributor), 200)
        assert response == {
            "file_name": "Contributor CV.pdf",
            "content_type": "application/pdf",
            "size_bytes": len(PDF),
            "uploaded_at": "2026-10-16T12:00:00Z",
        }
        assert len(_stored_files(storage_dir)) == 1
    elif case_id.endswith("002"):
        expect(_upload(api, contributor), 200)
        first = _stored_files(storage_dir)[0]
        replacement = PDF + b"% version 2\n"
        response = expect(_upload(
            api, contributor, replacement, "CV v2.pdf",
        ), 200)
        assert response["file_name"] == "CV v2.pdf"
        files = _stored_files(storage_dir)
        assert len(files) == 1 and files[0] != first
        assert api.get(f"{RESUME_URL}/file", headers=contributor).content == replacement
    elif case_id.endswith("003"):
        fake_pdf = _upload(
            api, contributor, b"PK\x03\x04 not a PDF", "cv.pdf", "application/pdf",
        )
        _error(fake_pdf, 415, "UNSUPPORTED_FILE_TYPE")
        assert _stored_files(storage_dir) == []
    elif case_id.endswith("004"):
        _error(_upload(api, contributor, b""), 422, "EMPTY_FILE")
        _error(api.put(
            RESUME_URL,
            data={"not_file": "x"},
            headers=contributor,
        ), 422, "VALIDATION_ERROR")
        assert _stored_files(storage_dir) == []
    elif case_id.endswith("005"):
        too_large = b"%PDF-" + b"0" * (10 * 1024 * 1024 + 70 * 1024)
        _error(_upload(api, contributor, too_large), 413, "RESUME_TOO_LARGE")
        assert _stored_files(storage_dir) == []
        monkeypatch.setattr("app.services.resume_service.MAX_BYTES", 1000)
        _error(_upload(api, contributor), 413, "RESUME_TOO_LARGE")
        assert _stored_files(storage_dir) == []
    elif case_id.endswith("006"):
        _error(_upload(api, bakery), 403, "ROLE_FORBIDDEN")
        _error(api.put(
            RESUME_URL, files={"file": ("cv.pdf", PDF, "application/pdf")},
        ), 401, "AUTH_REQUIRED")
    elif case_id.endswith("007"):
        response = expect(_upload(
            api, contributor, name="../../secret/Résumé",
        ), 200)
        assert response["file_name"] == "Résumé.pdf"
        disposition = api.get(
            f"{RESUME_URL}/file", headers=contributor,
        ).headers["content-disposition"]
        assert "filename*=UTF-8''R%C3%A9sum%C3%A9.pdf" in disposition
        assert 'filename="Resume.pdf"' in disposition
    else:
        raise AssertionError(f"Unknown resume-upload case: {case_id}")


@pytest.mark.parametrize("case_id", current_parameters("CUR-RESMETA-"))
def test_get_resume_metadata(case_id, api, contributor, bakery):
    if case_id.endswith("001"):
        uploaded = expect(_upload(api, contributor), 200)
        assert expect(api.get(RESUME_URL, headers=contributor), 200) == uploaded
    elif case_id.endswith("002"):
        _error(api.get(RESUME_URL, headers=contributor), 404, "RESUME_NOT_FOUND")
        _error(api.get(RESUME_URL), 401, "AUTH_REQUIRED")
        _error(api.get(RESUME_URL, headers=bakery), 403, "ROLE_FORBIDDEN")
    else:
        raise AssertionError(f"Unknown resume-metadata case: {case_id}")


@pytest.mark.parametrize("case_id", current_parameters("CUR-RESDOWNLOAD-"))
def test_download_own_resume(case_id, api, contributor, bakery):
    if case_id.endswith("001"):
        expect(_upload(api, contributor), 200)
        download = api.get(f"{RESUME_URL}/file", headers=contributor)
        assert download.status_code == 200, download.text
        assert download.content == PDF
        assert download.headers["content-type"] == "application/pdf"
        assert download.headers["x-content-type-options"] == "nosniff"
        assert download.headers["cache-control"] == "private, no-store"
        assert download.headers["content-disposition"].startswith(
            'attachment; filename="Contributor CV.pdf"'
        )
    elif case_id.endswith("002"):
        _error(api.get(f"{RESUME_URL}/file", headers=contributor),
               404, "RESUME_NOT_FOUND")
        _error(api.get(f"{RESUME_URL}/file"), 401, "AUTH_REQUIRED")
        _error(api.get(f"{RESUME_URL}/file", headers=bakery),
               403, "ROLE_FORBIDDEN")
    else:
        raise AssertionError(f"Unknown resume-download case: {case_id}")


@pytest.mark.parametrize("case_id", current_parameters("CUR-RESDELETE-"))
def test_delete_resume(case_id, api, contributor, bakery, storage_dir):
    if case_id.endswith("001"):
        expect(_upload(api, contributor), 200)
        assert len(_stored_files(storage_dir)) == 1
        deleted = api.delete(RESUME_URL, headers=contributor)
        assert deleted.status_code == 204, deleted.text
        assert _stored_files(storage_dir) == []
        _error(api.get(RESUME_URL, headers=contributor), 404, "RESUME_NOT_FOUND")
        _error(api.get(f"{RESUME_URL}/file", headers=contributor),
               404, "RESUME_NOT_FOUND")
    elif case_id.endswith("002"):
        _error(api.delete(RESUME_URL, headers=contributor), 404, "RESUME_NOT_FOUND")
        _error(api.delete(RESUME_URL), 401, "AUTH_REQUIRED")
        _error(api.delete(RESUME_URL, headers=bakery), 403, "ROLE_FORBIDDEN")
    else:
        raise AssertionError(f"Unknown resume-deletion case: {case_id}")


@pytest.mark.parametrize("case_id", current_parameters("CUR-APPRES-"))
def test_download_applicant_resume(
    case_id, api, contributor, jordan, bakery, events_org,
):
    if case_id.endswith("001"):
        expect(_upload(api, contributor), 200)
        application_id = _apply(api, contributor)
        application = expect(api.get(
            f"{APPLICATIONS_URL}/{application_id}", headers=bakery,
        ), 200)
        assert application["applicant"]["has_resume"] is True
        download = api.get(
            f"{APPLICATIONS_URL}/{application_id}/resume", headers=bakery,
        )
        assert download.status_code == 200, download.text
        assert download.content == PDF
    elif case_id.endswith("002"):
        application_id = _apply(api, contributor)
        expect(api.post(
            f"{APPLICATIONS_URL}/{application_id}/withdraw", headers=contributor,
        ), 200)
        replacement = PDF + b"% latest version\n"
        expect(_upload(api, contributor, replacement, "Latest CV.pdf"), 200)
        download = api.get(
            f"{APPLICATIONS_URL}/{application_id}/resume", headers=bakery,
        )
        assert download.content == replacement
    elif case_id.endswith("003"):
        expect(_upload(api, contributor), 200)
        application_id = _apply(api, contributor)
        _error(api.get(
            f"{APPLICATIONS_URL}/{application_id}/resume", headers=events_org,
        ), 404, "APPLICATION_NOT_FOUND")
        _error(api.get(
            f"{APPLICATIONS_URL}/{application_id}/resume", headers=jordan,
        ), 404, "APPLICATION_NOT_FOUND")
        _error(api.get(f"{APPLICATIONS_URL}/{application_id}/resume"),
               401, "AUTH_REQUIRED")
    elif case_id.endswith("004"):
        application_id = _apply(api, contributor)
        _error(api.get(
            f"{APPLICATIONS_URL}/{application_id}/resume", headers=bakery,
        ), 404, "RESUME_NOT_FOUND")
        _error(api.get(
            f"{APPLICATIONS_URL}/9999/resume", headers=bakery,
        ), 404, "APPLICATION_NOT_FOUND")
        _error(api.get(
            f"{APPLICATIONS_URL}/0/resume", headers=bakery,
        ), 422, "VALIDATION_ERROR")
    else:
        raise AssertionError(f"Unknown applicant-resume case: {case_id}")
