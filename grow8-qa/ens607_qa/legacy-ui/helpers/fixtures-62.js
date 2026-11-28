import {expect} from '@playwright/test';
import {baseItems} from './ui-fixtures.js';
export {baseItems};
export const mineItems=[
 {opportunity_id:301,title:'Inventory Audit',description:'Count warehouse stock with spreadsheets.',status:'open',category:{code:'knowledge',name:'Knowledge-based'},location:'Calgary',work_mode:'on_site',expected_hours:12,application_deadline:'2030-10-01T15:00:00Z',compensation_type:'stipend',compensation_amount:120},
 {opportunity_id:302,title:'Garden Volunteer',description:'Restore the community garden.',status:'draft',category:{code:'community',name:'Community'},location:'Edmonton',work_mode:'remote',expected_hours:5,application_deadline:'2030-11-01T15:00:00Z',compensation_type:'unpaid',compensation_amount:null},
 {opportunity_id:303,title:'Event Support',description:'Volunteer for weekend events.',status:'closed',category:{code:'community',name:'Community'},location:'Calgary',work_mode:'hybrid',expected_hours:9,application_deadline:'2030-12-01T15:00:00Z',compensation_type:'paid',compensation_amount:60},
];
export const categories=[{code:'knowledge',name:'Knowledge-based',description:'Remote knowledge work'},{code:'community',name:'Community',description:'Physical event support'}];
export const mockCors={'access-control-allow-origin':'*','access-control-allow-methods':'GET,POST,PATCH,OPTIONS','access-control-allow-headers':'authorization,content-type'};
export const jsonReply=(route,status,body)=>{
 const u=new URL(route.request().url());
 if(status===200 && u.pathname.endsWith('/opportunities/mine') && Array.isArray(body?.items) && body.total===undefined){
  const offset=Number(u.searchParams.get('offset')||0),limit=Number(u.searchParams.get('limit')||100),items=body.items;
  body={...body,items:items.slice(offset,offset+limit),total:items.length,limit,offset};
 }
 return route.fulfill({status,contentType:'application/json',headers:mockCors,body:JSON.stringify(body)});
};
export async function auth(page,token='grow8-e2e-test-token'){
 await page.addInitScript(t=>{localStorage.setItem('access_token',t);localStorage.setItem('user_name','Test Creator');},token);
}
export async function mockApi(page, handler, {applications=[],role='creator'}={}){
 await page.route('**/api/v1/**',async route=>{
  if(route.request().method()==='OPTIONS')return route.fulfill({status:204,headers:mockCors});
  const url=new URL(route.request().url());
  if(url.pathname.endsWith('/auth/me') && route.request().headers()['authorization']) return jsonReply(route,200,{user_id:2,email:'fixture@grow8.dev',full_name:'Test Creator',role});
  if(url.pathname.endsWith('/skills')) return jsonReply(route,200,[{code:'spreadsheets',name:'Spreadsheets'}]);
  if(url.pathname.endsWith('/applications/received')) return jsonReply(route,200,{items:applications,total:applications.length,limit:100,offset:0});
  if(url.pathname.endsWith('/submissions/received')) return jsonReply(route,200,{items:[],total:0,limit:100,offset:0});
  return handler(route,url.pathname,route.request());
 });
}
export async function openMine(page,{items=mineItems,status=200,token=true,onRequest}={}){
 if(token) await auth(page);
 await mockApi(page,async(route,path,request)=>{
  if(path.endsWith('/opportunities/mine')){
    onRequest?.(request);
    return jsonReply(route,status,status===200?{items}: {detail:'Temporary API error'});
  }
  return jsonReply(route,404,{detail:'not mocked'});
 });
 await page.goto('/creator/opportunities');
 if(status===200&&token)await expect(page.locator('.mo-card')).toHaveCount(items.length);
 else await expect(page.getByRole('alert')).toBeVisible();
}
export async function openCreate(page,{token=true,categoryItems=categories,categoryStatus=200,onCreate,onPublish}={}){
 if(token)await auth(page);
 await mockApi(page,async(route,path,request)=>{
  if(path.endsWith('/opportunities/mine'))return jsonReply(route,200,{items:[]});
  if(path.endsWith('/notifications/unread-count'))return jsonReply(route,200,{unread_count:0});
  if(path.endsWith('/notifications'))return jsonReply(route,200,{items:[],total:0,limit:20,offset:0});
  if(path.endsWith('/categories'))return jsonReply(route,categoryStatus,categoryStatus===200?{items:categoryItems}:{detail:'Categories unavailable'});
  if(path.endsWith('/opportunities')&&request.method()==='POST'){
    if(onCreate)return onCreate(route,request);
    return jsonReply(route,201,{opportunity_id:601,status:'draft'});
  }
  if(path.endsWith('/publish')&&request.method()==='POST'){
    if(onPublish)return onPublish(route,request);
    return jsonReply(route,200,{opportunity_id:601,status:'open'});
  }
  return jsonReply(route,404,{detail:'not mocked'});
 });
 await page.goto('/creator/opportunities/create');
 await expect(page.getByRole('heading',{name:'Create an Opportunity'})).toBeVisible();
 await expect(page.locator('#category_id')).toBeEnabled();
}
export async function fillValid(page){
 await page.locator('#title').fill('Community Digital Training');
 await page.locator('#category_id').selectOption('knowledge');
 await page.locator('#description').fill('Teach introductory digital literacy and support local volunteers.');
 await page.locator('#location').fill('Calgary');
 await page.locator('#work_mode').selectOption('remote');
 await page.locator('#start_date').fill('2030-10-20');
 await page.locator('#end_date').fill('2030-10-22');
 await page.locator('#application_deadline').fill('2030-10-18');
 await page.locator('#expected_hours').fill('8');
 await page.locator('#applicant_limit').fill('10');
 await page.locator('#requirements').fill('Basic computer skills');
 await page.locator('#working_conditions').fill('Daytime supervised work.');
 await page.locator('#safety_information').fill('Follow site safety guidance.');
 await page.locator('#accessibility_details').fill('Accessible workspace available.');
}
export const titleList=page=>page.locator('.browse-opportunity-card h3').allTextContents();
export const visibleBrowseCards=page=>page.locator('.browse-opportunity-card');
export const browseSearch=page=>page.getByRole('searchbox',{name:'Search opportunities'});
export const browseCount=page=>page.locator('.browse-results-count strong').last();
export async function browse(page,items=baseItems){
 await auth(page);
 await mockApi(page,async(route,path)=>path.endsWith('/opportunities')?jsonReply(route,200,{items,total:items.length}):jsonReply(route,404,{}));
 await page.goto('/opportunities');
 await expect(visibleBrowseCards(page)).toHaveCount(items.length);
}

export const dashboardItems=mineItems.map((item)=>({...item,organization:{organization_id:1,name:'Test Organization',city:'Calgary'}}));
export const dashboardApplications=[
 {application_id:401,status:'pending',opportunity:dashboardItems[0],applicant:{user_id:11,full_name:'QA Applicant One',skills:[],has_resume:false},submitted_at:'2026-10-10T12:00:00Z',decided_at:null,submission_id:null,work_status:'not_submitted'},
 {application_id:402,status:'accepted',opportunity:dashboardItems[0],applicant:{user_id:12,full_name:'QA Applicant Two',skills:[],has_resume:false},submitted_at:'2026-10-10T12:00:00Z',decided_at:'2026-10-11T12:00:00Z',submission_id:null,work_status:'not_submitted'},
 {application_id:403,status:'rejected',opportunity:dashboardItems[0],applicant:{user_id:13,full_name:'QA Applicant Three',skills:[],has_resume:false},submitted_at:'2026-10-10T12:00:00Z',decided_at:'2026-10-11T12:00:00Z',submission_id:null,work_status:'not_submitted'},
 {application_id:404,status:'accepted',opportunity:dashboardItems[2],applicant:{user_id:14,full_name:'QA Applicant Four',skills:[],has_resume:false},submitted_at:'2026-10-10T12:00:00Z',decided_at:'2026-10-11T12:00:00Z',submission_id:501,work_status:'completed'},
];
export async function openDashboard(page){
 await auth(page);
 await mockApi(page,(route,path)=>{
  if(path.endsWith('/opportunities/mine'))return jsonReply(route,200,{items:dashboardItems});
  if(path.endsWith('/notifications/unread-count'))return jsonReply(route,200,{unread_count:0});
  if(path.endsWith('/notifications'))return jsonReply(route,200,{items:[],total:0,limit:20,offset:0});
  return jsonReply(route,404,{});
 },{applications:dashboardApplications});
 await page.goto('/creator/dashboard');
 await expect(page.getByRole('heading',{name:'Welcome, Test Organization!'})).toBeVisible();
 await expect(page.locator('.creator-stats')).toHaveAttribute('aria-busy','false');
}
