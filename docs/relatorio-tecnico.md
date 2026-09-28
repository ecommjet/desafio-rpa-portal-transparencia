# Relatório técnico

## Arquitetura

A solução separa navegação, extração e transporte. `robot.py` controla navegador e ciclo da consulta; `extraction.py` converte o DOM em estruturas previsíveis; `models.py` valida o contrato; `api.py` expõe o caso de uso por HTTP.

Playwright foi escolhido por oferecer suporte nativo a Chromium headless, isolamento por contexto, esperas orientadas ao DOM, interceptação de rede nos testes e screenshot em memória. Cada execução recebe UUID, contexto e prazo próprios. O semáforo de concorrência protege a memória do servidor.

## Coleta

O fluxo navega pela página inicial oficial, pesquisa uma pessoa, seleciona o primeiro resultado e extrai o panorama. Links compatíveis com Auxílio Brasil, Auxílio Emergencial e Bolsa Família são percorridos com paginação limitada e indicação explícita de completude.

A captura do panorama é produzida pelo navegador em PNG e incorporada ao resultado como Base64. Capturas de falha ficam no bloco `diagnostico`, separadas da evidência funcional.

## Falhas externas

O portal pode aplicar AWS WAF/CAPTCHA a acessos automatizados. O robô detecta título, conteúdo e elementos característicos, fecha os recursos e devolve `PORTAL_BLOQUEADO`. Não há tentativa de resolver ou contornar a verificação humana.

Mudanças no DOM são concentradas nos seletores e nas funções de extração. Limites de tempo e paginação impedem execuções indefinidas e produzem resultado parcial quando já existem dados úteis.

## API e segurança

A API FastAPI fornece OpenAPI/Swagger, validação Pydantic, cabeçalho `X-API-Key`, respostas sem cache e códigos HTTP compatíveis com cada classe de erro. Entradas e respostas não são registradas nos logs. Saídas locais, `.env`, tokens e screenshots estão fora do versionamento.

## Hiperautomação

O n8n chama a API pública, monta o arquivo JSON e o envia ao Google Drive. Depois registra consulta, pessoa, data/hora, status e link em uma planilha central. Drive e Sheets usam nós oficiais e credenciais OAuth2 armazenadas no próprio n8n.

## Validação

A suíte contém 36 testes. As páginas do portal são simuladas por rotas locais controladas, mas o navegador utilizado é Chromium real. Isso permite validar navegação, eventos, paginação, screenshot, concorrência e erros sem depender da disponibilidade do governo nem transmitir dados pessoais.

O workflow tem uma validação própria em Node.js que verifica sua estrutura, serialização Base64, nós Google, colunas e ausência de credenciais exportadas.
