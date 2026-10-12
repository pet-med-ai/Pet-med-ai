// Exercise the actual doctor's launcher, never a replacement acceptance bootstrap.
const {chromium,expect}=require('@playwright/test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const {spawn,spawnSync,execFileSync}=require('node:child_process');
const {createHash}=require('node:crypto');
const {trackBrowser}=require('./clinical_visit_journey_harness.cjs');
const out=process.env.PMAI_ACCEPTANCE_OUT,python=process.env.PMAI_PYTHON||'python';
assert(out&&process.env.PMAI_SYNTHETIC_ACCEPTANCE==='PR26');
fs.mkdirSync(out,{recursive:true});
const UI='http://127.0.0.1:5174',API='http://127.0.0.1:18027';
const manifest=JSON.parse(fs.readFileSync('tests/fixtures/clinical_doctor_trial_cw_b26_cases.json','utf8'));
const fixture=JSON.parse(fs.readFileSync(manifest.source_fixture,'utf8'));
fixture.cases.forEach((row,index)=>{row.patient_name=manifest.patient_names[index]+' 手工建档';});
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
const report={schema:manifest.schema,head:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),
 status:'INCOMPLETE',platform:process.platform,macos_run_verified:false,doctor_acceptance:'not_inferred',
 cases:[],passed:[],faults:{},errors:[],external:[],requests:[],launcher_receipts:[]};
let launcher,browser,context,page,tracker,account,ready,token,temp,downloadCount=0;
function pythonRun(args){
 const result=spawnSync(python,['-B',...args],{encoding:'utf8',maxBuffer:8*1024*1024});
 assert.equal(result.status,0,result.stderr);return result.stdout;
}
function snapshot(cid){
 const script="import sqlite3,hashlib,json,sys;from pathlib import Path;p=Path(sys.argv[1]);assert p.parent.name.startswith('pmai-cwb26-') and not p.is_symlink();c=sqlite3.connect('file:'+str(p)+'?mode=ro',uri=True);print(json.dumps({'sha256':hashlib.sha256('\\n'.join(c.iterdump()).encode()).hexdigest()}));c.close()";
 return JSON.parse(pythonRun(['-c',script,path.join(ready.temporary_dir,'synthetic.sqlite')]));
}
function fileReceipt(name,extra={}){const bytes=fs.readFileSync(path.join(out,name));return {file:name,bytes:bytes.length,sha256:digest(bytes),...extra};}
function trialHeaders(info){return {'X-PMAI-Trial-Session':info.session,'X-PMAI-Trial-Head':info.head,'X-PMAI-Trial-Source':info.source_sha256};}
async function start(label){
 const receipt=path.join(out,'cwb26-launcher-'+label+'.json');
 launcher=spawn(python,['-B','scripts/run_clinical_doctor_trial_cw_b26.py','--receipt',receipt],
  {env:{...process.env,DATABASE_URL:'postgresql://example.invalid/production',OPENAI_API_KEY:'cwb26-poison-sentinel'},
   stdio:['ignore','pipe','pipe']});
 let buffer='',stderr='';
 launcher.stderr.on('data',chunk=>{stderr+=chunk;});
 const info=await new Promise((resolve,reject)=>{
  const timer=setTimeout(()=>reject(new Error('Real launcher readiness timed out')),120000);
  launcher.stdout.on('data',chunk=>{
   buffer+=chunk;
   let at;
   while((at=buffer.indexOf('\n'))!==-1){
    const line=buffer.slice(0,at);buffer=buffer.slice(at+1);
    if(line.startsWith('PMAI_TRIAL_READY ')){clearTimeout(timer);resolve(JSON.parse(line.slice(17)));}
   }
  });
  launcher.once('error',error=>{clearTimeout(timer);reject(error);});
  launcher.once('exit',code=>{clearTimeout(timer);if(code!==0)reject(new Error('Real launcher exited '+code+': '+stderr));});
 });
 info.receipt=receipt;
 assert.equal(info.url,UI);assert.equal(info.api,API);assert.equal(info.head,report.head);
 return info;
}
async function stop(info){
 const process=launcher;
 if(process&&process.exitCode===null){
  const stopped=new Promise((resolve,reject)=>{
   const timer=setTimeout(()=>reject(new Error('Launcher did not clean up')),15000);
   process.once('exit',code=>{clearTimeout(timer);code===0?resolve():reject(new Error('Launcher stop failed '+code));});
  });
  process.kill('SIGTERM');await stopped;
 }
 const receipt=JSON.parse(fs.readFileSync(info.receipt,'utf8'));
 assert.equal(receipt.status,'STOPPED');assert.equal(receipt.children_stopped,true);
 assert.equal(receipt.temporary_data_removed,true);assert(!fs.existsSync(info.temporary_dir));
 const text=fs.readFileSync(info.receipt,'utf8');
 assert(!text.includes(info.password)&&!text.includes('cwb26-poison-sentinel')&&!text.includes('"token"'));
 report.launcher_receipts.push(fileReceipt(path.basename(info.receipt)));
 launcher=null;
}
async function screenshot(name){
 await page.screenshot({path:path.join(out,name),fullPage:true});
 (report.screenshots??=[]).push(fileReceipt(name));
}
async function run(){
 ready=await start('first');temp=ready.samples_dir;account={email:ready.email,password:ready.password};
 report.source_sha256=ready.source_sha256;
 browser=await chromium.launch({headless:true});
 context=await browser.newContext({serviceWorkers:'block',acceptDownloads:true,viewport:{width:1440,height:1040},extraHTTPHeaders:trialHeaders(ready)});
 tracker=await trackBrowser(context,{origins:[UI,API],errors:report.errors,external:report.external});
 page=await context.newPage();page.on('dialog',d=>d.accept());page.on('download',()=>downloadCount++);
 report.http_observations=[];
 page.on('response',response=>{
  if(response.url().startsWith(API))report.http_observations.push({path:new URL(response.url()).pathname,
   status:response.status(),method:response.request().method(),
   identity:response.headers()['x-pmai-trial-session']===ready.session,
   exposed:response.headers()['access-control-expose-headers']||null});
 });
 page.on('requestfailed',request=>{
  if(request.url().startsWith(API))report.http_observations.push({path:new URL(request.url()).pathname,
   failure:request.failure()?.errorText,method:request.method()});
 });
 page.on('request',request=>{
  if(!request.url().startsWith(API))return;
  const pathname=new URL(request.url()).pathname;
  if(['POST','PUT','PATCH','DELETE'].includes(request.method())&&pathname.startsWith('/api/')){
   let data;try{data=request.postDataJSON();}catch{}
   report.requests.push({method:request.method(),path:pathname,request_id:data?.request_id??null});
  }
 });
 const response=await context.request.get(API+'/__doctor_trial');assert(response.ok());
 const info=await response.json();assert.equal(info.synthetic_only,true);assert.deepEqual(info.cases.map(row=>row.name),manifest.patient_names);
 // A truthful wrong-version response must leave all business UI unmounted.
 await page.route(API+'/__doctor_trial',route=>route.fulfill({status:200,contentType:'application/json',
  headers:{'Access-Control-Allow-Origin':UI},body:JSON.stringify({...info,session:'f'.repeat(64)})}));
 await page.goto(UI);await expect(page.getByRole('alert')).toContainText('试用环境未通过核对');
 assert.equal(report.requests.length,0);await screenshot('cwb26-mismatch.png');
 await page.unroute(API+'/__doctor_trial');await login();
 await page.getByText('练习步骤与犬猫样例',{exact:true}).click();
 await expect(page.getByRole('link',{name:manifest.patient_names[0],exact:true})).toBeVisible();
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1040});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await screenshot('cwb26-entry-'+width+'.png');
 }
 await page.setViewportSize({width:1440,height:1040});
 const unknown=await context.request.get(API+'/api/cases',{headers:{'X-PMAI-Trial-Session':'0'.repeat(64)}});
 assert.equal(unknown.status(),409);
 const disabled=await context.request.post(API+'/ai/consult',{data:{}});
 assert.equal(disabled.status(),403);
 // Check seeded records, then independently exercise real manual creates for both species.
 for(const row of info.cases){const saved=await call('GET','/api/cases/'+row.id);assert.equal(saved.patient_name,row.name);}
 for(const data of fixture.cases)await journey(data);
 const oldToken=token,oldReady=ready;
 assert.equal(report.cases.length,2);assert.equal(report.cases.flatMap(row=>row.documents).length,4);
 for(const row of report.cases)assert.deepEqual(row.steps,fixture.steps);
 await tracker.drain();
 await stop(oldReady);
 await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
 await expect(page.getByRole('alert')).toContainText('连接已断开');
 await screenshot('cwb26-disconnected.png');
 // A new invocation must have independent identity, credentials, signing key and initial state.
 ready=await start('second');temp=ready.samples_dir;account={email:ready.email,password:ready.password};
 assert.notEqual(ready.session,oldReady.session);assert.notEqual(ready.password,oldReady.password);
 assert.notEqual(ready.temporary_dir,oldReady.temporary_dir);
 await context.setExtraHTTPHeaders(trialHeaders(ready));
 const wrongSession=await context.request.get(API+'/api/cases',{headers:{...trialHeaders(oldReady),Authorization:'Bearer '+oldToken}});
 assert.equal(wrongSession.status(),409);
 const oldAccount=await context.request.get(API+'/api/cases',{headers:{Authorization:'Bearer '+oldToken}});
 assert.equal(oldAccount.status(),401);
 await page.goto(UI);await page.evaluate(()=>localStorage.clear());await login();
 const fresh=await call('GET','/api/cases');
 const rows=Array.isArray(fresh)?fresh:fresh.items;
 assert.equal(rows.length,2);assert.deepEqual(rows.map(row=>row.patient_name).sort(),manifest.patient_names.slice().sort());
 report.faults={wrong_identity_before_render:'PASS',wrong_session_request:409,disabled_external_route:403,
  disconnected_page:'PASS',previous_session:409,previous_token:401,new_session_seed_count:2};
 await tracker.drain();await tracker.close();tracker=null;context=null;
 await browser.close();browser=null;
 await stop(ready);
 for(const row of report.cases)for(const doc of row.documents)assert.equal(fileReceipt(doc.file).sha256,doc.sha256);
 assert.deepEqual(report.errors,[]);assert.deepEqual(report.external,[]);
 report.external_business_calls=0;report.status='PASS';
 console.log('PASS CW-B26 real launcher, dog/cat workflows, identity failures, clean restart and retained downloads');
}
const button = (scope,name) => scope.getByRole('button',{name,exact:true});
const region = name => page.getByRole('region',{name,exact:true});
const label = (scope,name) => scope.getByLabel(name,{exact:true});
const field = name => page.locator('label').filter({has:page.getByText(name,{exact:true})}).locator('input, textarea, select');
const caseLabels = {patient_name:'病例名 / 宠物名（必填）',species:'物种',sex:'性别',age_info:'年龄信息',breed:'品种 / 宠物信息',weight:'体重',coat_color:'毛色',owner_name:'主人姓名',owner_phone:'主人电话',chief_complaint:'主诉（必填）',history:'既往史 / 动态问诊追问记录',exam_findings:'体检 / 化验 / 来源信息',analysis:'AI 分析',treatment:'治疗建议',prognosis:'风险提示 / 后续随访'};
async function call(method,url,data,auth=token) {
  const response=await context.request.fetch(API+url,{method,headers:{Authorization:'Bearer '+auth},data});
  assert(response.ok(),`${method} ${url}: ${response.status()} ${await response.text()}`);
  return response.status()===204?null:response.json();
}
async function login() {
  await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill(account.email);
  await page.getByPlaceholder('密码',{exact:true}).fill(account.password);await button(page,'登录').click();
  await expect(button(page,'退出')).toBeVisible();token=await page.evaluate(()=>localStorage.getItem('token'));
}
function step(row,name) {assert.equal(fixture.steps[row.steps.length],name);row.steps.push(name);console.log('PASS',row.species,name);}
function saveCount(cid,suffix) {return report.requests.filter(r=>r.method==='POST'&&r.path===`/api/cases/${cid}/`+suffix).length;}
async function reviewSave(panel, preview, checked, confirm, draft) {
  await button(panel,preview).click();await expect(button(panel,confirm)).toBeDisabled();
  await label(panel,checked).check();await button(panel,confirm).click();
  await expect(panel.getByRole('region',{name:draft,exact:true})).toHaveCount(0);
}
async function upload(panel, row, name, kind) {
  await label(panel,'选择检查文件').setInputFiles(path.join(temp,name));await button(panel,'上传待核对原件').click();
  await expect(panel).toContainText('原件已暂存');await label(panel,'资料标题').fill('CW26 '+kind+' 原件');
  await label(panel,'资料类型').selectOption(kind);await button(panel,'核对资料关联').click();
  await expect(button(panel,'确认资料操作')).toBeDisabled();await label(panel,'已核对病例、原件和资料信息').check();
  await button(panel,'确认资料操作').click();await expect(button(panel,'确认资料操作')).toHaveCount(0);
  const item=panel.getByRole('listitem').filter({hasText:'CW26 '+kind+' 原件'});await expect(item).toContainText('已关联');
  const waiting=page.waitForEvent('download');await button(item,'下载原件').click();const download=await waiting;
  const saved=`cwb26-${row.species}-${kind}-${name}`;await download.saveAs(path.join(out,saved));
  assert.deepEqual(fs.readFileSync(path.join(out,saved)),fs.readFileSync(path.join(temp,name)));
  const listing=await call('GET',`/api/cases/${row.case_id}/attachments`),source=listing.items.find(a=>a.metadata.kind===kind);
  assert(source);row.originals.push(fileReceipt(saved,{attachment_id:source.id}));return source;
}
async function saveLab(panel, correction=false) {
  if(!correction){
    await label(panel,'报告类型').selectOption(fixture.lab.report.panel);
    const names={title:'报告标题',specimen:'样本类型',collected_at:'采样时间（含时区）',reported_at:'报告时间（含时区）',laboratory:'实验室',device:'仪器',note:'报告备注'};
    for(const [key,name] of Object.entries(names))await label(panel,name).fill(fixture.lab.report[key]);
    const names2={name:'项目名称',value:'结果原文',unit:'结果单位',reference:'参考范围原文',reference_low:'参考下限',reference_high:'参考上限',reference_unit:'参考单位',flag:'报告标记原文',position:'页码或原件位置'};
    await label(panel,'项目 1 结果类型').selectOption('number');
    for(const [key,name] of Object.entries(names2))await label(panel,'项目 1 '+name).fill(fixture.lab.items[0][key]);
  }else{
    await button(panel,'更正检验记录').click();await label(panel,'项目 1 结果原文').fill(fixture.corrected_lab_value);
    await label(panel,'更正或撤销原因').fill(fixture.correction_reason);
  }
  await label(panel,'已核对项目 1').check();
  await reviewSave(panel,'核对整份检验记录','已核对整份检验记录','确认保存检验记录','检验录入草稿');
}
async function selectDocument(row,template) {
  const doc=region('文书草稿内容核对');
  await button(page,template==='outpatient_record_zh'?'导出门诊病历草稿 DOCX':'导出宠主说明草稿 DOCX').click();
  await expect(doc).toBeVisible();await button(doc,'选择已核对检验报告').click();
  await label(doc,'纳入 '+fixture.lab.report.title).last().check();
  await button(doc,'选择已核对影像报告').click();await label(doc,'纳入影像 '+fixture.imaging.title).check();
  await button(doc,'选择复查计划附节').click();await button(doc,'将此计划纳入本次文书').last().click();
  await button(doc,'选择人工随访记录附节').click();await button(doc,'将此随访纳入本次文书').last().click();
  await button(doc,'重新读取草稿').click();
  await expect(doc.getByRole('region',{name:'文书人工随访附节',exact:true})).toBeVisible();
  await expect(label(doc,'已核对本次草稿内容（仍未签署）')).toBeEnabled();
  await expect(button(doc,'确认并下载草稿 DOCX')).toBeDisabled();return doc;
}
async function openQueue() {
  await page.goto(UI+'/followup-plans');await label(page,'计划日期范围').selectOption('all');
  await label(page,'显示人工随访记录').check();
}
async function journey(data) {
  const row={species:data.species,steps:[],documents:[],screenshots:[],originals:[],confirm_request_ids:[]};
  await page.goto(UI+'/cases/new/edit');
  if(await button(region('手工新建病例核对'),'核对保存结果').count()){
    await button(region('手工新建病例核对'),'核对保存结果').click();
    await button(region('手工新建病例核对'),'新建另一个病例').click();
  }
  for(const [key,name] of Object.entries(caseLabels)){
    if(key==='species')await field(name).selectOption(data[key]);else await field(name).fill(data[key]);
  }
  const review=region('手工新建病例核对'),beforeCreates=report.requests.filter(r=>r.method==='POST'&&r.path==='/api/cases').length;
  await button(review,'核对新建内容').click();await expect(button(review,'确认并创建病例')).toBeDisabled();
  await label(review,'已核对本次新建内容').check();await button(review,'确认并创建病例').click();
  await expect(review).toContainText('本次核对的十五项内容一致');
  const receipt=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('pmai.manual-create-attempt.v1')));
  row.case_id=receipt.caseId;assert.deepEqual(receipt.payload,data);step(row,'case_ui_saved');
  row.saved_case=await call('GET','/api/cases/'+row.case_id);for(const key of Object.keys(data))assert.equal(row.saved_case[key],data[key]);
  step(row,'case_readback');await review.getByRole('link',{name:'查看已保存病例 #'+row.case_id,exact:true}).click();
  await expect(region('完整病史原文')).toContainText(data.history.trim());
  await button(page,'打开检查资料').click();const attachments=region('检查资料');
  const labSource=await upload(attachments,row,'synthetic.png','lab'),imageSource=await upload(attachments,row,'synthetic.pdf','dr');
  step(row,'attachments_ui_saved');
  await button(page,'打开检验项目').click();const lab=region('检验项目人工录入');await button(lab,'录入检验报告').click();
  await label(lab,'检验原件').selectOption(labSource.id);await saveLab(lab);step(row,'lab_ui_saved');
  await button(page,'打开影像记录').click();const imaging=region('影像报告人工录入');await button(imaging,'录入影像报告').click();
  await label(imaging,'影像原件').selectOption(imageSource.id);await label(imaging,'检查类型').selectOption('dr');
  const imageNames={title:'报告标题',body_part:'检查部位',taken_at:'检查时间（含时区）',institution:'出具机构',findings:'所见原文',impression:'结论原文',limitations:'局限性原文',note:'备注原文',position:'页码或原件位置'};
  for(const [key,name] of Object.entries(imageNames))await label(imaging,name).fill(fixture.imaging[key]);
  await label(imaging,'已核对所见原文').check();await label(imaging,'已核对结论原文').check();
  await reviewSave(imaging,'核对整份影像记录','已核对整份影像记录','确认保存影像记录','影像录入草稿');step(row,'imaging_ui_saved');
  await saveLab(lab,true);row.lab=await call('GET',`/api/cases/${row.case_id}/manual-lab`);
  assert.deepEqual(row.lab.reports.map(r=>r.state),['superseded','confirmed']);
  assert.equal(row.lab.reports[0].data.items[0].value,fixture.lab.items[0].value);
  assert.equal(row.lab.reports[1].data.items[0].value,fixture.corrected_lab_value);step(row,'lab_ui_corrected');
  row.imaging=await call('GET',`/api/cases/${row.case_id}/manual-imaging`);assert.deepEqual(row.imaging.reports[0].data,fixture.imaging);
  await button(page,'打开复查计划').click();const plan=region('人工复查计划');await button(plan,'新增复查计划').click();
  for(const [name,key] of [['计划复查日期','planned_date'],['复查目的','purpose'],['提前返回条件','return_conditions'],['复查备注','note']])await label(plan,name).fill(fixture.plan[key]);
  await label(plan,'复查项目 1').fill(fixture.plan.items[0]);await button(plan,'添加复查项目').click();await label(plan,'复查项目 2').fill(fixture.plan.items[1]);
  await reviewSave(plan,'预览并核对复查计划','已核对复查计划','确认保存复查计划','复查计划草稿');
  row.plans=await call('GET',`/api/cases/${row.case_id}/followup-plan`);assert.deepEqual(row.plans.plans[0].data,fixture.plan);step(row,'plan_ui_saved');
  await button(page,'打开人工随访记录').click();const contact=region('人工随访记录');await button(contact,'新增人工随访记录').click();
  await label(contact,'随访来源计划').selectOption(String(row.plans.plans[0].id));await label(contact,'随访联系时间').fill(fixture.contact.occurred_at.slice(0,16));
  await label(contact,'随访联系方式').selectOption(fixture.contact.method);await label(contact,'随访联系结果').selectOption(fixture.contact.outcome);
  await label(contact,'随访记录原文').fill(fixture.contact.note);await label(contact,'随访后续安排').fill(fixture.contact.next_action);
  await reviewSave(contact,'预览并核对人工随访','已核对人工随访','确认保存人工随访','人工随访草稿');
  row.contacts=await call('GET',`/api/cases/${row.case_id}/followup-contacts`);assert.deepEqual(row.contacts.records[0].data,fixture.contact);step(row,'contact_ui_saved');
  row.readonly_before=snapshot(row.case_id);
  await openQueue();await page.getByRole('link',{name:`回看随访 #${row.contacts.records[0].id} 版本 1`,exact:true}).click();
  await expect(region('人工随访记录')).toContainText(`正在回看随访 #${row.contacts.records[0].id} 版本 1`);step(row,'queue_exact_contact');
  await openQueue();await page.getByRole('link',{name:`回看来源计划 #${row.plans.plans[0].id} 版本 1`,exact:true}).click();
  await expect(region('人工复查计划')).toContainText(`正在回看计划 #${row.plans.plans[0].id} 版本 1`);step(row,'queue_exact_source');
  for(const template of ['outpatient_record_zh','owner_visit_summary_zh']){
    const doc=await selectDocument(row,template);
    for(const value of [fixture.contact.note.trim(),fixture.plan.purpose.trim(),fixture.imaging.findings.trim(),fixture.corrected_lab_value])await expect(doc).toContainText(value);
    if(template==='outpatient_record_zh')for(const [viewport,size] of [['wide',{width:1440,height:1040}],['narrow',{width:390,height:844}]]){
      await page.setViewportSize(size);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      const name=`cwb26-${row.species}-${viewport}.png`;await doc.screenshot({path:path.join(out,name)});row.screenshots.push(fileReceipt(name,{viewport}));
    }
    await page.setViewportSize({width:1440,height:1040});await label(doc,'已核对本次草稿内容（仍未签署）').check();
    const waiting=page.waitForEvent('download');await button(doc,'确认并下载草稿 DOCX').click();const download=await waiting;
    const name=`cwb26-${row.species}-${template}.docx`;await download.saveAs(path.join(out,name));
    row.documents.push(fileReceipt(name,{template,case_id:row.case_id,plan_id:row.plans.plans[0].id,contact_id:row.contacts.records[0].id}));
    await button(doc,'关闭草稿核对').click();
  }
  step(row,'documents_reviewed_downloaded');await page.reload();await expect(region('完整病史原文')).toBeVisible();
  assert.equal(await region('完整病史原文').locator('.text-body').textContent(),data.history);
  await page.goto(UI);await button(page,'退出').click();await login();await page.goto(UI+'/cases/'+row.case_id);
  assert.deepEqual(await call('GET','/api/cases/'+row.case_id),row.saved_case);
  assert.deepEqual(await call('GET',`/api/cases/${row.case_id}/followup-contacts`),row.contacts);step(row,'refresh_relogin_readback');
  row.readonly_after=snapshot(row.case_id);assert.deepEqual(row.readonly_after,row.readonly_before);
  row.requests={create:report.requests.filter(r=>r.method==='POST'&&r.path==='/api/cases').length-beforeCreates,
    attachments:saveCount(row.case_id,'attachments/confirm'),lab:saveCount(row.case_id,'manual-lab/confirm'),
    imaging:saveCount(row.case_id,'manual-imaging/confirm'),plan:saveCount(row.case_id,'followup-plan/confirm'),contact:saveCount(row.case_id,'followup-contacts/confirm')};
  row.confirm_request_ids=report.requests.filter(r=>r.path.startsWith(`/api/cases/${row.case_id}/`)&&r.path.endsWith('/confirm')).map(r=>r.request_id);
  report.cases.push(row);report.passed.push(row.species+'_complete_visit');
}

run().catch(async error=>{
 report.status='FAIL';report.errors.push(error.stack||String(error));process.exitCode=1;console.error(error);
 if(page&&!page.isClosed()){
  await screenshot('cwb26-failure.png').catch(()=>{});
  fs.writeFileSync(path.join(out,'cwb26-failure-dom.txt'),await page.locator('body').innerText().catch(()=>''));
 }
}).finally(async()=>{
 if(tracker)await tracker.close().catch(e=>report.errors.push(String(e)));
 if(browser)await browser.close();
 if(launcher&&launcher.exitCode===null){
  try{await stop(ready);}catch(error){report.errors.push(String(error));launcher?.kill('SIGKILL');}
 }
 if(report.errors.length||report.external.length){report.status='FAIL';process.exitCode=1;}
 fs.writeFileSync(path.join(out,'cwb26-doctor-trial.json'),JSON.stringify(report,null,2));
});
