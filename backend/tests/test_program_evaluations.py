from io import BytesIO

from app.main import app
from app.services.auth_tokens import issue_app_token
from app.services.program_evaluation_store import program_evaluation_path_for_email


def test_upload_rejects_without_token(tmp_path, monkeypatch):
    client = app.test_client()
    response = client.post('/program-evaluations')
    assert response.status_code == 401


def test_upload_and_retrieve_pdf(tmp_path, monkeypatch):
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret')
    email = 'student@example.com'
    token = issue_app_token(email)

    client = app.test_client()

    data = {
        'file': (BytesIO(b'%PDF-1.4 test file'), 'evaluation.pdf')
    }
    response = client.post(
        '/program-evaluations',
        headers={'Authorization': f'Bearer {token}'},
        data=data,
        content_type='multipart/form-data',
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body.get("hasProgramEvaluation") is True
    assert "parsed" in body

    path = program_evaluation_path_for_email(email)
    assert path.exists()

    get_response = client.get(
        '/program-evaluations',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert get_response.status_code == 200
    assert get_response.mimetype == 'application/pdf'

    parsed_response = client.get(
        '/program-evaluations/parsed',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert parsed_response.status_code == 200
    parsed_body = parsed_response.get_json()
    assert parsed_body["email"] == email
    assert "parsed_data" in parsed_body


def test_get_pdf_via_query_token(tmp_path, monkeypatch):
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret')
    email = 'student@example.com'
    token = issue_app_token(email)

    client = app.test_client()
    data = {
        'file': (BytesIO(b'%PDF-1.4 test file'), 'evaluation.pdf')
    }
    upload_response = client.post(
        '/program-evaluations',
        headers={'Authorization': f'Bearer {token}'},
        data=data,
        content_type='multipart/form-data',
    )
    assert upload_response.status_code == 201

    get_response = client.get(
        f'/program-evaluations?token={token}',
    )

    assert get_response.status_code == 200
    assert get_response.mimetype == 'application/pdf'
