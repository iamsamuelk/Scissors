import pytest
from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch, MagicMock
from models import URL, Click

client = TestClient(app)

# Mocking the database session
@pytest.fixture
def mock_db_session():
    with patch('database.SessionLocal') as mock:
        mock.return_value = MagicMock()
        yield mock
    
# Test for GET /all_urls
def test_read_all_by_user(mock_db_session):
    mock_db_session.return_value.query.return_value.all.return_value = [
        URL(id=1, key="testkey", target_url="https://example.com"),
        URL(id=2, key="test2key", target_url="https://example2.com")
    ]
    response = client.get("/scissors")
    assert response.status_code == 200
    assert len(response.json()) == 2

# Test for POST /url (creating a URL)
def test_create_url(mock_db_session):
    test_url = {"target_url": "https://example.com", "custom_key": "mycustomkey"}
    response = client.post("/short_url", json=test_url)
    assert response.status_code == 201
    assert response.json()["url"] == "http://localhost/mycustomkey"

# Test for GET /{url_key} (redirecting to target URL)
def test_redirect_to_target_url(mock_db_session):
    mock_db_url = URL(id=1, key="testkey", target_url="https://example.com")
    mock_db_session.return_value.query.return_value.get.return_value = mock_db_url
    response = client.get("/testkey")
    assert response.status_code == 307  # Check for redirect status code
    assert response.headers["location"] == "https://example.com"

# Test for GET /admin/{secret_key} (getting URL info)
def test_get_url_info(mock_db_session):
    mock_db_url = URL(id=1, secret_key="testsecret", target_url="https://example.com")
    mock_db_session.return_value.query.return_value.get.return_value = mock_db_url
    response = client.get("/admin/testsecret")
    assert response.status_code == 200
    assert response.json()["target_url"] == "https://example.com"

# Test for PUT /admin/deactivate/{secret_key} (deactivating a URL)
def test_deactivate_url(mock_db_session):
    mock_db_url = URL(id=1, secret_key="testsecret", target_url="https://example.com")
    mock_db_session.return_value.query.return_value.get.return_value = mock_db_url
    response = client.put("/admin/deactivate/testsecret")
    assert response.status_code == 200
    assert "Successfully deactivated shortened URL" in response.json()["detail"]

# Test for PUT /admin/reactivate/{secret_key} (reactivating a URL)
def test_reactivate_url(mock_db_session):
    mock_db_url = URL(id=1, secret_key="testsecret", target_url="https://example.com")
    mock_db_session.return_value.query.return_value.get.return_value = mock_db_url
    response = client.put("/admin/reactivate/testsecret")
    assert response.status_code == 200
    assert "Successfully reactivated shortened URL" in response.json()["detail"]
