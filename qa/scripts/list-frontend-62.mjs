import {readFileSync,readdirSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const approved=JSON.parse(readFileSync(resolve(root,'frontend/test-cases-62.json'),'utf8'));
const observed=[];
for(const suite of ['smoke','sanity','regression']){
 for(const file of readdirSync(resolve(root,'frontend/tests',suite)).filter(x=>x.endsWith('.grow8-62.spec.js'))){
  const src=readFileSync(resolve(root,'frontend/tests',suite,file),'utf8');
  for(const match of src.matchAll(/test\(['"]((?:HOME|BRW|DASH|MYOP|CRT)-\d{3}) (@(?:smoke|sanity|regression))\b/g)){
   observed.push({id:match[1],suite:match[2].slice(1),file});
  }
 }
}
const errors=[];
for(const [id,caseInfo] of Object.entries(approved)){
 const found=observed.filter(x=>x.id===id);
 if(found.length!==1)errors.push(`${id}: ${found.length} implementations (expected 1)`);
 else if(found[0].suite!==caseInfo.suite.toLowerCase())errors.push(`${id}: suite ${found[0].suite} != ${caseInfo.suite}`);
}
for(const x of observed)if(!approved[x.id])errors.push(`Unexpected ID: ${x.id}`);
console.log('Grow8 frontend 62-case inventory:');
for(const suite of ['smoke','sanity','regression'])console.log(`  ${suite}: ${observed.filter(x=>x.suite===suite).length}`);
console.log(`  total: ${observed.length} | expected: ${Object.keys(approved).length}`);
if(errors.length){console.error(errors.join('\n'));process.exitCode=1}else console.log('PASS: Every approved ID has exactly one correctly tagged test.');
