from fastapi.testclient import TestClient
from src.database import initialize_database
from src.web import app


def setup_module(): initialize_database()


def test_health_and_customers():
    client=TestClient(app)
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/customers").status_code == 200
