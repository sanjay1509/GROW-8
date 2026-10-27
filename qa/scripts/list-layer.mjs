import { spawnSync } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const qaRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const layer = process.argv[2];
if (!['frontend','backend','database'].includes(layer)) process.exit(2);
const result=spawnSync(process.execPath,[resolve(qaRoot,'node_modules/playwright/cli.js'),'test','--list'], {
  cwd:qaRoot,stdio:'inherit',env:{...process.env,QA_LAYER:layer,QA_SUITE:'regression',QA_RUN_ID:'list-only'}
});
process.exit(result.status ?? 1);
