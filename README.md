# Observa — RPA do Portal da Transparência

Solução para o [desafio 01 da mostQI](https://github.com/mostqi/desafios-fullstack-python/tree/main/desafio-01): robô Python + Playwright, API FastAPI/Swagger, interface web e bônus com **n8n + Google Drive + Sheets**.

**Estado da validação:** os testes de integração usam páginas sintéticas e navegador real. Uma sessão real assistida permitiu validar a navegação, o panorama, um benefício e a estrutura atual do portal. O acesso headless ainda recebe verificação humana (AWS WAF/CAPTCHA) nesta rede. O robô identifica o bloqueio e devolve erro explícito, sem contornar CAPTCHA nem inventar resultados. A coleta autônoma e os demais cenários ainda precisam de homologação em um ambiente no qual o portal libere a navegação.

## Funcionalidades

- Consulta por nome, CPF ou NIS e filtro opcional de beneficiário de programa social.
- Seleção do primeiro resultado de pessoa física na ordem devolvida pelo portal.
- Extração de nome, CPF mascarado, NIS e localidade quando disponíveis; preservação do texto, campos e tabelas do panorama.
- Screenshot do panorama em PNG codificado em Base64.
- Navegação pelos detalhes de Auxílio Brasil, Auxílio Emergencial e Bolsa Família, com paginação e indicação de coleta parcial.
- Chromium headless e contexto isolado por consulta; limite configurável de concorrência.
- Prazo global incluindo fila, fechamento do contexto e erros estruturados.
- API com OpenAPI, chave opcional e resposta sem cache.

- Interface responsiva para consultar, visualizar captura, baixar JSON e exportar para o Google.
- OAuth Google, upload com nome padronizado e registro no Sheets, com retomada e controle de duplicações.
- Workflow n8n importável e workflow CLI com checkpoint.
- Configuração Docker, Render e CI GitHub Actions.

**Online:** a API está publicada em [portfolio.ecommjet.com.br](https://portfolio.ecommjet.com.br), protegida por chave e executando em Docker/Easypanel na VPS. O workflow foi importado no n8n self-hosted e a chamada autenticada foi validada. Resta autorizar a conta Google para testar o arquivamento real no Drive/Sheets. A integração Google já é coberta por testes com serviços simulados.

## Testar agora neste projeto

Produção: [interface](https://portfolio.ecommjet.com.br), [Swagger](https://portfolio.ecommjet.com.br/docs) e [health check](https://portfolio.ecommjet.com.br/health). Os endpoints de consulta e arquivamento exigem `X-API-Key`; a chave está configurada de forma privada no servidor e na credencial Header Auth do n8n.

O ambiente e o Chromium já foram instalados nesta pasta:

```bash
bash scripts/start.sh
```

Abra **[a interface](http://127.0.0.1:8000)**. Informe nome/CPF/NIS e clique em **Consultar portal**. O resultado permite baixar JSON, abrir a captura e, após conectar o Google, salvar no Drive/Sheets. `PORTAL_BLOQUEADO` indica impedimento do portal, não falha de instalação.

Para concluir a autorização do bônus ou importar uma nova cópia do workflow, siga **[Google + n8n](docs/bonus-google.md)**. O artefato está em **[workflows/n8n-consulta-google.json](workflows/n8n-consulta-google.json)**. Os detalhes da publicação estão em **[deploy](docs/deploy.md)**.

## Executar localmente

Requer Python 3.11 ou superior. Validado localmente com Python 3.14.3 em macOS ARM64.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.browsers"
python -m playwright install chromium
# Copie somente se ainda não tiver um .env configurado:
test -f .env || cp .env.example .env
uvicorn app.api:app --host 127.0.0.1 --port 8000
```

No Linux, instale as dependências de sistema com `python -m playwright install --with-deps chromium`. Execute os comandos a partir da raiz do projeto. A variável `PLAYWRIGHT_BROWSERS_PATH` precisa ser exportada para o processo do Playwright; apenas escrevê-la no `.env` não configura o driver.

Abra [a interface](http://127.0.0.1:8000) ou [Swagger](http://127.0.0.1:8000/docs). O contrato JSON também está em `/openapi.json` e a verificação de processo em `/health` (não testa a disponibilidade do portal).

```bash
curl -X POST http://127.0.0.1:8000/consultas \
  -H 'Content-Type: application/json' \
  -d '{"termo":"NOME PARA CONSULTA","beneficiario_programa_social":true}'
```

Se `API_KEY` estiver configurada, envie `X-API-Key` ou use o botão **Authorize** no Swagger. A implantação pública usa HTTPS, chave obrigatória e concorrência 1. O limite de concorrência é por processo; múltiplos workers multiplicam a quantidade de navegadores.

### Linha de comando

```bash
python -m app.cli 'NOME PARA CONSULTA' --social --output outputs/consulta.json
```

O comando também fica disponível como `transparencia` após `pip install -e .`. Saída 0 indica coleta completa; saída 2 indica erro ou coleta parcial. `/consultas` não persiste o resultado no servidor; o arquivamento Google usa checkpoints locais. O workflow CLI salva entrada, resultado e recibo em `outputs/runs/` para permitir retomada.

### Docker

```bash
docker compose up --build
```

A porta é publicada apenas em `127.0.0.1`. Não é necessário instalar Python ou Chromium no host. O build necessita de acesso à internet. A imagem Docker foi validada na implantação da VPS.

## Contrato do resultado

| Campo | Conteúdo |
|---|---|
| `consulta_id` | UUID único por execução |
| `consultado_em` | Data/hora UTC no início da consulta |
| `status` | `sucesso`, `parcial` ou `erro` |
| `codigo`, `mensagem` | Diagnóstico quando aplicável |
| `pessoa` | Identificação disponível e snapshot do panorama |
| `beneficios` | Programa, URL, snapshots das páginas, completude e erro |
| `evidencia` | `mime_type` e `base64` da captura do panorama |
| `etapa`, `duracao_ms` | Etapa alcançada e duração da execução |
| `diagnostico` | URL, título e captura da falha, quando possível; separado da evidência do panorama |

Os snapshots guardam `url`, `texto`, `campos` e `tabelas`. Valores monetários e datas são preservados como exibidos, sem conversão ambígua. Campos ausentes ficam `null`. O CPF mascarado não é reconstruído. O termo de busca não é ecoado no resultado de sucesso.

HTTP 200 significa que houve coleta completa **ou parcial**: confira sempre `status` e `beneficios[].completo`. HTTP 404 indica ausência de resultado, 422 entrada inválida, 401 chave inválida, 502 bloqueio/falha do portal e 504 prazo excedido.

### Verificação humana do portal

O enunciado exige execução autônoma em modo headless, mas não exige implementar um resolvedor de CAPTCHA. Se o AWS WAF apresentar uma verificação humana, o robô encerra a consulta com `status=erro` e `codigo=PORTAL_BLOQUEADO`, incluindo uma captura de diagnóstico. A documentação da entrega deve registrar essa limitação. Uma sessão em que uma pessoa resolveu o desafio pode ser usada para validar seletores e dados, mas deve ser identificada como `modo_execucao=assistido` e não substitui o teste headless.

Para CPF/NIS não encontrado, a mensagem é `Não foi possível retornar os dados no tempo de resposta solicitado`, conforme o enunciado. Para nome não encontrado, é `Foram encontrados 0 resultados para o termo …`. O código `NAO_ENCONTRADO` distingue esses casos de um timeout efetivo.

## Configuração

| Variável | Padrão | Efeito |
|---|---|---|
| `HEADLESS` | `true` | Executar sem janela |
| `MAX_CONCURRENT` | `3` | Contextos simultâneos por processo |
| `QUERY_TIMEOUT_SECONDS` | `120` | Prazo total, incluindo fila |
| `NAVIGATION_TIMEOUT_MS` | `30000` | Prazo das operações Playwright |
| `WAF_WAIT_MS` | `8000` | Espera pela verificação automática normal do portal |
| `MAX_DETAIL_PAGES` | `100` | Limite por link de benefício; excedê-lo gera parcial |
| `API_KEY` | vazia | Chave do cabeçalho `X-API-Key` |
| `REQUIRE_API_KEY` | `false` | Impede iniciar sem chave; habilitar em hospedagem |
| `PLAYWRIGHT_BROWSERS_PATH` | configuração Playwright | Diretório dos navegadores; exportar no shell |

## Testes

```bash
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.browsers"
python -m pytest -q
```

Os testes interceptam todas as requisições do navegador e fornecem HTML fictício; não enviam nomes/CPFs ao governo. Cobrem validação, autenticação, busca por nome/documento, filtro social, primeiro resultado, os três benefícios, duas páginas, PNG/Base64, ausência de resultados, CAPTCHA, detalhes parciais, limite de paginação, timeout e isolamento de duas consultas simultâneas.

Também testam WAF com página vazia, a interface desktop/mobile, download, exportação, recuperação de falhas após gravação no Google, conflito de conteúdo e retomada do workflow. Os testes do Google não fazem chamadas reais.

Uma consulta real assistida, autorizada pelo titular, permitiu abrir o panorama e os detalhes de Auxílio Emergencial. A extração das capturas locais gerou `outputs/resultado-assistido.json`, com uma tabela de nove registros e a imagem do panorama. Esse resultado declara `modo_execucao=assistido` e `status=parcial`: não comprova execução autônoma nem valida todos os programas e a paginação. As capturas e os dados pessoais ficam em `outputs/`, excluído do versionamento.

Última execução local: **36 testes passaram em 13,00 segundos**, incluindo regressões do layout observado no portal e a estrutura real do controle de paginação.

Para verificar a estrutura e os scripts do workflow n8n (requer Node.js):

```bash
node scripts/verify_workflow.cjs
```

Para diagnosticar somente o acesso inicial real, sem buscar uma pessoa:

```bash
PLAYWRIGHT_BROWSERS_PATH=.browsers .venv/bin/python scripts/diagnose_portal.py
```

O diagnóstico grava HTML, screenshot e relatório em `outputs/diagnostico/`. Não compartilhe esses arquivos sem revisar seu conteúdo.

### Homologação pendente

Para inspecionar o portal **com janela aberta e sem encerramento automático**, use:

```bash
.venv/bin/python scripts/portal_session.py
```

Esse é um diagnóstico **assistido**. Se necessário, faça a verificação humana na própria janela. O navegador permanece aberto entre os comandos e após erros. No terminal, envie `{"acao":"estado"}`, `{"acao":"pessoas"}`, `{"acao":"busca"}` e `{"acao":"consultar","termo":"TESTE INEXISTENTE MOSTQI XYZ"}` para avançar. Encerre explicitamente com `{"acao":"sair"}` ou Ctrl+C. A sessão assistida não comprova o requisito headless/autônomo.

1. Em uma rede com acesso normal ao portal, executar uma consulta autorizada e verificar a busca, o primeiro registro e o panorama.
2. Conferir os seletores em `app/robot.py` e a identificação dos links em `app/extraction.py` contra o DOM atual; as páginas sintéticas não garantem compatibilidade com ele.
3. Usar um registro que tenha cada um dos três programas e comparar todos os detalhes e a paginação com a navegação manual.
4. Repetir os cinco cenários do enunciado e duas consultas simultâneas, verificando também o JSON e a imagem.
5. Se houver CAPTCHA, registrar `PORTAL_BLOQUEADO`; isso é um impedimento externo e não comprova sucesso funcional.

## Organização e decisões

`app/robot.py` gerencia navegador e fluxo; `extraction.py` concentra a leitura do DOM; `models.py` define o contrato; `api.py` e `cli.py` são as entradas. `google_export.py` arquiva no Google, `google_setup.py` configura OAuth e `workflow.py` oferece execução retomável via API. `app/static/` contém a interface e `workflows/` o n8n. Consulte [o relatório técnico](docs/relatorio-tecnico.md).

Resultados podem conter dados pessoais públicos e screenshots. `outputs/`, `secrets/` e `.env` estão fora do versionamento. A aplicação não registra respostas nos logs. Configure também a retenção de execuções do n8n, que pode armazenar entradas/saídas dos nós.
