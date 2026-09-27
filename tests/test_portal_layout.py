"""Regressões do layout observado em 26/09/2026, com dados fictícios."""
import asyncio

from playwright.async_api import async_playwright

from app.config import Settings
from app.extraction import snapshot, person_fields
from app.robot import Robot


def test_current_slug_and_collapsed_panorama():
    async def scenario():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page()
                await page.set_content('''<main>
                    <a href="https://portaldatransparencia.gov.br/busca/pessoa-fisica/123-pessoa-ficticia">Pessoa Fictícia</a>
                    <strong>Nome</strong><span>PESSOA FICTÍCIA</span>
                    <strong>CPF</strong><span>***.000.000-**</span>
                    <div class="br-accordion"><button aria-controls="dados" onclick="document.getElementById('dados').hidden=false">Recebimentos de recursos</button>
                    <div id="dados" hidden><h3>Auxílio Emergencial</h3><table><thead><tr><th>Valor</th></tr></thead><tbody><tr><td>600,00</td></tr></tbody></table></div></div>
                </main>''')
                robot = Robot(Settings())
                assert (await robot._person_link(page)).endswith("/123-pessoa-ficticia")
                assert not await page.locator("#dados").is_visible()
                await robot._expand_panorama(page)
                assert await page.locator("#dados").is_visible()
                data = await snapshot(page)
                assert data.tabelas[0][0] == {"Valor": "600,00"}
                assert person_fields(data.texto, data.campos)["nome"] == "PESSOA FICTÍCIA"
            finally:
                await browser.close()
    asyncio.run(scenario())


def test_cookie_button_uses_accessible_name():
    async def scenario():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page()
                await page.set_content('<button aria-label="Rejeitar cookies" onclick="this.remove()">Rejeitar cookies opcionais</button>')
                await Robot(Settings())._dismiss_cookies(page)
                assert await page.locator("button").count() == 0
            finally:
                await browser.close()
    asyncio.run(scenario())
