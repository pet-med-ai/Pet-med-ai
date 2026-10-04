// Actual Chromium + isolated authenticated API. Faults never fabricate AI success.
const {chromium,expect}=require('@playwright/test');
const assert=require('node:assert/strict'), fs=require('node:fs'), path=require('node:path');
const {execFileSync}=require('node:child_process');
const UI='http://127.0.0.1:5173', API='http://127.0.0.1:18026', out=process.env.PMAI_ACCEPTANCE_OUT;
assert(out && process.env.PMAI_SYNTHETIC_ACCEPTANCE==='PR26'); fs.mkdirSync(out,{recursive:true});
const families = ['appetite_weight', 'polyuria_polydipsia', 'cough_breathing', 'syncope_seizure', 'urinary_abnormality', 'itching_hair_loss', 'lameness_pain'].filter(k=>fs.existsSync(path.join(__dirname,'../../knowledge-base/companion/intake',k+'.json')));
assert(families.includes('appetite_weight'));
let family, title, config, batch, browser,context,page,auth; const passed=[],failures=[],external=[],errors=[],samples=[];
const region=name=>page.getByRole('region',{name,exact:true});
const field=label=>page.locator('label').filter({has:page.getByText(label,{exact:true})}).locator('input,textarea,select');
const form=()=>region('犬猫'+title+'问诊');
const q=key=>form().locator('[data-intake-question="'+key+'"]');
const record=async name=>{passed.push(family+'_'+name);console.log('PASS:',name);await page.screenshot({path:path.join(out,'b1-'+passed.length+'.png'),fullPage:true});};
async function login(){
 await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill('browser-owner@example.com');await page.getByPlaceholder('密码',{exact:true}).fill('Synthetic-PR26-only-20260916');
 await page.getByRole('button',{name:'登录',exact:true}).click();await expect(page.getByRole('button',{name:'退出',exact:true})).toBeVisible();
 auth={Authorization:'Bearer '+await page.evaluate(()=>localStorage.getItem('token'))};
}
async function read(id){const r=await context.request.get(API+'/api/cases/'+id,{headers:auth});assert.equal(r.status(),200);return r.json();}
async function confirmIntake(){
 await form().getByRole('button',{name:'核对'+title+'问卷汇总',exact:true}).click();
 await form().getByRole('button',{name:'确认当前'+title+'问卷',exact:true}).click();
 await expect(form()).toContainText('当前'+title+'问卷已核对');
}
async function setup(){
 context=await browser.newContext({acceptDownloads:true,serviceWorkers:'block',viewport:{width:1440,height:1000}});
 await context.route('**/*',r=>{if([UI,API].includes(new URL(r.request().url()).origin))return r.continue();external.push(r.request().url());return r.abort();});
 page=await context.newPage();page.on('dialog',d=>d.accept());page.on('pageerror',e=>errors.push(e.message)); await login();
}
async function runAnimal(animal){
 await setup(); const raw='  '+animal+'医生原文🐾\n未见黑便 <5 & >2 {{literal}}\t保留尾部  \n'+(animal==='cat'?'长原文不截断🐾\n'.repeat(90):'');
 const original='  原医生病史🐾\n末尾保留。  \n';
 await field('病例名 / 宠物名').fill(batch+'合成'+animal);await field('物种').selectOption(animal);await field('主诉（必填）').fill('合成'+title+'采集，非真实病例');await field('既往史').fill(original);
 await field('主人姓名').fill(batch+'合成宠主'+animal);await field('毛色').fill(animal==='dog'?'合成黑白色':'合成虎斑色');
 await page.getByLabel('选择主诉问诊',{exact:true}).selectOption(family);
 await page.getByRole('button',{name:'使用犬猫'+title+'问诊',exact:true}).click();await form().getByRole('button',{name:'开始'+title+'问诊',exact:true}).click();
 await q('onset').locator('select').selectOption('observed');await q('onset').locator('textarea').fill('医生记录起病经过');
 const textRows=config.questions.filter(q=>q.kind==='text'&&!q.when&&!['onset','notes'].includes(q.key));
 const branch=config.questions.find(q=>q.when);
 await q(textRows[0].key).locator('select').selectOption('not_asked');await q(textRows[1].key).locator('select').selectOption('uncertain');
 await q(textRows[2].key).locator('select').selectOption('unobservable');await q(branch.when).locator('select').selectOption('observed');
 await q(branch.key).locator('select').selectOption('observed');await q(branch.key).locator('textarea').fill('原条件分支🐾\n保留原文');
 await q(branch.when).locator('select').selectOption('absent');await expect(q(branch.key).locator('textarea')).toHaveValue('原条件分支🐾\n保留原文');await expect(q(branch.key).locator('textarea')).not.toBeEditable();
 await q('notes').locator('select').selectOption('observed');await q('notes').locator('textarea').fill(raw);await confirmIntake();
 await q('notes').locator('textarea').fill(raw+'修改');await expect(form()).not.toContainText('当前'+title+'问卷已核对');await q('notes').locator('textarea').fill(raw);
 await page.getByRole('button',{name:'收起问卷并保留输入',exact:true}).click();await expect(form()).not.toBeVisible();await page.getByRole('button',{name:'使用犬猫'+title+'问诊',exact:true}).click();await expect(q('notes').locator('textarea')).toHaveValue(raw);await expect(form()).not.toContainText('当前'+title+'问卷已核对');
 await page.reload();await page.getByRole('button',{name:'恢复本页草稿',exact:true}).click();await expect(q('notes').locator('textarea')).toHaveValue(raw);await expect(form()).not.toContainText('当前'+title+'问卷已核对');
 await field('物种').selectOption(animal==='dog'?'cat':'dog');await expect(form()).toContainText('旧确认已失效');await expect(form().getByRole('button',{name:'核对'+title+'问卷汇总',exact:true})).toBeDisabled();await field('物种').selectOption(animal);
 await confirmIntake();await record(animal+'_explicit_intake_states_inactive_raw_refresh_and_species_guard');
 let id;
 if(animal==='dog'){
  const created=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/ai/consult/session');await page.getByRole('button',{name:'提交分析（不入库）',exact:true}).click();const r=await created;assert.equal(r.status(),200);const s=await r.json();assert(s.answers[0].structured_intake_snapshot);
  await expect(form()).not.toContainText('当前'+title+'问卷已核对');await confirmIntake();
  await page.getByPlaceholder('如 HS-0001 / Dr.Zhao',{exact:true}).fill(batch+'-Synthetic');await page.getByRole('button',{name:'确认覆核并写入审计',exact:true}).click();await expect(page.getByRole('button',{name:'审计已写入',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'进入保存前核对 →',exact:true}).click();const save=region('首次保存病例核对');await save.getByRole('button',{name:'核对保存内容',exact:true}).click();await save.getByLabel('已核对本次保存内容',{exact:true}).check();
  let writes=0;const endpoint='**/api/ai/consult/session/*/save-case';await page.route(endpoint,r=>{writes++;return r.continue();});
  await save.getByRole('button',{name:'确认并保存病例',exact:true}).evaluate(e=>{e.click();e.click();});await expect(region('本次保存回读')).toBeVisible();assert.equal(writes,1);await page.unroute(endpoint);
  const state=await context.request.get(API+'/api/ai/consult/session/'+s.session_id,{headers:auth});id=(await state.json()).case_id;
  await record('dog_ai_context_snapshot_and_reviewed_duplicate_click_save_once');
 }else{
  const endpoint='**/api/ai/consult/session';await page.route(endpoint,r=>r.fulfill({status:503,contentType:'application/json',body:'{"detail":"Synthetic AI unavailable"}'}));
  await page.getByRole('button',{name:'提交分析（不入库）',exact:true}).click();await expect(page.locator('body')).toContainText('分析请求失败');await page.unroute(endpoint);await expect(q('notes').locator('textarea')).toHaveValue(raw);
  await confirmIntake();await page.getByRole('button',{name:'手工新建（核对后保存）',exact:true}).click();const manual=region('手工新建病例核对');await manual.getByRole('button',{name:'核对新建内容',exact:true}).click();await manual.getByLabel('已核对本次新建内容',{exact:true}).check();
  let writes=0;await page.route('**/api/cases',r=>{if(r.request().method()==='POST')writes++;return r.continue();});
  let blocked=true;await page.route(/\/api\/cases\/\d+$/,r=>{if(r.request().method()==='GET'&&blocked){blocked=false;return r.abort();}return r.continue();});
  await manual.getByRole('button',{name:'确认并创建病例',exact:true}).evaluate(e=>{e.click();e.click();});await expect(manual.getByRole('button',{name:'核对保存结果',exact:true})).toBeVisible();
  await page.reload();await region('手工新建病例核对').getByRole('button',{name:'核对保存结果',exact:true}).click();await expect(region('手工新建病例核对')).toContainText('本次核对的十五项内容一致');assert.equal(writes,1);
  const receipt=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pmai.manual-create-attempt.v1')));id=receipt.caseId;assert.equal(Object.keys(receipt.payload).length,15);
  await page.unroute('**/api/cases');await page.unroute(/\/api\/cases\/\d+$/);await record('cat_ai_failure_manual_fifteen_fields_unknown_readback_get_only');
 }
 let saved=await read(id);assert(saved.history.startsWith(original));assert.equal(saved.history.split(raw).length-1,1);
 for(const state of ['未填写','未询问','明确否定','不确定','无法观察','已记录'])assert(saved.history.includes('状态：'+state),state);
 assert(saved.history.includes('当前不适用'));assert(saved.history.includes('模板版本：'+family+'-intake-v1+'));assert(saved.history.includes('医生采集'));
 await page.goto(UI);await page.getByRole('button',{name:'退出',exact:true}).click();await login();await page.goto(UI+'/cases/'+id);await page.reload();
 assert.equal(await region('完整病史原文').locator('.text-body').textContent(),saved.history);
 await page.getByRole('link',{name:'编辑',exact:true}).click();await field('既往史 / 动态问诊追问记录').fill(saved.history+'\n'+batch+'医生核对更正🐾');const edit=region('病例修改核对');await edit.getByRole('button',{name:'核对修改内容',exact:true}).click();await edit.getByLabel('已核对本次病例修改',{exact:true}).check();await edit.getByRole('button',{name:'确认并保存修改',exact:true}).click();await expect(region('修改后服务器回读')).toBeVisible();
 saved=await read(id);assert(saved.history.includes(raw));assert(saved.history.endsWith(batch+'医生核对更正🐾'));await edit.getByRole('link',{name:'查看已保存病例 #'+id,exact:true}).click();
 await record(animal+'_logout_relogin_backread_and_reviewed_correction_keep_original');
 for(const [label,key] of [['导出门诊病历草稿 DOCX','outpatient'],['导出宠主说明草稿 DOCX','owner-summary']]){
  const event=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/clinical-docs/render-preview');await page.getByRole('button',{name:label,exact:true}).click();const p=await (await event).json();assert.equal(p.context['visit.history'],saved.history);
  if(key==='outpatient'){assert.equal(p.context['visit.owner_name'],batch+'合成宠主'+animal);assert.equal(p.context['visit.coat_color'],animal==='dog'?'合成黑白色':'合成虎斑色');}
  const review=region('文书草稿内容核对');await expect(review.getByRole('button',{name:'确认并下载草稿 DOCX',exact:true})).toBeDisabled();
  await review.getByLabel('已核对本次草稿内容（仍未签署）',{exact:true}).check();const eventDownload=page.waitForEvent('download');await review.getByRole('button',{name:'确认并下载草稿 DOCX',exact:true}).click();const download=await eventDownload;
  const file=path.join(out,batch.toLowerCase()+'-'+family+'-'+animal+'-'+key+'.docx');await download.saveAs(file);
  const text=execFileSync('python',['-c','import sys,zipfile;from xml.etree import ElementTree as E;root=E.fromstring(zipfile.ZipFile(sys.argv[1]).read("word/document.xml"));ns="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}";print("\\n".join("".join((n.text or "") if n.tag==ns+"t" else "\\n" if n.tag==ns+"br" else "\\t" if n.tag==ns+"tab" else "" for n in p.iter()) for p in root.iter(ns+"p")))',file],{encoding:'utf8'});
  if(key==='outpatient'){assert(text.includes(batch+'合成宠主'+animal));assert(text.includes(animal==='dog'?'合成黑白色':'合成虎斑色'));}
  assert(text.includes(saved.history));assert(text.includes(raw));assert.deepEqual(await read(id),saved);samples.push({family,species:animal,case_id:id,file:path.basename(file),history:saved.history});
  await review.getByRole('button',{name:'关闭草稿核对',exact:true}).click();await record(animal+'_'+key+'_review_and_actual_docx_exact_history_read_only');
 }
 await context.close();
}
async function main(){browser=await chromium.launch({headless:true});for(const key of families){family=key;batch=['appetite_weight','polyuria_polydipsia','cough_breathing'].includes(key)?'B1':'B2';config=JSON.parse(fs.readFileSync(path.join(__dirname,'../../knowledge-base/companion/intake',key+'.json'),'utf8'));title=config.label.replace(/^犬猫/,'').replace(/问诊$/,'');await runAnimal('dog');await runAnimal('cat');}assert.deepEqual(errors,[]);assert.deepEqual(external,[]);}
main().catch(async e=>{process.exitCode=1;failures.push(String(e));console.error(e);if(page&&!page.isClosed()){await page.screenshot({path:path.join(out,'b1-failure.png'),fullPage:true}).catch(()=>{});fs.writeFileSync(path.join(out,'b1-failure-dom.txt'),await page.locator('body').innerText().catch(()=>''));}}).finally(async()=>{fs.writeFileSync(path.join(out,'b1-intake-checks.json'),JSON.stringify({passed,failures,errors,external,samples},null,2));if(browser)await browser.close();});
