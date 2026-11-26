import { spawn, spawnSync } from 'node:child_process';
import { existsSync, readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import net from 'node:net';
const qa=path.dirname(fileURLToPath(import.meta.url)),root=path.dirname(qa),backend=path.join(root,'grow8-backend'),frontend=path.join(root,'grow8-');
const layer=process.argv[2]||'all';
if(!['all','ui','api'].includes(layer))throw Error('Usage: node grow8-qa/run-local.mjs [all|ui|api]');
const windows=process.platform==='win32';
const npm=windows?'npm.cmd':'npm';
const id=`grow8qa${Date.now()}`;
const report=path.join(qa,'reports',id);mkdirSync(report,{recursive:true});console.log('Evidence folder:',report);
const ports={api:18000,ui:15173,mysql:13307,rabbit:15673};
const env={...process.env,QA_REPORT_DIR:report,API_HOST_PORT:String(ports.api),MYSQL_HOST_PORT:String(ports.mysql),RABBITMQ_MGMT_HOST_PORT:String(ports.rabbit),CORS_ORIGINS:`http://localhost:${ports.ui}`,QA_API_URL:`http://localhost:${ports.api}/api/v1`,QA_UI_URL:`http://localhost:${ports.ui}`,VITE_API_BASE_URL:`http://localhost:${ports.api}/api/v1`};
const compose=['compose','--project-name',id,'--env-file',path.join(backend,'.env.example'),'-f',path.join(backend,'docker-compose.yml')];
let started=false,server=null,exitCode=1;
function run(cmd,args,cwd,required=true){console.log(`> ${cmd} ${args.join(' ')}`);const r=spawnSync(cmd,args,{cwd,env,stdio:'inherit',shell:windows&&cmd===npm});if(required&&(r.error||r.status!==0))throw Error(`${cmd} failed (${r.error?.message||r.status})`);return r.status??1;}
async function wait(url,seconds){const until=Date.now()+seconds*1000;while(Date.now()<until){try{const r=await fetch(url,{signal:AbortSignal.timeout(3000)});if(r.ok)return;}catch{}await new Promise(r=>setTimeout(r,2000));}throw Error(`Timed out waiting for ${url}`);}
async function portFree(p){await new Promise((resolve,reject)=>{const s=net.createServer();s.once('error',()=>reject(Error(`Port ${p} is occupied. Stop the other process before running isolated QA.`)));s.listen(p,()=>s.close(resolve));});}
try{
 if(!existsSync(path.join(backend,'.env.example'))||!existsSync(path.join(frontend,'package-lock.json')))throw Error('Extract grow8-qa into the GROW-8 repository root.');
 run('docker',['info'],root);run('docker',['compose','version'],root);
 for(const p of [ports.api,ports.mysql,ports.rabbit,...(layer==='api'?[]:[ports.ui])])await portFree(p);
 // Use the exact package version and the frontend's existing lockfile. No application source edits.
 run(npm,['install','--no-audit','--no-fund'],qa);
 run(process.execPath,[path.join(qa,'verify-inventory.mjs')],qa);
 run(npm,['exec','--','playwright','test','--list',...(layer==='all'?[]:[`--project=${layer}`])],qa);
 if(layer!=='api'){
   run(npm,['ci','--no-audit','--no-fund'],frontend);
   run(npm,['exec','--','playwright','install',...(process.env.CI?['--with-deps']:[]),'chromium'],qa);
 }
 started=true;run('docker',[...compose,'up','-d','--build'],backend);
 await wait(`http://localhost:${ports.api}/health`,240);
 // Allow the three consumers to connect and declare their queues before the first event.
 await new Promise(r=>setTimeout(r,5000));
 if(layer!=='api'){
   server=spawn(npm,['run','dev','--','--host','localhost','--port',String(ports.ui),'--strictPort'],{cwd:frontend,env,stdio:'inherit',shell:windows});
   await wait(`http://localhost:${ports.ui}`,120);
 }
 const sha=spawnSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).stdout?.trim()||'unknown';
 writeFileSync(path.join(report,'run-meta.json'),JSON.stringify({started_at:new Date().toISOString(),commit:sha,layer,compose_project:id},null,2));
 // Run browser and live API cases. Legacy in-process API cases use an isolated grow8_test schema.
 exitCode=run(npm,['exec','--','playwright','test',...(layer==='all'?[]:[`--project=${layer}`])],qa,false);
 if(layer!=='ui'){
   const legacy=run('docker',[...compose,'run','--rm','--no-deps','-u','root','-v',`${path.join(qa,'legacy-api')}:/app/api/tests/backend_qa:ro`,'-v',`${path.join(backend,'db')}:/app/db:ro`,'-v',`${report}:/qa-report`,'-e','QA_LEGACY_REPORT_DIR=/qa-report','api','sh','-c','python -m pip install -q --disable-pip-version-check -r requirements-dev.txt pytest-html==4.1.1 && python -m pytest tests/backend_qa --rootdir=/app/api -v -ra --tb=short --html=/qa-report/legacy-api.html --self-contained-html --junitxml=/qa-report/legacy-api-junit.xml'],backend,false);
   if(legacy!==0)exitCode=1;
 }
 if(run(process.execPath,[path.join(qa,'export-results.mjs')],qa,false)!==0)exitCode=1;
}catch(e){console.error(e);writeFileSync(path.join(report,'setup-failure.txt'),`${new Date().toISOString()}\n${e.stack||e.message}\n`);exitCode=1;}
finally{
 if(server?.pid){if(windows)spawnSync('taskkill',['/pid',String(server.pid),'/T','/F'],{stdio:'ignore'});else server.kill();}
 if(started){const logs=spawnSync('docker',[...compose,'logs','--no-color','--tail','1500'],{cwd:backend,env,encoding:'utf8',maxBuffer:32*1024*1024});writeFileSync(path.join(report,'compose.log'),(logs.stdout||'')+(logs.stderr||''));run('docker',[...compose,'down','-v','--remove-orphans'],backend,false);}
}
process.exit(exitCode);

