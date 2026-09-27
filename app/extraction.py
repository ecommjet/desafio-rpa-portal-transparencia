"""Extração conservadora: preserva texto e cabeçalhos sem inferir dados ausentes."""
import re
import unicodedata
from urllib.parse import urljoin, urlparse

from playwright.async_api import Page

from app.models import Snapshot

ORIGIN = "https://portaldatransparencia.gov.br"
SEARCH_URL = f"{ORIGIN}/pessoa-fisica/busca/lista"


def normalized(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.casefold())
                   if unicodedata.category(c) != "Mn")


def portal_url(href: str, base: str = ORIGIN) -> str | None:
    url = urljoin(base, href)
    parsed = urlparse(url)
    if parsed.scheme == "https" and parsed.netloc == urlparse(ORIGIN).netloc:
        return url
    return None


def person_fields(text: str, fields: dict[str, str]) -> dict[str, str | None]:
    result = {}
    for key in ("nome", "cpf", "nis", "localidade"):
        value = next((v for k, v in fields.items() if normalized(k).strip(" :") == key), None)
        if not value:
            match = re.search(rf"^\s*{key}\s*:?\s*\n?([^\n]+)", text, re.I | re.M)
            value = match.group(1).strip() if match else None
        result[key] = value
    return result


async def snapshot(page: Page) -> Snapshot:
    data = await page.evaluate("""() => {
      const root = document.querySelector('#main-content') || document.querySelector('main, #conteudo') || document.body;
      const fields = {};
      root.querySelectorAll('dt, label, strong').forEach(el => {
        const next = el.nextElementSibling;
        if (next && el.innerText.trim() && next.innerText.trim())
          fields[el.innerText.trim()] = next.innerText.trim();
      });
      const tables = [...root.querySelectorAll('table')].map(table => {
        const heads = [...table.querySelectorAll('thead th')].map(e => e.innerText.replace(/[⇅⇵]/g, '').trim());
        return [...table.querySelectorAll('tbody tr')].map(tr => {
          const row = {};
          [...tr.querySelectorAll('td')].forEach((td, i) => {
            let key = heads[i] || `coluna_${i + 1}`;
            if (key in row) key += `_${i + 1}`;
            row[key] = td.innerText.trim();
          });
          return row;
        }).filter(row => Object.keys(row).length);
      });
      return {texto: root.innerText.trim(), campos: fields, tabelas: tables};
    }""")
    return Snapshot(url=page.url, **data)


async def benefit_links(page: Page) -> list[tuple[str, str]]:
    links = await page.evaluate("""() => [...(document.querySelector('#main-content') || document.querySelector('main, #conteudo') || document.body).querySelectorAll('a[href]')]
      .map(a => {
        let el = a;
        let context = a.innerText;
        for (let i = 0; i < 5 && el.parentElement; i++) {
          el = el.parentElement;
          if (el.querySelectorAll('a[href]').length > 2) break;
          context = el.innerText;
          if (/aux[ií]lio|bolsa fam[ií]lia/i.test(context)) break;
        }
        return {href: a.getAttribute('href'), text: a.innerText, context};
      })""")
    found = []
    seen = set()
    for link in links:
        url = portal_url(link["href"], page.url)
        context = normalized(link["context"] + " " + link["href"])
        for name, tokens in (
            ("Auxílio Brasil", ("auxilio brasil", "auxilio-brasil")),
            ("Auxílio Emergencial", ("auxilio emergencial", "auxilio-emergencial")),
            ("Bolsa Família", ("bolsa familia", "bolsa-familia")),
        ):
            if url and any(t in context for t in tokens) and url != page.url and url not in seen:
                found.append((name, url))
                seen.add(url)
                break
    return found
