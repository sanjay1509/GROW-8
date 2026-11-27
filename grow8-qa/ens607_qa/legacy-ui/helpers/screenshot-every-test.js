import {test as base, expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
const catalog=JSON.parse(readFileSync(new URL('../test-cases-62.json',import.meta.url),'utf8'));
function sanitize(value) {
  if(value==null) return value;
  if(typeof value==='string') return value.replace(/Bearer\s+[^\s"']+/gi,'Bearer <redacted>').replace(/eyJ[A-Za-z0-9_.-]{20,}/g,'<redacted-token>').slice(0,1800);
  if(Array.isArray(value)) return value.slice(0,12).map(sanitize);
  if(typeof value==='object') return Object.fromEntries(Object.entries(value).slice(0,24).map(([k,v])=>[k,/(password|token|authorization|secret|cookie)/i.test(k)?'<redacted>':sanitize(v)]));
  return value;
}
export const test=base.extend({
  page:async({page},use,testInfo)=>{
    const id=testInfo.title.match(/\b(?:HOME|BRW|DASH|MYOP|CRT)-\d{3}\b/)?.[0];
    const observed=[];const pending=[];
    const onRequest=request=>{
      if(!request.url().includes('/api/v1/'))return;
      let requestBody=null;
      try{requestBody=request.postDataJSON()}catch{requestBody=request.postData()?.slice(0,1000)??null}
      observed.push({method:request.method(),url:request.url().replace(/^https?:\/\/[^/]+/,''),request:sanitize(requestBody),responseStatus:null,response:null});
    };
    const onResponse=response=>{
      if(!response.url().includes('/api/v1/'))return;
      pending.push((async()=>{
        let body=null;
        try{const txt=await response.text();try{body=JSON.parse(txt)}catch{body=txt.slice(0,900)}}catch{}
        const matching=[...observed].reverse().find(x=>x.responseStatus===null && x.method===response.request().method() && x.url===response.url().replace(/^https?:\/\/[^/]+/,''));
        if(matching){matching.responseStatus=response.status();matching.response=sanitize(body)}
      })());
    };
    page.on('request',onRequest);page.on('response',onResponse);
    try{await use(page)}finally{
      await Promise.allSettled(pending);
      await testInfo.attach('Expected vs actual HTTP evidence', {body:JSON.stringify({testId:id,approvedCase:catalog[id]??null,actualHttpExchanges:observed},null,2),contentType:'application/json'});
      if(!page.isClosed())try{
        const screenshot=await page.screenshot({fullPage:true,animations:'disabled',timeout:10000});
        await testInfo.attach(`Full-page screenshot (${testInfo.status})`,{body:screenshot,contentType:'image/png'});
      }catch(e){console.warn(`Screenshot unavailable for ${id}: ${e.message}`)}
      page.off('request',onRequest);page.off('response',onResponse);
    }
  },
});
export {expect};
