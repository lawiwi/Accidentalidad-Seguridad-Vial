import os
import sys
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c

def test_health(client):
    rv = client.get("/health")
    assert rv.status_code == 200
    assert rv.json.get("status") == "healthy"


@pytest.mark.parametrize("path", ["/Etapa6", "/Etapa6/"])
def test_etapa6_legacy_route_redirects_to_conocimiento_oculto(client, path):
    rv = client.get(path)
    assert rv.status_code == 302
    assert rv.headers["Location"] == "/conocimiento-oculto/"
    assert client.get(rv.headers["Location"]).status_code == 200


if __name__ == "__main__":
    os.system("pip install pytest")
    os.system("pytest -q")