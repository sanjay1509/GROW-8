import { spawnSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const qaRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const layerInput = process.argv[2];
const suite = process.argv[3];
const layers = layerInput === 'all' ? ['frontend','backend','database'] : [layerInput];
if (!['frontend', 'backend', 'database', 'all'].includes(layerInput) ||
    !['smoke', 'sanity', 'regression', 'all'].includes(suite) || (suite === 'all' && layerInput !== 'frontend')) {
  console.error('Usage: node scripts/run-layer.mjs frontend|backend|database|all smoke|sanity|regression; frontend all');
  process.exit(2);
}
let failures = 0;
for (const layer of layers) {
  const runId = `${new Date().toISOString().replace(/[:.]/g, '-')}-${process.pid}`;
  const directory = resolve(qaRoot, 'reports', layer, suite);
  mkdirSync(directory, { recursive: true });
  const invocation = { runId, layer, suite, startedAt: new Date().toISOString(), report: `reports/${layer}/${suite}/${runId}/html` };
  console.log(`\nRunning ${layer.toUpperCase()} ${suite.toUpperCase()} [${runId}]`);
  const args = [resolve(qaRoot, 'node_modules/playwright/cli.js'), 'test'];
  // Frontend regression is regression-only; legacy backend/database regression behavior remains unchanged.
  if ((layer === 'frontend' && suite !== 'all') || (layer !== 'frontend' && suite !== 'regression')) args.push('--grep', `@${suite}`);
  const result = spawnSync(process.execPath, args, {
    stdio: 'inherit',
    cwd: qaRoot,
    env: { ...process.env, QA_LAYER: layer, QA_SUITE: suite, QA_RUN_ID: runId },
  });
  invocation.finishedAt = new Date().toISOString();
  invocation.exitCode = result.status ?? 1;
  writeFileSync(resolve(directory, 'latest.json'), JSON.stringify(invocation, null, 2) + '\n');
  if (result.error) console.error(result.error.message);
  console.log(`Report: ${invocation.report}`);
  if (invocation.exitCode !== 0) failures += 1;
}
process.exit(failures ? 1 : 0);
