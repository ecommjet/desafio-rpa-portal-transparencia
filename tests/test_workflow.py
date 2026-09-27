import httpx
import pytest

from app.models import Query, Result
from app.workflow import execute


def test_retry_uses_saved_result_instead_of_running_robot_again(tmp_path):
    result, calls = Result(), []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/consultas":
            return httpx.Response(502, json=result.model_dump(mode="json"))
        if calls.count("/integracoes/google/arquivar") == 1:
            return httpx.Response(503, json={"codigo": "GOOGLE_NAO_CONFIGURADO"})
        return httpx.Response(200, json={"consulta_id": result.consulta_id, "arquivo_url": "https://drive.google.com/file/d/test/view"})

    with httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            execute(Query(termo="Teste"), tmp_path, client)
        receipt = execute(Query(termo="Teste"), tmp_path, client)
        assert receipt["status_consulta"] == "erro"
        assert calls.count("/consultas") == 1
        assert (tmp_path / "recibo.json").is_file()
        with pytest.raises(ValueError, match="outra consulta"):
            execute(Query(termo="Outro"), tmp_path, client)
