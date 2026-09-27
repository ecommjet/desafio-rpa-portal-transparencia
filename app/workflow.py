"""Workflow CLI: chama a API, salva checkpoint e aciona o arquivo Google via API."""
import argparse
import json
import os
from pathlib import Path
from uuid import uuid4

import httpx
from filelock import FileLock

from app.models import Query, Result
from app.storage import save_json


def execute(query: Query, directory: Path, client: httpx.Client):
    directory.mkdir(parents=True, exist_ok=True)
    with FileLock(str(directory / "workflow.lock"), timeout=1):
        query_path, result_path = directory / "entrada.json", directory / "resultado.json"
        if query_path.exists() and json.loads(query_path.read_text()) != query.model_dump():
            raise ValueError("Este run-id já foi usado com outra consulta")
        save_json(query_path, query.model_dump())
        if result_path.exists():
            result = Result.model_validate_json(result_path.read_text())
        else:
            response = client.post("/consultas", json=query.model_dump())
            # A API retorna Result também em 404/502/504. Arquivamos o erro como
            # erro, sem confundi-lo com coleta bem-sucedida.
            try:
                data = response.json()
            except ValueError:
                response.raise_for_status()
                raise
            if "consulta_id" not in data:
                response.raise_for_status()
                raise ValueError("A API não devolveu um resultado de consulta")
            result = Result.model_validate(data)
            save_json(result_path, result.model_dump(mode="json"))
        response = client.post("/integracoes/google/arquivar", json=result.model_dump(mode="json"))
        response.raise_for_status()
        receipt = response.json()
        save_json(directory / "recibo.json", receipt)
        return {"status_consulta": result.status, **receipt}


def main():
    parser = argparse.ArgumentParser(description="Executar consulta via API e arquivar no Google")
    parser.add_argument("termo")
    parser.add_argument("--social", action="store_true")
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--run-id", default=None, help="Reutilize para retomar após falha no Google")
    args = parser.parse_args()
    run_id = args.run_id or str(uuid4())
    if not run_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in run_id):
        parser.error("run-id deve conter somente letras, números, hífen ou underscore")
    print(f"Execução: {run_id}")
    api = httpx.URL(args.api)
    if api.scheme != "https" and not (api.scheme == "http" and api.host in ("localhost", "127.0.0.1", "::1")):
        parser.error("Use HTTPS para APIs remotas")
    from app.config import Settings
    settings = Settings()
    headers = {"X-API-Key": settings.api_key.get_secret_value()} if settings.api_key else {}
    try:
        with httpx.Client(base_url=args.api, headers=headers, timeout=300, follow_redirects=False) as client:
            receipt = execute(Query(termo=args.termo, beneficiario_programa_social=args.social), Path("outputs/runs") / run_id, client)
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
    except (httpx.HTTPError, ValueError) as exc:
        parser.exit(2, f"Workflow não concluído ({type(exc).__name__}). Confira a API e o Google; retome usando --run-id {run_id}.\n")


if __name__ == "__main__":
    main()
