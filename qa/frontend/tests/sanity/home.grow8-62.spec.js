import {test,expect} from '../../helpers/screenshot-every-test.js';
import {browse} from '../../helpers/fixtures-62.js';
test('HOME-003 @sanity Navbar Opportunities opens Browse',async({page})=>{
 await page.goto('/');
 await page.getByRole('link',{name:'Opportunities',exact:true}).click();
 await expect(page).toHaveURL(/\/opportunities$/);
 await expect(page.getByRole('heading',{name:'Browse Opportunities'})).toBeVisible();
});
test('HOME-004 @sanity Explore Opportunities opens Browse',async({page})=>{
 await page.goto('/');
 await page.getByRole('link',{name:'Explore Opportunities'}).click();
 await expect(page).toHaveURL(/\/opportunities$/);
 await expect(page.getByRole('heading',{name:'Browse Opportunities'})).toBeVisible();
});
