import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url)), read=p=>fs.readFileSync(path.join(root,p),'utf8'), catalog=JSON.parse(read('cases.json')),map=JSON.parse(read('legacy-id-map.json'));
function walk(d){return fs.readdirSync(d,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(path.join(d,e.name)):[path.join(d,e.name)]);}
const actual={ui:[],api:[]};
for(const layer of ['ui','api'])for(const m of read(`tests/${layer}.spec.mjs`).matchAll(/\brun\((\d+),/g))actual[layer].push(`${layer.toUpperCase()}-${m[1].padStart(3,'0')}`);
for(const f of walk(path.join(root,'legacy-ui/tests')).filter(x=>x.endsWith('.spec.js')))for(const m of fs.readFileSync(f,'utf8').matchAll(/\btest\(['"](UI-\d{3}) /g))actual.ui.push(m[1]);
const old=JSON.parse(read('legacy-api/cases.json')).cases;
const prefixes=walk(path.join(root,'legacy-api')).filter(f=>/test_.*\.py$/.test(f)).flatMap(f=>[...fs.readFileSync(f,'utf8').matchAll(/@pytest\.mark\.parametrize\('case_id',parameters\('([^']+)'\)\)/g)].map(m=>m[1]));
for(const prefix of prefixes)for(const c of old.filter(x=>x.id.startsWith(prefix)))actual.api.push(map.api[c.id]);
for(const layer of ['ui','api']){const exp=catalog[layer].map(c=>c.id),expectedCount=layer==='ui'?108:301;const counts=new Map();for(const id of actual[layer])counts.set(id,(counts.get(id)||0)+1);const missing=exp.filter(id=>!counts.has(id)),extra=actual[layer].filter(id=>!exp.includes(id)),dup=[...counts].filter(([,n])=>n!==1);if(exp.length!==expectedCount||new Set(exp).size!==expectedCount||missing.length||extra.length||dup.length||actual[layer].length!==expectedCount)throw Error(`${layer}: ${JSON.stringify({expected:exp.length,actual:actual[layer].length,missing,extra,dup})}`);console.log(`${layer.toUpperCase()}: ${actual[layer].length} unique source-defined test IDs match catalog; no missing or duplicate IDs.`);}
console.log('Static inventory verified: 409 IDs. This is not an execution result.');
