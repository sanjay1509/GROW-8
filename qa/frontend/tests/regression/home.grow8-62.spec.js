import {test,expect} from '../../helpers/screenshot-every-test.js';

test('HOME-005 @regression Contributor and Creator cards navigate to configured destinations',async({page})=>{
 await page.goto('/');
 const contributor=page.getByRole('button',{name:'Open Contributor Dashboard'});
 const creator=page.getByRole('button',{name:'Open Creator Dashboard'});
 await expect(contributor).toBeVisible();await expect(creator).toBeVisible();
 await expect(contributor).toContainText('Find opportunities, gain skills');
 await expect(creator).toContainText('Post opportunities');
 await contributor.click();await expect(page).toHaveURL(/\/contributor-dashboard$/);
 await page.goto('/');await page.getByRole('button',{name:'Open Creator Dashboard'}).click();
 await expect(page).toHaveURL(/\/creator\/dashboard$/);
});
test('HOME-006 @regression Featured cards show sample opportunities and metadata',async({page})=>{
 await page.goto('/');
 const cards=page.locator('.grow8-featured .grow8-opportunity-card');
 // Sample order intentionally random: assert membership, not position.
 await expect(cards).toHaveCount(3);
 for(const title of ['Social Media Support','Event Volunteer Support','Data Entry and Organization']){
   await expect(page.locator('.grow8-featured').getByText(title,{exact:true})).toBeVisible();
 }
 await expect(page.locator('.grow8-featured').getByText('Green Future NGO')).toBeVisible();
 await expect(page.locator('.grow8-featured').getByText('Calgary, AB').first()).toBeVisible();
});
test('HOME-007 @regression Featured View All navigates to Browse',async({page})=>{
 await page.goto('/');await page.locator('.grow8-featured').getByRole('link',{name:/View All/}).click();
 await expect(page).toHaveURL(/\/opportunities$/);
});
test('HOME-008 @regression About, Mission, Purpose, Vision are present',async({page})=>{
 await page.goto('/');
 for(const label of ['About Grow8','Our Mission','Our Purpose','Our Vision']){
   await expect(page.getByRole('heading',{name:label})).toBeVisible();
 }
});
test('HOME-009 @regression Back to Top scrolls window to top',async({page})=>{
 await page.goto('/');
 await page.evaluate(()=>window.scrollTo(0,document.body.scrollHeight));
 await expect(page.getByRole('button',{name:'Back to top'})).toHaveClass(/visible/);
 await page.getByRole('button',{name:'Back to top'}).click();
 await expect.poll(()=>page.evaluate(()=>window.scrollY),{timeout:10000}).toBeLessThan(20);
});
