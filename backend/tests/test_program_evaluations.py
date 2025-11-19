import os
from io import BytesIO

from app.main import app, issue_app_token, program_evaluation_path_for_email


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

    path = program_evaluation_path_for_email(email)
    assert os.path.exists(path)

    get_response = client.get(
        '/program-evaluations',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert get_response.status_code == 200
    assert get_response.mimetype == 'application/pdf'


