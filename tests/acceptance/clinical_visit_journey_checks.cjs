// CW-B24: the same synthetic patient is created, reviewed and followed through real UI saves.
const {chromium, expect} = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), os = require('node:os');
const {spawn, spawnSync, execFileSync} = require('node:child_process');
const {randomUUID, createHash} = require('node:crypto');
const {trackBrowser} = require('./clinical_visit_journey_harness.cjs');
const UI = 'http://127.0.0.1:5173', API = 'http://127.0.0.1:18026';
const out = process.env.PMAI_ACCEPTANCE_OUT, python = process.env.PMAI_PYTHON || 'python';
assert(out && process.env.PMAI_SYNTHETIC_ACCEPTANCE === 'PR26');
fs.mkdirSync(out, {recursive:true});
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'pmai-cwb24-'));
fs.writeFileSync(path.join(temp, 'synthetic-only'), 'CW-B24');
fs.mkdirSync(path.join(temp, 'private'));
const environment = path.join(temp, 'environment.json');
const sqlite = process.argv.includes('--local-sqlite');
fs.writeFileSync(environment, JSON.stringify({database_url:sqlite ? 'sqlite:///' + path.join(temp,'synthetic.sqlite') : process.env.DATABASE_URL,
  private_dir:path.join(temp,'private')}));
const fixturePath = 'tests/fixtures/clinical_visit_journey_cw_b24_cases.json';
const fixture = JSON.parse(fs.readFileSync(fixturePath,'utf8'));
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const report = {schema:fixture.schema, head:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),
  fixture_sha256:digest(fs.readFileSync(fixturePath)), status:'INCOMPLETE', backend:sqlite?'sqlite':'postgresql',
  doctor_acceptance:'pending', merged:false, deployed:false, cases:[], passed:[], faults:{}, errors:[], external:[], requests:[]};
let server, browser, context, page, tracker, token, downloadCount=0;
const account = {email:'cwb24-'+randomUUID()+'@example.com',password:randomUUID()};
const button = (scope,name) => scope.getByRole('button',{name,exact:true});
const region = name => page.getByRole('region',{name,exact:true});
const label = (scope,name) => scope.getByLabel(name,{exact:true});
const field = name => page.locator('label').filter({has:page.getByText(name,{exact:true})}).locator('input, textarea, select');
const caseLabels = {patient_name:'病例名 / 宠物名（必填）',species:'物种',sex:'性别',age_info:'年龄信息',breed:'品种 / 宠物信息',weight:'体重',coat_color:'毛色',owner_name:'主人姓名',owner_phone:'主人电话',chief_complaint:'主诉（必填）',history:'既往史 / 动态问诊追问记录',exam_findings:'体检 / 化验 / 来源信息',analysis:'AI 分析',treatment:'治疗建议',prognosis:'风险提示 / 后续随访'};
function pythonRun(args) {
  const result=spawnSync(python,['-B',...args],{encoding:'utf8',env:process.env,maxBuffer:8*1024*1024});
  assert.equal(result.status,0,result.stderr+'\n'+result.stdout);return result.stdout;
}
function snapshot(cid) { return JSON.parse(pythonRun(['tests/acceptance/clinical_visit_journey_readback.py','--environment',environment,'--snapshot',String(cid)])); }
function fileReceipt(name, extra={}) {const file=path.join(out,name),bytes=fs.readFileSync(file);return {file:name,bytes:bytes.length,sha256:digest(bytes),...extra};}
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
  await expect(panel).toContainText('原件已暂存');await label(panel,'资料标题').fill('CW24 '+kind+' 原件');
  await label(panel,'资料类型').selectOption(kind);await button(panel,'核对资料关联').click();
  await expect(button(panel,'确认资料操作')).toBeDisabled();await label(panel,'已核对病例、原件和资料信息').check();
  await button(panel,'确认资料操作').click();await expect(button(panel,'确认资料操作')).toHaveCount(0);
  const item=panel.getByRole('listitem').filter({hasText:'CW24 '+kind+' 原件'});await expect(item).toContainText('已关联');
  const waiting=page.waitForEvent('download');await button(item,'下载原件').click();const download=await waiting;
  const saved=`cwb24-${row.species}-${kind}-${name}`;await download.saveAs(path.join(out,saved));
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
      const name=`cwb24-${row.species}-${viewport}.png`;await doc.screenshot({path:path.join(out,name)});row.screenshots.push(fileReceipt(name,{viewport}));
    }
    await page.setViewportSize({width:1440,height:1040});await label(doc,'已核对本次草稿内容（仍未签署）').check();
    const waiting=page.waitForEvent('download');await button(doc,'确认并下载草稿 DOCX').click();const download=await waiting;
    const name=`cwb24-${row.species}-${template}.docx`;await download.saveAs(path.join(out,name));
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
async function faults() {
  const row=report.cases[0],root=`/api/cases/${row.case_id}/followup-contacts`;
  await page.goto(UI+'/cases/'+row.case_id);await button(page,'打开人工随访记录').click();const editor=region('人工随访记录');
  await button(editor,'更正人工随访记录').click();await label(editor,'随访记录原文').fill(fixture.corrected_contact_note);
  await label(editor,'随访更正或撤销原因').fill(fixture.correction_reason);
  let confirms=0,committed;
  await page.route(API+root+'/confirm',async route=>{confirms++;const actual=await route.fetch();assert.equal(actual.status(),200);committed=await actual.json();await route.abort('failed');});
  const receiptPattern=new RegExp('/followup-contacts/requests/');
  await page.route(receiptPattern,route=>route.abort('failed'));
  await button(editor,'预览并核对人工随访').click();await label(editor,'已核对人工随访').check();await button(editor,'确认保存人工随访').click();
  await expect(region('随访保存结果待核对')).toBeVisible();await expect(button(editor,'核对随访保存结果')).toBeEnabled();
  await expect(label(editor,'随访记录原文')).toHaveValue(fixture.corrected_contact_note);
  assert(committed);assert.equal(confirms,1);
  await page.unroute(receiptPattern);await page.unroute(API+root+'/confirm');
  await button(editor,'核对随访保存结果').click();await expect(region('随访保存结果待核对')).toHaveCount(0);
  await expect(region('人工随访草稿')).toHaveCount(0);assert.equal(confirms,1);
  const corrected=await call('GET',root);assert.equal(corrected.records.length,2);assert.equal(corrected.records[1].data.note,fixture.corrected_contact_note);
  report.faults.lost_write_response={status:'PASS',confirm_posts:confirms,version:corrected.records[1].version};report.passed.push('lost_write_response');

  let doc=await selectDocument(row,'owner_visit_summary_zh');await label(doc,'已核对本次草稿内容（仍未签署）').check();
  // Clearly marked fault preparation: another authenticated client corrects only this synthetic source.
  const listing=await call('GET',root),old=listing.records.at(-1),source=listing.plans.find(p=>p.id===old.source.id);
  const body={request_id:randomUUID().replaceAll('-',''),operation:'correct',contact_id:old.id,expected_contact_token:old.token,
    source_plan_id:source.id,source_plan_version:source.version,expected_source_token:source.token,
    expected_case_token:listing.case_token,expected_state_token:listing.state_token,data:{...old.data,next_action:'并发更正后的合成安排'},reason:fixture.correction_reason};
  const preview=await call('POST',root+'/preview',body);await call('POST',root+'/confirm',{...body,preview_token:preview.preview_token,reviewed:true});
  const before=snapshot(row.case_id),downloads=downloadCount;
  const response=page.waitForResponse(r=>r.url()===API+'/api/clinical-docs/render');await button(doc,'确认并下载草稿 DOCX').click();
  assert.equal((await response).status(),409);await expect(doc).toContainText('原确认已失效');assert.equal(downloadCount,downloads);
  assert.deepEqual(snapshot(row.case_id),before);await button(doc,'关闭草稿核对').click();
  report.faults.stale_document_source={status:'PASS',rejected_status:409,readonly_before:before,readonly_after:snapshot(row.case_id)};report.passed.push('stale_document_source');

  const other={email:'cwb24-other-'+randomUUID()+'@example.com',password:randomUUID()};
  assert((await context.request.post(API+'/auth/signup',{data:other})).ok());
  const logged=await context.request.post(API+'/auth/login',{form:{username:other.email,password:other.password}});assert(logged.ok());const otherToken=(await logged.json()).access_token;
  const late=[];
  for(const mode of ['case','account']){
    await page.evaluate(t=>localStorage.setItem('token',t),token);await page.goto(UI+'/cases/'+row.case_id);
    let arrive,release,finish,routeError;const seen=new Promise(r=>arrive=r),gate=new Promise(r=>release=r),done=new Promise(r=>finish=r);
    await page.route(API+'/api/clinical-docs/render-preview',async route=>{
      try {const actual=await route.fetch();assert.equal(actual.status(),200);arrive();await gate;
        try {await route.fulfill({response:actual});}catch(error){
          if(!/ERR_ABORTED|aborted/i.test(route.request().failure()?.errorText||''))throw error;
          late.push({mode,cancelled_request:true});
        }
      }catch(error){routeError=error;arrive();}finally{finish();}
    },{times:1});
    await button(page,'导出门诊病历草稿 DOCX').click();await seen;
    if(mode==='case')await page.goto(UI+'/cases/'+report.cases[1].case_id);
    else await page.evaluate(t=>{localStorage.setItem('token',t);window.dispatchEvent(new StorageEvent('storage',{key:'token'}));},otherToken);
    release();await done;if(routeError)throw routeError;await page.unroute(API+'/api/clinical-docs/render-preview');
    await expect(region('文书草稿内容核对')).toHaveCount(0);assert.equal(downloadCount,downloads);
  }
  for(const suffix of ['', '/followup-plan','/followup-contacts','/manual-lab','/manual-imaging']){
    const denied=await context.request.get(API+'/api/cases/'+row.case_id+suffix,{headers:{Authorization:'Bearer '+otherToken}});assert.equal(denied.status(),404);
    assert(!(await denied.text()).includes(fixture.contact.note));
  }
  report.faults.late_case_account_response={status:'PASS',modes:['case','account'],late};report.passed.push('late_case_account_response');
  await page.evaluate(t=>localStorage.setItem('token',t),token);await page.goto(UI+'/cases/'+row.case_id);
  doc=await selectDocument(row,'outpatient_record_zh');await label(doc,'已核对本次草稿内容（仍未签署）').check();
  let actualRender=0;await page.route(API+'/api/clinical-docs/render',async route=>{const actual=await route.fetch();assert.equal(actual.status(),200);actualRender++;await route.abort('failed');},{times:1});
  const readonly=snapshot(row.case_id);await button(doc,'确认并下载草稿 DOCX').click();
  await expect(doc).toContainText('请重新读取并核对草稿后重试');
  await expect(button(doc,'确认并下载草稿 DOCX')).toHaveCount(0);await expect(button(doc,'重新读取草稿')).toBeEnabled();
  assert.equal(actualRender,1);assert.equal(downloadCount,downloads);
  await button(doc,'关闭草稿核对').click();await page.unroute(API+'/api/clinical-docs/render');
  doc=await selectDocument(row,'owner_visit_summary_zh');await button(doc,'关闭草稿核对').click();
  assert.equal(downloadCount,downloads);assert.deepEqual(snapshot(row.case_id),readonly);
  report.faults.failed_cancelled_download={status:'PASS',downloads:0,actual_render_responses:actualRender,readonly_before:readonly,readonly_after:snapshot(row.case_id)};
  report.passed.push('failed_cancelled_download');
  row.confirm_request_ids.push(body.request_id);
}
async function main() {
  pythonRun(['tests/fixtures/build_attachment_cw_b6_fixtures.py',temp]);
  const log=fs.openSync(path.join(out,'cwb24-backend.log'),'w');
  server=spawn(python,['-B','tests/acceptance/fixture.py','--visit-journey',environment],{env:process.env,stdio:['ignore',log,log]});fs.closeSync(log);
  for(let i=0;i<80;i++){assert.equal(server.exitCode,null,'Journey backend exited');try{if((await fetch(API+'/healthz')).ok)break;}catch{}assert(i<79,'Journey backend unavailable');await new Promise(r=>setTimeout(r,200));}
  browser=await chromium.launch({headless:true});context=await browser.newContext({serviceWorkers:'block',viewport:{width:1440,height:1040},acceptDownloads:true});
  tracker=await trackBrowser(context,{origins:[UI,API],errors:report.errors,external:report.external});page=await context.newPage();page.on('dialog',d=>d.accept());page.on('download',()=>downloadCount++);
  page.on('request',request=>{if(!request.url().startsWith(API))return;const pathname=new URL(request.url()).pathname;
    if(['POST','PUT','PATCH','DELETE'].includes(request.method())&&pathname.startsWith('/api/')){
      let data;try{data=request.postDataJSON();}catch{}report.requests.push({method:request.method(),path:pathname,request_id:data?.request_id??null});
    }
  });
  const signup=await context.request.post(API+'/auth/signup',{data:account});assert(signup.ok());report.owner_id=(await signup.json()).id;
  await login();for(const data of fixture.cases)await journey(data);await faults();
  for(const row of report.cases){row.final_contacts=await call('GET',`/api/cases/${row.case_id}/followup-contacts`);
    const ids=report.requests.filter(r=>r.path===`/api/cases/${row.case_id}/followup-contacts/confirm`).map(r=>r.request_id);row.confirm_request_ids=[...new Set([...row.confirm_request_ids,...ids])];}
  await tracker.drain();assert.deepEqual(report.errors,[]);assert.deepEqual(report.external,[]);report.status='PASS';
}
main().catch(async error=>{
  report.errors.push(error.stack||String(error));report.status='FAIL';process.exitCode=1;console.error(error);
  if(page&&!page.isClosed()){
    await page.screenshot({path:path.join(out,'cwb24-failure.png'),fullPage:true}).catch(()=>{});
    fs.writeFileSync(path.join(out,'cwb24-failure-dom.txt'),await page.locator('body').innerText().catch(()=>''));
  }
}).finally(async()=>{
  if(tracker)await tracker.close().catch(e=>report.errors.push(String(e)));
  if(browser)await browser.close();
  if(report.errors.length||report.external.length){report.status='FAIL';process.exitCode=1;}
  const reportFile=path.join(out,'cwb24-journey.json');fs.writeFileSync(reportFile,JSON.stringify(report,null,2));
  if(report.status==='PASS'){
    try {console.log(pythonRun(['tests/acceptance/clinical_visit_journey_readback.py','--environment',environment,'--input',reportFile,'--output',path.join(out,'cwb24-independent-readback.json')]));}
    catch(error){report.status='FAIL';report.errors.push(String(error));process.exitCode=1;fs.writeFileSync(reportFile,JSON.stringify(report,null,2));console.error(error);}
  }
  if(server&&server.exitCode===null){server.kill('SIGTERM');await new Promise(resolve=>{const timer=setTimeout(()=>{server.kill('SIGKILL');resolve();},5000);server.once('exit',()=>{clearTimeout(timer);resolve();});});}
  fs.rmSync(temp,{recursive:true,force:true});
});
