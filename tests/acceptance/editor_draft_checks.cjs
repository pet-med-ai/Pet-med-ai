// Real browser/application/database. Faults only block GET or browser storage;
// no successful API response is fabricated and no save is retried automatically.
const {chromium,expect}=require('@playwright/test');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const UI='http://127.0.0.1:5173',API='http://127.0.0.1:18026',PREFIX='pmai.case-edit-draft.v1.',out=process.env.PMAI_ACCEPTANCE_OUT;
assert(out && process.env.PMAI_SYNTHETIC_ACCEPTANCE==='PR26');
let browser,context,page,auth,cid;const passed=[],failures=[],pageErrors=[],external=[],writes=[];
const draft=()=>page.getByRole('region',{name:'病例编辑草稿',exact:true});
const review=()=>page.getByRole('region',{name:'病例修改核对',exact:true});
const field=label=>page.locator('label').filter({has:page.getByText(label,{exact:true})}).locator('textarea');
const treatment=()=>field('治疗建议'),history=()=>field('既往史 / 动态问诊追问记录');
const next=suffix=>page.waitForResponse(r=>r.request().method()==='POST' && new URL(r.url()).pathname.endsWith(suffix));
const cached=()=>page.evaluate(key=>sessionStorage.getItem(key),PREFIX+cid);
async function request(method,route,data){assert(route.startsWith('/api/'));const r=await context.request.fetch(API+route,{method,headers:auth,data});assert.equal(r.status(),method==='POST'&&route==='/api/cases'?201:200,await r.text());return r.json();}
async function record(name){passed.push(name);console.log('PASS:',name);await page.screenshot({path:path.join(out,`editor-draft-${passed.length}-${name}.png`),fullPage:true});}
async function login(owner='browser-owner'){
 await page.getByPlaceholder('邮箱',{exact:true}).fill(owner+'@example.com');await page.getByPlaceholder('密码',{exact:true}).fill('Synthetic-PR26-only-20260916');
 const r=next('/auth/login');await page.getByRole('button',{name:'登录',exact:true}).click();assert.equal((await r).status(),200);
 await expect(page.getByRole('button',{name:'退出',exact:true})).toBeVisible();auth={Authorization:'Bearer '+await page.evaluate(()=>localStorage.getItem('token'))};
}
async function newCase(name){const c=await request('POST','/api/cases',{patient_name:name,species:'dog',chief_complaint:'编辑草稿合成主诉',history:'  服务器病史🐾\r\n保留尾部。  \n'});await request('PUT','/api/cases/'+c.id,{treatment:'服务器原治疗'});return c.id;}
async function openEditor(id=cid){await page.goto(UI+'/cases/'+id+'/edit');await expect(page.getByRole('heading',{name:'编辑病例 #'+id,exact:true})).toBeVisible();}
async function reloadOffer(){await page.reload();await expect(draft()).toContainText('发现本病例未保存的编辑草稿');}
async function restore(){const n=writes.length;await draft().getByRole('button',{name:'恢复本病例编辑草稿',exact:true}).click();await expect(draft().getByRole('button',{name:'恢复本病例编辑草稿',exact:true})).toHaveCount(0);assert.equal(writes.length,n);}
async function preview(){const r=next('/preview-edit');await review().getByRole('button',{name:/^(核对修改内容|重新核对修改)$/}).click();assert.equal((await r).status(),200);await review().getByLabel('已核对本次病例修改',{exact:true}).check();}
async function main(){
 browser=await chromium.launch({headless:true});console.log('Chromium editor draft acceptance:',browser.version());
 context=await browser.newContext({viewport:{width:1440,height:1000},serviceWorkers:'block'});
 await context.route('**/*',route=>{const origin=new URL(route.request().url()).origin;if([UI,API].includes(origin))return route.continue();external.push(origin);return route.abort();});
 page=await context.newPage();page.on('dialog',d=>d.accept());page.on('pageerror',e=>pageErrors.push(e.message));page.on('request',r=>{if(['POST','PUT','PATCH','DELETE'].includes(r.method()))writes.push(new URL(r.url()).pathname);});
 await page.goto(UI);await login();cid=await newCase('编辑草稿合成犬');await openEditor();
 const original=await request('GET','/api/cases/'+cid),text='  未保存治疗🐾\n保留尾部。  \n';await treatment().fill(text);
 const n=writes.length;await reloadOffer();await expect(treatment()).toHaveValue(original.treatment);await expect(treatment()).toBeDisabled();assert.equal(writes.length,n);
 await restore();await expect(treatment()).toHaveValue(text);assert.deepEqual(await request('GET','/api/cases/'+cid),original);assert.deepEqual(JSON.parse(await cached()).changes,{treatment:text});await record('refresh_restores_exact_changed_fields_without_write');

 await preview();await reloadOffer();const newer=original.history+'\n另一医生的新病史';await request('PUT','/api/cases/'+cid,{history:newer});await restore();
 await expect(history()).toHaveValue(newer.replace(/\r\n/g,'\n'));await expect(treatment()).toHaveValue(text);await expect(review().getByLabel('已核对本次病例修改',{exact:true})).toHaveCount(0);await expect(review().getByRole('button',{name:'确认并保存修改',exact:true})).toHaveCount(0);await record('recovery_adopts_latest_untouched_fields_and_discards_confirmation');

 await preview();await review().getByRole('button',{name:'确认并保存修改',exact:true}).click();await expect(review().getByRole('region',{name:'修改后服务器回读',exact:true})).toBeVisible();assert.equal(await cached(),null);assert.equal((await request('GET','/api/cases/'+cid)).history,newer);await record('reviewed_save_and_readback_clear_editor_draft');
 await treatment().fill('保存后的新输入');await reloadOffer();await restore();await expect(treatment()).toHaveValue('保存后的新输入');assert.equal((await request('GET','/api/cases/'+cid)).treatment,text);await record('later_edit_stays_separate_from_saved_case');

 await reloadOffer();const raw=await cached(),getRoute='**/api/cases/'+cid+'/edit-state';await page.route(getRoute,route=>route.abort('failed'));const beforeRetry=writes.length;
 await draft().getByRole('button',{name:'恢复本病例编辑草稿',exact:true}).click();await expect(draft()).toContainText('暂时无法读取最新病例');assert.equal(await cached(),raw);
 await page.unroute(getRoute);await restore();assert.equal(writes.length,beforeRetry);await expect(treatment()).toHaveValue('保存后的新输入');await record('failed_recovery_keeps_draft_and_retries_get_only');

 await request('PUT','/api/cases/'+cid,{owner_phone:'synthetic-intervening-update'});let r=next('/preview-edit');await review().getByRole('button',{name:'核对修改内容',exact:true}).click();assert.equal((await r).status(),409);await expect(treatment()).toHaveValue('保存后的新输入');assert.equal((await request('GET','/api/cases/'+cid)).treatment,text);await record('intervening_server_change_still_rejects_stale_draft_preview');
 await review().getByRole('button',{name:'读取最新病例并保留本次修改',exact:true}).click();await expect(review()).toContainText('已读取最新病例');await preview();
 await page.route(getRoute,route=>route.abort('failed'));await review().getByRole('button',{name:'确认并保存修改',exact:true}).click();await expect(review()).toContainText('保存结果待核对');const confirmed=writes.filter(x=>x.endsWith('/confirm-edit')).length;
 await page.unroute(getRoute);await reloadOffer();await restore();await expect(draft()).toContainText('草稿中的修改与服务器一致');assert.equal(await cached(),null);assert.equal(writes.filter(x=>x.endsWith('/confirm-edit')).length,confirmed);await expect(review().getByRole('button',{name:'核对修改内容',exact:true})).toBeDisabled();await record('refresh_after_committed_save_resolves_by_get_without_second_post');

 await treatment().fill('病例甲待保存');const first=cid;cid=await newCase('另一个编辑草稿合成犬');await openEditor();await expect(treatment()).toHaveValue('服务器原治疗');await expect(draft()).not.toContainText('发现本病例未保存的编辑草稿');await treatment().fill('病例乙待保存');const second=cid;
 cid=first;await openEditor();await restore();await expect(treatment()).toHaveValue('病例甲待保存');assert(await page.evaluate(key=>!!sessionStorage.getItem(key),PREFIX+second));await record('different_cases_keep_separate_editor_drafts');
 await reloadOffer();const beforeDiscard=writes.length;await draft().getByRole('button',{name:'丢弃编辑草稿',exact:true}).click();await expect(treatment()).toHaveValue('保存后的新输入');assert.equal(await cached(),null);assert(await page.evaluate(key=>!!sessionStorage.getItem(key),PREFIX+second));assert.equal(writes.length,beforeDiscard);await record('discard_only_removes_selected_case_draft_without_write');

 await treatment().fill('退出前未保存');await page.getByRole('button',{name:'返回首页',exact:true}).click();await page.getByRole('button',{name:'退出',exact:true}).click();await expect(page.getByRole('button',{name:'登录',exact:true})).toBeVisible();assert.equal(await page.evaluate(prefix=>Object.keys(sessionStorage).filter(k=>k.startsWith(prefix)).length,PREFIX),0);
 await login('pg-other');await openEditor();await expect(draft()).not.toContainText('发现本病例未保存的编辑草稿');await expect(treatment()).toHaveValue('');await expect(treatment()).toBeDisabled();await record('logout_clears_all_editor_drafts_before_another_account');
 await page.getByRole('button',{name:'返回首页',exact:true}).click();await page.getByRole('button',{name:'退出',exact:true}).click();await login();cid=await newCase('编辑草稿故障合成犬');
 await page.evaluate(key=>sessionStorage.setItem(key,'{broken'),PREFIX+cid);await openEditor();await expect(draft()).toContainText('编辑草稿不可读取或已过期');await expect(treatment()).toHaveValue('服务器原治疗');assert.equal(await cached(),null);await record('corrupt_editor_draft_does_not_replace_server_content');
 await treatment().fill('即将过期的输入');await page.evaluate(key=>{const d=JSON.parse(sessionStorage.getItem(key));d.updatedAt=Date.now()-9*60*60*1000;sessionStorage.setItem(key,JSON.stringify(d));},PREFIX+cid);await page.reload();await expect(draft()).toContainText('编辑草稿不可读取或已过期');await expect(treatment()).toHaveValue('服务器原治疗');assert.equal(await cached(),null);await record('expired_editor_draft_is_rejected_without_write');
 await treatment().fill('存储故障前输入');await page.evaluate(prefix=>{const original=Storage.prototype.setItem;Storage.prototype.setItem=function(key,value){if(this===sessionStorage&&key.startsWith(prefix))throw new DOMException('Synthetic quota fault','QuotaExceededError');return original.call(this,key,value);};},PREFIX);
 await treatment().fill('存储故障后的最新输入');await expect(draft()).toContainText('浏览器无法暂存最新修改');await expect(treatment()).toHaveValue('存储故障后的最新输入');assert.equal(await cached(),null);assert.equal((await request('GET','/api/cases/'+cid)).treatment,'服务器原治疗');assert.deepEqual(pageErrors,[]);assert.deepEqual(external,[]);await record('storage_failure_keeps_current_input_and_removes_stale_cache');
}
main().then(()=>{process.exitCode=0;}).catch(async error=>{process.exitCode=1;console.error(error);failures.push(String(error));if(page){await page.screenshot({path:path.join(out,'editor-draft-failure.png'),fullPage:true}).catch(()=>{});fs.writeFileSync(path.join(out,'editor-draft-failure-dom.txt'),await page.locator('body').innerText().catch(()=>''));}}).finally(async()=>{fs.writeFileSync(path.join(out,'editor-draft-checks.json'),JSON.stringify({passed,failures,pageErrors,external},null,2));if(browser)await browser.close();});
