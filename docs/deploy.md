# Implantação

A API é executada em contêiner Docker na VPS e publicada por HTTPS em `portfolio.ecommjet.com.br`. O manifesto [compose.easypanel.yaml](../compose.easypanel.yaml) define health check, reinício automático, limite de logs, volume persistente e `shm_size` para o Chromium.

## Variáveis de produção

```dotenv
HEADLESS=true
REQUIRE_API_KEY=true
API_KEY=<segredo>
MAX_CONCURRENT=1
QUERY_TIMEOUT_SECONDS=120
```

O proxy do Easypanel encaminha o domínio para a porta 8000 do contêiner. A porta não precisa ser exposta diretamente pela VPS.

## Verificação

```bash
curl https://portfolio.ecommjet.com.br/health
curl -I https://portfolio.ecommjet.com.br/docs
```

Os endpoints protegidos respondem 401 sem `X-API-Key`. O health check confirma o processo da API; a disponibilidade do portal externo é avaliada durante cada consulta.

## Atualização

O serviço é construído a partir do repositório Git. Uma nova implantação recompila a imagem, instala o Chromium e substitui somente o contêiner da API. O n8n, o banco e os demais serviços da VPS não fazem parte desse compose.
