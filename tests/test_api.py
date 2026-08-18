import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_extract_invalid_url():
    response = client.post("/playlist/extract", json={"url": "https://invalid-url.com"})
    assert response.status_code == 400
    assert "Invalid YouTube playlist URL" in response.json()["detail"]


def test_download_playlist_invalid_url():
    response = client.post("/playlist/download", json={"url": "https://invalid-url.com"})
    assert response.status_code == 400


def test_job_status_not_found():
    response = client.get("/playlist/status/non-existent-job-id")
    assert response.status_code == 404
