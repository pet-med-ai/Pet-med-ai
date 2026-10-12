// CW-B25: actual app, authenticated synthetic data, browser geometry and literal text.
const {chromium, expect} = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const {spawn, spawnSync, execFileSync} = require('node:child_process');
const {randomUUID, createHash} = require('node:crypto');
const {trackBrowser} = require('./clinical_visit_journey_harness.cjs');
const UI = 'http://127.0.0.1:5173', API = 'http://127.0.0.1:18026';
const out = process.env.PMAI_ACCEPTANCE_OUT, python = process.env.PMAI_PYTHON || 'python';
assert(out && process.env.PMAI_SYNTHETIC_ACCEPTANCE === 'PR26');
fs.mkdirSync(out, {recursive:true});
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'cwb25-browser-'));
const sqlite = process.argv.includes('--local-sqlite');
const fixturePath = 'tests/fixtures/clinical_lab_readability_cw_b25_cases.json';
const fixture = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const report = {schema:fixture.schema, head:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),
  worktree_clean:!execFileSync('git',['status','--porcelain'],{encoding:'utf8'}).trim(),
  source_sha256:Object.fromEntries(['components/ClinicalLabTable.css','components/CaseLabResults.jsx','components/CaseLabRangeReview.jsx','components/ClinicalDocLabSelection.jsx','pages/CaseDetail.jsx'].map(name=>[name,digest(fs.readFileSync('frontend/src/'+name))])),
  fixture_sha256:digest(fs.readFileSync(fixturePath)), status:'INCOMPLETE', backend:sqlite?'sqlite':'postgresql',
  doctor_acceptance:'pending', merged:false, deployed:false, layouts:[], cases:[], screenshots:[], errors:[], external:[], requests:[]};
let server, browser, context, page, tracker, token, downloads = 0;
const button = (scope,name) => scope.getByRole('button',{name,exact:true});
const region = name => page.getByRole('region',{name,exact:true});
const prefix = sqlite ? `
import os,sys,tempfile
from pathlib import Path
tmp=tempfile.TemporaryDirectory(prefix='cwb25-api-')
database=Path(tmp.name)/'synthetic.sqlite'
assert not database.exists()
os.environ.clear();os.environ.update(DATABASE_URL='sqlite:///'+str(database),SECRET_KEY='synthetic-cwb25-only',ENVIRONMENT='test',RENDER='false')
sys.path[:]=[str(Path('backend').resolve())]+[p for p in sys.path if Path(p or '.').resolve()!=Path('.').resolve()]
def guard(event,args):
    if event in {'socket.connect','socket.connect_ex','socket.bind'} and isinstance(args[1],tuple):
        assert args[1][0] in {'127.0.0.1','::1'} and args[1][1]==18026
    if event=='socket.getaddrinfo':assert args[0] in {'127.0.0.1','localhost','::1',None}
    if event=='sqlite3.connect':assert Path(args[0]).resolve()==database
sys.addaudithook(guard)
import main,db,models
db.Base.metadata.create_all(db.engine)
from fastapi.testclient import TestClient
with TestClient(main.app) as client:
    assert client.post('/auth/signup',json={'email':'browser-owner@example.com','password':'Synthetic-PR26-only-20260916'}).status_code==200
` : `
import sys
sys.path.insert(0,'tests/acceptance')
import fixture as f
main=f.main
`;
const boot = prefix + `
import os,tempfile
private=tempfile.TemporaryDirectory(prefix='cwb25-private-')
os.environ.update(CASE_ATTACHMENTS_ENABLED='1',CASE_ATTACHMENTS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_DIR=private.name,MANUAL_LAB_RESULTS_ENABLED='1',MANUAL_LAB_RESULTS_SYNTHETIC_ONLY='1',MANUAL_LAB_DOCUMENTS_ENABLED='1',MANUAL_LAB_DOCUMENTS_SYNTHETIC_ONLY='1',LAB_RANGE_REVIEW_ENABLED='1',LAB_RANGE_REVIEW_SYNTHETIC_ONLY='1')
import uvicorn
uvicorn.run(main.app,host='127.0.0.1',port=18026,loop='asyncio')
`;
async function call(method,url,data) {
  const response = await context.request.fetch(API+url,{method,headers:{Authorization:'Bearer '+token},data});
  assert(response.ok(),`${method} ${url}: ${response.status()} ${await response.text()}`);
  return response.json();
}
function expectedRows(data, mode) {
  const types = {number:'数值',comparison:'比较值（如 <5）',text:'文本结果',not_tested:'未测',not_provided:'未提供'};
  return data.items.map((r,i) => {
    const missing = v => v || '未提供';
    if (mode === 'document') return [r.name,types[r.result_type] && ['not_tested','not_provided'].includes(r.result_type) ? types[r.result_type] : r.value,missing(r.unit),missing(r.reference),missing(r.flag),r.position];
    return [mode === 'range' ? `${i+1}. ${r.name}\n${r.position}` : r.name,types[r.result_type],r.value || (mode === 'range' ? '未提供' : '未填写'),missing(r.unit),missing(r.reference),missing(r.reference_low),missing(r.reference_high),missing(r.reference_unit),missing(r.flag),...(mode === 'range' ? [] : [r.position])];
  });
}
async function inspect(tableRegion, data, mode, label) {
  await expect(tableRegion).toBeVisible();
  await tracker.drain();
  const start = report.requests.length, downloadStart = downloads;
  const table = tableRegion.locator('table');
  const expected = expectedRows(data,mode);
  for (const width of fixture.viewport_widths) {
    await page.setViewportSize({width,height:1100});
    await tableRegion.evaluate(el => { el.scrollLeft=0; });
    await expect(table.locator('tbody tr')).toHaveCount(data.items.length);
    const cells = await table.locator('tbody tr').evaluateAll(rows => rows.map(row => [...row.cells].map(c=>c.textContent)));
    for (let i=0;i<expected.length;i++) assert.deepEqual(cells[i].slice(0,expected[i].length),expected[i],label+' literal row '+i);
    const geometry = await tableRegion.evaluate((el,{items,mode}) => {
      const issues=[], t=el.querySelector('table'), box=el.getBoundingClientRect();
      const headers=[...t.querySelectorAll('thead th')];
      if (!headers.length || headers.some(h=>h.scope!=='col')) issues.push('missing column header association');
      if (el.tabIndex!==0 || !el.getAttribute('aria-label')) issues.push('missing named keyboard scroll region');
      if (box.left < -1 || box.right > innerWidth+1) issues.push('table region outside viewport');
      if (document.documentElement.scrollWidth>innerWidth+1) issues.push('page horizontal overflow');
      for (const [r,row] of [...t.tBodies[0].rows].entries()) for (const [c,cell] of [...row.cells].entries()) {
        const cb=cell.getBoundingClientRect();
        if(cell.scrollWidth>cell.clientWidth+1) issues.push(`overflow ${r}/${c}`);
        const valueColumn=mode==='document'?1:2;
        const atomic=(mode==='document'?[2,3]:[3,4,5,6,7]).includes(c) || (c===valueColumn && ['number','comparison'].includes(items[r].result_type));
        const text=cell.firstChild;
        if (!text || text.nodeType!==Node.TEXT_NODE) {issues.push(`unexpected cell content ${r}/${c}`);continue;}
        let offset=0;
        for(const line of text.textContent.split('\n')) {
          if(line.length) {
            const range=document.createRange();range.setStart(text,offset);range.setEnd(text,offset+line.length);
            const rects=[...range.getClientRects()].filter(x=>x.width>0);
            if(atomic && new Set(rects.map(x=>Math.round(x.top))).size!==1) issues.push(`split literal ${r}/${c}`);
            if(rects.some(x=>x.left<cb.left-1 || x.right>cb.right+1)) issues.push(`overlapping content ${r}/${c}`);
          }
          offset+=line.length+1;
        }
      }
      const overflow_elements=issues.includes('page horizontal overflow') ? [...document.body.querySelectorAll('*')].filter(node=>!node.closest('.clinical-lab-table-region') && node.getBoundingClientRect().right>innerWidth+1).slice(0,12).map(node=>({tag:node.tagName,class:node.className,text:node.textContent.slice(0,90),right:node.getBoundingClientRect().right})) : [];
      const overflow_text=[];
      if(issues.includes('page horizontal overflow')) {
        const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
        for(let node=walker.nextNode();node && overflow_text.length<12;node=walker.nextNode()) {
          if(node.parentElement.closest('.clinical-lab-table-region,script,style'))continue;
          const range=document.createRange();range.selectNodeContents(node);
          const right=Math.max(0,...[...range.getClientRects()].map(rect=>rect.right));
          if(right>innerWidth+1)overflow_text.push({tag:node.parentElement.tagName,class:node.parentElement.className,text:node.textContent.slice(0,90),right});
        }
      }
      return {issues,overflow_elements,overflow_text,page_width:document.documentElement.scrollWidth,viewport:innerWidth,region_width:box.width,scroll_width:el.scrollWidth,columns:headers.length,rows:t.tBodies[0].rows.length};
    },{items:data.items,mode});
    if(geometry.issues.length) report.errors.push(label+' '+width+' '+JSON.stringify(geometry));
    await tableRegion.focus();
    await expect(tableRegion).toBeFocused();
    if (geometry.scroll_width > geometry.region_width+2) {
      await page.keyboard.press('ArrowRight');
      await expect.poll(()=>tableRegion.evaluate(el=>el.scrollLeft)).toBeGreaterThan(0);
    }
    // Reach and inspect every column without changing data or triggering a save.
    const headers=table.locator('thead th');
    for(let col=0;col<geometry.columns;col++) {
      const reachable=await headers.nth(col).evaluate(th=>{
        const el=th.closest('[role="region"]');el.scrollLeft=th.offsetLeft;
        const a=el.getBoundingClientRect(),b=th.getBoundingClientRect();
        return b.right>a.left && b.left<a.right;
      });
      assert(reachable,label+' unreachable column '+col);
    }
    report.layouts.push({label,width,...geometry,literals_match:true,keyboard_scroll:true,all_columns_reachable:true});
    if([390,1440].includes(width)) for(const edge of (width===390?['left','right']:['left'])) {
      await tableRegion.evaluate((el,edge)=>{el.scrollLeft=edge==='left'?0:el.scrollWidth;},edge);
      const name=`cwb25-${label}-${width}-${edge}.png`;
      await tableRegion.screenshot({path:path.join(out,name)});
      const bytes=fs.readFileSync(path.join(out,name));report.screenshots.push({file:name,bytes:bytes.length,sha256:digest(bytes)});
    }
  }
  await tracker.drain();
  assert.deepEqual(report.requests.slice(start).filter(r=>!['GET','HEAD','OPTIONS'].includes(r.method)),[],label+' wrote during reading');
  assert.equal(downloads,downloadStart,label+' downloaded during reading');
  await page.setViewportSize({width:1440,height:1100});
  console.log('CHECKED',label,fixture.viewport_widths.join(','));
}
async function main() {
  const generated=spawnSync(python,['-B','tests/fixtures/build_attachment_cw_b6_fixtures.py',temp],{encoding:'utf8'});
  assert.equal(generated.status,0,generated.stderr);
  const log=fs.openSync(path.join(out,'cwb25-backend.log'),'w');
  server=spawn(python,['-B','-c',boot],{stdio:['ignore',log,log],env:process.env});
  for(let i=0;i<80;i++) {
    assert.equal(server.exitCode,null,'Synthetic backend exited');
    try {if((await fetch(API+'/healthz')).ok)break;}catch{}
    assert(i<79,'Synthetic backend unavailable');await new Promise(r=>setTimeout(r,200));
  }
  browser=await chromium.launch({headless:true});
  context=await browser.newContext({serviceWorkers:'block',viewport:{width:1440,height:1100}});
  tracker=await trackBrowser(context,{origins:[UI,API],errors:report.errors,external:report.external});
  page=await context.newPage();page.on('dialog',d=>d.accept());page.on('download',()=>downloads++);
  page.on('request',r=>report.requests.push({method:r.method(),path:new URL(r.url()).pathname}));
  await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill('browser-owner@example.com');
  await page.getByPlaceholder('密码',{exact:true}).fill('Synthetic-PR26-only-20260916');await button(page,'登录').click();
  await expect(button(page,'退出')).toBeVisible();token=await page.evaluate(()=>localStorage.getItem('token'));
  for(const species of ['dog','cat']) {
    const cid=(await call('POST','/api/cases',{...fixture.case,species,patient_name:'CW-B25 合成 '+species})).id;
    const attachments=`/api/cases/${cid}/attachments`, root=`/api/cases/${cid}/manual-lab`;
    const upload=await context.request.post(API+attachments+'/uploads/'+randomUUID().replaceAll('-',''),{headers:{Authorization:'Bearer '+token,'Content-Type':'application/pdf','X-Attachment-Filename':'synthetic.pdf','X-Case-Token':(await call('GET',attachments)).case_token},data:fs.readFileSync(path.join(temp,'synthetic.pdf'))});
    assert(upload.ok(),await upload.text());const source=(await upload.json()).attachment;
    const ab={request_id:randomUUID().replaceAll('-',''),attachment_id:source.id,operation:'confirm',expected_case_token:(await call('GET',attachments)).case_token,metadata:{title:'CW-B25 合成原件',kind:'lab',taken_at:'',reported_at:'',source:'',note:''},reason:''};
    const ap=await call('POST',attachments+'/preview',ab);await call('POST',attachments+'/confirm',{...ab,preview_token:ap.preview_token,reviewed:true});
    const lb={request_id:randomUUID().replaceAll('-',''),attachment_id:source.id,operation:'create',expected_case_token:(await call('GET',root)).case_token,report_id:null,expected_report_token:'',data:fixture.data,reason:''};
    const lp=await call('POST',root+'/preview',lb);const saved=(await call('POST',root+'/confirm',{...lb,preview_token:lp.preview_token,reviewed:true})).report;
    await page.goto(UI+'/cases/'+cid);await button(page,'打开检验项目').click();
    const lab=region('检验项目人工录入'), record=lab.getByRole('article',{name:'检验记录 '+saved.id,exact:true});
    await record.locator('summary').click();
    await inspect(record.getByRole('region',{name:'人工检验表，可横向滚动',exact:true}),fixture.data,'manual',species+'-saved');
    await button(record,'更正检验记录').click();
    await lab.getByLabel('项目 1 结果原文',{exact:true}).fill(fixture.correction_value);
    for(let i=0;i<fixture.data.items.length;i++) await lab.getByLabel('已核对项目 '+(i+1),{exact:true}).check();
    await lab.getByLabel('更正或撤销原因',{exact:true}).fill('CW-B25 合成版式核对');
    await button(lab,'核对整份检验记录').click();
    const changed=structuredClone(fixture.data);changed.items[0].value=fixture.correction_value;
    const review=region('整份检验核对');
    await inspect(review.getByRole('region',{name:'人工检验表，可横向滚动',exact:true}).first(),changed,'manual',species+'-review');
    await expect(button(lab,'确认保存检验记录')).toBeDisabled();
    await lab.getByLabel('已核对整份检验记录',{exact:true}).check();await button(lab,'确认保存检验记录').click();
    await expect(review).toHaveCount(0);
    const after=(await call('GET',root)).reports;
    assert.equal(after.length,2);assert.equal(after.find(r=>r.state==='confirmed').data.items[0].value,fixture.correction_value);
    const history=lab.getByRole('article',{name:'检验记录 '+saved.id,exact:true});
    if((await history.locator('details').getAttribute('open')) === null) await history.locator('summary').click();
    await inspect(history.getByRole('region',{name:'人工检验表，可横向滚动',exact:true}),fixture.data,'manual',species+'-history');
    await button(page,'打开检验结果区间核对').click();
    await inspect(region('区间核对表，可横向滚动'),changed,'range',species+'-range');
    await button(page,'收起检验项目').click();await button(page,'收起检验结果区间核对').click();
    for(const [name,template] of [['导出门诊病历草稿 DOCX','outpatient'],['导出宠主说明草稿 DOCX','owner']]) {
      await button(page,name).click();const doc=region('文书草稿内容核对');
      await button(doc,'选择已核对检验报告').click();await doc.getByLabel('纳入 '+fixture.data.report.title,{exact:true}).check();
      await button(doc,'重新读取草稿').click();
      await inspect(region('文书检验表，可横向滚动'),changed,'document',species+'-'+template);
      await expect(button(doc,'确认并下载草稿 DOCX')).toBeDisabled();await button(doc,'关闭草稿核对').click();
    }
    assert.deepEqual((await call('GET',root)).reports,after,'Reading changed saved versions');
    report.cases.push({species,case_id:cid,original_report_id:saved.id,current_report_id:after.find(r=>r.state==='confirmed').id,versions:after.length});
  }
  assert.equal(report.layouts.length,48);assert.equal(report.screenshots.length,36);
  assert.equal(downloads,0);await tracker.drain();assert.deepEqual(report.errors,[]);assert.deepEqual(report.external,[]);
  report.status='PASS';report.external_business_calls=0;
}
main().catch(async error=>{
  process.exitCode=1;report.errors.push(String(error));console.error(error);
  if(page&&!page.isClosed())await page.screenshot({path:path.join(out,'cwb25-failure.png'),fullPage:true}).catch(()=>{});
}).finally(async()=>{
  try {if(tracker)await tracker.close();if(browser)await browser.close();}catch(e){report.errors.push(String(e));process.exitCode=1;}
  if(server&&server.exitCode===null){server.kill('SIGTERM');await new Promise(resolve=>{const timer=setTimeout(()=>{server.kill('SIGKILL');resolve();},5000);server.once('exit',()=>{clearTimeout(timer);resolve();});});}
  report.lifecycle=tracker?.receipt();if(report.errors.length)report.status='FAIL';
  fs.writeFileSync(path.join(out,'cwb25-readability.json'),JSON.stringify(report,null,2));fs.rmSync(temp,{recursive:true,force:true});
});
