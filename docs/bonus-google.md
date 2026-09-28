# Hiperautomação com n8n, Google Drive e Google Sheets

O bônus é implementado pelo workflow [n8n-consulta-google.json](../workflows/n8n-consulta-google.json). O n8n coordena a chamada da API e usa os nós oficiais do Google para persistir o resultado.

## Sequência

| Nó | Responsabilidade |
|---|---|
| 1. Configurar armazenamento | gatilho executado uma vez para preparar a conta Google |
| Criar pasta de consultas | cria a pasta que receberá os arquivos JSON |
| Criar planilha de registro | cria a planilha e a aba `consultas` |
| Inicializar colunas | cria as sete colunas do registro central |
| 2. Receber consulta | webhook `POST` que inicia automaticamente cada consulta |
| Localizar pasta / planilha | encontra os recursos pelo nome, sem IDs fixos no workflow |
| Entrada | URL da API, termo e filtro social |
| Consultar RPA | chamada autenticada a `POST /consultas` |
| Validar resultado | valida UUID, data/hora e status |
| Preparar arquivo JSON | serializa o resultado integral como binário UTF-8 |
| Salvar JSON no Drive | upload para a pasta de consultas |
| Preparar registro | seleciona os sete campos do índice central |
| Registrar no Google Sheets | acrescenta uma linha na planilha central |
| Recibo da execução | devolve status, IDs e links dos recursos |

O Drive recebe `CONSULTA_ID_DATA_HORA.json`. A planilha possui as colunas:

| Coluna | Origem |
|---|---|
| `consulta_id` | UUID gerado pela API |
| `nome` | pessoa encontrada, quando disponível |
| `cpf` | valor exibido pelo portal, inclusive máscara |
| `consultado_em` | data/hora UTC da consulta |
| `arquivo_json` | link direto para o arquivo do Drive |
| `status` | `sucesso`, `parcial` ou `erro` |
| `codigo` | código estruturado, quando houver |

## Credenciais e segurança

O artefato versionado não contém credenciais. Após a importação, os nós recebem três credenciais armazenadas pelo n8n:

- Header Auth com o cabeçalho `X-API-Key`;
- OAuth2 do Google Drive;
- OAuth2 do Google Sheets.

O JSON e a planilha permanecem privados no Google Drive. O workflow não altera permissões nem publica links. As credenciais são renovadas pelo n8n e não passam pela API Python.

O fluxo aceita resultados de erro do robô para preservar o diagnóstico da execução. Nesse caso, a linha no Sheets registra `status=erro` e o respectivo código; o arquivamento concluído não muda o status da coleta.
