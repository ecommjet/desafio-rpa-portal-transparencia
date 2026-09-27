"""Diagnóstico explícito do acesso inicial, sem enviar dados de uma pessoa."""
import asyncio
import argparse
import json
import re
from time import monotonic
from pathlib import Path

from playwright.async_api import Error, async_playwright, expect


async def main():
    parser = argparse.ArgumentParser(description="Inspecionar o acesso normal ao portal, sem realizar consulta")
    parser.add_argument("--headed", action="store_true", help="Exibir a janela do navegador")
    parser.add_argument("--home", action="store_true", help="Começar na página inicial")
    parser.add_argument("--people", action="store_true", help="Clicar em Pessoas Físicas e Jurídicas na página inicial")
    parser.add_argument("--search", action="store_true", help="Seguir também o cartão Busca de Pessoa Física")
    parser.add_argument("--term", help="Termo de teste para preencher no formulário real")
    parser.add_argument("--first", action="store_true", help="Abrir o primeiro resultado após a busca")
    parser.add_argument("--channel", choices=["chrome", "chromium"], default="chromium")
    parser.add_argument("--observe-seconds", type=int, default=12)
    parser.add_argument("--output", type=Path, default=Path("outputs/diagnostico"))
    args = parser.parse_args()
    if args.headed:
        parser.error("Para diagnóstico visível sem fechar a sessão, use: python scripts/portal_session.py")
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    report = {"eventos": [], "headed": args.headed, "channel": args.channel}
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=not args.headed, channel=args.channel)
        try:
            page = await browser.new_page(locale="pt-BR")
            page.on("response", lambda response: report["eventos"].append({
                "status": response.status, "url": response.url.split("?")[0]
            }) if response.request.resource_type == "document" else None)
            try:
                url = "https://portaldatransparencia.gov.br/" if args.home or args.people or args.search else "https://portaldatransparencia.gov.br/pessoa-fisica/busca/lista"
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Error as exc:
                report["erro_navegacao"] = str(exc).split("Call log:")[0]
            # Observa apenas o carregamento normal. Não clica ou resolve desafios.
            deadline = monotonic() + max(0, min(args.observe_seconds, 45))
            while monotonic() < deadline:
                await asyncio.sleep(0.5)
            if args.people or args.search:
                reject = page.get_by_role("button", name=re.compile("Rejeitar cookies opcionais", re.I))
                if await reject.count() and await reject.first.is_visible():
                    await reject.first.click()
                try:
                    link = page.locator('a[href="/pessoa/visao-geral"]').first
                    await link.focus()
                    await link.press("Enter")
                    await page.wait_for_load_state("domcontentloaded")
                    await asyncio.sleep(2)
                    if args.search:
                        if await reject.count() and await reject.first.is_visible():
                            await reject.first.click()
                        await page.get_by_role("link", name=re.compile(r"^Busca de Pessoa Física")).click()
                        await page.wait_for_load_state("domcontentloaded")
                        await asyncio.sleep(2)
                        if args.term:
                            await page.locator("#termo").fill(args.term)
                            await page.locator("#termo").press("Enter")
                            await expect(page.locator("#infoTermo strong")).to_have_text(args.term, timeout=30000)
                            await page.locator(".loading-busca").wait_for(state="hidden", timeout=30000)
                            if args.first and await page.locator("#resultados a.link-busca-nome").count():
                                await page.locator("#resultados a.link-busca-nome").first.click()
                                await page.wait_for_load_state("domcontentloaded")
                                await asyncio.sleep(2)
                except Error as exc:
                    report["erro_interacao"] = str(exc).split("Call log:")[0]
            report["url"] = page.url
            report["titulo"] = await page.title()
            report["texto"] = (await page.locator("body").inner_text(timeout=5000))[:15000]
            report["inputs"] = await page.locator("input").evaluate_all("els => els.map(el => ({id: el.id, name: el.name, placeholder: el.placeholder, type: el.type}))")
            report["links"] = await page.locator("a[href]").evaluate_all("els => els.map(el => ({texto: el.innerText.trim(), href: el.getAttribute('href')})).filter(a => a.texto)")
            await page.screenshot(path=str(output / "pagina.png"), full_page=True, timeout=10000)
            (output / "pagina.html").write_text(await page.content(), encoding="utf-8")
        finally:
            await browser.close()
    (output / "relatorio.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {**report, "texto": report.get("texto", "")[:10000], "links": [a for a in report.get("links", []) if '/pessoa' in a['href'] or 'Buscar' in a['texto'] or 'Consultar' in a['texto']]}
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
