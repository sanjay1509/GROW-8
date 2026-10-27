import { spawnSync } from 'node:child_process';
import { readFileSync, existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const qaRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const [layer, suite] = process.argv.slice(2);
if (!['frontend','backend','database'].includes(layer) || !['smoke','sanity','regression'].includes(suite)) {
  console.error('Usage: node scripts/open-report.mjs frontend|backend|database smoke|sanity|regression');
  process.exit(2);
}
const latest = resolve(qaRoot, 'reports', layer, suite, 'latest.json');
if (!existsSync(latest)) {
  console.error(`No ${layer} ${suite} report yet. Execute the test command first.`);
  process.exit(1);
}
const {report} = JSON.parse(readFileSync(latest,'utf8'));
const result = spawnSync(process.execPath,[resolve(qaRoot,'node_modules/playwright/cli.js'), 'show-report', resolve(qaRoot, report)],{cwd:qaRoot,stdio:'inherit'});
process.exit(result.status ?? 1);
