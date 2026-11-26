import { expect, request } from '@playwright/test';
import { randomUUID } from 'node:crypto';
export const base=process.env.QA_API_URL||'http://localhost:18000/api/v1';
export const accounts={creator:'maple.bakery@grow8.dev',other:'foodbank@grow8.dev',contributor:'alex.chen@grow8.dev',second:'jordan.lee@grow8.dev',admin:'admin@grow8.dev'};
export const password=process.env.QA_SEED_PASSWORD||'Grow8Dev!2026';
export const uniq=()=>`QA-${randomUUID().slice(0,12)}`;
export const day=n=>new Date(Date.now()+n*86400000).toISOString().slice(0,10);
export const pdf=(name='qa.pdf')=>({name,mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n')});
export const txt={name:'work.txt',mimeType:'text/plain',buffer:Buffer.from('QA completed work\n')};
const redact=(x)=>{if(Buffer.isBuffer(x))return {bytes:x.length};if(Array.isArray(x))return x.map(redact);if(x&&typeof x==='object')return Object.fromEntries(Object.entries(x).map(([k,v])=>[k,/password|access_token|authorization/i.test(k)?'[REDACTED]':redact(v)]));return x;};
export async function world(info){
 const ctx=await request.newContext({baseURL:base.replace(/\/$/,'')+'/',timeout:15000});const logs=[];const sessions={};
 async function call(role,method,path,data,status=200,form=false){
  const token=role? (sessions[role]||await login(role)).access_token:null;
  const opts={method,headers:token?{Authorization:`Bearer ${token}`}:{}};
  if(data!==undefined)opts[form?'multipart':'data']=data;
  const res=await ctx.fetch(path.replace(/^\//,''),opts);let body; const ct=res.headers()['content-type']||'';if(ct.includes('json')) body=await res.json();else if(ct.includes('pdf')||ct.includes('octet-stream')||ct.includes('text/plain'))body={content_type:ct,bytes:(await res.body()).length};else body=await res.text();
  logs.push({method,path,role,request: redact(data),expected_status:status,status:res.status(),body});
  expect(res.status(),`${method} ${path}: ${JSON.stringify(body).slice(0,500)}`).toBe(status);return body;
 }
 async function login(role,pw=password){const b=await call(null,'POST','auth/login',{email:accounts[role],password:pw});sessions[role]=b;return b;}
 const get=(r,p,s=200)=>call(r,'GET',p,undefined,s); const post=(r,p,d,s=200)=>call(r,'POST',p,d,s);const patch=(r,p,d,s=200)=>call(r,'PATCH',p,d,s);const put=(r,p,d,s=200)=>call(r,'PUT',p,d,s); const del=(r,p,s=204)=>call(r,'DELETE',p,undefined,s);const form=(r,m,p,d,s=200)=>call(r,m,p,d,s,true);
 async function draft(extra={}){const title=uniq();return post('creator','opportunities',{title,description:'QA work',category:'community',...extra},201);}
 async function opportunity(extra={}){const d=await draft({requirements:'QA skills',location:'Calgary',work_mode:'remote',skills:['data-cleaning'],start_date:day(2),end_date:day(30),expected_hours:8,compensation_type:'unpaid',applicant_limit:3,application_deadline:new Date(Date.now()+86400000).toISOString(),working_conditions:'Remote supervision',safety_information:'Follow safety instructions',accessibility_details:'Accessible remote work',...extra});return post('creator',`opportunities/${d.opportunity_id}/publish`);}
 const apply=(o,role='contributor',extra={},s=201)=>form(role,'POST',`opportunities/${o.opportunity_id}/applications`,{application_details:JSON.stringify({name:'QA contributor',email:accounts[role],phone:'5550100',study:'Engineering',experience:'QA experience',achievements:'QA project'}),...extra},s);
 const decide=(a,decision='accepted',s=200,role='creator')=>post(role,`applications/${a.application_id}/decision`,{decision},s);
 async function accepted(){const o=await opportunity();const a=await apply(o);await decide(a);return {o,a};}
 const submit=(a,extra={},s=201)=>form('contributor','POST',`applications/${a.application_id}/submission`,{description:'QA completed work',hours_claimed:'5',...extra},s);
 async function submitted(){const {o,a}=await accepted();const sub=await submit(a);return {o,a,sub};}
 const verify=(sub,decision='approved',s=200,extra={})=>post('creator',`submissions/${sub.submission_id}/verification`,{decision,...(decision==='approved'?{verified_hours:'4'}:{comment:'QA rejection reason'}),...extra},s);
 async function completed(){const {o,a,sub}=await submitted();await verify(sub);return {o,a,sub};}
 const feedback=(a,role='contributor',extra={},s=201)=>post(role,`applications/${a.application_id}/feedback`,{rating:4,comment:'QA feedback',...extra},s);
 const review=(f,decision='approved',s=200,extra={})=>post('admin',`admin/feedback/${f.feedback_id}/review`,{decision,...(decision==='rejected'?{reason:'QA rejection'}:{}),...extra},s);
 const report=(o,role='contributor',s=201)=>post(role,`opportunities/${o.opportunity_id}/reports`,{reason:'misleading_terms',details:'QA private details'},s);
 const reviewReport=(r,decision='upheld',s=200,extra={})=>post('admin',`admin/reports/${r.report_id}/review`,{decision,...(decision==='upheld'?{reason:'QA moderation'}:{}),...extra},s);
 async function notice(role,o,type){await expect.poll(async()=>{const v=await get(role,'notifications?limit=100');return v.items.some(n=>n.opportunity_id===o.opportunity_id&&n.notification_type===type);},{timeout:30000,intervals:[500,1000,2000]}).toBe(true);}
 async function finish(){await info.attach('api-evidence.json',{body:Buffer.from(JSON.stringify(redact(logs),null,2)),contentType:'application/json'});await ctx.dispose();}
 return {call,get,post,patch,put,del,form,login,draft,opportunity,apply,decide,accepted,submit,submitted,verify,completed,feedback,review,report,reviewReport,notice,finish};
}
