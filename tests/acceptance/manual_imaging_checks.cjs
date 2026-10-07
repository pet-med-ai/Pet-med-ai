// Real Chromium + real authenticated app and bytes. No service or route mock.
const {chromium,expect}=require('@playwright/test');
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {createHash,randomUUID}=require('node:crypto'),{spawn,spawnSync}=require('node:child_process');
const UI='http://127.0.0.1:5173',API='http://127.0.0.1:18026',out=process.env.PMAI_ACCEPTANCE_OUT;
assert(out&&process.env.PMAI_SYNTHETIC_ACCEPTANCE==='PR26');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'cwb9-browser-')),passed=[],errors=[],external=[];
let browser,page,server;
const python=process.env.PMAI_PYTHON||'python';
const generated=spawnSync(python,['-B','tests/fixtures/build_attachment_cw_b6_fixtures.py',temp],{encoding:'utf8'});
assert.equal(generated.status,0,generated.stderr);
const prefix=process.argv.includes('--local-sqlite')?`
import os,sys,tempfile
from pathlib import Path
tmp=tempfile.TemporaryDirectory(prefix='cwb9-api-')
os.environ.clear();os.environ.update(DATABASE_URL='sqlite:///'+str(Path(tmp.name)/'synthetic.sqlite'),SECRET_KEY='synthetic-cwb9-only',ENVIRONMENT='test',RENDER='false')
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
private=tempfile.TemporaryDirectory(prefix='cwb9-private-')
os.environ.update(CASE_ATTACHMENTS_ENABLED='1',CASE_ATTACHMENTS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_DIR=private.name,MANUAL_LAB_RESULTS_ENABLED='1',MANUAL_LAB_RESULTS_SYNTHETIC_ONLY='1',MANUAL_LAB_DOCUMENTS_ENABLED='1',MANUAL_LAB_DOCUMENTS_SYNTHETIC_ONLY='1',MANUAL_IMAGING_ENABLED='1',MANUAL_IMAGING_SYNTHETIC_ONLY='1')
import uvicorn
uvicorn.run(main.app,host='127.0.0.1',port=18026,loop='asyncio')
`;
async function main(){
 const log=fs.openSync(path.join(out,'cwb9-backend.log'),'w');server=spawn(python,['-B','-c',boot],{stdio:['ignore',log,log],env:process.env});
 for(let i=0;i<70;i++){if(server.exitCode!==null)throw Error('Document backend exited');try{if((await fetch(API+'/healthz')).ok)break;}catch{}if(i===69)throw Error('Document backend unavailable');await new Promise(r=>setTimeout(r,200));}
 browser=await chromium.launch({headless:true});const context=await browser.newContext({serviceWorkers:'block',viewport:{width:1400,height:1080},acceptDownloads:true});
 await context.route('**/*',r=>[UI,API].includes(new URL(r.request().url()).origin)?r.continue():(external.push(r.request().url()),r.abort()));
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 async function login(){await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill('browser-owner@example.com');await page.getByPlaceholder('密码',{exact:true}).fill('Synthetic-PR26-only-20260916');await page.getByRole('button',{name:'登录',exact:true}).click();await expect(page.getByRole('button',{name:'退出',exact:true})).toBeVisible();}
 await login();const auth={Authorization:'Bearer '+await page.evaluate(()=>localStorage.getItem('token'))};
 async function call(method,url,data){const r=await context.request.fetch(API+url,{method,headers:auth,data});assert(r.ok(),await r.text());return r.json();}
 const original=JSON.parse(fs.readFileSync('tests/fixtures/manual_imaging_cw_b9_cases.json','utf8'));
 const labData=JSON.parse(fs.readFileSync('tests/fixtures/manual_lab_cw_b7_cases.json','utf8')),results=[];
 const button=(scope,name)=>scope.getByRole('button',{name,exact:true});
 const fields={title:'报告标题',body_part:'检查部位',taken_at:'检查时间（含时区）',institution:'出具机构',findings:'所见原文',impression:'结论原文',limitations:'局限性原文',note:'备注原文',position:'页码或原件位置'};
 for(const species of ['dog','cat']){
  const cid=(await call('POST','/api/cases',{patient_name:'CW-B9合成'+species,species,owner_name:'合成宠主',coat_color:'黑白（合成）',chief_complaint:'合成影像验收',history:'原始病史 < & {{literal}}'})).id;
  const files=`/api/cases/${cid}/attachments`,root=`/api/cases/${cid}/manual-imaging`,modality=species==='dog'?'dr':'ultrasound';
  async function sourceOp(source,operation,kind,title='合成影像原件'){
   const b={request_id:randomUUID().replaceAll('-',''),attachment_id:source.id,operation,expected_case_token:(await call('GET',files)).case_token,metadata:{title,kind,taken_at:'',reported_at:'',source:'',note:''},reason:operation==='withdraw'?'合成撤销':''};
   const p=await call('POST',files+'/preview',b);return call('POST',files+'/confirm',{...b,preview_token:p.preview_token,reviewed:true});
  }
  async function attach(name,kind){const mime=name.endsWith('.pdf')?'application/pdf':'image/png',raw=fs.readFileSync(path.join(temp,name));const upload=await context.request.post(API+files+'/uploads/'+randomUUID().replaceAll('-',''),{headers:{...auth,'Content-Type':mime,'X-Attachment-Filename':name,'X-Case-Token':(await call('GET',files)).case_token},data:raw});assert(upload.ok());const item=(await upload.json()).attachment;await sourceOp(item,'confirm',kind);return item;}
  const source=await attach(species==='dog'?'synthetic.pdf':'synthetic.png',modality);
  const before=await call('GET','/api/cases/'+cid);
  await page.goto(UI+'/cases/'+cid);await button(page,'打开影像记录').click();
  const editor=page.getByRole('region',{name:'影像报告人工录入',exact:true});
  await button(editor,'录入影像报告').click();await editor.getByLabel('影像原件',{exact:true}).selectOption(source.id);
  const downloading=page.waitForEvent('download');await button(editor,'打开核对原件').click();const file=await downloading;
  const rawPath=path.join(out,`cwb9-${species}-original`);await file.saveAs(rawPath);assert.equal(createHash('sha256').update(fs.readFileSync(rawPath)).digest('hex'),source.sha256);
  await editor.getByLabel('检查类型',{exact:true}).selectOption(modality);
  for(const [key,label] of Object.entries(fields))await editor.getByLabel(label,{exact:true}).fill(original[key]);
  async function reviewSave(){await editor.getByLabel('已核对所见原文',{exact:true}).check();await editor.getByLabel('已核对结论原文',{exact:true}).check();await button(editor,'核对整份影像记录').click();await expect(button(editor,'确认保存影像记录')).toBeDisabled();await editor.getByLabel('已核对整份影像记录',{exact:true}).check();await button(editor,'确认保存影像记录').click();await expect(editor.getByRole('region',{name:'影像录入草稿',exact:true})).toHaveCount(0);}
  await reviewSave();let rows=(await call('GET',root)).reports;assert.equal(rows.length,1);assert.deepEqual(rows[0].data,{...original,modality});
  await page.screenshot({path:path.join(out,'cwb9-'+species+'-saved.png'),fullPage:true});
  passed.push(species+'_real_manual_entry_source_bytes_section_checks_and_save');
  // A real lab report is selected together with the manually entered image.
  const labSource=await attach(species==='dog'?'synthetic.png':'synthetic.pdf','lab'),labRoot=`/api/cases/${cid}/manual-lab`;
  const lb={request_id:randomUUID().replaceAll('-',''),attachment_id:labSource.id,operation:'create',expected_case_token:(await call('GET',labRoot)).case_token,report_id:null,expected_report_token:'',data:labData,reason:''};const lp=await call('POST',labRoot+'/preview',lb);await call('POST',labRoot+'/confirm',{...lb,preview_token:lp.preview_token,reviewed:true});
  const panel=page.getByRole('region',{name:'文书草稿内容核对',exact:true});
  async function choose(label,mixed=false){await button(page,label).click();await button(panel,'选择已核对影像报告').click();await panel.getByLabel('纳入影像 '+original.title,{exact:true}).check();if(mixed){await button(panel,'选择已核对检验报告').click();await panel.getByLabel('纳入 '+labData.report.title,{exact:true}).check();}await button(panel,'重新读取草稿').click();await expect(panel.getByRole('region',{name:'影像报告文书附节',exact:true})).toBeVisible();await expect(button(panel,'确认并下载草稿 DOCX')).toBeDisabled();}
  for(const [label,template] of [['导出门诊病历草稿 DOCX','outpatient_record_zh'],['导出宠主说明草稿 DOCX','owner_visit_summary_zh']]){
   await choose(label,true);await expect(panel).toContainText(original.impression);await expect(panel).toContainText(source.sha256);
   await panel.getByLabel('已核对本次草稿内容（仍未签署）',{exact:true}).check();const waiting=page.waitForEvent('download');await button(panel,'确认并下载草稿 DOCX').click();const d=await waiting;const dest=path.join(out,`cwb9-${species}-${template}.docx`);await d.saveAs(dest);
   const xml=spawnSync(python,['-c',"import sys,zipfile;from xml.etree import ElementTree as E;z=zipfile.ZipFile(sys.argv[1]);print(''.join(E.fromstring(z.read('word/document.xml')).itertext()))",dest],{encoding:'utf8'});assert.equal(xml.status,0,xml.stderr);for(const v of [original.impression,original.taken_at,'影像报告附节','检验结果附节','0.0100',source.sha256])assert(xml.stdout.includes(v),v);
   await button(panel,'关闭草稿核对').click();passed.push(species+'_'+template+'_real_mixed_selection_review_download');
  }
  // Actual UI correction retains the old version, then a source revision invalidates export.
  await button(editor,'刷新影像记录').click();await button(editor,'更正影像记录').click();await editor.getByLabel('所见原文',{exact:true}).fill('更正原文 <tag> & {{visit.history}}');await editor.getByLabel('更正或撤销原因',{exact:true}).fill('合成医生更正');await reviewSave();
  rows=(await call('GET',root)).reports;assert.equal(rows.length,2);assert.equal(rows[0].state,'superseded');assert.equal(rows[1].version,2);
  await choose('导出门诊病历草稿 DOCX');await expect(panel).toContainText('更正原文 <tag> & {{visit.history}}');await panel.getByLabel('已核对本次草稿内容（仍未签署）',{exact:true}).check();
  await sourceOp(source,'update',modality,'修订原件标题');await button(panel,'确认并下载草稿 DOCX').click();await expect(panel).toContainText('原确认已失效');
  await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await expect(panel).toContainText('当前没有可纳入');await expect(button(panel,'确认并下载草稿 DOCX')).toHaveCount(0);
  await button(panel,'返回影像记录与原件').click();await expect(panel).toHaveCount(0);await expect(editor).toContainText('需重新核对');
  await button(editor,'撤销影像记录').click();await editor.getByLabel('更正或撤销原因',{exact:true}).fill('合成撤销');await button(editor,'核对整份影像记录').click();await editor.getByLabel('已核对整份影像记录',{exact:true}).check();await button(editor,'确认保存影像记录').click();await expect(editor).toContainText('已撤销');
  const after=await call('GET','/api/cases/'+cid);assert.equal(after.history,before.history);results.push({case_id:cid,species,reports:(await call('GET',root)).reports});await page.screenshot({path:path.join(out,'cwb9-'+species+'-withdrawn.png'),fullPage:true});
  passed.push(species+'_ui_correction_source_invalidation_stale_doc_refusal_withdrawal');
 }
 // Genuine delayed preview and export replies are dropped after leaving the case.
 const cid=results[0].case_id;await page.goto(UI+'/cases/'+cid);await button(page,'导出门诊病历草稿 DOCX').click();await expect(page.getByRole('region',{name:'文书草稿内容核对',exact:true})).toContainText('原始病史');
 await button(page,'关闭草稿核对').click();
 const otherEmail='cwb9-other-'+randomUUID()+'@example.com';
 assert((await context.request.post(API+'/auth/signup',{data:{email:otherEmail,password:'Synthetic-PR26-only-20260916'}})).ok());
 const otherLogin=await context.request.post(API+'/auth/login',{form:{username:otherEmail,password:'Synthetic-PR26-only-20260916'}});assert(otherLogin.ok());const otherToken=(await otherLogin.json()).access_token;
 for(const scenario of ['case','account'])for(const endpoint of ['render-preview','render']){
  await page.evaluate(t=>localStorage.setItem('token',t),auth.Authorization.slice(7));await page.goto(UI+'/cases/'+cid);
  let ready,release,finished;const seen=new Promise(r=>ready=r),gate=new Promise(r=>release=r),done=new Promise(r=>finished=r);let downloadCount=0;const listener=()=>downloadCount++;page.on('download',listener);
  await page.route('**/clinical-docs/'+endpoint,async route=>{try{const response=await route.fetch();assert.equal(response.status(),200);ready();await gate;await route.fulfill({response}).catch(()=>{});}finally{finished();}});
  await button(page,'导出门诊病历草稿 DOCX').click();
  if(endpoint==='render'){await page.getByLabel('已核对本次草稿内容（仍未签署）',{exact:true}).check();await button(page,'确认并下载草稿 DOCX').click();}
  await seen;if(scenario==='case')await page.goto(UI+'/cases/'+results[1].case_id);else await page.evaluate(t=>{localStorage.setItem('token',t);window.dispatchEvent(new StorageEvent('storage',{key:'token'}));},otherToken);release();await done;await page.unroute('**/clinical-docs/'+endpoint);await expect(page.getByRole('region',{name:'文书草稿内容核对',exact:true})).toHaveCount(0);assert.equal(downloadCount,0);page.off('download',listener);
 }
 passed.push('genuine_late_preview_and_download_discarded_after_case_and_account_change');
 await page.evaluate(t=>localStorage.setItem('token',t),auth.Authorization.slice(7));await page.goto(UI);await button(page,'退出').click();await login();await page.goto(UI+'/cases/'+cid);
 await page.reload();await button(page,'导出门诊病历草稿 DOCX').click();await expect(button(page,'选择已核对影像报告')).toBeVisible();await expect(page.getByRole('region',{name:'影像报告文书附节',exact:true})).toHaveCount(0);
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);fs.writeFileSync(path.join(out,'cwb9-browser-saved.json'),JSON.stringify({results,external_calls:0},null,2));
}
main().catch(async e=>{process.exitCode=1;errors.push(String(e));console.error(e);if(page&&!page.isClosed())await page.screenshot({path:path.join(out,'cwb9-failure.png'),fullPage:true}).catch(()=>{});}).finally(async()=>{
 if(browser)await browser.close();if(server&&server.exitCode===null){server.kill('SIGTERM');await new Promise(resolve=>{const timer=setTimeout(()=>{server.kill('SIGKILL');resolve();},5000);server.once('exit',()=>{clearTimeout(timer);resolve();});});}
 fs.rmSync(temp,{recursive:true,force:true});fs.writeFileSync(path.join(out,'cwb9-imaging-checks.json'),JSON.stringify({passed,errors,external,external_calls:0,backend:process.argv.includes('--local-sqlite')?'SQLite':'PostgreSQL'},null,2));
});
