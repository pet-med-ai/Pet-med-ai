// Real Chromium + real authenticated app and bytes. No service or route mock.
const {chromium,expect}=require('@playwright/test');
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {createHash,randomUUID}=require('node:crypto'),{spawn,spawnSync}=require('node:child_process');
const UI='http://127.0.0.1:5173',API='http://127.0.0.1:18026',out=process.env.PMAI_ACCEPTANCE_OUT;
assert(out&&process.env.PMAI_SYNTHETIC_ACCEPTANCE==='PR26');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'cwb7-browser-')),passed=[],errors=[],external=[];
let browser,page,server;
const python=process.env.PMAI_PYTHON||'python';
const generated=spawnSync(python,['-B','tests/fixtures/build_attachment_cw_b6_fixtures.py',temp],{encoding:'utf8'});
assert.equal(generated.status,0,generated.stderr);
const prefix=process.argv.includes('--local-sqlite')?`
import os,sys,tempfile
from pathlib import Path
tmp=tempfile.TemporaryDirectory(prefix='cwb7-api-')
os.environ.clear();os.environ.update(DATABASE_URL='sqlite:///'+str(Path(tmp.name)/'synthetic.sqlite'),SECRET_KEY='synthetic-cwb7-only',ENVIRONMENT='test',RENDER='false')
sys.path[:]=[str(Path('backend').resolve())]+[p for p in sys.path if Path(p or '.').resolve()!=Path('.').resolve()]
def guard(event,args):
    if event in {'socket.connect','socket.connect_ex','socket.bind'} and isinstance(args[1],tuple):
        assert args[1][0] in {'127.0.0.1','::1'} and args[1][1]==18026
    if event=='socket.getaddrinfo':assert args[0] in {'127.0.0.1','localhost','::1',None}
sys.addaudithook(guard)
import main,db,models
db.Base.metadata.create_all(db.engine)
from fastapi.testclient import TestClient
with TestClient(main.app) as client:
    assert client.post('/auth/signup',json={'email':'browser-owner@example.com','password':'Synthetic-PR26-only-20260916'}).status_code==200
`:`
import sys
sys.path.insert(0,'tests/acceptance')
import fixture as f
main=f.main
`;
const boot=prefix+`
import os,tempfile
from pathlib import Path
private=tempfile.TemporaryDirectory(prefix='cwb7-private-')
os.environ.update(CASE_ATTACHMENTS_ENABLED='1',CASE_ATTACHMENTS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_DIR=private.name,MANUAL_LAB_RESULTS_ENABLED='1',MANUAL_LAB_RESULTS_SYNTHETIC_ONLY='1')
import uvicorn
uvicorn.run(main.app,host='127.0.0.1',port=18026,loop='asyncio')
`;
async function main(){
 const log=fs.openSync(path.join(out,'cwb7-backend.log'),'w');
 server=spawn(python,['-B','-c',boot],{stdio:['ignore',log,log],env:process.env});
 for(let i=0;i<70;i++){
  if(server.exitCode!==null)throw Error('Manual lab backend exited');
  try{if((await fetch(API+'/healthz')).ok)break;}catch{}
  if(i===69)throw Error('Manual lab backend unavailable');await new Promise(r=>setTimeout(r,200));
 }
 browser=await chromium.launch({headless:true});
 const context=await browser.newContext({serviceWorkers:'block',viewport:{width:1400,height:1080},acceptDownloads:true});
 await context.route('**/*',r=>[UI,API].includes(new URL(r.request().url()).origin)?r.continue():(external.push(r.request().url()),r.abort()));
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 async function login(){await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill('browser-owner@example.com');await page.getByPlaceholder('密码',{exact:true}).fill('Synthetic-PR26-only-20260916');await page.getByRole('button',{name:'登录',exact:true}).click();await expect(page.getByRole('button',{name:'退出',exact:true})).toBeVisible();}
 await login();const auth={Authorization:'Bearer '+await page.evaluate(()=>localStorage.getItem('token'))};
 async function call(method,url,data){const r=await context.request.fetch(API+url,{method,headers:auth,data});assert(r.ok(),await r.text());return r.json();}
 const original=JSON.parse(fs.readFileSync('tests/fixtures/manual_lab_cw_b7_cases.json','utf8'));
 const reportLabels={title:'报告标题',specimen:'样本类型',collected_at:'采样时间（含时区）',reported_at:'报告时间（含时区）',laboratory:'实验室',device:'仪器',note:'报告备注'};
 const rowLabels={name:'项目名称',value:'结果原文',unit:'结果单位',reference:'参考范围原文',reference_low:'参考下限',reference_high:'参考上限',reference_unit:'参考单位',flag:'报告标记原文',position:'页码或原件位置'};
 const results=[];
 for(const species of ['dog','cat']){
  const cid=(await call('POST','/api/cases',{patient_name:'CW-B7合成'+species,species,owner_name:'合成宠主',coat_color:'黑白（合成）',chief_complaint:'合成检验录入验收',history:'原始合成病史；未见呕吐。'})).id;
  const root=`/api/cases/${cid}/manual-lab`,files=`/api/cases/${cid}/attachments`;
  const name=species==='dog'?'synthetic.pdf':'synthetic.png',mime=species==='dog'?'application/pdf':'image/png',raw=fs.readFileSync(path.join(temp,name));
  const upload=await context.request.post(API+files+'/uploads/'+randomUUID().replaceAll('-',''),{headers:{...auth,'Content-Type':mime,'X-Attachment-Filename':name,'X-Case-Token':(await call('GET',files)).case_token},data:raw});assert.equal(upload.status(),200);
  const source=(await upload.json()).attachment;
  const metadata={title:'合成检验原件',kind:'lab',taken_at:'',reported_at:'',source:'合成实验室',note:''};
  async function attachOp(operation,title){const body={request_id:randomUUID().replaceAll('-',''),attachment_id:source.id,operation,expected_case_token:(await call('GET',files)).case_token,metadata:{...metadata,title:title||metadata.title},reason:operation==='withdraw'?'合成误关联':''};const p=await call('POST',files+'/preview',body);return call('POST',files+'/confirm',{...body,preview_token:p.preview_token,reviewed:true});}
  await attachOp('confirm');
  let labReads=0;page.on('request',r=>{if(r.url()===API+root)labReads++;});
  await page.goto(UI+'/cases/'+cid);await expect(page.getByRole('button',{name:'打开检验项目',exact:true})).toBeVisible();assert.equal(labReads,0);
  await page.getByRole('button',{name:'打开检验项目',exact:true}).click();
  const panel=page.getByRole('region',{name:'检验项目人工录入',exact:true});await expect(panel).toContainText('CW-B7合成'+species);
  await panel.getByRole('button',{name:'录入检验报告',exact:true}).click();await panel.getByLabel('检验原件',{exact:true}).selectOption(source.id);
  const downloading=page.waitForEvent('download');await panel.getByRole('button',{name:'打开核对原件',exact:true}).click();const file=await downloading;
  const dest=path.join(out,'cwb7-original-'+species+'-'+name);await file.saveAs(dest);assert.deepEqual(fs.readFileSync(dest),raw);
  await panel.getByLabel('报告类型',{exact:true}).selectOption(original.report.panel);
  for(const [key,label] of Object.entries(reportLabels))await panel.getByLabel(label,{exact:true}).fill(original.report[key]);
  for(const [i,row] of original.items.entries()){
   if(i)await panel.getByRole('button',{name:'添加检验项目',exact:true}).click();
   await panel.getByLabel(`项目 ${i+1} 结果类型`,{exact:true}).selectOption(row.result_type);
   for(const [key,label] of Object.entries(rowLabels))await panel.getByLabel(`项目 ${i+1} ${label}`,{exact:true}).fill(row[key]);
   await panel.getByLabel(`已核对项目 ${i+1}`,{exact:true}).check();
  }
  async function preview(){await panel.getByRole('button',{name:'核对整份检验记录',exact:true}).click();await expect(panel.getByRole('region',{name:'整份检验核对',exact:true})).toBeVisible();await expect(panel.getByRole('button',{name:'确认保存检验记录',exact:true})).toBeDisabled();}
  async function confirm(){await panel.getByLabel('已核对整份检验记录',{exact:true}).check();await panel.getByRole('button',{name:'确认保存检验记录',exact:true}).evaluate(button=>{button.click();button.click();});await expect(panel.getByRole('region',{name:'整份检验核对',exact:true})).toHaveCount(0);}
  await preview();await panel.getByLabel('已核对整份检验记录',{exact:true}).check();await panel.getByLabel('项目 1 结果原文',{exact:true}).fill('0.0200');await expect(panel.getByRole('region',{name:'整份检验核对',exact:true})).toHaveCount(0);
  await expect(panel.getByRole('button',{name:'核对整份检验记录',exact:true})).toBeDisabled();await panel.getByLabel('项目 1 结果原文',{exact:true}).fill('0.0100');await panel.getByLabel('已核对项目 1',{exact:true}).check();await preview();
  if(species==='dog'){
   let posts=0,gets=0;page.on('request',r=>{if(r.url().includes(root+'/requests/'))gets++;});
   await page.route('**/manual-lab/confirm',async r=>{posts++;await r.fetch();await r.abort('failed');});
   await confirm();await expect(panel).toContainText('已回读保存结果');assert.equal(posts,1);assert.equal(gets,1);await page.unroute('**/manual-lab/confirm');
  }else await confirm();
  let saved=await call('GET',root);assert.equal(saved.reports.length,1);assert.equal(saved.reports[0].state,'confirmed');
  assert.equal(saved.reports[0].data.items[0].decimal,'0.0100');assert.equal(saved.reports[0].data.items[3].result_type,'not_tested');assert.equal(saved.reports[0].data.items[5].value,'0');
  passed.push(species+'_real_form_original_download_exact_values_row_whole_checks_and_single_commit');
  await panel.getByRole('button',{name:'更正检验记录',exact:true}).click();await panel.getByLabel('项目 1 结果原文',{exact:true}).fill('0.0300');await panel.getByLabel('更正或撤销原因',{exact:true}).fill('合成抄录更正');
  for(let i=0;i<original.items.length;i++)await panel.getByLabel(`已核对项目 ${i+1}`,{exact:true}).check();
  await preview();await confirm();saved=await call('GET',root);assert.deepEqual(saved.reports.map(r=>r.state),['superseded','confirmed']);assert.equal(saved.reports[0].data.items[0].value,'0.0100');assert.equal(saved.reports[1].data.items[0].value,'0.0300');
  // Use the actual attachment panel to verify in-page change notification.
  await page.getByRole('button',{name:'打开检查资料',exact:true}).click();const attachment=page.getByRole('region',{name:'检查资料',exact:true});await attachment.getByRole('button',{name:'更正资料信息',exact:true}).click();await attachment.getByLabel('资料标题',{exact:true}).fill('已更正合成原件');
  await attachment.getByRole('button',{name:'核对资料关联',exact:true}).click();await attachment.getByLabel('已核对病例、原件和资料信息',{exact:true}).check();await attachment.getByRole('button',{name:'确认资料操作',exact:true}).click();await expect(panel).toContainText('需重新核对');
  await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await expect(panel).toContainText('需重新核对');
  await panel.getByRole('button',{name:'撤销检验记录',exact:true}).click();await panel.getByLabel('更正或撤销原因',{exact:true}).fill('合成撤销验收');await preview();await confirm();await expect(panel).toContainText('已撤销');
  await page.reload();await page.getByRole('button',{name:'打开检验项目',exact:true}).click();await expect(panel).toContainText('已撤销');
  saved=await call('GET',root);assert.deepEqual(saved.reports.map(r=>r.state),['superseded','withdrawn']);
  const clinical=await call('GET','/api/cases/'+cid);assert.equal(clinical.history,'原始合成病史；未见呕吐。');
  for(const template of ['outpatient_record_zh','owner_visit_summary_zh']){
   const body={case_id:cid,template_id:template},p=await call('POST','/api/clinical-docs/render-preview',body);assert(!JSON.stringify(p.context).includes(original.report.title));
   const doc=await context.request.post(API+'/api/clinical-docs/render',{headers:auth,data:{...body,expected_content_snapshot:p.content_snapshot}});assert.equal(doc.status(),200);fs.writeFileSync(path.join(out,`cwb7-${species}-${template}.docx`),await doc.body());
  }
  await page.screenshot({path:path.join(out,'cwb7-'+species+'-history.png'),fullPage:true});results.push({case_id:cid,species,reports:saved.reports});
  passed.push(species+'_correction_versions_source_revision_invalidation_withdraw_refresh_both_docx');
 }
 // Draft stays only in memory across a real refresh and a subsequent login.
 await page.getByRole('button',{name:'录入检验报告',exact:true}).click();await page.getByLabel('报告标题',{exact:true}).fill('不应恢复的草稿');await page.reload();await page.getByRole('button',{name:'打开检验项目',exact:true}).click();await expect(page.getByRole('region',{name:'检验录入草稿',exact:true})).toHaveCount(0);
 await page.goto(UI);await page.getByRole('button',{name:'退出',exact:true}).click();await login();await page.goto(UI+'/cases/'+results[1].case_id);await page.getByRole('button',{name:'打开检验项目',exact:true}).click();await expect(page.getByRole('region',{name:'检验项目人工录入',exact:true})).toContainText('已撤销');
 passed.push('unsaved_draft_not_persisted_and_relogin_retains_saved_versions');
 // Hold a genuine preview response; switching case or account must discard it.
 const lateCase=(await call('POST','/api/cases',{patient_name:'迟到响应合成病例',species:'dog',chief_complaint:'合成核对',history:'不可串入别的病例'})).id;
 const lateFiles=`/api/cases/${lateCase}/attachments`,lateRoot=`/api/cases/${lateCase}/manual-lab`;
 const lateUpload=await context.request.post(API+lateFiles+'/uploads/'+randomUUID().replaceAll('-',''),{headers:{...auth,'Content-Type':'image/png','X-Attachment-Filename':'synthetic.png','X-Case-Token':(await call('GET',lateFiles)).case_token},data:fs.readFileSync(path.join(temp,'synthetic.png'))});assert(lateUpload.ok());
 const lateSource=(await lateUpload.json()).attachment;
 const lb={request_id:randomUUID().replaceAll('-',''),attachment_id:lateSource.id,operation:'confirm',expected_case_token:(await call('GET',lateFiles)).case_token,metadata:{title:'迟到合成原件',kind:'lab',taken_at:'',reported_at:'',source:'',note:''},reason:''};
 const lp=await call('POST',lateFiles+'/preview',lb);await call('POST',lateFiles+'/confirm',{...lb,preview_token:lp.preview_token,reviewed:true});
 const otherEmail='cwb7-other-'+randomUUID()+'@example.com';
 assert((await context.request.post(API+'/auth/signup',{data:{email:otherEmail,password:'Synthetic-PR26-only-20260916'}})).ok());
 const otherLogin=await context.request.post(API+'/auth/login',{form:{username:otherEmail,password:'Synthetic-PR26-only-20260916'}});assert(otherLogin.ok());const otherToken=(await otherLogin.json()).access_token;
 for(const scenario of ['case','account']){
  await page.goto(UI+'/cases/'+lateCase);await page.getByRole('button',{name:'打开检验项目',exact:true}).click();await page.getByRole('button',{name:'录入检验报告',exact:true}).click();
  await page.getByLabel('检验原件',{exact:true}).selectOption(lateSource.id);await page.getByLabel('报告标题',{exact:true}).fill('迟到草稿');await page.getByLabel('项目 1 项目名称',{exact:true}).fill('合成检验');await page.getByLabel('项目 1 结果原文',{exact:true}).fill('0.0100');await page.getByLabel('项目 1 页码或原件位置',{exact:true}).fill('第1页');await page.getByLabel('已核对项目 1',{exact:true}).check();
  let ready,release,finished;const seen=new Promise(r=>ready=r),gate=new Promise(r=>release=r),done=new Promise(r=>finished=r);
  await page.route('**/manual-lab/preview',async route=>{try{const response=await route.fetch();assert.equal(response.status(),200);ready();await gate;await route.fulfill({response}).catch(()=>{});}finally{finished();}});
  await page.getByRole('button',{name:'核对整份检验记录',exact:true}).click();await seen;
  if(scenario==='case')await page.goto(UI+'/cases/'+results[0].case_id);
  else await page.evaluate(t=>{localStorage.setItem('token',t);window.dispatchEvent(new StorageEvent('storage',{key:'token'}));},otherToken);
  release();await done;await page.unroute('**/manual-lab/preview');await expect(page.getByRole('region',{name:'整份检验核对',exact:true})).toHaveCount(0);await expect(page.getByText('迟到草稿',{exact:true})).toHaveCount(0);
 }
 assert.equal((await call('GET',lateRoot)).reports.length,0);
 passed.push('genuine_late_preview_discarded_after_case_or_account_switch_no_write');
 fs.writeFileSync(path.join(out,'cwb7-browser-saved.json'),JSON.stringify({results,external_calls:0},null,2));assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
}
main().catch(async e=>{process.exitCode=1;errors.push(String(e));console.error(e);if(page&&!page.isClosed())await page.screenshot({path:path.join(out,'cwb7-failure.png'),fullPage:true}).catch(()=>{});}).finally(async()=>{
 if(browser)await browser.close();
 if(server&&server.exitCode===null){server.kill('SIGTERM');await new Promise(resolve=>{const timer=setTimeout(()=>{server.kill('SIGKILL');resolve();},5000);server.once('exit',()=>{clearTimeout(timer);resolve();});});}
 fs.rmSync(temp,{recursive:true,force:true});fs.writeFileSync(path.join(out,'cwb7-manual-lab-checks.json'),JSON.stringify({passed,errors,external,external_calls:0,backend:process.argv.includes('--local-sqlite')?'SQLite':'PostgreSQL'},null,2));
});
