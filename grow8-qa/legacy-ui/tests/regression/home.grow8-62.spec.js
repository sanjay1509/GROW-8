import {test,expect} from '../../helpers/screenshot-every-test.js';
import {baseItems,jsonReply,mockApi} from '../../helpers/fixtures-62.js';

test('UI-050 HOME-005 @regression Contributor and Creator cards navigate to configured destinations',async({page})=>{
 await page.goto('/');
 const contributor=page.getByRole('button',{name:'Contributor sign in options'});
 const creator=page.getByRole('button',{name:'Creator sign in options'});
 await expect(contributor).toBeVisible();await expect(creator).toBeVisible();
 await expect(contributor).toContainText('Find opportunities, gain skills');
 await expect(creator).toContainText('Post opportunities');
 await contributor.click();
 await expect(page.getByRole('dialog').getByRole('heading',{name:'Continue as a Contributor'})).toBeVisible();
 await page.getByRole('button',{name:'Log in as a Contributor'}).click();
 await expect(page).toHaveURL(/\/login\?role=contributor&mode=login/);
 await page.goto('/');await creator.click();
 await expect(page.getByRole('dialog').getByRole('heading',{name:'Continue as a Creator'})).toBeVisible();
 await page.getByRole('button',{name:'Log in as a Creator'}).click();
 await expect(page).toHaveURL(/\/login\?role=creator&mode=login/);
 // Logged-in role cards still route directly to their own dashboards.
 let role='creator';
 await page.route('**/api/v1/auth/me',route=>jsonReply(route,200,{user_id:2,email:'fixture@grow8.dev',full_name:'Test User',role}));
 await page.evaluate(()=>localStorage.setItem('access_token','grow8-e2e-test-token'));
 await page.goto('/');await creator.click();await expect(page).toHaveURL(/\/creator\/dashboard$/);
 role='contributor';await page.goto('/');await contributor.click();await expect(page).toHaveURL(/\/contributor-dashboard$/);
});
test('UI-051 HOME-006 @regression Featured cards show sample opportunities and metadata',async({page})=>{
 const featuredItems=baseItems.slice(0,3);
 await mockApi(page,(route,path)=>path.endsWith('/opportunities')
  ?jsonReply(route,200,{items:featuredItems,total:featuredItems.length})
  :jsonReply(route,404,{}));
 await page.goto('/');
 const cards=page.locator('.grow8-featured .grow8-opportunity-card');
 await expect(cards).toHaveCount(3);
 for(const title of featuredItems.map(item=>item.title)){
   await expect(page.locator('.grow8-featured').getByText(title,{exact:true})).toBeVisible();
 }
 await expect(page.locator('.grow8-featured').getByText('Maple Street Bakery')).toBeVisible();
 await expect(page.locator('.grow8-featured').getByText('Calgary').first()).toBeVisible();
});
test('UI-052 HOME-007 @regression Featured View All navigates to Browse',async({page})=>{
 await page.goto('/');await page.locator('.grow8-featured').getByRole('link',{name:/View All/}).click();
 await expect(page).toHaveURL(/\/opportunities$/);
});
test('UI-053 HOME-008 @regression About, Mission, Purpose, Vision are present',async({page})=>{
 await page.goto('/');
 for(const label of ['About Grow8','Our Mission','Our Purpose','Our Vision']){
   await expect(page.getByRole('heading',{name:label})).toBeVisible();
 }
});
test('UI-054 HOME-009 @regression Back to Top scrolls window to top',async({page})=>{
 await page.goto('/');
 await page.evaluate(()=>window.scrollTo(0,document.body.scrollHeight));
 await expect(page.getByRole('button',{name:'Back to top'})).toHaveClass(/visible/);
 await page.getByRole('button',{name:'Back to top'}).click();
 await expect.poll(()=>page.evaluate(()=>window.scrollY),{timeout:10000}).toBeLessThan(20);
});
