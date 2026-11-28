// Real frontend + v2 API + fresh PostgreSQL. Linux Chromium is not native Safari.
import assert from 'node:assert/strict';
import { randomBytes } from 'node:crypto';
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
const require = createRequire(import.meta.url);
const { chromium, expect } = require(process.env.PMAI_PLAYWRIGHT_MODULE || '@playwright/test');
const state = process.env.PMAI_ACCEPTANCE_STATE;
assert(state, 'PMAI_ACCEPTANCE_STATE is required');
const receipt = JSON.parse(fs.readFileSync(path.join(state, 'receipt.json')));
const fixture = JSON.parse(fs.readFileSync(path.join(state, 'accounts.json')));
const control = action => execFileSync(process.env.PMAI_ACCEPTANCE_PYTHON || 'python', ['scripts/treatment_acceptance.py', '--state', state, 'control', action], { stdio: 'pipe' });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
const errors = [], checks = [], caseWritePaths = [];
page.on('pageerror', e => errors.push(String(e)));
page.on('request', request => {
  const pathname = new URL(request.url()).pathname;
  if (['POST', 'PATCH', 'PUT', 'DELETE'].includes(request.method()) && pathname.startsWith('/api/v2/organizations/')) {
    caseWritePaths.push(pathname);
  }
});
const text = '合成验收 café 🐾\n原文 {{literal}}; literal \\n remains';
const result = { candidate: receipt.candidate, browser: 'Linux Chromium', manual_safari_result: 'PENDING', acceptance: 'NOT_CLOSED', checks };

async function login(name='doctor-a', tab=page) {
  await tab.getByLabel('邮箱', { exact: true }).fill(name + '@example.invalid');
  await tab.getByLabel('密码', { exact: true }).fill(fixture.password);
  await tab.getByRole('button', { name: '登录', exact: true }).click();
  await expect(tab.getByRole('button', { name: '退出登录', exact: true })).toBeVisible();
}
async function openCase(id, tab=page) {
  await tab.getByLabel('机构／院区', { exact: true }).selectOption(fixture.org + '/' + fixture.clinic);
  await tab.getByRole('row').filter({ has: tab.getByRole('cell', { name: '#' + id, exact: true }) }).getByRole('button', { name: '查看', exact: true }).click();
  await expect(tab.locator('[aria-label="病例详情"] h2').first()).toContainText('#' + id);
  if (await tab.locator('[aria-label="治疗签署"]').count()) await expect(tab.getByRole('button', { name: '重新读取治疗记录', exact: true })).toBeEnabled();
}
async function logout() { await page.getByRole('button', { name: '退出登录', exact: true }).click(); await expect(page.getByRole('button', { name: '登录', exact: true })).toBeEnabled(); }
const saveDraft = () => page.getByRole('button', { name: '保存治疗草稿', exact: true }).click();
async function freeze(content=text, save=saveDraft) {
  await page.getByLabel('治疗诊断', { exact: true }).fill('合成诊断，仅软件验收');
  await page.getByLabel('治疗评估', { exact: true }).fill(content);
  await page.getByLabel('治疗措施', { exact: true }).fill(content);
  await save();
  await page.getByRole('button', { name: '冻结版本供核对', exact: true }).click();
  await expect(page.getByLabel('已核对冻结版本', { exact: true })).toBeEnabled();
}
async function saveWithForeignReceipt() {
  const casePath = `/api/v2/organizations/${fixture.org}/clinics/${fixture.clinic}/cases/101`;
  const draftPath = casePath + '/treatment/draft';
  const draftURL = new URL(draftPath, receipt.url).href;
  const writesBefore = caseWritePaths.length;
  const lookups = [];
  function observeLookup(request) {
    const url = new URL(request.url());
    if (request.method() === 'GET' && url.pathname.startsWith(casePath + '/commands/')) lookups.push(url.href);
  }
  page.on('request', observeLookup);
  let committed;
  // Forward the existing first save once. Change only the committed response delivered to the page.
  await page.route(draftURL, async route => {
    const original = await route.fetch({ maxRedirects: 0, maxRetries: 0 });
    committed = await original.json();
    const foreignKey = committed.idempotency_key === '0'.repeat(64) ? '1'.repeat(64) : '0'.repeat(64);
    await route.fulfill({ response: original, json: { ...committed, idempotency_key: foreignKey } });
  }, { times: 1 });
  const [delivered] = await Promise.all([
    page.waitForResponse(response => response.url() === draftURL && response.request().method() === 'PATCH'),
    saveDraft(),
  ]);
  const key = delivered.request().headers()['idempotency-key'];
  const submitted = delivered.request().postDataJSON().content;
  assert.match(key, /^[0-9a-f]{64}$/);
  assert.equal(delivered.status(), 201);
  assert.equal(committed.state, 'committed');
  assert.equal(committed.operation, 'draft.save');
  assert.equal(committed.idempotency_key, key);
  const altered = await delivered.json();
  assert.notEqual(altered.idempotency_key, key);
  assert.deepEqual({ ...altered, idempotency_key: key }, committed);

  const lookup = page.getByRole('button', { name: '查询原请求', exact: true });
  const freezeButton = page.getByRole('button', { name: '冻结版本供核对', exact: true });
  await expect(lookup).toBeEnabled();
  await expect(page.getByText('待核对请求：' + key, { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: '保存治疗草稿', exact: true })).toBeDisabled();
  await expect(freezeButton).toBeDisabled();
  assert.deepEqual(lookups, []);
  const lookupURL = new URL(casePath + '/commands/' + key + '?operation=draft.save', receipt.url).href;
  const aggregateURL = new URL(casePath + '/treatment', receipt.url).href;
  const [original, aggregate] = await Promise.all([
    page.waitForResponse(response => response.url() === lookupURL && response.request().method() === 'GET'),
    page.waitForResponse(response => response.url() === aggregateURL && response.request().method() === 'GET'),
    lookup.click(),
  ]);
  assert.equal(original.status(), 201);
  assert.deepEqual(await original.json(), committed);
  assert.equal(aggregate.status(), 200);
  const recovered = await aggregate.json();
  assert.equal(recovered.draft_etag, committed.draft_etag);
  assert.equal(recovered.draft.draft_version, committed.draft_version);
  assert.deepEqual(recovered.draft.content, submitted);
  await expect(lookup).toHaveCount(0);
  await expect(page.getByLabel('治疗评估', { exact: true })).toHaveValue(submitted.assessment);
  await expect(freezeButton).toBeEnabled();
  assert.deepEqual(lookups, [lookupURL]);
  assert.deepEqual(caseWritePaths.slice(writesBefore), [draftPath]);
  page.off('request', observeLookup);
  checks.push('foreign-draft-receipt-original-key-recovery-no-repeat-write');
}
async function review() {
  await page.getByLabel('已核对冻结版本', { exact: true }).check();
  await page.getByLabel('操作原因', { exact: true }).fill('核对合成原文');
  await page.getByRole('button', { name: '审核通过', exact: true }).click();
  // The action button itself also says 审核通过. Wait for the persisted review,
  // after reload has reset the previous acknowledgement, before checking again.
  await expect(page.getByRole('button', { name: '审核通过', exact: true })).toHaveCount(0);
  await expect(page.locator('[aria-label="冻结版本"]')).toContainText('审核：');
  await expect(page.getByLabel('已核对冻结版本', { exact: true })).toBeEnabled();
}
async function sign() {
  await page.getByLabel('已核对冻结版本', { exact: true }).check();
  await page.getByLabel('签署认证密码', { exact: true }).fill(fixture.password);
  await page.getByRole('button', { name: '再次认证并确认签署', exact: true }).click();
}
async function readback() {
  await expect(page.locator('[aria-label="独立回读签署"]')).toBeVisible();
}
async function checkUnchangedApprovedDraft() {
  const path = `/api/v2/organizations/${fixture.org}/clinics/${fixture.clinic}/cases/101/treatment`;
  const treatmentRead = response => response.request().method() === 'GET' && new URL(response.url()).pathname === path;
  const [reviewed] = await Promise.all([page.waitForResponse(treatmentRead), review()]);
  assert.equal(reviewed.status(), 200);
  const before = await reviewed.json();
  const revision = before.revisions.find(r => r.id === before.plan.head_revision_id);
  const approval = before.reviews.find(r => r.revision_id === revision.id);
  assert.equal(approval.decision, 'approve');
  assert.equal(revision.draft_version, before.draft.draft_version);

  const save = page.getByRole('button', { name: '保存治疗草稿', exact: true });
  const assessment = page.getByLabel('治疗评估', { exact: true });
  const acknowledgement = page.getByLabel('已核对冻结版本', { exact: true });
  const password = page.getByLabel('签署认证密码', { exact: true });
  const signButton = page.getByRole('button', { name: '再次认证并确认签署', exact: true });
  const writesBefore = caseWritePaths.length;
  let additionalRequests = 0;
  const countRequest = () => { additionalRequests++; };
  page.on('request', countRequest);
  try {
    await expect(save).toBeDisabled();
    await acknowledgement.check();
    await password.fill('synthetic-confirmation-only');
    await expect(signButton).toBeEnabled();
    const original = before.draft.content.assessment;
    await expect(assessment).toHaveValue(original);
    await assessment.fill(original + '\n临时编辑');
    await assessment.fill(original);
    await save.click();
    await expect(page.getByText('草稿内容与已读取的版本一致，无需重复保存。', { exact: true })).toBeVisible();
    await expect(save).toBeDisabled();
    await expect(acknowledgement).toBeEnabled();
    await expect(acknowledgement).not.toBeChecked();
    await expect(password).toHaveValue('');
    await expect(signButton).toBeDisabled();
    assert.equal(additionalRequests, 0);
    assert.equal(caseWritePaths.length, writesBefore);
  } finally {
    page.off('request', countRequest);
  }

  // Reread separately to verify the persisted draft and approval after the request-free save.
  const [reread] = await Promise.all([page.waitForResponse(treatmentRead),
    page.getByRole('button', { name: '重新读取治疗记录', exact: true }).click()]);
  assert.equal(reread.status(), 200);
  const after = await reread.json();
  assert.equal(after.draft.draft_version, before.draft.draft_version);
  assert.equal(after.draft_etag, before.draft_etag);
  assert.equal(after.plan.head_revision_id, revision.id);
  assert.deepEqual(after.reviews.find(r => r.revision_id === revision.id), approval);
  await expect(acknowledgement).toBeEnabled();
  result.unchanged_approved_draft = { case_id: 101, draft_version: after.draft.draft_version,
    draft_etag: after.draft_etag, revision_id: revision.id, review_id: approval.id,
    additional_requests: additionalRequests, case_writes: caseWritePaths.length - writesBefore };
  checks.push('reverted-draft-preserves-approval-without-repeat-save');
}
async function checkConfirmationSwitch() {
  const frozen = page.getByLabel('已核对冻结版本', { exact: true });
  const revoke = page.getByLabel('已核对待作废签署', { exact: true });
  const password = page.getByLabel('签署认证密码', { exact: true });
  const signButton = page.getByRole('button', { name: '再次认证并确认签署', exact: true });
  const revokeButton = page.getByRole('button', { name: '再次认证并作废签署', exact: true });
  const writesBefore = caseWritePaths.length;
  let reauthRequests = 0;
  const observe = request => {
    if (new URL(request.url()).pathname === '/api/v2/auth/reauthenticate') reauthRequests++;
  };
  page.on('request', observe);
  try {
    await page.getByLabel('操作原因', { exact: true }).fill('合成操作切换核对');
    await expect(password).toBeDisabled();
    for (const [selected, other, submit, otherSubmit] of [
      [frozen, revoke, signButton, revokeButton],
      [revoke, frozen, revokeButton, signButton],
      [frozen, revoke, signButton, revokeButton],
    ]) {
      await selected.check();
      await expect(other).not.toBeChecked();
      await expect(password).toHaveValue('');
      await expect(submit).toBeDisabled();
      await expect(otherSubmit).toBeDisabled();
      await password.fill('synthetic-confirmation-only');
      await expect(submit).toBeEnabled();
      await expect(otherSubmit).toBeDisabled();
    }
    await frozen.uncheck();
    await expect(password).toHaveValue('');
    await expect(password).toBeDisabled();
    assert.equal(reauthRequests, 0);
    assert.equal(caseWritePaths.length, writesBefore);
    result.confirmation_switch = { case_id: 101, actions: ['sign', 'revoke', 'sign'],
      reauthentication_requests: reauthRequests, case_writes: caseWritePaths.length - writesBefore };
  } finally {
    page.off('request', observe);
  }
}
async function rejectWrongPassword(action) {
  const frozen = page.getByLabel('已核对冻结版本', { exact: true });
  const revoke = page.getByLabel('已核对待作废签署', { exact: true });
  const password = page.getByLabel('签署认证密码', { exact: true });
  const button = page.getByRole('button', { name: action === 'sign' ? '再次认证并确认签署' : '再次认证并作废签署', exact: true });
  await (action === 'revoke' ? revoke : frozen).check();
  await password.fill('deliberately-invalid-synthetic-password');
  const writesBefore = caseWritePaths.length;
  const [proof] = await Promise.all([
    page.waitForResponse(response => response.request().method() === 'POST' &&
      new URL(response.url()).pathname === '/api/v2/auth/reauthenticate'),
    button.click(),
  ]);
  assert.equal(proof.status(), 401);
  assert.equal((await proof.json()).code, 'REAUTHENTICATION_FAILED');
  await expect(page.getByText('再次认证未通过，本次操作尚未提交。请重新核对并输入当前账号密码。', { exact: true })).toBeVisible();
  await expect(page.locator('[aria-label="病例详情"] h2').first()).toContainText('#101');
  await expect(page.locator('[aria-label="冻结版本"]')).toContainText('审核通过');
  await expect(frozen).not.toBeChecked();
  if (action === 'revoke') {
    await expect(revoke).not.toBeChecked();
    await expect(page.locator('[aria-label="当前有效签署"]')).toBeVisible();
  }
  await expect(password).toHaveValue('');
  await expect(button).toBeDisabled();
  await expect(page.getByRole('button', { name: '查询原请求', exact: true })).toHaveCount(0);
  assert.equal(caseWritePaths.length, writesBefore, 'Rejected proof must not send a case mutation');
  return writesBefore;
}
async function checkDiscardOnCaseSwitch() {
  const heading = page.locator('[aria-label="病例详情"] h2').first();
  const assessment = page.getByLabel('治疗评估', { exact: true });
  const rowButton = id => page.getByRole('row')
    .filter({ has: page.getByRole('cell', { name: '#' + id, exact: true }) })
    .getByRole('button', { name: '查看', exact: true });
  const writesBefore = caseWritePaths.length;
  await openCase(110);
  // Only #104 has an imported treatment draft. #110 starts with an empty assessment.
  await expect(assessment).toHaveValue('');
  const localText = '仅在本页的合成评估 🐾\n未保存 {{navigation}}';
  await assessment.fill(localText);

  async function selectImportedCase(discard) {
    const targetPath = `/api/v2/organizations/${fixture.org}/clinics/${fixture.clinic}/cases/104`;
    const [prompt, detail] = await Promise.all([
      page.waitForEvent('dialog', { timeout: 10000 }).then(async dialog => {
        const observed = { type: dialog.type(), message: dialog.message() };
        if (discard) await dialog.accept();
        else await dialog.dismiss();
        return observed;
      }),
      page.waitForResponse(response => response.request().method() === 'GET' && new URL(response.url()).pathname === targetPath),
      rowButton(104).click(),
    ]);
    assert.equal(detail.status(), 200);
    assert.equal(prompt.type, 'confirm');
    assert.match(prompt.message, /未保存.*草稿/);
  }

  await selectImportedCase(false);
  await expect(heading).toContainText('#110');
  await expect(assessment).toHaveValue(localText);
  await expect(page.getByText('有尚未保存的修改。保存后才能冻结和签署。', { exact: true })).toBeVisible();

  await selectImportedCase(true);
  await expect(heading).toContainText('#104');
  await expect(assessment).toHaveValue(text);
  await expect(page.getByLabel('治疗措施', { exact: true })).toHaveValue(text);

  await rowButton(110).click();
  await expect(heading).toContainText('#110');
  await expect(assessment).toHaveValue('');
  assert.equal(caseWritePaths.length, writesBefore, 'Navigating and discarding must send no case mutation');
  checks.push('dirty-case-switch-cancel-preserves-confirm-discards-without-write');
}
async function prepared(kind, caseId) {
  await expect.poll(() => {
    const events = JSON.parse(fs.readFileSync(path.join(state, 'events.json')));
    return events.some(e => e.event === 'response_prepared' && e.kind === kind
      && (caseId == null || e.path.includes('/cases/' + caseId + '/')));
  }).toBe(true);
}

async function checkExpiredClipboard(values) {
  const heading = page.getByRole('heading', { name: '未保存原文 · 只读保留', exact: true });
  const expired = page.locator('[aria-label="治疗签署"] > section').filter({ has: heading });
  await expect(expired).toBeVisible();
  const origin = new URL(receipt.url);
  assert.equal(origin.hostname, '127.0.0.1');
  const context = page.context();
  await context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: origin.origin });
  try {
    for (const [term, expected] of Object.entries(values)) {
      const field = expired.getByText(term, { exact: true }).locator('xpath=following-sibling::*[1][self::dd]');
      assert.equal(await field.textContent(), expected, term + ' original');
      await page.evaluate(() => navigator.clipboard.writeText('等待本次原生复制'));
      const selected = await field.evaluate(element => {
        const range = document.createRange();
        range.selectNodeContents(element);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        return selection.toString();
      });
      await page.keyboard.press('Control+c');
      assert.equal(selected, expected, term + ' native selection');
      await expect.poll(() => page.evaluate(() => navigator.clipboard.readText()), { message: term + ' native copy' }).toBe(expected);
    }
  } finally {
    await context.clearPermissions();
  }
}

async function checkSignedListItems() {
  const label = '合成同名诊断\r\n 第二行 🐾 ';
  const diagnoses = [
    { label, code_system: '合成体系 A', code: ' A / 01 ' },
    { label, code_system: null, code: '独立编码 B' },
    { label: '只有体系', code_system: '合成体系 C', code: null },
    { label: '无编码', code_system: null, code: null },
    { label: '明确保存的空值', code_system: '', code: '' },
  ];
  const goals = ['目标甲\r\n目标乙', '目标甲', '目标乙', '', ' \u3000\t', ' {{保留}} 🐾 '];
  const content = { schema: 'treatment-content-v1', diagnoses, assessment: text,
    treatment: { goals, management_text: text, monitoring_text: '', followup_text: '' },
    linked_orders: [], provenance: { ai_generation_ids: [], voice_transcript_revision_ids: [] } };

  async function checkSection(name) {
    const section = page.locator(`[aria-label="${name}"]`);
    const diagnosisRows = section.getByRole('list', { name: '诊断条目', exact: true }).locator(':scope > li');
    const goalRows = section.getByRole('list', { name: '治疗目标条目', exact: true }).locator(':scope > li');
    await expect(diagnosisRows).toHaveCount(diagnoses.length);
    await expect(goalRows).toHaveCount(goals.length);
    await expect(diagnosisRows.first().locator(':scope > span').first()).toHaveCSS('white-space', /^(pre|pre-wrap|break-spaces)$/);
    await expect(goalRows.first()).toHaveCSS('white-space', /^(pre|pre-wrap|break-spaces)$/);
    const displayed = await diagnosisRows.evaluateAll(rows => rows.map(row => ({
      label: row.querySelector(':scope > span').textContent,
      coding: [...row.querySelectorAll('dt')].map(term => [term.textContent, term.nextElementSibling.textContent]),
    })));
    assert.deepEqual(displayed, diagnoses.map(item => ({
      label: item.label,
      coding: [['编码体系', item.code_system], ['编码', item.code]].filter(([, value]) => value !== null),
    })), name);
    assert.deepEqual(await goalRows.allTextContents(), goals, name);
  }

  // #110 was only visited for the discard check. Seed pre-existing structured data via the synthetic doctor's API.
  const treatmentURL = new URL(`/api/v2/organizations/${fixture.org}/clinics/${fixture.clinic}/cases/110/treatment`, receipt.url);
  assert.equal(treatmentURL.hostname, '127.0.0.1');
  const [initial] = await Promise.all([
    page.waitForResponse(r => r.url() === treatmentURL.href && r.request().method() === 'GET'),
    openCase(110),
  ]);
  assert.equal(initial.status(), 200);
  assert.equal((await initial.json()).draft, null);
  const authorization = await initial.request().headerValue('authorization');
  assert.ok(authorization?.startsWith('Bearer '), 'Synthetic doctor session required');
  const saved = await page.request.patch(treatmentURL.href + '/draft', {
    headers: { Authorization: authorization, 'If-None-Match': '*', 'Idempotency-Key': randomBytes(32).toString('hex') },
    data: { content }, maxRedirects: 0, maxRetries: 0,
  });
  assert.equal(saved.status(), 201);
  assert.equal((await saved.json()).state, 'committed');
  const writesBefore = caseWritePaths.length;
  await page.getByRole('button', { name: '重新读取治疗记录', exact: true }).click();
  await page.getByRole('button', { name: '冻结版本供核对', exact: true }).click();
  await checkSection('冻结版本');
  await review();
  const [signed] = await Promise.all([
    page.waitForResponse(r => r.url().startsWith(treatmentURL.href + '/signatures/') && r.request().method() === 'GET'),
    sign(),
  ]);
  assert.equal(signed.status(), 200);
  const record = await signed.json();
  assert.equal(record.state, 'effective');
  assert.deepEqual(record.revision.content, content);
  assert.deepEqual(JSON.parse(record.revision.canonical_utf8).content, content);
  await checkSection('当前有效签署');
  await checkSection('独立回读签署');
  const revisionsPath = treatmentURL.pathname + '/revisions';
  assert.deepEqual(caseWritePaths.slice(writesBefore),
    [revisionsPath, revisionsPath + '/' + record.revision.id + '/reviews', revisionsPath + '/' + record.revision.id + '/signatures']);
  checks.push('frozen-signed-readback-preserve-list-items-and-diagnosis-coding');
  return record.signature.id;
}

async function revokeAfterReasonEdit(tab, signatureId, reason) {
  const input = tab.getByLabel('操作原因', { exact: true });
  const confirm = tab.getByLabel('已核对待作废签署', { exact: true });
  const password = tab.getByLabel('签署认证密码', { exact: true });
  const submit = tab.getByRole('button', { name: '再次认证并作废签署', exact: true });
  const signaturePath = `/api/v2/organizations/${fixture.org}/clinics/${fixture.clinic}/cases/110/treatment/signatures/${signatureId}`;
  const mutations = [];
  const observe = req => {
    if (['POST', 'PATCH', 'PUT', 'DELETE'].includes(req.method())) mutations.push([req.method(), new URL(req.url()).pathname]);
  };
  tab.on('request', observe);
  try {
    await expect(confirm).toBeDisabled();
    await input.fill('合成病例：尚待更正的原因');
    await confirm.check();
    await password.fill(fixture.password);
    await expect(submit).toBeEnabled();
    await input.fill(reason);
    await expect(confirm).not.toBeChecked();
    await expect(password).toHaveValue('');
    await expect(submit).toBeDisabled();
    await confirm.check();
    await expect(submit).toBeDisabled();
    await password.fill(fixture.password);
    const writesBeforeSubmit = mutations.length;
    assert.equal(writesBeforeSubmit, 0);

    const [readback] = await Promise.all([
      tab.waitForResponse(r => new URL(r.url()).pathname === signaturePath && r.request().method() === 'GET'),
      submit.click(),
    ]);
    assert.equal(readback.status(), 200);
    const { state, terminal_event: event } = await readback.json();
    assert.equal(state, 'revoked');
    assert.equal(event.signature_id, signatureId);
    assert.equal(event.reason, reason);
    await expect(tab.locator('[aria-label="独立回读签署"]')).toContainText(signatureId + ' · revoked');
    assert.deepEqual(mutations, [['POST', '/api/v2/auth/reauthenticate'], ['POST', signaturePath + '/revocations']]);
    result.revocation_reason_edit = { case_id: 110, signature_id: signatureId, readback_reason: event.reason,
      mutations_before_submit: writesBeforeSubmit, mutations };
    checks.push('edited-revocation-reason-requires-new-acknowledgement-and-password');
  } finally {
    tab.off('request', observe);
  }
}

async function checkReadbackAfterExternalRevocation(signatureId) {
  // The original doctor's page stays open with its confirmed effective readback.
  const oldPanel = page.locator('[aria-label="独立回读签署"]');
  await expect(oldPanel).toContainText(signatureId + ' · effective');
  const reason = '合成病例：独立会话作废复核';
  const other = await browser.newPage();
  other.on('pageerror', error => errors.push(String(error)));
  try {
    await other.goto(receipt.url);
    await login('doctor-b', other);
    await openCase(110, other);
    await revokeAfterReasonEdit(other, signatureId, reason);
  } finally {
    await other.close();
  }

  const writesBefore = caseWritePaths.length;
  const path = `/api/v2/organizations/${fixture.org}/clinics/${fixture.clinic}/cases/110/treatment`;
  const url = new URL(path, receipt.url).href;
  const refresh = page.getByRole('button', { name: '重新读取治疗记录', exact: true });
  const currentPanel = page.locator('[aria-label="当前有效签署"]');
  const warning = page.getByText('签署状态待核对，请重新读取治疗记录。', { exact: true });
  const requests = [];
  let allRequestCount = 0;
  const observe = req => {
    allRequestCount++;
    const pathname = new URL(req.url()).pathname;
    if (pathname.startsWith('/api/v2/')) requests.push({ method: req.method(), path: pathname });
  };
  async function reread() {
    const [response] = await Promise.all([
      page.waitForResponse(r => r.url() === url && r.request().method() === 'GET'),
      refresh.click(),
    ]);
    return response;
  }
  // Doctor B has already revoked on the real API. Inject one unavailable GET on doctor A's page only.
  const injected = { detail: '合成验收：本次读取暂不可用' };
  await page.route(url, route => route.request().method() === 'GET'
    ? route.fulfill({ status: 503, json: injected }) : route.fallback(), { times: 1 });
  page.on('request', observe);
  try {
    const unavailable = await reread();
    assert.equal(unavailable.status(), 503);
    assert.deepEqual(await unavailable.json(), injected);
    await expect(warning).toBeVisible();
    await expect(currentPanel).toHaveCount(0);
    await expect(oldPanel).toHaveCount(0);
    await expect(page.getByText(/ · 有效 · /)).toHaveCount(0);
    await expect(page.getByText(/ · 状态待核对 · /)).toBeVisible();
    await expect(page.getByRole('button', { name: /^(创建修订草稿|再次认证并作废签署)$/, disabled: false })).toHaveCount(0);
    await expect(page.getByRole('button', { name: '保存治疗草稿', exact: true })).toBeDisabled();
    await expect(refresh).toBeEnabled();

    const response = await reread();
    assert.equal(response.status(), 200);
    const record = await response.json();
    assert.equal(record.plan.active_signature_id, null);
    const event = record.events.find(event => event.signature_id === signatureId && event.event === 'revoked');
    assert.ok(event);
    await expect(page.getByText(/ · 已作废 · /)).toBeVisible();
    await expect(warning).toHaveCount(0);
    await expect(currentPanel).toHaveCount(0);
    await expect(oldPanel).toHaveCount(0);
    const signature = record.signatures.find(s => s.id === signatureId);
    assert.equal(signature.signer_id, 1);
    assert.equal(record.actor_id, 1);
    assert.equal(event.actor_id, 2);
    assert.equal(event.reason, reason);
    assert.ok(Number.isFinite(Date.parse(event.created_at)));
    const revision = record.revisions.find(r => r.id === signature.revision_id);
    const summary = page.getByText(`查看版本 ${revision.revision_no} 的作废记录`, { exact: true });
    const details = page.locator('details').filter({ has: summary });
    const beforeDetails = allRequestCount;
    await expect(details).toHaveJSProperty('open', false);
    await summary.click();
    await expect(details.locator('dl')).toBeVisible();
    const displayed = await details.locator('dt').evaluateAll(terms =>
      Object.fromEntries(terms.map(term => [term.textContent, term.nextElementSibling.textContent])));
    assert.deepEqual(displayed, {
      '作废账号 ID': String(event.actor_id), '作废时间': event.created_at, '作废原因': event.reason,
    });
    await summary.click();
    await expect(details).toHaveJSProperty('open', false);
    assert.equal(allRequestCount, beforeDetails);
    assert.deepEqual(requests, [{ method: 'GET', path }, { method: 'GET', path }]);
    assert.equal(caseWritePaths.length, writesBefore);
    result.refresh_after_injected_503 = {
      case_id: 110, account: 'doctor-a', requests,
      response_statuses: [unavailable.status(), response.status()], case_writes: caseWritePaths.length - writesBefore,
    };
    result.revocation_history_details = {
      case_id: 110, signature_id: signatureId, revision_no: revision.revision_no,
      signer_id: signature.signer_id, revocation_actor_id: event.actor_id, created_at: event.created_at,
      reason: event.reason, additional_requests: allRequestCount - beforeDetails,
    };
    checks.push('manual-refresh-clears-readback-after-another-clinician-revokes',
      'failed-aggregate-refresh-withholds-effective-status-until-retry',
      'revocation-history-discloses-actor-time-and-reason-without-requests');
  } finally {
    page.off('request', observe);
  }
}

async function checkSupersessionHistory(record) {
  assert.equal(record.scope.case_id, 101);
  const replacement = record.events.find(event => event.event === 'superseded');
  assert.ok(replacement, 'The first signature must have a recorded successor');
  const revocation = record.events.find(event => event.event === 'revoked' && event.signature_id === replacement.successor_signature_id);
  assert.ok(revocation, 'The direct successor must already be revoked');
  function signedVersion(id, state) {
    const signature = record.signatures.find(s => s.id === id);
    assert.ok(signature);
    const revision = record.revisions.find(r => r.id === signature.revision_id);
    assert.ok(revision);
    return { signature_id: id, revision_no: revision.revision_no, state };
  }
  const predecessor = signedVersion(replacement.signature_id, replacement.event);
  const successor = signedVersion(revocation.signature_id, revocation.event);
  const current = signedVersion(record.plan.active_signature_id, 'effective');
  assert.equal(record.events.some(event => event.signature_id === current.signature_id), false);
  assert.ok(predecessor.revision_no < successor.revision_no && successor.revision_no < current.revision_no);

  const summary = page.getByText(`查看版本 ${predecessor.revision_no} 的替代记录`, { exact: true });
  const details = page.locator('details').filter({ has: summary });
  await expect(details).toHaveJSProperty('open', false);
  let additionalRequests = 0;
  const countRequest = () => { additionalRequests++; };
  page.on('request', countRequest);
  try {
    await summary.click();
    await expect(details.locator('dl')).toBeVisible();
    const term = details.locator('dt').filter({ hasText: /^接替版本$/ });
    await expect(term.locator('xpath=following-sibling::*[1][self::dd]')).toHaveText(`版本 ${successor.revision_no}`);
    await summary.click();
    await expect(details).toHaveJSProperty('open', false);
    const revoke = page.getByLabel('已核对待作废签署', { exact: true });
    const password = page.getByLabel('签署认证密码', { exact: true });
    await page.getByLabel('操作原因', { exact: true }).fill('合成历史原文查阅');
    await revoke.check();
    await password.fill('synthetic-history-only');
    for (const [version, expectedText] of [[predecessor, text], [successor, text + '\n修订']]) {
      const original = page.getByText(`查看版本 ${version.revision_no} 的签署原文`, { exact: true });
      const disclosure = page.locator('details').filter({ has: original });
      await expect(disclosure).toHaveJSProperty('open', false);
      await original.click();
      for (const field of ['评估', '治疗措施']) {
        const label = disclosure.getByText(field, { exact: true });
        const displayed = label.locator('xpath=following-sibling::*[1][self::dd]');
        await expect(displayed).toBeVisible();
        assert.equal(await displayed.textContent(), expectedText);
      }
      await original.click();
      await expect(disclosure).toHaveJSProperty('open', false);
      await expect(revoke).toBeChecked();
      await expect(page.getByLabel('已核对冻结版本', { exact: true })).not.toBeChecked();
      await expect(password).toHaveValue('synthetic-history-only');
    }
    await revoke.uncheck();
    await expect(password).toHaveValue('');
    await expect(page.getByText(`查看版本 ${current.revision_no} 的签署原文`, { exact: true })).toHaveCount(0);
    assert.equal(additionalRequests, 0);
  } finally {
    page.off('request', countRequest);
  }
  result.supersession_history_details = { case_id: record.scope.case_id, predecessor, successor, current,
    archived_original_versions: [predecessor.revision_no, successor.revision_no], retained_revocation_confirmation: true,
    additional_requests: additionalRequests };
  checks.push('superseded-history-shows-direct-successor-after-revocation-and-resigning');
  checks.push('archived-signed-text-after-reopening-preserves-revocation-confirmation');
}

async function checkRefreezeAfterSourceChange() {
  const path = `/api/v2/organizations/${fixture.org}/clinics/${fixture.clinic}/cases/108/treatment`;
  const aggregateResponse = r => new URL(r.url()).pathname === path && r.request().method() === 'GET';
  const approval = page.getByRole('button', { name: '审核通过', exact: true });
  const acknowledgement = page.getByLabel('已核对冻结版本', { exact: true });
  const freezeButton = page.getByRole('button', { name: '冻结版本供核对', exact: true });
  const warning = page.getByText('冻结后病例资料或签署规则已变化，请重新冻结版本后再审核或签署。', { exact: true });
  const writesBefore = caseWritePaths.length;

  control('source-change');
  // The clinician has not refreshed yet. The server still fences the first stale review.
  await acknowledgement.check();
  await page.getByLabel('操作原因', { exact: true }).fill('旧来源失效');
  const [rejection, reread] = await Promise.all([
    page.waitForResponse(r => r.url().endsWith('/reviews') && r.request().method() === 'POST'),
    page.waitForResponse(aggregateResponse),
    approval.click(),
  ]);
  assert.equal(rejection.status(), 409);
  assert.equal((await rejection.json()).code, 'SOURCE_CHANGED');
  await expect(page.getByText('病例、诊断资料或签署规则已变化。请重新读取并冻结新版本。', { exact: true })).toBeVisible();
  assert.equal(reread.status(), 200);
  const stale = await reread.json();
  const old = stale.revisions.find(r => r.id === stale.plan.head_revision_id);
  assert.ok(stale.source_epoch > old.source_manifest.case.clinical_epoch);
  await expect(warning).toBeVisible();
  await expect(acknowledgement).not.toBeChecked();
  await expect(acknowledgement).toBeDisabled();
  for (const name of ['审核通过', '要求修订', '审核拒绝']) {
    await expect(page.getByRole('button', { name, exact: true })).toBeDisabled();
  }
  await expect(freezeButton).toBeEnabled();

  const [frozen, updated] = await Promise.all([
    page.waitForResponse(r => new URL(r.url()).pathname === path + '/revisions' && r.request().method() === 'POST'),
    page.waitForResponse(aggregateResponse),
    freezeButton.click(),
  ]);
  assert.equal(frozen.status(), 201);
  assert.equal(frozen.request().postDataJSON().expected_source_epoch, stale.source_epoch);
  assert.equal(updated.status(), 200);
  const latest = await updated.json();
  const current = latest.revisions.find(r => r.id === latest.plan.head_revision_id);
  assert.equal(current.id, (await frozen.json()).revision_id);
  assert.notEqual(current.id, old.id);
  assert.equal(current.source_manifest.case.clinical_epoch, stale.source_epoch);
  assert.deepEqual(current.content, old.content);
  await expect(warning).toHaveCount(0);
  await expect(acknowledgement).not.toBeChecked();
  await acknowledgement.check();
  await page.getByLabel('操作原因', { exact: true }).fill('核对更新后的病例资料');
  await expect(approval).toBeEnabled();
  assert.deepEqual(caseWritePaths.slice(writesBefore), [path + '/revisions/' + old.id + '/reviews', path + '/revisions']);
  checks.push('reread-stale-source-blocks-review-until-new-revision');
}

try {
  await page.goto(receipt.url);
  await login();
  await checkDiscardOnCaseSwitch();
  await openCase(101); await freeze(text, saveWithForeignReceipt); await checkUnchangedApprovedDraft();
  const beforeSign = await rejectWrongPassword('sign');
  await sign(); await readback();
  assert.equal(caseWritePaths.length, beforeSign + 1);
  assert.match(caseWritePaths.at(-1), /\/cases\/101\/treatment\/revisions\/[^/]+\/signatures$/);
  assert((await page.locator('[aria-label="独立回读签署"]').textContent()).includes(text));
  checks.push('save-freeze-review-sign-independent-readback', 'exact-utf8-text', 'sign-wrong-password-retry-readback');
  await logout(); await login('frontdesk'); await openCase(101);
  await expect(page.locator('[aria-label="治疗签署"]')).toHaveCount(0);
  assert(!(await page.locator('[aria-label="病例详情"]').textContent()).includes(text));
  await logout(); await login('admin');
  await expect(page.getByText('当前账号尚无病例读取权限，请联系院内权限管理员。', { exact: true })).toBeVisible();
  await logout(); await login('remote'); await openCase(102);
  await expect(page.getByRole('button', { name: '保存治疗草稿', exact: true })).toBeDisabled();
  await expect(page.getByRole('row').filter({ has: page.getByRole('cell', { name: '#101', exact: true }) })).toHaveCount(0);
  checks.push('frontdesk-projection-admin-separation-cross-clinic-readonly');
  await logout(); await login('assistant'); await openCase(102); await freeze();
  await page.getByLabel('已核对冻结版本', { exact: true }).check(); await page.getByLabel('操作原因', { exact: true }).fill('助理不能审核');
  await expect(page.getByRole('button', { name: '审核通过', exact: true })).toBeDisabled();
  checks.push('assistant-draft-without-signing');
  await logout(); await login(); await openCase(108); await freeze();
  await page.getByLabel('治疗评估', { exact: true }).fill(text + '\n新草稿');
  await page.getByRole('button', { name: '保存治疗草稿', exact: true }).click();
  await expect(page.getByText('草稿已修改，此冻结版本不能继续审核或签署。', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: '冻结版本供核对', exact: true }).click();
  await expect(page.getByLabel('已核对冻结版本', { exact: true })).toBeEnabled();
  await checkRefreezeAfterSourceChange();
  const writesBeforeExpiry = caseWritePaths.length;
  const expiredLists = { 诊断: '合成诊断甲 🐾\n\n合成诊断乙  \n\n', 治疗目标: '合成目标甲　\n\n合成目标乙 {{literal}}\n\n' };
  await page.getByLabel('治疗诊断', { exact: true }).fill(expiredLists.诊断);
  await page.getByLabel('治疗目标', { exact: true }).fill(expiredLists.治疗目标);
  await page.getByLabel('治疗评估', { exact: true }).fill(text + '\n未保存');
  control('expire');
  const [expiredResponse] = await Promise.all([
    page.waitForResponse(r => r.request().method() === 'GET' && new URL(r.url()).pathname === `/api/v2/organizations/${fixture.org}/clinics/${fixture.clinic}/cases/108/treatment`),
    page.getByRole('button', { name: '重新读取治疗记录', exact: true }).click(),
  ]);
  assert.equal(expiredResponse.status(), 401);
  await checkExpiredClipboard(expiredLists);
  assert((await page.locator('[aria-label="治疗签署"]').textContent()).includes(text + '\n未保存'));
  assert.equal(caseWritePaths.length, writesBeforeExpiry);
  checks.push('stale-draft-and-diagnostic-source', '401-copyable-original', '401-native-copy-diagnosis-goals-trailing-blank-lines');
  await logout(); await login(); await openCase(109); await freeze(); await review();
  control('lose-sign-response'); await sign(); await prepared('lose-sign-response', 109);
  await page.getByRole('button', { name: '停止等待（保留原请求）', exact: true }).click();
  await logout(); await login(); await openCase(109);
  await page.getByRole('button', { name: '查询原请求', exact: true }).click(); await readback();
  assert.equal(caseWritePaths.filter(p => p.includes('/cases/109/') && p.endsWith('/signatures')).length, 1);
  control('release'); checks.push('lost-response-same-account-query-no-duplicate');
  control('policy-two'); await openCase(107); await freeze(); await review(); await sign();
  await expect(page.getByText('本院要求由另一位已核验医生签署。', { exact: true })).toBeVisible();
  await logout(); await login('doctor-b'); await openCase(107); await sign(); await readback();
  checks.push('two-person-rule');
  control('policy-self'); await openCase(101);
  await page.getByLabel('操作原因', { exact: true }).fill('合成修订');
  await page.getByRole('button', { name: '创建修订草稿', exact: true }).click();
  await freeze(text + '\n修订'); await review();
  const activeCard = page.getByRole('region', { name: '当前有效签署' });
  await expect(activeCard).toBeVisible();
  await checkConfirmationSwitch();
  const beforeReplacement = caseWritePaths.length;
  control('lose-sign-response');
  try {
    await sign(); await prepared('lose-sign-response', 101);
    await expect(page.getByText('签署结果待核对，请查询原请求。', { exact: true })).toBeVisible();
    await expect(activeCard).toHaveCount(0);
    await expect(page.getByText(/ · 状态待核对 · /)).toBeVisible();
    await page.getByRole('button', { name: '停止等待（保留原请求）', exact: true }).click();
    await page.getByRole('button', { name: '查询原请求', exact: true }).click();
    await readback();
    assert.equal(caseWritePaths.length, beforeReplacement + 1);
    assert.match(caseWritePaths.at(-1), /\/cases\/101\/treatment\/revisions\/[^/]+\/signatures$/);
  } finally {
    control('release');
  }
  await expect(activeCard).toBeVisible();
  await expect(page.getByText(/已由新签署替代/)).toBeVisible();
  checks.push('pending-replacement-signature-withdraws-old-effective-status');
  await page.getByLabel('操作原因', { exact: true }).fill('合成作废');
  const beforeRevoke = await rejectWrongPassword('revoke');
  await page.getByLabel('已核对待作废签署', { exact: true }).check();
  await page.getByLabel('签署认证密码', { exact: true }).fill(fixture.password);
  await page.getByRole('button', { name: '再次认证并作废签署', exact: true }).click();
  await expect(page.getByText(/ · 已作废 · /)).toBeVisible();
  await expect(page.locator('[aria-label="独立回读签署"]')).toContainText('revoked');
  assert.equal(caseWritePaths.length, beforeRevoke + 1);
  assert.match(caseWritePaths.at(-1), /\/cases\/101\/treatment\/signatures\/[^/]+\/revocations$/);
  await freeze(text + '\n作废后新签署'); await review();
  const aggregatePath = `/api/v2/organizations/${fixture.org}/clinics/${fixture.clinic}/cases/101/treatment`;
  const [afterResigning] = await Promise.all([
    page.waitForResponse(r => new URL(r.url()).pathname === aggregatePath && r.request().method() === 'GET'),
    sign(),
  ]);
  assert.equal(afterResigning.status(), 200);
  await readback();
  const signedRecord = await afterResigning.json();
  await expect(page.locator('[aria-label="独立回读签署"]')).toContainText(signedRecord.plan.active_signature_id + ' · effective');
  await logout(); await login();
  const [reopened] = await Promise.all([
    page.waitForResponse(response => response.url() === afterResigning.url() && response.request().method() === 'GET'),
    openCase(101),
  ]);
  assert.equal(reopened.status(), 200);
  const reopenedRecord = await reopened.json();
  assert.equal(reopenedRecord.plan.active_signature_id, signedRecord.plan.active_signature_id);
  await checkSupersessionHistory(reopenedRecord);
  checks.push('amend-revoke-resign-history', 'revoke-wrong-password-retry-readback');
  for (const kind of ['late-200', 'late-401']) {
    control(kind);
    await page.getByRole('row').filter({ has: page.getByRole('cell', { name: '#101', exact: true }) }).getByRole('button', { name: '查看', exact: true }).click();
    await prepared(kind);
    await logout(); await login('doctor-b'); await openCase(103);
    control('release');
    await expect(page.locator('[aria-label="病例详情"] h2').first()).toContainText('#103');
    await expect(page.getByRole('button', { name: '退出登录', exact: true })).toBeVisible();
    checks.push(kind + '-account-case-isolation');
    await logout(); await login(); await openCase(101);
  }
  const signedId = await checkSignedListItems();
  await checkReadbackAfterExternalRevocation(signedId);
  assert.deepEqual(errors, []);
  result.status = 'PASS';
} catch (error) {
  result.status = 'FAILED'; result.error = String(error); result.page_errors = errors;
  throw error;
} finally {
  fs.writeFileSync(path.join(state, 'chromium-receipt.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
  await browser.close();
}
