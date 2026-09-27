from fastapi.testclient import TestClient

from app.api import create_app
from app.config import Settings
from app.models import Result
import pytest


class StubRobot:
    def __init__(self, settings):
        pass

    async def start(self):
        pass

    async def close(self):
        pass

    async def query(self, query):
        return Result(codigo="NAO_ENCONTRADO", mensagem="Nenhum registro")


def test_validation_auth_and_status():
    with TestClient(create_app(Settings(api_key="test-key"), StubRobot)) as client:
        assert client.get("/health").status_code == 200
        assert client.post("/consultas", json={"termo": "Teste"}).status_code == 401
        headers = {"X-API-Key": "test-key"}
        assert client.post("/consultas", json={"termo": ""}, headers=headers).status_code == 422
        response = client.post("/consultas", json={"termo": "Teste"}, headers=headers)
        assert response.status_code == 404
        assert response.json()["codigo"] == "NAO_ENCONTRADO"
        assert response.headers["Cache-Control"] == "no-store"
        assert "/consultas" in client.get("/openapi.json").json()["paths"]
        assert client.get("/").status_code == 200
        assert "observa" in client.get("/").text
        assert client.get("/static/app.js").status_code == 200
        assert client.get("/integracoes/google/status", headers=headers).json() == {"configurado": False}
        assert client.post("/integracoes/google/arquivar", json=Result().model_dump(mode="json")).status_code == 401
        response = client.post("/integracoes/google/arquivar", json=Result().model_dump(mode="json"), headers=headers)
        assert response.status_code == 503
        assert response.json()["codigo"] == "GOOGLE_NAO_CONFIGURADO"
        assert client.post("/integracoes/google/arquivar", json={}, headers=headers).status_code == 422


def test_deployment_cannot_start_without_required_key():
    with pytest.raises(RuntimeError, match="API_KEY"):
        with TestClient(create_app(Settings(require_api_key=True, api_key=None), StubRobot)):
            pass
