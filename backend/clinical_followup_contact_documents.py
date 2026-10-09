"""CW-B21/B22: explicitly selected contact facts in unsigned visit/owner drafts."""
from contextlib import contextmanager, ExitStack
from datetime import datetime
import json
import os
from xml.etree import ElementTree as ET

import clinical_followup_contacts as contacts
import clinical_followup_plan_documents as plan_docs
from models import Case, AuditLog

plans, labs, images, comparisons = plan_docs.plans, plan_docs.labs, plan_docs.images, plan_docs.comparisons
SCHEMA = 'clinical-followup-contact-documents-cw-b21-v1'
OWNER_SCHEMA = 'clinical-followup-contact-owner-documents-cw-b22-v1'
OWNER_TEMPLATE = 'owner_visit_summary_zh'
KEY = '__manual_followup_contact_document'
PRIVATE_HEADERS = plan_docs.PRIVATE_HEADERS
METHODS = {'phone': '电话', 'wechat': '微信', 'in_person': '当面', 'other': '其他'}
OUTCOMES = {'reached': '已取得联系', 'not_reached': '未取得联系', 'declined': '对方拒绝沟通', 'other': '其他'}
SOURCE_STATES = {'planned': '当前已核对计划', 'needs_review': '病例已变化，计划待重新核对',
                 'superseded': '来源计划已更正', 'withdrawn': '来源计划已撤销'}


def ensure_enabled(template_id='outpatient_record_zh'):
    contacts.ensure_enabled()
    if (os.getenv('FOLLOWUP_CONTACT_DOCUMENTS_ENABLED') != '1'
            or os.getenv('FOLLOWUP_CONTACT_DOCUMENTS_SYNTHETIC_ONLY') != '1'):
        raise contacts.Error('contact_documents_disabled', 503)
    if template_id == OWNER_TEMPLATE and (
            os.getenv('FOLLOWUP_CONTACT_OWNER_DOCUMENTS_ENABLED') != '1'
            or os.getenv('FOLLOWUP_CONTACT_OWNER_DOCUMENTS_SYNTHETIC_ONLY') != '1'):
        raise contacts.Error('contact_owner_documents_disabled', 503)


def validate_selection(value):
    if (not isinstance(value, dict) or set(value) != {'id', 'version', 'token', 'source_token', 'case_token'}
            or not plans.positive(value['id']) or not plans.positive(value['version'])
            or value['version'] > contacts.MAX_VERSIONS
            or any(not isinstance(value[k], str) or not plans.HASH.fullmatch(value[k])
                   for k in ('token', 'source_token', 'case_token'))):
        raise contacts.Error('contact_document_invalid_selection', 422)


def audit_token(db, case):
    # metadata is a SQL name; extra_data is the actual ORM JSON attribute.
    rows = db.query(AuditLog).filter_by(case_id=case.id, source=contacts.SOURCE).order_by(AuditLog.log_id).limit(101).all()
    if len(rows) > 100:
        raise contacts.Error('contact_invalid_saved_data')
    def value(row, col):
        v = getattr(row, 'extra_data' if col.name == 'metadata' else col.key)
        return v.isoformat() if isinstance(v, datetime) else v
    return plans.digest([{c.name: value(row, c) for c in AuditLog.__table__.columns} for row in rows])


def read_selected(db, case, selection, *, template_id='outpatient_record_zh'):
    listing = contacts.listing_data(db, case)  # validates ALL chains and audits
    record = next((r for r in listing['records'] if r['id'] == selection['id']), None)
    if record is None:
        raise contacts.Error('contact_not_found', 404)
    source = next(p for p in listing['plans'] if p['id'] == record['source']['id'])
    if (record['state'] != 'recorded' or record['version'] != selection['version']
            or record['token'] != selection['token'] or source['token'] != selection['source_token']
            or listing['case_token'] != selection['case_token']):
        raise contacts.Error('contact_document_changed_review_again')
    return {'schema': OWNER_SCHEMA if template_id == OWNER_TEMPLATE else SCHEMA,
            **({'template_id': OWNER_TEMPLATE} if template_id == OWNER_TEMPLATE else {}),
            'case_id': case.id, 'timezone': 'Asia/Shanghai',
            'selection': selection, 'case': listing['case'], 'record': record,
            'audit_token': audit_token(db, case)}


@contextmanager
def snapshot(uid, cid, selection, lab_ids, image_ids, comparison, has_comparison, followup, has_followup,
             *, template_id='outpatient_record_zh'):
    validate_selection(selection)
    if template_id not in ('outpatient_record_zh', OWNER_TEMPLATE) or (
            template_id == OWNER_TEMPLATE and has_comparison):
        raise contacts.Error('contact_document_unsupported_template_selection', 422)
    ensure_enabled(template_id)
    with ExitStack() as stack:
        reports, imaging, compared, plan = [], [], None, None
        if has_followup:
            db, reports, imaging, compared, plan = stack.enter_context(plan_docs.snapshot(
                uid, cid, followup, lab_ids, image_ids, comparison, has_comparison,
                template_id=template_id))
            case = db.get(Case, cid)
        elif has_comparison:
            db, reports, imaging, compared = stack.enter_context(comparisons.snapshot(uid, cid, comparison, lab_ids, image_ids))
            case = db.get(Case, cid)
        elif image_ids:
            db, reports, imaging = stack.enter_context(images.snapshot(uid, cid, image_ids, lab_ids))
            case = db.get(Case, cid)
        elif lab_ids:
            db, case, reports = stack.enter_context(labs.snapshot(uid, cid, lab_ids))
        else:
            db, case = stack.enter_context(plans.transaction(uid, cid))
        payload = read_selected(db, case, selection, template_id=template_id)
        # The caller builds the entire document before releasing existing locks.
        yield db, reports, imaging, compared, plan, payload


def add_context(context, payload):
    context[KEY] = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return context  # Never replace the CURRENT follow-up arrangement with history.


def identity(label, case):
    return (label + f"：病例 #{case['id']}；动物：" + (case['patient_name'] or '未填写')
            + '；物种：' + (case['species'] or '未填写') + '；宠主：' + (case['owner_name'] or '未填写'))


def append_section(xml, context):
    p = json.loads(context[KEY]); r = p['record']; d = r['data']; s = r['source']; data = s['data']
    root = ET.fromstring(xml); body = root.find(labs.W+'body')
    if body is None:
        raise contacts.Error('contact_document_invalid_template')
    para = labs.paragraph
    owner = p['schema'] == OWNER_SCHEMA
    nodes = [para('人工随访记录附节 · ' + ('宠主说明 · ' if owner else '') + '医生本次明确选择', bold=True, keep=True, page=True),
             para('草稿 · 待医生核对 · 尚未签署。联系或尝试记录不代表已复诊、完成检查、改善或关闭计划。'),
             para(identity('当前病例身份', p['case'])), para(identity('联系登记时身份', r['case_snapshot'])),
             para('实际联系或尝试时间（上海）：'+d['occurred_at']),
             para('联系方式：'+METHODS[d['method']]+'；实际结果：'+OUTCOMES[d['outcome']]),
             para('记录原文：'+d['note']), para('后续安排原文：'+(d['next_action'] or '未填写')),
             para('更正原因：'+(r['reason'] or '首次保存')),
             para(f"联系记录 ID：{r['id']}；根 ID：{r['root_id']}；版本：{r['version']}"),
             para('登记账号：'+r['recorded_by']+'；确认时间：'+r['recorded_at']),
             para('联系版本内容标识：'+r['token']),
             para('联系发生时的来源计划 · 历史原文', bold=True, keep=True),
             para('以下为该联系冻结的来源，不自动作为本次文书的当前复查安排。'),
             para('来源当前状态：'+SOURCE_STATES[r['source_state']]),
             para(identity('来源计划保存时身份', s['case_snapshot'])),
             para(f"来源计划 ID：{s['id']}；根 ID：{s['root_id']}；版本：{s['version']}"),
             para('来源计划日期（上海）：'+data['planned_date']), para('来源复查目的：'+data['purpose']),
             plan_docs.items_table(data['items']), para('来源提前返回条件：'+(data['return_conditions'] or '未填写')),
             para('来源备注：'+(data['note'] or '未填写')),
             para('来源核对账号：'+s['reviewed_by']+'；核对时间：'+s['reviewed_at']),
             para('来源当前内容标识：'+p['selection']['source_token']),
             para('审计校验标识：'+p['audit_token']), para('附节版本：'+p['schema']),
             para('导出账号：'+context['export.account_id']+'；生成时间：'+context['timestamp']+'；文书内容校验标识：'+context['hash'])]
    if owner:
        nodes.insert(2, para('本附节保留历史沟通及来源原文，请医生核对是否适合出示给宠主。'))
    at = list(body).index(body.find(labs.W+'sectPr')) if body.find(labs.W+'sectPr') is not None else len(body)
    for node in nodes:
        body.insert(at, node); at += 1
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)
