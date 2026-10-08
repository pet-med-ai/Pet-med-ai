"""CW-B13: one explicitly selected saved comparison in an unsigned outpatient draft."""
from contextlib import contextmanager
import json
import os
from xml.etree import ElementTree as ET

import clinical_lab_comparison as comparison
import manual_lab_documents as labs
import manual_imaging_documents as images
import case_attachment_service as attachments
from case_attachment_store import Store, AttachmentError

KEY = '__manual_lab_comparison_document'
SCHEMA = 'clinical-lab-comparison-documents-cw-b13-v1'
ROW_FIELDS = ('id', 'root_id', 'version', 'token', 'title', 'reviewed_by', 'reviewed_at', 'source', 'report')
PRIVATE_HEADERS = {'Cache-Control': 'private, no-store', 'X-PMAI-Writes-Database': 'false'}


def ensure_enabled():
    comparison.ensure_enabled()
    labs.ensure_enabled()
    if os.getenv('LAB_COMPARISON_DOCUMENTS_ENABLED') != '1' or os.getenv('LAB_COMPARISON_DOCUMENTS_SYNTHETIC_ONLY') != '1':
        raise AttachmentError('lab_comparison_documents_disabled', 503)


def read_selected(store, db, case, request):
    try:
        saved = comparison.assemble(store, db, case)
    except AttachmentError as error:
        if error.status == 422:
            raise AttachmentError('lab_comparison_document_invalid_saved_data', 409) from error
        raise
    if request['snapshot'] != saved['snapshot']:
        raise AttachmentError('lab_comparison_stale_snapshot', 409)
    a, b = (comparison.selected(saved, request[key]) for key in ('a', 'b'))
    result = comparison.compare(a, b, request['doctor_confirmed'])
    if not result['can_calculate']:
        raise AttachmentError('lab_comparison_document_not_comparable', 422)
    def side(pair):
        row, item = pair
        return {key: row[key] for key in ROW_FIELDS} | {'item': item}
    payload = {'schema': SCHEMA, 'rules': comparison.RULES, 'case_id': case.id,
               'selection': request, 'a': side(a), 'b': side(b), 'result': result}
    labs._validate_text(payload)
    return payload


@contextmanager
def snapshot(uid, cid, request, lab_ids, image_ids):
    ensure_enabled()
    comparison.validate_request(request)
    if image_ids: images.imaging.ensure_enabled()
    store = Store()
    # No nested readers/transactions: body, originals, all selected sections and
    # DOCX bytes share the mutation lock and this one case transaction.
    with store.locked(), attachments.transaction(uid, cid) as (db, case):
        payload = read_selected(store, db, case, request)
        reports = labs.read_selected(store, db, case, lab_ids) if lab_ids else []
        imaging = images.read_selected(store, db, case, image_ids) if image_ids else []
        yield db, reports, imaging, payload


def add_context(context, payload):
    # Exclude volatile read/generation times. Saved reviewer times remain bound.
    context[KEY] = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return context


def table(payload):
    w = labs.W
    widths = [2000, 3680, 3680]
    table = ET.Element(w+'tbl'); props = ET.SubElement(table, w+'tblPr')
    ET.SubElement(props, w+'tblW', {w+'w': '9360', w+'type': 'dxa'})
    ET.SubElement(props, w+'tblLayout', {w+'type': 'fixed'})
    borders = ET.SubElement(props, w+'tblBorders')
    for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        ET.SubElement(borders, w+side, {w+'val': 'single', w+'sz': '4', w+'color': 'D9D9D9'})
    grid = ET.SubElement(table, w+'tblGrid')
    for width in widths: ET.SubElement(grid, w+'gridCol', {w+'w': str(width)})
    values = [['保存原文', 'A · 较早采样', 'B · 较晚采样']]
    fields = [('name', '项目名称'), ('result_type', '结果类型'), ('value', '结果原文'), ('unit', '单位'),
              ('reference', '参考范围原文'), ('reference_low', '参考下限'), ('reference_high', '参考上限'),
              ('reference_unit', '参考单位'), ('flag', '原始标记'), ('position', '原文位置')]
    values += [[label, payload['a']['item'][key], payload['b']['item'][key]] for key, label in fields]
    for index, cells in enumerate(values):
        row = ET.SubElement(table, w+'tr'); rp = ET.SubElement(row, w+'trPr')
        if not index: ET.SubElement(rp, w+'tblHeader')
        # Long source text can span pages; never force an unbounded row together.
        if max(map(len, cells)) < 150: ET.SubElement(rp, w+'cantSplit')
        for width, text in zip(widths, cells):
            cell = ET.SubElement(row, w+'tc'); cp = ET.SubElement(cell, w+'tcPr')
            ET.SubElement(cp, w+'tcW', {w+'w': str(width), w+'type': 'dxa'})
            ET.SubElement(cp, w+'vAlign', {w+'val': 'center'})
            if not index: ET.SubElement(cp, w+'shd', {w+'fill': 'E8EEF4'})
            margin = ET.SubElement(cp, w+'tcMar')
            for side in ('top', 'left', 'bottom', 'right'):
                ET.SubElement(margin, w+side, {w+'w': '90', w+'type': 'dxa'})
            cell.append(labs.paragraph(text, bold=not index))
    return table


def append_section(xml, context):
    payload = json.loads(context[KEY]); root = ET.fromstring(xml); body = root.find(labs.W+'body')
    if body is None: raise AttachmentError('lab_comparison_document_invalid_template', 409)
    paragraph = labs.paragraph
    nodes = [paragraph('检验前后对照附节 · 医生本次明确选择', bold=True, keep=True, page=True),
             paragraph('草稿 · 待医生核对 · 尚未签署。方法与采样条件确认仅用于本次文书，不代表医生验收。'),
             paragraph('数值变化不等于病情变化；不自动诊断，不进行单位换算。')]
    for key in ('a', 'b'):
        row = payload[key]
        nodes.append(paragraph(key.upper()+' · '+row['title'], bold=True, keep=True))
        for field, label in [('panel', '检验组合'), ('specimen', '样本类型'), ('laboratory', '实验室'), ('device', '设备'),
                             ('collected_at', '采样时间'), ('reported_at', '报告时间'), ('note', '报告备注原文')]:
            nodes.append(paragraph(label+'：'+row['report'][field]))
        nodes += [paragraph(f"病例：{payload['case_id']}；记录 ID：{row['id']}；报告根 ID：{row['root_id']}；版本：{row['version']}；项目序号：{row['item']['index']}"),
                  paragraph(f"核对账号：{row['reviewed_by']}；核对时间：{row['reviewed_at']}"),
                  paragraph('来源文件：'+row['source']['name']+'；SHA-256：'+row['source']['sha256']),
                  paragraph('保存版本标识：'+row['token'])]
    nodes.append(table(payload))
    delta = payload['result']['delta']
    nodes.append(paragraph('差值 B−A：'+delta['value']+' '+delta['unit'], bold=True))
    nodes.append(paragraph({'increase': '数值增加', 'decrease': '数值减少', 'same': '数值相同'}[delta['state']]))
    if payload['result']['reference_changed']:
        nodes.append(paragraph('参考范围不同，请分别回看；两侧参考范围不会互相套用。', bold=True))
    nodes += [paragraph('规则版本：'+payload['rules']+'；附节版本：'+SCHEMA),
              paragraph('导出账号：'+context['export.account_id']+'；生成时间：'+context['timestamp']+'；文书内容校验标识：'+context['hash'])]
    at = list(body).index(body.find(labs.W+'sectPr')) if body.find(labs.W+'sectPr') is not None else len(body)
    for node in nodes: body.insert(at, node); at += 1
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)
