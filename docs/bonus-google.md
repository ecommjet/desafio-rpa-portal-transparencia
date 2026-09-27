# Bônus: n8n + Google Drive + Google Sheets

O workflow n8n chama o robô por HTTP e entrega seu resultado ao exportador Python. O exportador usa OAuth 2.0 e as APIs oficiais para criar o JSON no Drive e atualizar o registro no Sheets. A autenticação Google fica no servidor; o n8n guarda somente a credencial da API.

O código e os testes estão implementados. **A conexão a uma conta Google, a execução no seu n8n e o deploy online ainda precisam ser feitos.** Nenhuma credencial foi criada ou enviada automaticamente.

## 1. Autorizar sua conta Google uma vez

1. No [Google Cloud Console](https://console.cloud.google.com/), crie ou selecione um projeto para o desafio.
2. Habilite **Google Drive API** e **Google Sheets API**.
3. Configure o Google Auth Platform / tela de consentimento. Se o aplicativo estiver em teste, adicione seu e-mail aos usuários de teste.
4. Crie um cliente OAuth do tipo **Desktop app** e baixe seu JSON.
5. Salve-o como `secrets/client.json`, na pasta do projeto. Não coloque esse arquivo no Git nem em conversas.
6. Com o ambiente virtual ativado, execute:

```bash
python -m app.google_setup
```

Esse comando abre a autorização no navegador. Você escolhe a conta e autoriza o aplicativo. Depois ele cria uma pasta **Observa — consultas** e uma planilha **Observa — registro de consultas**, com a aba **Consultas** e cabeçalhos prontos.

É solicitado somente o escopo `drive.file`, para arquivos criados/abertos pelo aplicativo. Por isso o setup cria seus próprios recursos: colar o ID de uma pasta arbitrária não necessariamente concede acesso. O Google documenta esse escopo em [permissões do Drive](https://developers.google.com/workspace/drive/api/guides/api-specific-auth); o [update do Sheets](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/update) também o aceita.

O token fica em `secrets/google-token.json`, com permissão local restrita. Os IDs dos recursos ficam em `secrets/google-resources.json`, permitindo retomar o setup. Copie as variáveis exibidas para `.env` e reinicie a API.

```dotenv
GOOGLE_TOKEN_FILE=secrets/google-token.json
GOOGLE_DRIVE_FOLDER_ID=ID_DA_PASTA_CRIADA
GOOGLE_SPREADSHEET_ID=ID_DA_PLANILHA_CRIADA
GOOGLE_SHEET_TAB=Consultas
```

O token permite renovar o acesso sem login a cada consulta. Revogação ou expiração exigem nova autorização. Para reautorizar, preserve uma cópia do token antigo fora do repositório e execute o setup com `--token secrets/google-token-novo.json`, depois atualize a variável. Referência: [OAuth para aplicativos Desktop](https://developers.google.com/identity/protocols/oauth2/native-app).

## 2. Testar na interface

Abra `http://127.0.0.1:8000`, faça uma consulta e clique em **Salvar no Google**. O resultado informa os links do JSON e da planilha. Mesmo quando o portal bloqueia a consulta, é possível arquivar o diagnóstico: a planilha continua indicando `erro`, não sucesso da coleta.

O arquivo segue `CONSULTA_ID_DATA_HORA_UTC.json` e contém o resultado integral, incluindo imagem Base64 quando disponível. As colunas são:

| Coluna | Valor |
|---|---|
| consulta_id | UUID da consulta |
| nome | Nome apresentado pelo portal, se disponível |
| cpf | CPF como apresentado pelo portal, inclusive máscara |
| consultado_em | Data/hora UTC |
| arquivo_json | Link direto ao arquivo no Drive |
| status | sucesso / parcial / erro |
| codigo | Código de diagnóstico |

O arquivo fica privado na sua conta. O link exige acesso autorizado ao Drive; o código não cria permissões públicas. As células são gravadas com `RAW`, sem interpretar nomes como fórmulas.

## 3. Importar no n8n

Importe [n8n-consulta-google.json](../workflows/n8n-consulta-google.json) usando **Import from File** no menu do workflow. O arquivo não contém credenciais e vem inativo.

Fluxo: **Executar consulta → Entrada → Consultar RPA → Validar resultado → Arquivar no Drive e Sheets → Recibo da execução**.

1. No nó **Entrada**, edite `api_url`, `termo` e `beneficiario_programa_social`.
2. Defina `API_KEY` no `.env` da API e reinicie-a. Gere um valor forte localmente, por exemplo com `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
3. No n8n, crie uma credencial **Header Auth** com Name `X-API-Key` e Value igual à chave da API.
4. Selecione essa credencial nos dois nós **HTTP Request**.
5. Execute o workflow. O recibo separa `status_coleta` de `status_arquivamento`.

| Onde o n8n está | URL da API |
|---|---|
| Mesmo computador, sem Docker | `http://127.0.0.1:8000` |
| Docker no macOS/Windows, API no host | `http://host.docker.internal:8000` |
| Mesma rede Docker da API | `http://api:8000` |
| n8n remoto/cloud | URL HTTPS pública do deploy |

Se o n8n estiver em Docker e precisar acessar o host, inicie a API com `--host 0.0.0.0` e `REQUIRE_API_KEY=true`. Isso também pode disponibilizar a porta na sua rede local; use somente durante o teste ou controle o acesso pelo firewall. Em Linux, `host.docker.internal` pode exigir configuração `host-gateway` no Docker.

Não use `localhost` de um servidor n8n remoto esperando alcançar seu Mac. O bônus do enunciado exige uma API online; veja [deploy](deploy.md).

O primeiro HTTP aceita respostas HTTP de erro para preservar diagnósticos do RPA. O nó seguinte rejeita respostas sem um resultado válido, como chave incorreta. Só a etapa de arquivamento tem retries automáticos, sempre com o mesmo JSON. Referência das opções: [HTTP Request do n8n](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/).

O JSON do workflow e seus scripts foram verificados localmente, mas ainda não importados/executados na sua instância. Se houver diferença entre versões do n8n, confira os nós HTTP conforme a tabela e mantenha o corpo JSON, Header Auth e os timeouts de 180/300 segundos.

## 4. Executar ou retomar pelo terminal

Alternativa para diagnosticar o pipeline sem depender do editor n8n:

```bash
python -m app.workflow 'NOME PARA CONSULTA' --social --run-id demonstracao-01
```

Esse comando chama `/consultas`, salva `outputs/runs/demonstracao-01/resultado.json` e chama `/integracoes/google/arquivar`. Se o Google falhar, execute o mesmo comando com o mesmo `--run-id`: o resultado salvo é reutilizado, sem rodar outra busca. Para uma consulta nova, use outro ID.

No n8n, retome a etapa que falhou com o resultado original ou reenvie o JSON pelo endpoint de arquivamento. Reiniciar todo o workflow gera uma nova consulta, com outro UUID, portanto outro registro legítimo.

## Recuperação e limites

- Um ID do Drive é reservado e salvo antes do upload, evitando gerar um novo arquivo ao repetir a tentativa.
- O SHA-256 vincula o `consulta_id` ao conteúdo; reutilizar o mesmo ID com outro JSON gera conflito.
- Depois do upload, o exportador pesquisa o UUID na planilha antes de inserir. Um retry encontra a linha existente e a atualiza.
- O bloqueio local serializa exportações que compartilham `EXPORT_STATE_DIR`. Use **uma instância** do exportador; múltiplas réplicas independentes exigem coordenação distribuída para evitar corridas.
- Preserve o diretório de estado. Existe recuperação pelo Drive se o estado se perder, mas isso não é uma transação atômica entre Drive e Sheets.
- O setup pode criar recurso duplicado se sua primeira resposta de criação se perder antes de salvar o checkpoint. Confira os recursos antes de repetir o setup nessa situação.
- Testes usam serviços simulados e falhas após gravação. A integração Google real ainda depende do login e da validação na conta.
