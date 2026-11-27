import {expect} from '@playwright/test';
// Frontend-only deterministic data. These tests do not change Grow8 MySQL or backend.
export const baseItems = [
  { opportunity_id:101, title:'Data Entry Support', description:'Organize community spreadsheets.',category:{code:'knowledge',name:'Knowledge-based'},organization:{name:'Maple Street Bakery',city:'Calgary'},work_mode:'remote',expected_hours:8,application_deadline:'2030-08-10T18:00:00Z',skills:[{name:'Spreadsheets'}],location:'Calgary',compensation_type:'paid' },
  { opportunity_id:102, title:'Community Garden Cleanup',description:'Help the local community garden.',category:{code:'community',name:'Community'},organization:{name:'Bow River Community Food Bank',city:'Calgary'},work_mode:'on_site',expected_hours:4,application_deadline:'2030-07-05T18:00:00Z',skills:[{name:'Event setup'}],location:'Calgary' },
  { opportunity_id:103, title:'Inventory Spreadsheet Cleanup',description:'Clean inventory records.',category:{code:'knowledge',name:'Knowledge-based'},organization:{name:'YYC Neighbourhood Events',city:'Calgary'},work_mode:'hybrid',expected_hours:12,application_deadline:'2030-09-15T18:00:00Z',skills:[{name:'Spreadsheets'},{name:'Inventory management'}],location:'Calgary' },
  { opportunity_id:104, title:'Remote Content Review',description:'Translate outreach materials.',category:{code:'knowledge',name:'Knowledge-based'},organization:{name:'Blue River Collective',city:'Edmonton'},work_mode:'remote',expected_hours:3,application_deadline:'2030-11-20T18:00:00Z',skills:[{name:'Translation'}],location:'Edmonton' },
  { opportunity_id:105, title:'On-site Photography',description:'Photograph a local event.',category:{code:'community',name:'Community'},organization:{name:'City Arts Festival',city:'Calgary'},work_mode:'on_site',expected_hours:10,application_deadline:'2030-10-01T18:00:00Z',skills:[{name:'Photography'}],location:'Calgary' },
  { opportunity_id:106, title:'Hybrid Event Planning',description:'Plan an event with volunteers.',category:{code:'community',name:'Community'},organization:{name:'Civic Volunteers',city:'Calgary'},work_mode:'hybrid',expected_hours:5,application_deadline:'2030-12-01T18:00:00Z',skills:[{name:'Event setup'}],location:'Calgary' },
];

export const cards = page => page.locator('.browse-opportunity-card');
export const names = async page => cards(page).locator('h3').allTextContents();
export const search = page => page.getByRole('searchbox', { name: 'Search opportunities' });
export const sort = page => page.getByRole('combobox', { name: 'Sort opportunities' });
export const group = (page,name) => page.getByRole('group', {name});
export const checkbox = (page,name,label) => group(page,name).getByLabel(label,{exact:true});
export const cardFor = (page,title) => cards(page).filter({has:page.getByRole('heading',{name:title,exact:true})});
export const countLabel = page => page.locator('.browse-results-count strong');
export const dialog = page => page.getByRole('dialog');
export const offsetDay = days => {const d=new Date();d.setHours(12,0,0,0);d.setDate(d.getDate()+days);return d.toISOString().slice(0,10)+'T18:00:00Z';};
export const dataItem = (id,title,opts={}) => ({...baseItems[0],opportunity_id:id,title,...opts});

export async function openFixture(page,{items=baseItems,status=200,payload,delay=0,networkFailure=false}={}) {
  await page.route('**/api/v1/opportunities?**',async route => {
    if (networkFailure) return route.abort('failed');
    if(delay) await new Promise(resolve=>setTimeout(resolve,delay));
    return route.fulfill({status,contentType:'application/json',body:JSON.stringify(payload ?? (status===200?{items,total:items.length}:{error:'Test error'}))});
  });
  await page.goto('/opportunities');
  if (!delay) {
    const effectiveItems = payload ? payload.items : items;
    if (networkFailure || status !== 200 || !Array.isArray(effectiveItems)) {
      await page.getByRole('heading', {name: 'Unable to load opportunities'}).waitFor();
    } else if (effectiveItems.length === 0) {
      await page.getByRole('heading', {name: 'No opportunities found'}).waitFor();
    } else {
      await expect(cards(page)).toHaveCount(effectiveItems.length);
    }
  }
}
export async function openHome(page) {await page.goto('/');}
