import {test,expect} from '../../helpers/screenshot-every-test.js';
import {openMine,mineItems} from '../../helpers/fixtures-62.js';

test('MYOP-001 @smoke Creator token used for authenticated My Opportunities fetch',async({page})=>{
 const sent=[];await openMine(page,{onRequest:req=>sent.push({method:req.method(),authorization:req.headers()['authorization']})});
 await expect(page.getByRole('heading',{name:'My Opportunities'})).toBeVisible();
 await expect(page.getByRole('textbox',{name:'Search opportunities'})).toBeVisible();
 await expect(page.getByRole('combobox',{name:'Filter by status'})).toBeVisible();
 await expect(page.getByRole('button',{name:'Refresh'})).toBeVisible();
 expect(sent).toHaveLength(1);expect(sent[0]).toEqual({method:'GET',authorization:'Bearer grow8-e2e-test-token'});
});
test('MYOP-002 @smoke Cards show API title/category/status/description/location/hours/deadline/compensation',async({page})=>{
 await openMine(page);
 const x=mineItems[0];const card=page.locator('.mo-card').filter({hasText:x.title});
 await expect(card).toContainText(x.title);
 await expect(card).toContainText(x.category.name);
 await expect(card).toContainText('Open');
 await expect(card).toContainText(x.description);
 await expect(card).toContainText('Calgary');
 await expect(card).toContainText('12 expected hours');
 await expect(card).toContainText('Deadline:');
 await expect(card).toContainText('$120 stipend');
});
