# Relatório técnico

## Escopo

Implementação da Parte 1, API documentada, interface web e código do bônus Google/n8n. A API está publicada por HTTPS na VPS, o repositório é público e a chamada autenticada foi validada no n8n self-hosted. Permanecem pendentes a autorização Google e uma coleta autônoma bem-sucedida em ambiente liberado pelo WAF.

## Decisões

**Playwright assíncrono:** atende à biblioteca recomendada e permite DOM renderizado, captura de tela e contextos independentes. Um Chromium é compartilhado por processo; cookies e páginas ficam em contextos descartáveis. Um semáforo limita o uso de recursos e um timeout inclui a espera por uma vaga.

**FastAPI e Pydantic:** validam a entrada e publicam OpenAPI/Swagger. A interface CLI reutiliza o mesmo serviço. Nome é normalizado; entradas numéricas aceitam 11 dígitos de CPF/NIS, inclusive zeros à esquerda. Não se exige dígito verificador de CPF, pois o mesmo campo recebe NIS e deve permitir os cenários de documento inexistente.

**Extração conservadora:** preserva os dados exibidos, tabelas e texto completo da área principal. Não reconstrói CPF mascarado nem atribui valores a campos ausentes. O JSON preserva as páginas dos detalhes separadamente para rastreabilidade. URLs de navegação devem usar HTTPS e o host do portal.

**Resultados parciais:** a captura ocorre no panorama antes de abrir detalhes. Uma falha num benefício preserva o panorama e as páginas já coletadas. Um limite de paginação evita execução indefinida e é informado como incompletude, nunca como sucesso integral.

**Segurança:** configuração por ambiente, chave em cabeçalho e ausência de logs de respostas. `/consultas` não persiste resultados; o workflow CLI e o exportador guardam checkpoints locais com escrita atômica e permissões restritas. Docker Compose publica em localhost. `REQUIRE_API_KEY=true` impede iniciar sem chave em hospedagem.

**Bônus com n8n:** escolhido pela preferência do usuário. O workflow orquestra dois endpoints HTTP: coleta e arquivamento. As APIs Google ficam encapsuladas no Python, centralizando OAuth, upload retomável, checksum e reconciliação da linha. O escopo `drive.file` limita acesso aos recursos criados/autorizados para o aplicativo.

**Recuperação:** ID do Drive reservado antes do upload, SHA-256 para detectar conflito e pesquisa por UUID no Sheets antes de append. Um bloqueio de arquivo serializa o exportador em uma instância/diretório compartilhado. Não há garantia de transação distribuída nem coordenação entre réplicas independentes. O n8n repete apenas o arquivamento com o mesmo JSON.

## Desafios e limitações

**Correção sobre os testes visíveis:** o usuário informou que resolveu a verificação humana nas janelas do Playwright durante o diagnóstico. As navegações bem-sucedidas e a busca fictícia com zero resultados nesses testes devem ser classificadas como **assistidas**, não como comprovação de execução autônoma. O script anterior fechava a janela ao final de cada teste; `scripts/portal_session.py` mantém uma única sessão aberta para continuar a inspeção, sem exportar cookies e sem resolver CAPTCHA automaticamente.

O acesso público ao portal retornou uma página de verificação humana AWS WAF/CAPTCHA. Após a resolução manual pelo usuário, a sessão persistente permitiu inspecionar o DOM real e consultar um documento autorizado. Foram ajustados o caminho pela página inicial, envio da busca, espera pelos resultados atualizados, URLs com slug, expansão dos painéis do panorama e remoção do aviso de cookies. A homologação autônoma continua pendente.

O teste local de navegador foi inicialmente bloqueado pelo sandbox do macOS na inicialização do Chromium. Os testes de integração precisam de permissão para executar o navegador fora desse sandbox.

O layout e os componentes do portal podem mudar. A extração de campos e links é heurística; páginas que usem controles de detalhe diferentes de links ou paginação diferente das variantes suportadas exigem ajuste. O prazo total e o limite de páginas são proteções operacionais, não garantia de coleta ilimitada. Consultas em andamento não têm fila persistente; a retomada do workflow atua sobre resultados já salvos.

## Roteiro de apresentação

### Verificação local em 26/09/2026

- **36 testes passaram em 13,00 segundos**, cobrindo robô, API, Google, workflow, interface e regressões do layout observado, inclusive o botão interno da paginação atual. Há um aviso de depreciação do adaptador httpx do TestClient, sem falha funcional.
- Execução real da CLI com nome fictício: código de saída 2, JSON com `status=erro` e `codigo=TEMPO_ESGOTADO`, sem pessoa ou evidência. O arquivo local está em `outputs/verificacao-portal.json`, excluído do versionamento.
- O diagnóstico posterior do Chromium encontrou HTTP 202, título/corpo vazios e `#challenge-container` com scripts AWS WAF. A detecção agora inclui esse DOM; uma espera curta permite que a verificação automática normal termine, sem resolver CAPTCHA ou injetar tokens.
- Após a correção, a CLI real retornou `PORTAL_BLOQUEADO` em 1.490 ms, com captura de diagnóstico e sem dados de pessoa. Resultado local: `outputs/verificacao-portal-atual.json`.
- A imagem Docker está em execução na VPS via Easypanel. `https://portfolio.ecommjet.com.br/health` responde, o Swagger está publicado e requisições sem chave aos endpoints protegidos recebem 401.
- O workflow n8n passou na verificação local, foi importado na instância self-hosted e chamou a API pública com Header Auth. O teste retornou `PORTAL_BLOQUEADO` com captura de diagnóstico, comportamento esperado diante do WAF.
- A consulta real assistida encontrou o panorama e os detalhes de Auxílio Emergencial. A extração offline das capturas gerou `outputs/resultado-assistido.json`, com nove registros de uma tabela e imagem do panorama. O arquivo declara modo assistido e resultado parcial, pois o utilitário não verifica a completude da paginação. Os dados pessoais não integram os testes sintéticos nem a documentação versionada.
- O arquivamento real no Google aguarda a autorização OAuth da conta. A coleta real autônoma bem-sucedida segue limitada pelo WAF do portal.

### Sequência sugerida

1. Mostrar o contrato no Swagger e os módulos do projeto.
2. Executar a suíte de testes, destacando o uso de Chromium real com conteúdo fictício.
3. Explicar isolamento de contextos e demonstrar o teste de concorrência.
4. Em ambiente homologado, executar a consulta real e mostrar JSON, imagem e detalhes dos benefícios.
5. Mostrar a diferença entre sucesso, parcial e bloqueio; apresentar as pendências explicitamente.
6. Executar o n8n com a API online e mostrar o mesmo UUID no JSON do Drive e na linha do Sheets. Repetir o arquivamento para demonstrar reconciliação sem duplicação.

O checklist de homologação está no README. A demonstração em páginas sintéticas comprova o comportamento interno, mas não deve ser apresentada como coleta bem-sucedida no portal real.
