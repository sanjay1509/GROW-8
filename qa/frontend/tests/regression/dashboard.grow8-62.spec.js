import {test,expect} from '../../helpers/screenshot-every-test.js';
import {auth,mockApi,jsonReply,mineItems} from '../../helpers/fixtures-62.js';
test('DASH-005 @regression Recent Applications show all three status badges',async({page})=>{
 await page.goto('/creator/dashboard');
 const table=page.getByRole('table',{name:'Recent applications'});
 for(const status of ['Under Review','Selected','Rejected'])await expect(table.getByText(status,{exact:true}).first()).toBeVisible();
});
test('DASH-008 @regression Preview card navigates to My Opportunities without crash',async({page})=>{
 await auth(page);await mockApi(page,(route,path)=>path.endsWith('/opportunities/mine')?jsonReply(route,200,{items:mineItems}):jsonReply(route,404,{}));
 await page.goto('/creator/dashboard');
 await page.locator('.creator-opportunity-card').first().click();
 await expect(page).toHaveURL(/\/creator\/opportunities$/);
 await expect(page.getByRole('heading',{name:'My Opportunities'})).toBeVisible();
});
test('DASH-009 @regression Sidebar links work and mark the active route',async({page})=>{
 await auth(page);await mockApi(page,(route,path)=>path.endsWith('/opportunities/mine')?jsonReply(route,200,{items:mineItems}):jsonReply(route,404,{}));
 await page.goto('/creator/dashboard');
 const sidebar=page.getByRole('navigation',{name:'Creator navigation'});
 await expect(sidebar.getByRole('link',{name:'Dashboard'})).toHaveClass(/is-active/);
 await sidebar.getByRole('link',{name:'My Opportunities'}).click();
 await expect(page).toHaveURL(/\/creator\/opportunities$/);
 await expect(sidebar.getByRole('link',{name:'My Opportunities'})).toHaveClass(/is-active/);
 await sidebar.getByRole('link',{name:'Dashboard'}).click();
 await expect(page).toHaveURL(/\/creator\/dashboard$/);
 await expect(sidebar.getByRole('link',{name:'Dashboard'})).toHaveClass(/is-active/);
});
test('DASH-010 @regression Notification count and dismiss on Escape or outside click',async({page})=>{
 await auth(page);
 const notification={
  notification_id:1,notification_type:'application_submitted',title:'New application',
  message:'A contributor applied to Social Media Support.',opportunity_id:1,
  read_at:null,created_at:'2026-10-10T12:00:00Z',is_read:false,
 };
 await mockApi(page,(route,path)=>{
  if(path.endsWith('/notifications/unread-count'))return jsonReply(route,200,{unread_count:7});
  if(path.endsWith('/notifications'))return jsonReply(route,200,{items:[notification],total:1,limit:20,offset:0});
  if(path.endsWith('/auth/me'))return jsonReply(route,200,{user_id:2,email:'creator@example.test',full_name:'Test Creator',role:'creator'});
  return jsonReply(route,404,{});
 });
 await page.goto('/creator/dashboard');
 const bell=page.getByRole('button',{name:/Notifications: \d+ unread/});
 await expect(bell).toHaveAttribute('aria-label','Notifications: 7 unread');
 await bell.click();
 await expect(page.locator('#creator-notifications')).toBeVisible();
 await expect(page.locator('#creator-notifications')).toContainText('New application');
 await expect(page.locator('#creator-notifications').getByRole('link')).toContainText(/7 applications under review/);
 await page.keyboard.press('Escape');await expect(page.locator('#creator-notifications')).toHaveCount(0);
 await bell.click();await expect(page.locator('#creator-notifications')).toBeVisible();
 await page.getByRole('heading',{name:'Recent Applications'}).click();
 await expect(page.locator('#creator-notifications')).toHaveCount(0);
});
