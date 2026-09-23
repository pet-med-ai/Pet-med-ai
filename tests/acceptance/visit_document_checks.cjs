// Real UI -> reviewed create -> reviewed correction -> readback -> DOCX.
// Only existing disposable fixture credentials and loopback services are permitted.
const {chromium,expect}=require('@playwright/test');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {execFileSync}=require('node:child_process');
const UI='http://127.0.0.1:5173', API='http://127.0.0.1:18026', out=process.env.PMAI_ACCEPTANCE_OUT;
assert(out && process.env.PMAI_SYNTHETIC_ACCEPTANCE==='PR26');
let browser,context,page,auth;const passed=[],failures=[],external=[],errors=[],downloads=[],dialogs=[],mutations=[];
const region=name=>page.getByRole('region',{name,exact:true});
const field=label=>page.locator('label').filter({has:page.getByText(label,{exact:true})}).locator('input,textarea,select');
const record=async name=>{passed.push(name);console.log('PASS:',name);await page.screenshot({path:path.join(out,'visit-'+passed.length+'.png'),fullPage:true});};
const read=async id=>{const r=await context.request.get(API+'/api/cases/'+id,{headers:auth});assert.equal(r.status(),200);return r.json();};
async function main(){
 browser=await chromium.launch({headless:true});context=await browser.newContext({acceptDownloads:true,serviceWorkers:'block',viewport:{width:1440,height:1000}});
 await context.route('**/*',route=>{const origin=new URL(route.request().url()).origin;if([UI,API].includes(origin))return route.continue();external.push(origin);return route.abort();});
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('download',d=>downloads.push(d));page.on('dialog',async d=>{dialogs.push(d.message());await d.accept();});
 page.on('request',r=>{const p=new URL(r.url()).pathname;if(['POST','PUT','PATCH','DELETE'].includes(r.method())&&p.startsWith('/api/')&&!p.startsWith('/api/clinical-docs/'))mutations.push(p);});
 await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill('browser-owner@example.com');await page.getByPlaceholder('密码',{exact:true}).fill('Synthetic-PR26-only-20260916');await page.getByRole('button',{name:'登录',exact:true}).click();await expect(page.getByRole('button',{name:'退出',exact:true})).toBeVisible();auth={Authorization:'Bearer '+await page.evaluate(()=>localStorage.getItem('token'))};
 await page.goto(UI+'/cases/new/edit');
 for(const [label,value] of [['病例名 / 宠物名（必填）','M1文书合成犬'],['主诉（必填）','M1就诊主诉'],['既往史 / 动态问诊追问记录','M1问诊病史原文🐾'],['治疗建议','M1原处理']])await field(label).fill(value);
 const create=region('手工新建病例核对');await create.getByRole('button',{name:'核对新建内容',exact:true}).click();await create.getByLabel('已核对本次新建内容',{exact:true}).check();assert.equal(mutations.length,0);await create.getByRole('button',{name:'确认并创建病例',exact:true}).click();await expect(create).toContainText('本次核对的十五项内容一致');
 const savedLink=create.getByRole('link',{name:/查看已保存病例 #/});const id=Number((await savedLink.getAttribute('href')).split('/').at(-1));assert(id>0);await savedLink.click();await page.getByRole('link',{name:'编辑',exact:true}).click();
 await field('治疗建议').fill('M1医生更正后处理🐾');const edit=region('病例修改核对');await edit.getByRole('button',{name:'核对修改内容',exact:true}).click();await edit.getByLabel('已核对本次病例修改',{exact:true}).check();await edit.getByRole('button',{name:'确认并保存修改',exact:true}).click();await expect(region('修改后服务器回读')).toBeVisible();
 const actual=await read(id);assert.equal(actual.history,'M1问诊病史原文🐾');assert.equal(actual.treatment,'M1医生更正后处理🐾');await edit.getByRole('link',{name:'查看已保存病例 #'+id,exact:true}).click();await page.reload();await expect(region('完整病史原文')).toContainText(actual.history);await record('reviewed_visit_and_correction_read_back_exactly');
 const beforeWrites=mutations.length;
 for(const [label,name] of [['导出入院/住院记录 DOCX','admission'],['导出出院小结 DOCX','discharge'],['导出门诊病历草稿 DOCX','outpatient'],['导出宠主说明草稿 DOCX','owner-summary']]){
  const downloadEvent=page.waitForEvent('download');await page.getByRole('button',{name:label,exact:true}).click();const download=await downloadEvent;assert.match(download.suggestedFilename(),new RegExp('case-'+id));const file=path.join(out,'visit-'+name+'.docx');await download.saveAs(file);
  const content=execFileSync('python',['-c','import sys,zipfile;from xml.etree import ElementTree as E;z=zipfile.ZipFile(sys.argv[1]);print("".join(E.fromstring(z.read("word/document.xml")).itertext()))',file],{encoding:'utf8'});
  for(const value of ['M1文书合成犬','M1医生更正后处理🐾'])assert(content.includes(value),value);assert(!content.includes('{{'));assert.deepEqual(await read(id),actual);
  if(['outpatient','owner-summary'].includes(name)){assert(content.includes(actual.history));assert(content.includes('未填写'));assert(content.includes('未单独记录复查安排，请医生补充确认'));assert(content.includes('待医生核对'));assert(content.includes('尚未签署'));assert(!content.includes('最终诊断'));assert(!content.includes('电子章'));await record(name+'_draft_has_saved_text_and_missing_fields');}
 }
 assert.equal(mutations.length,beforeWrites);await record('four_docx_downloads_contain_corrected_case_without_write');
 let unlockDraft;const draftGate=new Promise(r=>unlockDraft=r);const draftEndpoint='**/api/clinical-docs/render';
 let draftRequests=0;await page.route(draftEndpoint,async route=>{draftRequests++;const response=await route.fetch();assert.equal(response.status(),200);await draftGate;await route.fulfill({response});});
 const ownerBefore=downloads.length;const draftDownload=page.waitForEvent('download');await page.getByRole('button',{name:'导出宠主说明草稿 DOCX',exact:true}).click();
 await expect(page.getByRole('button',{name:'导出门诊病历草稿 DOCX',exact:true})).toBeDisabled();await expect(page.getByRole('button',{name:'导出出院小结 DOCX',exact:true})).toBeDisabled();unlockDraft();await draftDownload;assert.equal(downloads.length,ownerBefore+1);assert.equal(draftRequests,1);await page.unroute(draftEndpoint);await record('draft_export_excludes_concurrent_template_download');
 let release,delivered=false;const hold=new Promise(r=>release=r);const endpoint='**/api/clinical-docs/render';
 await page.route(endpoint,async route=>{const response=await route.fetch();assert.equal(response.status(),200);await hold;await route.fulfill({response});delivered=true;});
 const beforeDownloads=downloads.length;await page.getByRole('button',{name:'导出出院小结 DOCX',exact:true}).click();await expect(page.getByRole('button',{name:'生成中…',exact:true})).toBeDisabled();await page.getByRole('link',{name:'返回首页',exact:true}).click();release();await expect.poll(()=>delivered).toBe(true);await page.evaluate(()=>new Promise(r=>setTimeout(r,100)));assert.equal(downloads.length,beforeDownloads);await page.unroute(endpoint);await record('leaving_detail_discards_late_download');
 await page.goto(UI+'/cases/'+id);await expect(region('完整病史原文')).toBeVisible();const del=await context.request.delete(API+'/api/cases/'+id,{headers:auth});assert.equal(del.status(),204);
 const responseEvent=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/clinical-docs/render');await page.getByRole('button',{name:'导出出院小结 DOCX',exact:true}).click();assert.equal((await responseEvent).status(),404);await expect(page.getByRole('status')).toContainText('导出失败');assert(dialogs.some(d=>d.includes('Case not found')));assert.equal(downloads.length,beforeDownloads);await expect(page.getByRole('button',{name:'导出出院小结 DOCX',exact:true})).toBeEnabled();await record('deleted_case_refused_with_readable_export_error');
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
}
main().catch(async e=>{process.exitCode=1;failures.push(String(e));console.error(e);if(page){await page.screenshot({path:path.join(out,'visit-failure.png'),fullPage:true}).catch(()=>{});fs.writeFileSync(path.join(out,'visit-failure-dom.txt'),await page.locator('body').innerText().catch(()=>''));}}).finally(async()=>{fs.writeFileSync(path.join(out,'visit-document-checks.json'),JSON.stringify({passed,failures,errors,external},null,2));if(browser)await browser.close();});
