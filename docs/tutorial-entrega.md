# Tutorial de teste e entrega

Este guia separa o que é obrigatório, o bônus e a interface opcional. O robô obrigatório é o código Python/Playwright: ele acessa e opera o próprio Portal da Transparência.

## 1. O que mostrar na avaliação

1. O Playwright abre `portaldatransparencia.gov.br` em modo headless.
2. O robô preenche nome, CPF ou NIS e o filtro social opcional.
3. O primeiro resultado é aberto e o panorama é coletado.
4. Auxílio Brasil, Auxílio Emergencial e Bolsa Família são percorridos quando encontrados.
5. A resposta contém JSON e screenshot PNG em Base64.
6. Cada consulta usa um contexto isolado e a concorrência é controlada por semáforo.
7. A API está online e documentada por OpenAPI.
8. O n8n chama a API e encaminha o resultado ao exportador Google.

A interface Observa em `/` é um extra. Ela aciona a mesma API e não participa da navegação no portal.

## 2. Preparar o ambiente local

Requisitos: Python 3.11 ou superior e Node.js somente para verificar o artefato n8n.

```bash
git clone https://github.com/ecommjet/desafio-rpa-portal-transparencia.git
cd desafio-rpa-portal-transparencia
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.browsers"
python -m playwright install chromium
test -f .env || cp .env.example .env
```

No Linux, instale também as bibliotecas do navegador:

```bash
python -m playwright install --with-deps chromium
```

## 3. Testar a Parte 1 pela CLI

Use somente dados próprios ou autorizados:

```bash
source .venv/bin/activate
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.browsers"
python -m app.cli 'NOME, CPF OU NIS AUTORIZADO' \
  --output outputs/consulta.json
```

Para o cenário filtrado:

```bash
python -m app.cli 'SOBRENOME AUTORIZADO' \
  --social \
  --output outputs/consulta-social.json
```

Abra o JSON e confira:

- `status`: `sucesso`, `parcial` ou `erro`;
- `pessoa`: identificação e snapshot do panorama;
- `beneficios`: detalhes e páginas de cada programa encontrado;
- `evidencia.base64`: captura do panorama;
- `diagnostico`: captura separada quando o portal bloqueia o acesso.

O processo termina com código 0 somente em coleta completa. Código 2 indica falha ou coleta parcial.

## 4. Testar a API local

Terminal 1:

```bash
bash scripts/start.sh
```

Terminal 2:

```bash
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/consultas \
  -H 'Content-Type: application/json' \
  -d '{"termo":"NOME, CPF OU NIS AUTORIZADO","beneficiario_programa_social":false}' \
  --output resultado.json
```

Swagger local: `http://127.0.0.1:8000/docs`.

## 5. Testar a API online

```bash
curl https://portfolio.ecommjet.com.br/health

curl -X POST https://portfolio.ecommjet.com.br/consultas \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: API_KEY_FORNECIDA_PRIVADAMENTE' \
  -d '{"termo":"NOME, CPF OU NIS AUTORIZADO","beneficiario_programa_social":false}' \
  --output resultado-online.json
```

Nunca publique a chave no Git. Gere uma chave temporária para o avaliador e troque-a depois da avaliação.

Para trocar a chave da implantação, gere um valor forte com `python -c "import secrets; print(secrets.token_urlsafe(32))"`, substitua `API_KEY` nas variáveis privadas do serviço Easypanel e faça o redeploy. Atualize a credencial Header Auth do n8n com o mesmo valor. Teste a nova chave antes de enviá-la por e-mail.

## 6. Executar a suíte e comprovar concorrência

```bash
source .venv/bin/activate
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.browsers"
python -m pytest -q
node scripts/verify_workflow.cjs
```

Teste isolado de simultaneidade:

```bash
python -m pytest -q tests/test_robot.py::test_concurrent_contexts_and_ids_are_isolated
```

Esse teste executa duas consultas ao mesmo tempo com páginas controladas, contextos separados e resultados independentes. A VPS usa concorrência 1 por memória; para uma demonstração real simultânea, aumente `MAX_CONCURRENT` para 2 somente depois de conferir RAM disponível e reinicie o serviço.

## 7. Entender o CAPTCHA/WAF

O desafio exige headless, mas não exige resolver CAPTCHA. Nesta VPS, o portal pode apresentar AWS WAF antes da busca. Nessa situação o resultado correto é:

```json
{
  "status": "erro",
  "codigo": "PORTAL_BLOQUEADO",
  "mensagem": "O portal apresentou um desafio antirrobô (AWS WAF/CAPTCHA)"
}
```

O robô inclui uma captura em `diagnostico`. Ele não tenta burlar o mecanismo e não inventa dados. Em uma rede liberada, o fluxo segue automaticamente. Para inspecionar manualmente o portal sem fechar a janela, use `python scripts/portal_session.py`; esse modo é apenas diagnóstico assistido e deve ser identificado como tal.

## 8. Concluir e testar o bônus

Situação atual:

- API pública: funcionando;
- chamada autenticada do n8n: funcionando;
- workflow: importado e salvo;
- exportador Drive/Sheets: implementado e testado com serviços simulados;
- OAuth e gravação real na conta Google: pendentes.

Para concluir:

1. No Google Cloud Console, crie um projeto.
2. Ative Google Drive API e Google Sheets API.
3. Configure a tela de consentimento e adicione seu e-mail como usuário de teste.
4. Crie um OAuth Client do tipo **Desktop app**.
5. Baixe o JSON para `secrets/client.json`.
6. Execute `python -m app.google_setup` e autorize no navegador.
7. Copie `GOOGLE_DRIVE_FOLDER_ID`, `GOOGLE_SPREADSHEET_ID` e o token para as variáveis privadas do serviço na VPS.
8. Reinicie o serviço.
9. No n8n, execute **Observa | RPA → Google Drive + Sheets**.
10. Confirme o JSON no Drive e a linha no Sheets com o mesmo `consulta_id` e o link do arquivo.
11. Reexecute somente o arquivamento do mesmo resultado e confirme que não houve duplicação.

Os detalhes e as variáveis estão em [bonus-google.md](bonus-google.md). Nunca envie `client.json`, token Google ou `.env` ao GitHub.

## 9. Checklist antes do envio

- [ ] Repositório público abre sem login.
- [ ] `https://portfolio.ecommjet.com.br/health` responde.
- [ ] Swagger abre por HTTPS.
- [ ] Chave temporária do avaliador foi testada.
- [ ] `python -m pytest -q` passa.
- [ ] `node scripts/verify_workflow.cjs` passa.
- [ ] Nenhum CPF, token, `.env` ou arquivo de `outputs/` está versionado.
- [ ] OAuth Google concluído ou pendência declarada honestamente.
- [ ] Links do Drive e Sheets conferidos, se o OAuth foi concluído.

## 10. Enviar o desafio

O repositório oficial do desafio instrui enviar a solução para `rh@most.com.br`. Modelo:

> **Assunto:** Desafio Full Stack Python/RPA — Alyson Castilho
>
> Olá, pessoal da mostQI.
>
> Segue minha entrega do desafio de RPA e hiperautomação:
>
> - Código-fonte: https://github.com/ecommjet/desafio-rpa-portal-transparencia
> - API online: https://portfolio.ecommjet.com.br
> - Swagger: https://portfolio.ecommjet.com.br/docs
> - Chave temporária da API: `[INFORMAR AQUI, SOMENTE NO E-MAIL]`
>
> Implementei o robô em Python com Playwright assíncrono, contextos isolados, captura Base64, coleta dos benefícios e API FastAPI. Escolhi n8n para o bônus, integrado a um exportador com OAuth 2.0 para Google Drive e Sheets, retomada e prevenção de duplicações.
>
> O Portal da Transparência pode apresentar AWS WAF/CAPTCHA ao acesso headless da VPS. O robô detecta esse bloqueio, devolve `PORTAL_BLOQUEADO` e inclui evidência de diagnóstico, sem tentar contornar a proteção. A suíte automatizada possui 36 testes.
>
> Situação do bônus Google: `[HOMOLOGADO DE PONTA A PONTA / CÓDIGO PRONTO, AGUARDANDO AUTORIZAÇÃO OAUTH]`.
>
> Fico à disposição para a apresentação técnica.
>
> Atenciosamente,  
> Alyson Castilho

Revise nome, situação do Google e chave antes de enviar. Não coloque CPF no e-mail.

## 11. Roteiro curto para apresentação

1. Explique a arquitetura: entrada → Playwright → panorama/benefícios → JSON/Base64 → API → n8n → Drive/Sheets.
2. Mostre `app/robot.py`, `app/extraction.py` e o contrato no Swagger.
3. Rode a suíte e o teste isolado de concorrência.
4. Faça uma consulta autorizada pela CLI ou API.
5. Mostre a diferença entre `sucesso`, `parcial` e `PORTAL_BLOQUEADO`.
6. Execute o n8n e confira o mesmo UUID no JSON do Drive e na linha do Sheets.
7. Reenvie o arquivamento para demonstrar que não duplica registros.
