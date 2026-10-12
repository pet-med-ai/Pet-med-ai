// Real Chromium + real authenticated app and bytes. No service or route mock.
const {chromium,expect}=require('@playwright/test');
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {createHash,randomUUID}=require('node:crypto'),{spawn,spawnSync}=require('node:child_process');
const UI='http://127.0.0.1:5173',API='http://127.0.0.1:18026',out=process.env.PMAI_ACCEPTANCE_OUT;
assert(out&&process.env.PMAI_SYNTHETIC_ACCEPTANCE==='PR26');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'cwb6-browser-')),passed=[],errors=[],external=[];
let browser,page,server;
const python=process.env.PMAI_PYTHON||'python';
const generated=spawnSync(python,['-B','tests/fixtures/build_attachment_cw_b6_fixtures.py',temp],{encoding:'utf8'});
assert.equal(generated.status,0,generated.stderr);
const prefix=process.argv.includes('--local-sqlite')?`
import os,sys,tempfile
from pathlib import Path
tmp=tempfile.TemporaryDirectory(prefix='cwb6-api-')
os.environ.clear();os.environ.update(DATABASE_URL='sqlite:///'+str(Path(tmp.name)/'synthetic.sqlite'),SECRET_KEY='synthetic-cwb6-only',ENVIRONMENT='test',RENDER='false')
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
private=tempfile.TemporaryDirectory(prefix='cwb6-private-')
os.environ.update(CASE_ATTACHMENTS_ENABLED='1',CASE_ATTACHMENTS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_DIR=private.name)
import uvicorn
uvicorn.run(main.app,host='127.0.0.1',port=18026,loop='asyncio')
`;
async function main(){
 const log=fs.openSync(path.join(out,'cwb6-backend.log'),'w');
 server=spawn(python,['-B','-c',boot],{stdio:['ignore',log,log],env:process.env});
 for(let i=0;i<70;i++){
  if(server.exitCode!==null)throw Error('Attachment backend exited; inspect cwb6-backend.log');
  try{if((await fetch(API+'/healthz')).ok)break;}catch{}
  if(i===69)throw Error('Attachment backend unavailable');
  await new Promise(r=>setTimeout(r,200));
 }
 browser=await chromium.launch({headless:true});
 const context=await browser.newContext({serviceWorkers:'block',viewport:{width:1400,height:1080},acceptDownloads:true});
 await context.route('**/*',r=>[UI,API].includes(new URL(r.request().url()).origin)?r.continue():(external.push(r.request().url()),r.abort()));
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 async function login(){await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill('browser-owner@example.com');await page.getByPlaceholder('密码',{exact:true}).fill('Synthetic-PR26-only-20260916');await page.getByRole('button',{name:'登录',exact:true}).click();await expect(page.getByRole('button',{name:'退出',exact:true})).toBeVisible();}
 await login();const auth={Authorization:'Bearer '+await page.evaluate(()=>localStorage.getItem('token'))};
 const created=await context.request.post(API+'/api/cases',{headers:auth,data:{patient_name:'CW-B6浏览器合成犬',species:'dog',chief_complaint:'合成检查资料验收',history:'原始手写病史；未见呕吐。'}});assert.equal(created.status(),201);
 const cid=(await created.json()).id,root=API+`/api/cases/${cid}/attachments`;
 let listCalls=0;page.on('request',r=>{if(r.url()===root)listCalls++;});
 async function open(){await page.goto(UI+'/cases/'+cid);await page.getByRole('button',{name:'打开检查资料',exact:true}).click();await expect(page.getByRole('region',{name:'检查资料',exact:true})).toContainText('CW-B6浏览器合成犬');}
 await page.goto(UI+'/cases/'+cid);await expect(page.getByRole('button',{name:'打开检查资料',exact:true})).toBeVisible();assert.equal(listCalls,0);
 await page.getByRole('button',{name:'打开检查资料',exact:true}).click();
 const panel=page.getByRole('region',{name:'检查资料',exact:true});await expect(panel.getByText('暂无匹配的检查资料。',{exact:true})).toBeVisible();
 passed.push('entry_is_lazy_and_bound_to_authenticated_saved_case');
 async function preview(){await panel.getByRole('button',{name:'核对资料关联',exact:true}).click();await expect(panel.getByRole('region',{name:'资料关联核对',exact:true})).toBeVisible();await expect(panel.getByRole('button',{name:'确认资料操作',exact:true})).toBeDisabled();}
 async function commit(){await panel.getByLabel('已核对病例、原件和资料信息',{exact:true}).check();await panel.getByRole('button',{name:'确认资料操作',exact:true}).click();await expect(panel.getByRole('button',{name:'确认资料操作',exact:true})).toHaveCount(0);}
 for(const [index,name] of ['synthetic.png','synthetic.pdf','synthetic.jpg'].entries()){
  await panel.getByLabel('选择检查文件',{exact:true}).setInputFiles(path.join(temp,name));
  await panel.getByRole('button',{name:'上传待核对原件',exact:true}).click();await expect(panel).toContainText('原件已暂存');
  await panel.getByLabel('资料标题',{exact:true}).fill('合成资料-'+index);await panel.getByLabel('资料类型',{exact:true}).selectOption(index===0?'lab':index===1?'dr':'ultrasound');
  await preview();await panel.getByLabel('已核对病例、原件和资料信息',{exact:true}).check();
  await panel.getByLabel('备注',{exact:true}).fill('仅合成验收');await expect(panel.getByRole('region',{name:'资料关联核对',exact:true})).toHaveCount(0);await preview();
  if(index===0){
   let posts=0;await page.route('**/attachments/confirm',async r=>{posts++;await r.fetch();await r.abort('failed');});
   await commit();await expect(panel).toContainText('操作结果已回读');assert.equal(posts,1);await page.unroute('**/attachments/confirm');
   passed.push('lost_confirm_reply_reads_status_without_repeating_post');
  }else await commit();
  const row=panel.getByRole('listitem').filter({hasText:'合成资料-'+index});await expect(row).toContainText('已关联');
  const event=page.waitForEvent('download');await row.getByRole('button',{name:'下载原件',exact:true}).click();const download=await event;
  const dest=path.join(out,'cwb6-download-'+name);await download.saveAs(dest);assert.deepEqual(fs.readFileSync(dest),fs.readFileSync(path.join(temp,name)));
  if(name.endsWith('.pdf'))assert.equal(await row.getByRole('button',{name:'查看图片',exact:true}).count(),0);
  else{await row.getByRole('button',{name:'查看图片',exact:true}).click();await expect(panel.getByRole('img',{name,exact:true})).toBeVisible();await panel.getByRole('button',{name:'关闭图片',exact:true}).click();}
 }
 passed.push('pdf_png_jpeg_upload_review_download_exact_bytes_and_protected_images');
 // Duplicate original does not create a new association or overwrite metadata.
 await panel.getByLabel('选择检查文件',{exact:true}).setInputFiles(path.join(temp,'synthetic.png'));
 await panel.getByRole('button',{name:'上传待核对原件',exact:true}).click();await expect(panel).toContainText('相同原件已关联');assert.equal(await panel.getByRole('listitem').count(),3);
 let row=panel.getByRole('listitem').filter({hasText:'合成资料-0'});await row.getByRole('button',{name:'更正资料信息',exact:true}).click();await panel.getByLabel('资料标题',{exact:true}).fill('更正后合成资料');await preview();await commit();
 await panel.getByLabel('筛选资料',{exact:true}).fill('更正后');assert.equal(await panel.getByRole('listitem').count(),1);await panel.getByLabel('筛选资料',{exact:true}).fill('');
 await panel.getByLabel('筛选类型',{exact:true}).selectOption('dr');assert.equal(await panel.getByRole('listitem').count(),1);await panel.getByLabel('筛选类型',{exact:true}).selectOption('');
 row=panel.getByRole('listitem').filter({hasText:'合成资料-1'});await row.getByRole('button',{name:'撤销关联',exact:true}).click();await panel.getByLabel('撤销原因',{exact:true}).fill('合成误关联');await preview();await commit();await expect(row).toContainText('已撤销');assert.equal(await row.getByRole('button',{name:'下载原件',exact:true}).count(),0);
 const listing=await (await context.request.get(root,{headers:auth})).json();assert.equal(listing.items.length,3);
 const withdrawn=listing.items.find(x=>x.state==='withdrawn');assert.equal((await context.request.get(root+'/'+withdrawn.id+'/content?request_id='+randomUUID().replaceAll('-',''),{headers:auth})).status(),404);
 passed.push('dedup_metadata_correction_filters_withdrawal_and_denied_raw_access');
 await open();await expect(panel).toContainText('更正后合成资料');await expect(panel).toContainText('已撤销');
 await page.goto(UI);await page.getByRole('button',{name:'退出',exact:true}).click();await login();await open();await expect(panel).toContainText('更正后合成资料');await expect(panel).toContainText('已撤销');
 passed.push('refresh_logout_relogin_preserves_final_associations');
 const saved=await (await context.request.get(API+'/api/cases/'+cid,{headers:auth})).json();assert.equal(saved.history,'原始手写病史；未见呕吐。');
 for(const template of ['outpatient_record_zh','owner_visit_summary_zh']){
  const p=await context.request.post(API+'/api/clinical-docs/render-preview',{headers:auth,data:{case_id:cid,template_id:template}});assert.equal(p.status(),200);const preview=await p.json();assert.equal(preview.context['visit.history'],saved.history);assert(!JSON.stringify(preview.context).includes('更正后合成资料'));
  const doc=await context.request.post(API+'/api/clinical-docs/render',{headers:auth,data:{case_id:cid,template_id:template,expected_content_snapshot:preview.content_snapshot}});assert.equal(doc.status(),200);fs.writeFileSync(path.join(out,'cwb6-'+template+'.docx'),await doc.body());
 }
 passed.push('both_actual_docx_and_case_history_remain_unchanged');
 await page.screenshot({path:path.join(out,'cwb6-final-attachments.png'),fullPage:true});
 fs.writeFileSync(path.join(out,'cwb6-browser-saved.json'),JSON.stringify({case_id:cid,items:listing.items.map(x=>({id:x.id,name:x.name,state:x.state,size:x.size,sha256:x.sha256})),external_calls:0},null,2));
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
}
main().catch(async e=>{process.exitCode=1;errors.push(String(e));console.error(e);if(page&&!page.isClosed())await page.screenshot({path:path.join(out,'cwb6-failure.png'),fullPage:true}).catch(()=>{});}).finally(async()=>{
 if(browser)await browser.close();
 if(server&&server.exitCode===null){server.kill('SIGTERM');await new Promise(resolve=>{const timer=setTimeout(()=>{server.kill('SIGKILL');resolve();},5000);server.once('exit',()=>{clearTimeout(timer);resolve();});});}
 fs.rmSync(temp,{recursive:true,force:true});fs.writeFileSync(path.join(out,'cwb6-attachment-checks.json'),JSON.stringify({passed,errors,external,external_calls:0,backend:process.argv.includes('--local-sqlite')?'SQLite':'PostgreSQL'},null,2));
});
