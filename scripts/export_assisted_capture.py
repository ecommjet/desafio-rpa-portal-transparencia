"""Extrai snapshots locais de uma sessão assistida, sem acessar o portal."""
import argparse
import asyncio
import base64
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if (ROOT / ".browsers").is_dir():
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".browsers"))

from playwright.async_api import async_playwright
from app.extraction import person_fields, snapshot
from app.models import Benefit, Evidence, Person, Result
from app.storage import save_json


async def main():
    parser = argparse.ArgumentParser(description="Gerar JSON de validação a partir de capturas assistidas locais")
    parser.add_argument("--panorama", type=Path, required=True, help="Prefixo estado-NNN, sem extensão")
    parser.add_argument("--details", type=Path, required=True)
    parser.add_argument("--programa", required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/resultado-assistido.json"))
    args = parser.parse_args()
    result = Result(modo_execucao="assistido", etapa="concluida")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            context = await browser.new_context(java_script_enabled=False)
            await context.route("**/*", lambda route: route.abort())
            page = await context.new_page()
            captures = []
            for prefix in (args.panorama, args.details):
                metadata = json.loads(prefix.with_suffix(".json").read_text())
                await page.set_content(prefix.with_suffix(".html").read_text(), wait_until="domcontentloaded")
                capture = await snapshot(page)
                capture.url = metadata["url"]
                captures.append(capture)
            panorama, details = captures
            result.pessoa = Person(panorama=panorama, **person_fields(panorama.texto, panorama.campos))
            if not result.pessoa.nome or not details.tabelas:
                raise ValueError("Captura sem identificação ou sem tabelas de detalhes")
            result.evidencia = Evidence(base64=base64.b64encode(args.panorama.with_suffix(".png").read_bytes()).decode())
            # Este utilitário não navega na paginação: não presume completude.
            result.beneficios = [Benefit(programa=args.programa, url=details.url, paginas=[details], completo=False,
                                         erro="Captura assistida de uma página; completude da paginação não verificada por este utilitário")]
            result.status = "parcial"
            result.codigo = "VALIDACAO_ASSISTIDA"
            result.mensagem = "Resultado extraído de capturas locais da sessão assistida; não comprova execução autônoma"
            save_json(args.output, result.model_dump(mode="json"))
            print(json.dumps({"arquivo": str(args.output), "modo": result.modo_execucao, "status": result.status,
                              "tabelas": len(details.tabelas), "linhas": sum(map(len, details.tabelas))}, ensure_ascii=False))
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
