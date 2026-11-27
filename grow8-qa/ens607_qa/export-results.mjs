import fs from 'node:fs';import path from 'node:path';
const dir=path.resolve(process.env.QA_REPORT_DIR||process.argv[2]||'reports/manual'),r=fs.existsSync(path.join(dir,'results.json'))?JSON.parse(fs.readFileSync(path.join(dir,'results.json'),'utf8')):{suites:[]};const meta=fs.existsSync(path.join(dir,'run-meta.json'))?JSON.parse(fs.readFileSync(path.join(dir,'run-meta.json'),'utf8')):{};const rows=[];
function visit(s){for(const spec of s.specs||[]){const id=spec.title.match(/^(UI|API)-\d{3}/)?.[0];if(!id)continue;for(const t of spec.tests||[]){const result=t.results?.at(-1);if(!result)continue;const st=result.status==='passed'?'Pass':result.status==='skipped'?'Skipped':result.status==='interrupted'?'Blocked':'Fail';const err=(result.error?.message||result.errors?.map(x=>x.message).join('\n')||'').replace(/\x1b\[[0-9;]*m/g,'');const evidence=(result.attachments||[]).filter(a=>a.path).map(a=>path.relative(dir,path.resolve(a.path)).replaceAll('\\','/')).join('; ');rows.push([meta.started_at||new Date().toISOString(),id,t.projectName||id.split('-')[0],st,st==='Pass'?'Automated assertions passed for implemented checks.':err.slice(0,2000)||result.status,result.duration,evidence,meta.commit||'unknown']);}}for(const ch of s.suites||[])visit(ch);}
for(const s of r.suites||[])visit(s);
const legacyDir=path.join(dir,'legacy-api-evidence');
if(fs.existsSync(legacyDir))for(const file of fs.readdirSync(legacyDir).filter(x=>x.endsWith('.json'))){const d=JSON.parse(fs.readFileSync(path.join(legacyDir,file),'utf8'));rows.push([meta.started_at||new Date().toISOString(),d.id,'api',d.status,d.actual,d.duration_ms,'legacy-api-evidence/'+file,meta.commit||'unknown']);}
const catalog=JSON.parse(fs.readFileSync(new URL('./cases.json',import.meta.url),'utf8'));
const expected=[...(meta.layer==='api'?[]:catalog.ui),...(meta.layer==='ui'?[]:catalog.api)].map(c=>c.id);
const unique=new Set(rows.map(row=>row[1]));if(unique.size!==rows.length)throw Error('Duplicate test IDs in execution output');
for(const id of unique)if(!expected.includes(id))throw Error('Unexpected result '+id);
const missing=expected.filter(id=>!unique.has(id));
if(missing.length)console.error('Missing actual execution records: '+missing.join(', '));
rows.sort((a,b)=>a[1].localeCompare(b[1]));
const safe=x=>{let v=String(x??'');if(/^[=+@-]/.test(v))v="'"+v;return '"'+v.replaceAll('"','""')+'"';};
fs.writeFileSync(path.join(dir,'case-results.csv'),[['Run UTC','Test Case ID','Layer','Status','Actual Results','Duration (ms)','Evidence','Commit'],...rows].map(a=>a.map(safe).join(',')).join('\n'),'utf8');console.log(`Exported ${rows.length} execution records.`);

if(missing.length)process.exitCode=1;
