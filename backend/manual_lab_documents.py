"""Opt-in, snapshot-bound transcription into draft documents. No clinical inference or writes."""
from contextlib import contextmanager
import json
import os
from xml.etree import ElementTree as ET

try:
    from backend import manual_lab_results as lab
    from backend import case_attachment_service as attachments
    from backend.case_attachment_store import Store, AttachmentError
except ModuleNotFoundError:
    import manual_lab_results as lab
    import case_attachment_service as attachments
    from case_attachment_store import Store, AttachmentError

KEY = '__manual_lab_documents'
SCHEMA = 'manual-lab-documents-cw-b8-v1'
MAX_REPORTS, MAX_ITEMS = 5, 200
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def ensure_enabled():
    lab.ensure_enabled()
    if os.getenv('MANUAL_LAB_DOCUMENTS_ENABLED') != '1' or os.getenv('MANUAL_LAB_DOCUMENTS_SYNTHETIC_ONLY') != '1':
        raise AttachmentError('manual_lab_documents_disabled', 503)


def selection(ids):
    if not isinstance(ids, list) or len(ids) > MAX_REPORTS or any(type(i) is not int or i <= 0 for i in ids) or len(set(ids)) != len(ids):
        raise AttachmentError('invalid_manual_lab_document_selection', 422)
    return sorted(ids)


def _xml_text(value):
    value = str(value)
    if any(not (c in '\t\r\n' or '\x20' <= c <= '\ud7ff' or '\ue000' <= c <= '\ufffd' or '\U00010000' <= c <= '\U0010ffff') for c in value):
        raise AttachmentError('manual_lab_document_invalid_text', 422)
    return value.replace('\r\n', '\n').replace('\r', '\n')


def _validate_text(value):
    if isinstance(value, dict):
        for v in value.values(): _validate_text(v)
    elif isinstance(value, list):
        for v in value: _validate_text(v)
    elif isinstance(value, str): _xml_text(value)


def read_selected(store, db, case, ids):
    rows = lab.document_reports(store, db, case, selection(ids))
    if sum(len(r['data']['items']) for r in rows) > MAX_ITEMS:
        raise AttachmentError('manual_lab_document_item_limit', 422)
    _validate_text(rows)
    return rows


@contextmanager
def snapshot(uid, cid, ids):
    ensure_enabled()
    ids = selection(ids)
    store = Store()
    # Same order as source/identity/report mutations; render bytes before releasing.
    with store.locked(), attachments.transaction(uid, cid) as (db, case):
        yield db, case, read_selected(store, db, case, ids)


def options(uid, cid):
    ensure_enabled()
    state = lab.listing(uid, cid)
    return {'case_id': cid, 'reports': [r for r in state['reports'] if r['state'] == 'confirmed'],
            'max_reports': MAX_REPORTS, 'max_items': MAX_ITEMS, 'writes_database': False}


def add_context(context, reports):
    if reports:
        context[KEY] = json.dumps({'schema': SCHEMA, 'reports': reports}, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return context


def paragraph(text='', *, bold=False, keep=False, page=False):
    p = ET.Element(W+'p')
    props = ET.SubElement(p, W+'pPr')
    ET.SubElement(props, W+'spacing', {W+'after': '100', W+'line': '260', W+'lineRule': 'auto'})
    if keep: ET.SubElement(props, W+'keepNext')
    if page: ET.SubElement(props, W+'pageBreakBefore')
    r = ET.SubElement(p, W+'r'); rp = ET.SubElement(r, W+'rPr')
    ET.SubElement(rp, W+'rFonts', {W+'ascii': 'Arial', W+'hAnsi': 'Arial', W+'eastAsia': 'SimSun'})
    ET.SubElement(rp, W+'sz', {W+'val': '20'})
    if bold: ET.SubElement(rp, W+'b')
    # Literal text, including braces, is data; never feed it back to token replacement.
    for i, line in enumerate(_xml_text(text).split('\n')):
        if i: ET.SubElement(r, W+'br')
        for j, part in enumerate(line.split('\t')):
            if j: ET.SubElement(r, W+'tab')
            ET.SubElement(r, W+'t', {'{http://www.w3.org/XML/1998/namespace}space': 'preserve'}).text = part
    return p


def result_text(row):
    return {'not_tested': '未测', 'not_provided': '未提供'}.get(row['result_type'], row['value'])


def table(items):
    widths = [1500, 1500, 1050, 2400, 1300, 1610]
    t = ET.Element(W+'tbl'); props = ET.SubElement(t, W+'tblPr')
    ET.SubElement(props, W+'tblW', {W+'w': str(sum(widths)), W+'type': 'dxa'})
    ET.SubElement(props, W+'tblLayout', {W+'type': 'fixed'})
    borders = ET.SubElement(props, W+'tblBorders')
    for side in ('top','left','bottom','right','insideH','insideV'):
        ET.SubElement(borders, W+side, {W+'val': 'single', W+'sz': '4', W+'color': 'D9D9D9'})
    grid = ET.SubElement(t, W+'tblGrid')
    for width in widths: ET.SubElement(grid, W+'gridCol', {W+'w': str(width)})
    values = [['项目', '结果原文', '单位', '参考区间原文', '原报告标记', '原报告位置']]
    values += [[r['name'], result_text(r), r['unit'] or '未提供', r['reference'] or '未提供', r['flag'] or '未提供', r['position']] for r in items]
    for index, values_row in enumerate(values):
        tr = ET.SubElement(t, W+'tr'); trp = ET.SubElement(tr, W+'trPr')
        if index == 0: ET.SubElement(trp, W+'tblHeader')
        if max(map(len, values_row)) < 150: ET.SubElement(trp, W+'cantSplit')
        for width, text in zip(widths, values_row):
            tc = ET.SubElement(tr, W+'tc'); tcp = ET.SubElement(tc, W+'tcPr')
            ET.SubElement(tcp, W+'tcW', {W+'w': str(width), W+'type': 'dxa'})
            if not index: ET.SubElement(tcp, W+'shd', {W+'fill': 'E8EEF4'})
            tc.append(paragraph(text, bold=index == 0))
    return t


def append_section(xml, context):
    if not context.get(KEY): return xml
    payload = json.loads(context[KEY]); root = ET.fromstring(xml); body = root.find(W+'body')
    if body is None: raise AttachmentError('manual_lab_document_invalid_template', 500)
    at = list(body).index(body.find(W+'sectPr')) if body.find(W+'sectPr') is not None else len(body)
    content = []
    for row in payload['reports']:
        report = row['data']['report']
        content += [paragraph('检验结果附节 · 医生选择的已核对原文', bold=True, keep=True, page=True),
                    paragraph('草稿 · 尚未签署；原报告标记仅为抄录，不代表系统判断。', keep=True),
                    paragraph(report['title'], bold=True, keep=True)]
        labels = [('specimen','样本'),('collected_at','采样时间'),('reported_at','报告时间'),('laboratory','实验室'),('device','仪器')]
        for key, label in labels: content.append(paragraph(label+'：'+(report[key] or '未提供'), keep=True))
        content.append(paragraph(f"病例：{context['visit.case_id']}；报告：{row['root_id']}；版本：{row['version']}；核对账号：{row['reviewed_by']}；核对时间：{row['reviewed_at']}", keep=True))
        content.append(paragraph('原件：'+row['source']['name']+'；完整性标识 SHA-256：'+row['source']['sha256'], keep=True))
        content.append(table(row['data']['items']))
        if report['note']: content.append(paragraph('报告备注原文：'+report['note']))
        content.append(paragraph('导出账号：'+context['export.account_id']+'；生成时间：'+context['timestamp']+'；文书内容校验标识：'+context['hash']))
    for node in content: body.insert(at, node); at += 1
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)
