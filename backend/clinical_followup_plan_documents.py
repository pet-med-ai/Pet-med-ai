"""CW-B15: exact saved plan in an unsigned, snapshot-bound outpatient draft."""
from contextlib import contextmanager, ExitStack
import json
import os
from xml.etree import ElementTree as ET

import clinical_followup_plans as plans
import manual_lab_documents as labs
import manual_imaging_documents as images
import clinical_lab_comparison_documents as comparisons
from models import Case

SCHEMA = 'clinical-followup-plan-documents-cw-b15-v1'
KEY = '__manual_followup_plan_document'
PRIVATE_HEADERS = {'Cache-Control': 'private, no-store', 'X-PMAI-Writes-Database': 'false'}


def ensure_enabled():
    plans.ensure_enabled()
    if (os.getenv('FOLLOWUP_PLAN_DOCUMENTS_ENABLED') != '1'
            or os.getenv('FOLLOWUP_PLAN_DOCUMENTS_SYNTHETIC_ONLY') != '1'):
        raise plans.PlanError('followup_plan_documents_disabled', 503)


def validate_selection(value):
    if (not isinstance(value, dict) or set(value) != {'id', 'version', 'token'}
            or not plans.positive(value['id']) or not plans.positive(value['version'])
            or value['version'] > plans.MAX_VERSIONS or not isinstance(value['token'], str)
            or not plans.HASH.fullmatch(value['token'])):
        raise plans.PlanError('followup_document_invalid_selection', 422)


def read_selected(db, case, selection):
    # Validate the entire saved chain; a corrupt or withdrawn plan is not absence.
    found = next(((row, meta) for row, meta in plans.records(db, case) if row.id == selection['id']), None)
    if found is None:
        raise plans.PlanError('followup_plan_not_found', 404)
    plan = plans.public(*found, case)
    if (plan['state'] != 'planned' or plan['version'] != selection['version']
            or plan['token'] != selection['token']):
        raise plans.PlanError('followup_document_changed_review_again')
    return {'schema': SCHEMA, 'case_id': case.id, 'timezone': 'Asia/Shanghai',
            'selection': selection, 'plan': plan}


@contextmanager
def snapshot(uid, cid, selection, lab_ids, image_ids, comparison, has_comparison):
    validate_selection(selection)
    ensure_enabled()
    # Reuse the original lock order and ONE session; never nest case transactions.
    # The caller creates all DOCX bytes before this context is released.
    with ExitStack() as stack:
        reports, imaging, compared = [], [], None
        if has_comparison:
            db, reports, imaging, compared = stack.enter_context(comparisons.snapshot(uid, cid, comparison, lab_ids, image_ids))
            case = db.get(Case, cid)
        elif image_ids:
            db, reports, imaging = stack.enter_context(images.snapshot(uid, cid, image_ids, lab_ids))
            case = db.get(Case, cid)
        elif lab_ids:
            db, case, reports = stack.enter_context(labs.snapshot(uid, cid, lab_ids))
        else:
            db, case = stack.enter_context(plans.transaction(uid, cid))
        payload = read_selected(db, case, selection)
        yield db, reports, imaging, compared, payload


def add_context(context, payload):
    context[KEY] = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    context['visit.follow_up'] = '本次已纳入复查计划原文，详见复查计划附节；计划不代表已完成复查。'
    return context


def items_table(items):
    w = labs.W
    table = ET.Element(w+'tbl'); props = ET.SubElement(table, w+'tblPr')
    ET.SubElement(props, w+'tblW', {w+'w': '9360', w+'type': 'dxa'})
    ET.SubElement(props, w+'tblLayout', {w+'type': 'fixed'})
    borders = ET.SubElement(props, w+'tblBorders')
    for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        ET.SubElement(borders, w+side, {w+'val': 'single', w+'sz': '4', w+'color': 'D9D9D9'})
    grid = ET.SubElement(table, w+'tblGrid')
    for width in (900, 8460): ET.SubElement(grid, w+'gridCol', {w+'w': str(width)})
    for index, values in enumerate([['序号', '复查项目原文']] + [[str(i+1), item] for i, item in enumerate(items)]):
        row = ET.SubElement(table, w+'tr'); rp = ET.SubElement(row, w+'trPr')
        if not index: ET.SubElement(rp, w+'tblHeader')
        # No cantSplit/keepNext on unbounded text; allow natural page breaks.
        for width, value in zip((900, 8460), values):
            cell = ET.SubElement(row, w+'tc'); cp = ET.SubElement(cell, w+'tcPr')
            ET.SubElement(cp, w+'tcW', {w+'w': str(width), w+'type': 'dxa'})
            if not index: ET.SubElement(cp, w+'shd', {w+'fill': 'E8EEF4'})
            cell.append(labs.paragraph(value, bold=not index))
    return table


def append_section(xml, context):
    payload = json.loads(context[KEY]); plan = payload['plan']; data = plan['data']
    root = ET.fromstring(xml); body = root.find(labs.W+'body')
    if body is None: raise plans.PlanError('followup_document_invalid_template')
    paragraph = labs.paragraph
    nodes = [paragraph('复查计划附节 · 医生本次明确选择', bold=True, keep=True, page=True),
             paragraph('草稿 · 待医生核对 · 尚未签署。计划不代表已复查、已预约或已联系宠主。'),
             paragraph('计划复查日期（上海）：'+data['planned_date']),
             paragraph('复查目的：'+data['purpose']), items_table(data['items']),
             paragraph('提前返回条件：'+(data['return_conditions'] or '未填写')),
             paragraph('备注：'+(data['note'] or '未填写')),
             paragraph(f"病例：{payload['case_id']}；计划记录 ID：{plan['id']}；计划根 ID：{plan['root_id']}；版本：{plan['version']}"),
             paragraph('确认账号：'+plan['reviewed_by']+'；确认时间：'+plan['reviewed_at']),
             paragraph('保存版本内容标识：'+plan['token']),
             paragraph('附节版本：'+SCHEMA),
             paragraph('导出账号：'+context['export.account_id']+'；生成时间：'+context['timestamp']+'；文书内容校验标识：'+context['hash'])]
    at = list(body).index(body.find(labs.W+'sectPr')) if body.find(labs.W+'sectPr') is not None else len(body)
    for node in nodes: body.insert(at, node); at += 1
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)
