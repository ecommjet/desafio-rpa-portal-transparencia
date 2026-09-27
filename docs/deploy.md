# Publicar a API para avaliação

O requisito do bônus inclui uma API online. **Ainda não há deploy realizado.** O destino escolhido é sua **VPS com n8n self-hosted**. Os arquivos abaixo preparam uma implantação única com estado persistente; o proxy/domínio precisa ser adaptado à configuração existente da VPS.

## VPS com n8n self-hosted (destino escolhido)

1. Transfira o código para uma pasta dedicada na VPS, sem sobrescrever a instalação do n8n.
2. Crie um arquivo `.env` privado nessa pasta com `API_KEY`, os IDs do Google e `GOOGLE_TOKEN_JSON` em uma única linha. Preserve permissões restritas. Não coloque esse arquivo no Git.
3. Execute `docker compose -f compose.vps.yaml up -d --build`.
4. Verifique `curl http://127.0.0.1:8001/health` e os logs com `docker compose -f compose.vps.yaml logs --tail=100 api`.
5. Configure seu proxy HTTPS existente para encaminhar o subdomínio escolhido à API. Se o proxy roda no host, o destino é `127.0.0.1:8001`. Se roda em container, conecte-o à rede apropriada e use o nome do serviço, não o localhost do container.
6. No n8n, configure a URL HTTPS pública e a credencial Header Auth da API. Teste a partir da própria execução n8n.

O compose publica somente em loopback, exige chave e persiste o estado em volume. Não ocupa as portas 80/443 e não altera o n8n. A porta local pode ser alterada com `OBSERVA_HOST_PORT`. Ajuste `MAX_CONCURRENT` aos recursos da VPS após medir o consumo do Chromium.

Se o n8n estiver em Docker na **mesma VPS**, você pode usar uma rede compartilhada existente:

```bash
# Substitua pelo nome real da rede do seu n8n:
export N8N_DOCKER_NETWORK=nome_da_rede
docker compose -f compose.vps.yaml -f compose.n8n-network.yaml up -d --build
```

Nesse caso, o nó Entrada pode usar `http://observa-api:8000`. O endpoint HTTPS continua necessário para o acesso dos avaliadores fora da VPS. Não aplique o override sem conferir a rede existente. O deployment ainda depende do acesso autorizado à VPS e dos dados do proxy/domínio.

## Render (alternativa, não utilizada)

1. Publique o código em um repositório seu, sem `.env`, `secrets/`, `outputs/`, `.venv/` ou `.browsers/`.
2. Na sua conta Render, crie um Blueprint a partir do repositório. O arquivo `render.yaml` descreve o serviço Docker e uma chave de API gerada.
3. Configure `GOOGLE_DRIVE_FOLDER_ID` e `GOOGLE_SPREADSHEET_ID` com os IDs criados no setup local.
4. Configure **GOOGLE_TOKEN_JSON como segredo** com o conteúdo de `secrets/google-token.json`. Faça isso diretamente no painel, sem colocar o token no repositório.
5. Após o build, abra `/health`, a interface `/` e `/docs` na URL HTTPS fornecida.
6. Informe a chave da API na interface e configure a mesma URL/credencial no n8n.

O blueprint usa o plano gratuito e concorrência 1 como ponto de partida. Chromium pode exceder os recursos disponíveis, e inicialização a frio pode ultrapassar o timeout do workflow. Teste a carga antes da apresentação e aqueça `/health` antes de executar a consulta. Não foi validado o consumo de memória nesse provedor. Confira as condições atuais no painel antes de contratar qualquer recurso.

O disco desse plano não é persistente. Para maior confiabilidade, use armazenamento persistente para `EXPORT_STATE_DIR` em uma implantação apropriada e mantenha uma única instância. O exportador pode recuperar arquivos via Drive, mas não substitui uma fila durável nem uma transação distribuída. Referência: [blueprints Render](https://render.com/docs/blueprint-spec).

## Docker em servidor próprio

`docker compose up --build` publica a API em localhost e persiste checkpoints em um volume. Para o Google, configure os IDs e `GOOGLE_TOKEN_JSON` como variáveis protegidas no servidor. Use um proxy HTTPS para acesso externo, com `API_KEY` forte e `REQUIRE_API_KEY=true`. Não exponha o n8n ou o token Google sem autenticação.

O container executa com usuário sem privilégios. O Dockerfile instala Chromium e suas bibliotecas Linux. Neste computador o daemon Docker estava desligado, então o build ainda não foi executado.

## Checklist de aceite online

- [ ] `/health` responde e `/docs` carrega por HTTPS.
- [ ] POST sem chave recebe 401.
- [ ] Consulta real autorizada produz panorama, benefícios e evidência verificáveis.
- [ ] Bloqueio do portal é reportado como erro, com diagnóstico.
- [ ] Duas consultas simultâneas têm UUIDs/resultados independentes (ajustar recursos e concorrência).
- [ ] n8n executa a consulta e recebe os links do Google.
- [ ] JSON no Drive contém a imagem e os mesmos dados retornados pela API.
- [ ] Reenviar o mesmo JSON não duplica o arquivo ou a linha.

Não compartilhe a API com os avaliadores como funcionalmente homologada até concluir esses passos, especialmente o acesso ao portal real.
