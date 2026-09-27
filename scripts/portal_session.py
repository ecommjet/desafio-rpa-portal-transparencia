"""Sessão VISÍVEL de diagnóstico assistido. Só fecha por comando explícito.

Não soluciona CAPTCHA. O usuário pode interagir na janela; os comandos seguintes
continuam na mesma página/contexto. Nenhum cookie é exportado para outra sessão.
"""
import asyncio
import json
import os
import re
from pathlib import Path

from playwright.async_api import Error, async_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
if (ROOT / ".browsers").is_dir():
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".browsers"))


async def capture(page, sequence):
    output = ROOT / "outputs/sessao-assistida"
    output.mkdir(parents=True, exist_ok=True)
    state = {"modo": "diagnostico_assistido", "url": page.url, "titulo": await page.title()}
    state["texto"] = (await page.locator("body").inner_text(timeout=5000))[:16000]
    state["inputs"] = await page.locator("input").evaluate_all("els => els.map(el => ({id:el.id,type:el.type,placeholder:el.placeholder}))")
    state["links"] = await page.locator("main a[href], #main-content a[href]").evaluate_all("els => els.map(el => ({texto:el.innerText.trim(),href:el.getAttribute('href')})).filter(el=>el.texto)")
    prefix = output / f"estado-{sequence:03d}"
    prefix.with_suffix(".json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    prefix.with_suffix(".html").write_text(await page.content(), encoding="utf-8")
    try:
        await page.screenshot(path=str(prefix.with_suffix(".png")), full_page=True, timeout=5000)
    except Error:
        state["captura"] = "Não disponível neste instante; a janela continua aberta"
    print(json.dumps(state, ensure_ascii=False), flush=True)


async def dismiss_cookies(page):
    reject = page.get_by_role("button", name=re.compile("Rejeitar cookies opcionais", re.I))
    if await reject.count() and await reject.first.is_visible():
        await reject.first.click()


async def command(page, payload):
    action = payload.get("acao", "estado")
    if action == "pessoas":
        await dismiss_cookies(page)
        link = page.locator('a[href="/pessoa/visao-geral"]').first
        await link.focus()
        await link.press("Enter")
        await page.wait_for_url("**/pessoa/visao-geral", wait_until="domcontentloaded")
    elif action == "busca":
        await dismiss_cookies(page)
        await page.get_by_role("link", name=re.compile(r"^Busca de Pessoa Física")).click()
        await page.locator("#termo").wait_for(state="visible")
    elif action == "consultar":
        await dismiss_cookies(page)
        if payload.get("social"):
            if not await page.locator("#beneficiarioProgramaSocial").is_visible():
                await page.get_by_role("button", name=re.compile("Refine a Busca", re.I)).click()
            await page.get_by_label("Beneficiário de Programa Social", exact=True).check()
        await page.locator("#termo").fill(payload["termo"])
        await page.locator("#termo").press("Enter")
        await expect(page.locator("#infoTermo strong")).to_have_text(payload["termo"], timeout=30000)
        await page.locator(".loading-busca").wait_for(state="hidden", timeout=30000)
    elif action == "primeiro":
        await page.locator("#resultados a.link-busca-nome").first.click()
        await page.wait_for_load_state("domcontentloaded")
    elif action == "estado":
        pass
    else:
        raise ValueError("Use estado, pessoas, busca, consultar, primeiro ou sair")


async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False, channel="chromium")
        page = await browser.new_page(locale="pt-BR", viewport={"width": 1440, "height": 1000})
        page.set_default_timeout(15000)
        print('Sessão assistida aberta. A janela só fecha com {"acao":"sair"}, Ctrl+C ou fechamento manual. A verificação humana é feita pelo usuário.', flush=True)
        try:
            await page.goto("https://portaldatransparencia.gov.br/", wait_until="domcontentloaded", timeout=30000)
        except Error:
            print("O carregamento demorou. A janela permanece aberta; use estado após verificar o portal.", flush=True)
        sequence = 0
        while browser.is_connected() and not page.is_closed():
            print('Aguardando comando JSON (ex.: {"acao":"estado"}).', flush=True)
            line = await asyncio.to_thread(input)
            try:
                payload = json.loads(line)
                if payload.get("acao") == "sair":
                    await browser.close()
                    return
                await command(page, payload)
                sequence += 1
                await capture(page, sequence)
            except (Error, ValueError, KeyError) as exc:
                print(json.dumps({"erro": str(exc).split("Call log:")[0], "janela_mantida_aberta": browser.is_connected()}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
