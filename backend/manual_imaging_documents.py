"""Read-only, opt-in imaging and laboratory snapshots for two draft documents."""
from contextlib import contextmanager
import json
from xml.etree import ElementTree as ET

try:
    from backend import manual_imaging_records as imaging, manual_lab_documents as lab_docs
    from backend import case_attachment_service as attachments
    from backend.case_attachment_store import Store, AttachmentError
except ModuleNotFoundError:
    import manual_imaging_records as imaging
    import manual_lab_documents as lab_docs
    import case_attachment_service as attachments
    from case_attachment_store import Store, AttachmentError

KEY = '__manual_imaging_documents'
SCHEMA = 'manual-imaging-documents-cw-b9-v1'
MAX_REPORTS, MAX_TEXT = 5, 20000
BODY_FIELDS = ('findings', 'impression', 'limitations', 'note')
W = lab_docs.W


def selection(ids):
    if not isinstance(ids, list) or len(ids) > MAX_REPORTS or any(type(i) is not int or i <= 0 for i in ids) or len(set(ids)) != len(ids):
        raise AttachmentError('invalid_manual_imaging_document_selection', 422)
    return sorted(ids)


def read_selected(store, db, case, ids):
    rows = imaging.document_reports(store, db, case, selection(ids))
    if sum(len(r['data'][k]) for r in rows for k in BODY_FIELDS) > MAX_TEXT:
        raise AttachmentError('manual_imaging_document_text_limit', 422)
    lab_docs._validate_text(rows)
    return rows


@contextmanager
def snapshot(uid, cid, imaging_ids, lab_ids):
    imaging.ensure_enabled()
    if lab_ids: lab_docs.ensure_enabled()
    image_ids, lab_ids = selection(imaging_ids), lab_docs.selection(lab_ids)
    store = Store()
    # One lock and one transaction for both selections, held through DOCX bytes.
    with store.locked(), attachments.transaction(uid, cid) as (db, case):
        images = read_selected(store, db, case, image_ids)
        labs = lab_docs.read_selected(store, db, case, lab_ids) if lab_ids else []
        yield db, labs, images


def options(uid, cid):
    state = imaging.listing(uid, cid)
    return {'case_id': cid, 'reports': [r for r in state['reports'] if r['state'] == 'confirmed'],
            'max_reports': MAX_REPORTS, 'max_text': MAX_TEXT, 'writes_database': False}


def add_context(context, reports):
    if reports: context[KEY] = json.dumps({'schema': SCHEMA, 'reports': reports}, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return context


def append_section(raw, context):
    root = ET.fromstring(raw); body = root.find(W+'body')
    if body is None: raise AttachmentError('manual_imaging_document_unavailable', 409)
    nodes = []
    for row in json.loads(context[KEY])['reports']:
        data, source = row['data'], row['source']
        nodes.append(lab_docs.paragraph('影像报告附节 · 医生核对原文', bold=True, keep=True, page=True))
        nodes.append(lab_docs.paragraph(data['title'] + ' · 版本 ' + str(row['version']), bold=True, keep=True))
        modality = {'dr': 'DR', 'ultrasound': '超声'}[data['modality']]
        for label, value in [('检查类型', modality), ('检查部位', data['body_part']), ('检查时间原文', data['taken_at']),
                             ('出具机构', data['institution']), ('原件位置', data['position']),
                             ('记录编号', row['root_id']), ('原件文件', source['name']), ('原件 SHA-256', source['sha256']),
                             ('核对账号', row['reviewed_by']), ('核对时间', row['reviewed_at'])]:
            nodes.append(lab_docs.paragraph(f'{label}：{value or "未提供"}'))
        for key, label in [('findings', '所见原文'), ('impression', '结论原文'), ('limitations', '局限性原文'), ('note', '备注原文')]:
            nodes.append(lab_docs.paragraph(label, bold=True, keep=True))
            nodes.append(lab_docs.paragraph(data[key] or '未提供'))
        nodes.append(lab_docs.paragraph('以上为医生核对后的记录原文；本文件仍为尚未签署的草稿。'))
        nodes.append(lab_docs.paragraph('导出账号：' + context.get('export.account_id', '') + ' · 内容校验标识：' + context.get('hash', '')))
    index = next((i for i, child in enumerate(body) if child.tag == W+'sectPr'), len(body))
    for node in nodes: body.insert(index, node); index += 1
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)
