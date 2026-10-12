// Real Chromium + real authenticated app and bytes. No service or route mock.
const {chromium,expect}=require('@playwright/test');
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {createHash,randomUUID}=require('node:crypto'),{spawn,spawnSync}=require('node:child_process');
const UI='http://127.0.0.1:5173',API='http://127.0.0.1:18026',out=process.env.PMAI_ACCEPTANCE_OUT;
assert(out&&process.env.PMAI_SYNTHETIC_ACCEPTANCE==='PR26');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'cwb13-browser-')),passed=[],errors=[],external=[];
let browser,page,server;
const python=process.env.PMAI_PYTHON||'python';
const generated=spawnSync(python,['-B','tests/fixtures/build_attachment_cw_b6_fixtures.py',temp],{encoding:'utf8'});
assert.equal(generated.status,0,generated.stderr);
const prefix=process.argv.includes('--local-sqlite')?`
import os,sys,tempfile
from pathlib import Path
tmp=tempfile.TemporaryDirectory(prefix='cwb13-api-')
os.environ.clear();os.environ.update(DATABASE_URL='sqlite:///'+str(Path(tmp.name)/'synthetic.sqlite'),SECRET_KEY='synthetic-cwb13-only',ENVIRONMENT='test',RENDER='false')
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
private=tempfile.TemporaryDirectory(prefix='cwb13-private-')
os.environ.update(CASE_ATTACHMENTS_ENABLED='1',CASE_ATTACHMENTS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_DIR=private.name,MANUAL_LAB_RESULTS_ENABLED='1',MANUAL_LAB_RESULTS_SYNTHETIC_ONLY='1',MANUAL_LAB_DOCUMENTS_ENABLED='1',MANUAL_LAB_DOCUMENTS_SYNTHETIC_ONLY='1',MANUAL_IMAGING_ENABLED='1',MANUAL_IMAGING_SYNTHETIC_ONLY='1',VISIT_OVERVIEW_ENABLED='1',VISIT_OVERVIEW_SYNTHETIC_ONLY='1',LAB_RANGE_REVIEW_ENABLED='1',LAB_RANGE_REVIEW_SYNTHETIC_ONLY='1',LAB_COMPARISON_ENABLED='1',LAB_COMPARISON_SYNTHETIC_ONLY='1',LAB_COMPARISON_DOCUMENTS_ENABLED='1',LAB_COMPARISON_DOCUMENTS_SYNTHETIC_ONLY='1')
import uvicorn
uvicorn.run(main.app,host='127.0.0.1',port=18026,loop='asyncio')
`;
async function main(){
 const log=fs.openSync(path.join(out,'cwb13-backend.log'),'w');server=spawn(python,['-B','-c',boot],{stdio:['ignore',log,log],env:process.env});
 for(let i=0;i<70;i++){if(server.exitCode!==null)throw Error('Comparison backend exited');try{if((await fetch(API+'/healthz')).ok)break;}catch{}if(i===69)throw Error('Comparison backend unavailable');await new Promise(r=>setTimeout(r,200));}
 browser=await chromium.launch({headless:true});const context=await browser.newContext({serviceWorkers:'block',viewport:{width:1500,height:1100},acceptDownloads:true});
 await context.route('**/*',r=>[UI,API].includes(new URL(r.request().url()).origin)?r.continue():(external.push(r.request().url()),r.abort()));
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill('browser-owner@example.com');await page.getByPlaceholder('密码',{exact:true}).fill('Synthetic-PR26-only-20260916');await page.getByRole('button',{name:'登录',exact:true}).click();await expect(page.getByRole('button',{name:'退出',exact:true})).toBeVisible();
 const auth={Authorization:'Bearer '+await page.evaluate(()=>localStorage.getItem('token'))};
 async function call(method,url,data){const r=await context.request.fetch(API+url,{method,headers:auth,data});assert(r.ok(),await r.text());return r.json();}
 const fixture=JSON.parse(fs.readFileSync('tests/fixtures/clinical_lab_comparison_cw_b12_cases.json','utf8'));
 const button=(scope,name)=>scope.getByRole('button',{name,exact:true});
 const view=page.getByRole('region',{name:'同次就诊检验前后对照',exact:true}),lab=page.getByRole('region',{name:'检验项目人工录入',exact:true});
 const results=[];let writes=[],downloads=0,confirms=0;
 const watch=r=>{if(!['GET','HEAD','OPTIONS'].includes(r.method()))writes.push(r.url());};
 page.on('download',()=>downloads++);page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/manual-lab/confirm'))confirms++;});
 for(const species of ['dog','cat']){
  const cid=(await call('POST','/api/cases',{...fixture.case,species,patient_name:'CW-B13合成'+species})).id;
  const files=`/api/cases/${cid}/attachments`,root=`/api/cases/${cid}/manual-lab`,url=`/api/cases/${cid}/lab-comparison`;
  const sources=[],rows=[];
  async function sourceOp(item,operation,title){
   const b={request_id:randomUUID().replaceAll('-',''),attachment_id:item.id,operation,expected_case_token:(await call('GET',files)).case_token,metadata:{title,kind:'lab',taken_at:'',reported_at:'',source:'',note:''},reason:operation==='confirm'?'':'合成来源核对'};
   const p=await call('POST',files+'/preview',b);return call('POST',files+'/confirm',{...b,preview_token:p.preview_token,reviewed:true});
  }
  for(let i=0;i<2;i++){
   const bytes=Buffer.from(fs.readFileSync(path.join(temp,'synthetic.pdf'),'latin1').replace('CW-B6',`CW-B${i}`),'latin1');
   const r=await context.request.post(API+files+'/uploads/'+randomUUID().replaceAll('-',''),{headers:{...auth,'Content-Type':'application/pdf','X-Attachment-Filename':`synthetic-${i}.pdf`,'X-Case-Token':(await call('GET',files)).case_token},data:bytes});assert(r.ok(),await r.text());
   const item=(await r.json()).attachment;sources.push(item);await sourceOp(item,'confirm','合成对照原件 '+i);
   const b={request_id:randomUUID().replaceAll('-',''),attachment_id:item.id,operation:'create',expected_case_token:(await call('GET',root)).case_token,report_id:null,expected_report_token:'',data:fixture.reports[i],reason:''};
   const p=await call('POST',root+'/preview',b);rows.push((await call('POST',root+'/confirm',{...b,preview_token:p.preview_token,reviewed:true})).report);
  }
  await page.goto(UI+'/cases/'+cid);await button(page,'打开就诊资料总览').click();await button(page,'核对门诊病历草稿').click();
  const doc=page.getByRole('region',{name:'文书草稿内容核对',exact:true});
  const selectedView=doc.getByRole('region',{name:'同次就诊检验前后对照',exact:true});
  const appendix=doc.getByRole('region',{name:'文书检验前后对照附节',exact:true});
  const whole=doc.getByRole('checkbox',{name:'已核对本次草稿内容（仍未签署）',exact:true});
  await expect(button(doc,'确认并下载草稿 DOCX')).toBeDisabled();await expect(appendix).toHaveCount(0);
  await button(doc,'选择检验前后对照附节').click();
  async function choose(){
    for(const [label,value] of [['对照报告 A',String(rows[0].id)],['对照报告 B',String(rows[1].id)],['对照项目 A','4'],['对照项目 B','4']])await selectedView.getByLabel(label,{exact:true}).selectOption(value);
    await selectedView.getByLabel('确认方法与采样条件可比',{exact:true}).check();await button(selectedView,'核对条件并预览数值差').click();
    await expect(button(selectedView,'纳入本次文书核对')).toBeVisible();await button(selectedView,'纳入本次文书核对').click();
  }
  async function full(){await button(doc,'重新读取草稿').click();await expect(appendix).toBeVisible();await expect(button(doc,'确认并下载草稿 DOCX')).toBeDisabled();}
  await expect(selectedView.getByLabel('对照报告 A',{exact:true})).toHaveValue('');await choose();await expect(appendix).toHaveCount(0);await full();
  for(const literal of [fixture.expected_deltas[3],fixture.reports[0].items[3].value,sources[0].sha256,sources[1].sha256,'参考范围不同','尚未签署'])await expect(appendix).toContainText(literal);
  await appendix.screenshot({path:path.join(out,'cwb13-'+species+'-appendix.png')});assert.equal(downloads,results.length);
  await button(selectedView,'交换 A 与 B').click();await expect(appendix).toHaveCount(0);await expect(whole).toHaveCount(0);await choose();await full();
  await button(doc,'移除本次对照附节').click();await expect(appendix).toHaveCount(0);await choose();await full();
  // A late complete preview may not revive an obsolete pair.
  let seenResolve,release,finished;let seen=new Promise(r=>seenResolve=r),gate=new Promise(r=>release=r),done=new Promise(r=>finished=r);
  const previewPattern='**/clinical-docs/render-preview';
  await page.route(previewPattern,async route=>{try{const response=await route.fetch();assert.equal(response.status(),200);seenResolve();await gate;await route.fulfill({response}).catch(()=>{});}finally{finished();}});
  await button(doc,'重新读取草稿').click();await seen;await selectedView.getByLabel('对照项目 A',{exact:true}).selectOption('1');release();await done;await page.unroute(previewPattern);await expect(appendix).toHaveCount(0);
  await choose();await full();await whole.check();
  // Late real DOCX bytes after focus invalidation cannot trigger a download.
  seen=new Promise(r=>seenResolve=r);gate=new Promise(r=>release=r);done=new Promise(r=>finished=r);
  const renderPattern='**/clinical-docs/render';
  await page.route(renderPattern,async route=>{try{const response=await route.fetch();assert.equal(response.status(),200);seenResolve();await gate;await route.fulfill({response}).catch(()=>{});}finally{finished();}});
  await button(doc,'确认并下载草稿 DOCX').click();await seen;await page.evaluate(()=>window.dispatchEvent(new Event('focus')));release();await done;await page.unroute(renderPattern);await expect(whole).toHaveCount(0);assert.equal(downloads,results.length);
  await choose();await full();await whole.check();const downloading=page.waitForEvent('download');await button(doc,'确认并下载草稿 DOCX').click();const download=await downloading;
  const file=path.join(out,'cwb13-'+species+'-outpatient.docx');await download.saveAs(file);assert(download.suggestedFilename().endsWith('.docx'));
  const probe=spawnSync(python,['-c',`import sys,zipfile,json,xml.etree.ElementTree as E
with zipfile.ZipFile(sys.argv[1]) as z: r=E.fromstring(z.read('word/document.xml'))
print(json.dumps({'text':''.join(r.itertext())},ensure_ascii=False))`,file],{encoding:'utf8'});assert.equal(probe.status,0,probe.stderr);
  const output=JSON.parse(probe.stdout);for(const literal of [fixture.expected_deltas[3],sources[0].sha256,sources[1].sha256,'检验前后对照附节','尚未签署'])assert(output.text.includes(literal));
  passed.push(species+'_explicit_pair_whole_review_exact_docx_swap_remove_late_preview_and_download');
  // Return to the exact saved version without losing an unfinished editor draft.
  await button(page,'打开检验项目').click();await button(lab,'录入检验报告').click();await lab.getByLabel('报告标题',{exact:true}).fill('CW-B13 未保存检验草稿');
  await button(selectedView,`回看检验记录 #${rows[0].id} 版本 1`).click();await expect(lab.getByLabel('报告标题',{exact:true})).toHaveValue('CW-B13 未保存检验草稿');
  const record=lab.getByRole('article',{name:'检验记录 '+rows[0].id,exact:true});await expect(record.locator('details')).toHaveAttribute('open','');await button(lab,'放弃本页检验草稿').click();
  await button(page,'核对门诊病历草稿').click();await button(doc,'选择检验前后对照附节').click();await choose();await full();await whole.check();
  await button(record,'更正检验记录').click();await lab.getByLabel('报告标题',{exact:true}).fill('CW-B13 更正保存');await lab.getByLabel('更正或撤销原因',{exact:true}).fill('合成文书失效核对');
  for(let n=1;n<=fixture.reports[0].items.length;n++)await lab.getByLabel('已核对项目 '+n,{exact:true}).check();
  await button(lab,'核对整份检验记录').click();await lab.getByLabel('已核对整份检验记录',{exact:true}).check();
  const confirmPattern='**/cases/'+cid+'/manual-lab/confirm',beforeConfirms=confirms;
  seen=new Promise(r=>seenResolve=r);gate=new Promise(r=>release=r);done=new Promise(r=>finished=r);
  await page.route(confirmPattern,async route=>{try{seenResolve();await gate;const response=await route.fetch();assert.equal(response.status(),200);if(species==='cat')await route.abort('failed');else await route.fulfill({response});}finally{finished();}});
  await button(lab,'确认保存检验记录').click();await seen;await expect(whole).toHaveCount(0);await expect(appendix).toHaveCount(0);release();await done;await page.unroute(confirmPattern);
  await expect(lab).toContainText(species==='cat'?'已回读保存结果，未重复提交。':'检验记录已保存。');assert.equal(confirms,beforeConfirms+1);
  passed.push(species+'_exact_version_navigation_draft_preservation_and_confirmation_start_'+(species==='cat'?'lost_reply_readback':'save'));
  results.push({case_id:cid,species,filename:path.basename(file),size:fs.statSync(file).size,sha256:createHash('sha256').update(fs.readFileSync(file)).digest('hex')});
 }
 // Switching case/account while a catalog is in flight must not repopulate it.
 for(const scenario of ['case','account']){
  await page.goto(UI+'/cases/'+results[0].case_id);await button(page,'打开就诊资料总览').click();await button(page,'核对门诊病历草稿').click();
  let seenResolve,release,finished;const seen=new Promise(r=>seenResolve=r),gate=new Promise(r=>release=r),done=new Promise(r=>finished=r);
  const pattern='**/cases/'+results[0].case_id+'/lab-comparison';
  await page.route(pattern,async route=>{try{const response=await route.fetch();seenResolve();await gate;await route.fulfill({response}).catch(()=>{});}finally{finished();}});
  await button(page,'选择检验前后对照附节').click();await seen;
  if(scenario==='case')await page.goto(UI+'/cases/'+results[1].case_id);
  else await page.evaluate(()=>{localStorage.removeItem('token');window.dispatchEvent(new StorageEvent('storage',{key:'token'}));});
  release();await done;await page.unroute(pattern);await expect(page.getByRole('region',{name:'文书检验前后对照附节',exact:true})).toHaveCount(0);
  passed.push('late_catalog_discarded_after_'+scenario);
 }
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.equal(downloads,2);
 fs.writeFileSync(path.join(out,'cwb13-browser-saved.json'),JSON.stringify({results,external_calls:0,explicit_downloads:downloads},null,2));
}
main().catch(async e=>{process.exitCode=1;errors.push(String(e));console.error(e);if(page&&!page.isClosed())await page.screenshot({path:path.join(out,'cwb13-failure.png'),fullPage:true}).catch(()=>{});}).finally(async()=>{
 if(browser)await browser.close();if(server&&server.exitCode===null){server.kill('SIGTERM');await new Promise(resolve=>{const timer=setTimeout(()=>{server.kill('SIGKILL');resolve();},5000);server.once('exit',()=>{clearTimeout(timer);resolve();});});}
 fs.rmSync(temp,{recursive:true,force:true});fs.writeFileSync(path.join(out,'cwb13-document-checks.json'),JSON.stringify({passed,errors,external,external_calls:0,backend:process.argv.includes('--local-sqlite')?'SQLite':'PostgreSQL'},null,2));
});
