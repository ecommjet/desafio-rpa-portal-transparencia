const fs = require('node:fs');
const assert = require('node:assert/strict');
const workflow = JSON.parse(fs.readFileSync('workflows/n8n-consulta-google.json', 'utf8'));
const nodes = new Map(workflow.nodes.map(node => [node.name, node]));
assert.equal(nodes.size, workflow.nodes.length);
for (const [source, ports] of Object.entries(workflow.connections)) {
  assert(nodes.has(source));
  for (const connection of ports.main.flat()) assert(nodes.has(connection.node));
}
const run = (name, input, reference = {}) => new Function('$input', '$', 'Buffer', nodes.get(name).parameters.jsCode)(
  { first: () => ({ json: input }) }, () => ({ first: () => ({ json: reference }) }), Buffer,
);
const input = run('Entrada')[0].json;
assert.equal(input.api_url, 'https://portfolio.ecommjet.com.br');
assert.equal(typeof input.beneficiario_programa_social, 'boolean');
const result = { consulta_id: 'example-id', consultado_em: '2026-09-27T20:00:00Z', status: 'erro', codigo: 'PORTAL_BLOQUEADO' };
assert.deepEqual(run('Validar resultado', result)[0].json, result);
assert.throws(() => run('Validar resultado', { detail: 'Unauthorized' }));
const prepared = run('Preparar arquivo JSON', result)[0];
assert.equal(prepared.binary.data.mimeType, 'application/json');
assert.equal(JSON.parse(Buffer.from(prepared.binary.data.data, 'base64')).consulta_id, 'example-id');
assert.equal(nodes.get('Salvar JSON no Drive').type, 'n8n-nodes-base.googleDrive');
assert.equal(nodes.get('Registrar no Google Sheets').type, 'n8n-nodes-base.googleSheets');
assert.equal(nodes.get('Registrar no Google Sheets').parameters.operation, 'append');
assert.deepEqual(nodes.get('Registrar no Google Sheets').parameters.columns.schema.map(column => column.id), ['consulta_id','nome','cpf','consultado_em','arquivo_json','status','codigo']);
for (const node of workflow.nodes) assert(!node.credentials, 'O artefato público não deve conter credenciais');
console.log('Workflow: API, JSON binário, Google Drive, Google Sheets e credenciais externas verificados.');
