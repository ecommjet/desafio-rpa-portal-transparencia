// Valida estrutura e scripts do artefato; não substitui importação no n8n.
const fs = require('node:fs');
const assert = require('node:assert/strict');
const workflow = JSON.parse(fs.readFileSync('workflows/n8n-consulta-google.json', 'utf8'));
const nodes = new Map(workflow.nodes.map(node => [node.name, node]));
assert.equal(nodes.size, workflow.nodes.length);
for (const [source, ports] of Object.entries(workflow.connections)) {
  assert(nodes.has(source));
  for (const connection of ports.main.flat()) assert(nodes.has(connection.node));
}
const run = (name, input, reference) => new Function('$input', '$', nodes.get(name).parameters.jsCode)(
  {first: () => ({json: input})}, () => ({first: () => ({json: reference})})
);
const input = run('Entrada')[0].json;
assert(input.api_url.startsWith('http'));
assert.equal(typeof input.beneficiario_programa_social, 'boolean');
const result = {consulta_id: 'example-id', consultado_em: new Date().toISOString(), status: 'erro', codigo: 'PORTAL_BLOQUEADO'};
assert.deepEqual(run('Validar resultado', result)[0].json, result);
assert.throws(() => run('Validar resultado', {detail: 'Unauthorized'}));
const receipt = run('Recibo da execução', {arquivo_url: 'https://drive.google.com/file/d/example/view'}, result)[0].json;
assert.equal(receipt.status_coleta, 'erro');
assert.equal(receipt.status_arquivamento, 'concluido');
for (const node of workflow.nodes.filter(n => n.type === 'n8n-nodes-base.httpRequest')) {
  assert.equal(node.parameters.genericAuthType, 'httpHeaderAuth');
  assert(!node.credentials);
}
assert.equal(nodes.get('Consultar RPA').retryOnFail, undefined);
assert.equal(nodes.get('Arquivar no Drive e Sheets').retryOnFail, true);
console.log('Workflow: estrutura, scripts, separação de status e credenciais verificados. Importação no n8n ainda necessária.');
