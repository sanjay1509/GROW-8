"""Approved backend QA suite helpers. Inherits *application* client/seeded_db fixtures
from /app/api/tests/conftest.py. Never use this directory as pytest rootdir.

No database assertions are made: any test DB inserts/updates are fixture setup only.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

import pytest

CATALOG = json.loads((Path(__file__).parent / 'cases.json').read_text(encoding='utf-8'))['cases']
BY_ID = {c['id']: c for c in CATALOG}
assert len(CATALOG) == len(BY_ID) == 237, 'Catalog must contain 237 unique approved IDs'

DEV_PASSWORD = 'Grow8Dev!2026'
EMAILS = {
    'creator': 'maple.bakery@grow8.dev',
    'other_creator': 'yyc.events@grow8.dev',
    'contributor': 'alex.chen@grow8.dev',
    'admin': 'admin@grow8.dev',
    'orgless_creator': None,
}
OPPS = '/api/v1/opportunities'
NOTIFS = '/api/v1/notifications'


def pytest_configure(config):
    for marker in ('smoke: critical quick check', 'sanity: feature confidence check',
                   'regression: functional and negative API assertions',
                   'deferred: approved but excluded infrastructure scenario'):
        config.addinivalue_line('markers', marker)


def parameters(prefix: str):
    cases = [c for c in CATALOG if c['id'].startswith(prefix)]
    if not cases:
        raise AssertionError(f'No approved cases for {prefix}')
    def marker(c):
        if c['automation_scope'] == 'deferred_infrastructure':
            return [pytest.mark.deferred, pytest.mark.skip(reason='Approved but deferred: infrastructure-failure testing excluded from current scope')]
        # Classification is a reporting/running convenience, not an unapproved change in case design.
        number = int(c['id'].split('-')[-1])
        if number == 1 or c['id'] in ('HLTH-006','CAT-002','SKL-002','MINE-002','NOTIF-003','UCNT-005','READ-006','ALLREAD-007'):
            return [pytest.mark.smoke]
        if number in (2, 3) and c['id'].split('-')[0] in ('CAT','SKL','CREATE','PATCH','PUB','NOTIF','UCNT','READ','ALLREAD'):
            return [pytest.mark.sanity]
        return [pytest.mark.regression]
    return [pytest.param(c['id'], marks=marker(c), id=c['id']) for c in cases]


def expect(response, status: int, code: str | None = None):
    assert response.status_code == status, f'expected HTTP {status}, got {response.status_code}: {response.text[:900]}'
    if code is not None:
        body = response.json()
        assert body.get('error', {}).get('code') == code, f'expected error code {code}: {body}'
    return response.json()


def page(response, *, total: int | None = None, limit: int | None = None, offset: int | None = None):
    body = expect(response, 200)
    assert set(body) == {'items', 'total', 'limit', 'offset'}, body
    assert isinstance(body['items'], list)
    assert isinstance(body['total'], int) and body['total'] >= 0
    assert isinstance(body['limit'], int) and 1 <= body['limit'] <= 100
    assert isinstance(body['offset'], int) and body['offset'] >= 0
    assert len(body['items']) <= body['limit']
    if total is not None: assert body['total'] == total
    if limit is not None: assert body['limit'] == limit
    if offset is not None: assert body['offset'] == offset
    return body


def ids(items):
    return [i['opportunity_id'] for i in items]


def valid_minimal():
    return {'title':'Approved API test draft','description':'A valid draft for QA validation.', 'category':'knowledge'}


def valid_complete(**updates):
    d = {
        'title':'Approved QA Inventory Project',
        'description':'Record and organize donated inventory for the team.',
        'category':'community', 'skills':['inventory', 'spreadsheets'],
        'requirements':'Attention to detail',
        'location':'Calgary', 'work_mode':'remote',
        'start_date':'2027-03-01', 'end_date':'2027-03-20',
        'expected_hours':8, 'compensation_type':'paid', 'compensation_amount':160,
        'compensation_details':'Fixed honorarium', 'applicant_limit':3,
        'application_deadline':'2027-02-15T23:59:00-07:00',
        'working_conditions':'Flexible daytime hours',
        'safety_information':'Remote work with normal computer precautions',
        'accessibility_details':'Flexible scheduling and screen-reader-friendly records',
    }
    d.update(updates)
    return d


def require_opportunity_shape(item):
    for field, typ in [('opportunity_id',int),('title',str),('description',str),('status',str),
                       ('category',dict),('organization',dict),('skills',list),
                       ('created_at',str),('updated_at',str)]:
        assert isinstance(item.get(field), typ), f'{field} missing/wrong type: {item}'
    assert item['opportunity_id'] >= 1
    assert {'code','name','description'} <= item['category'].keys()
    assert {'organization_id','name','organization_type','city'} <= item['organization'].keys()
    for skill in item['skills']: assert set(skill) == {'code','name'}


def require_notification_shape(item):
    expected = {'notification_id','notification_type','title','message','opportunity_id','read_at','created_at','is_read'}
    assert set(item) == expected
    assert isinstance(item['notification_id'], int)
    assert isinstance(item['title'], str) and isinstance(item['message'], str)
    assert isinstance(item['is_read'], bool)
    assert item['is_read'] == (item['read_at'] is not None)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: ('<redacted>' if ('password' in k.lower() or 'secret' in k.lower() or
                                    k.lower() in ('authorization','access_token','jwt_secret'))
                   else _sanitize(v)) for k,v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(v) for v in value]
    if isinstance(value, str):
        if value.startswith('Bearer ') or value.count('.') == 2 and len(value)>80:
            return '<redacted-token>'
        return value[:1500]
    return value


class EvidenceClient:
    def __init__(self, client, request):
        self.client = client
        self.request = request
        self.trace: list[dict] = []
        self.expected = BY_ID.get(request.node.callspec.params.get('case_id', ''), {}).get('expected_result', '')
        request.node._approved_qa = self

    def request_api(self, method, url, **kwargs):
        response = self.client.request(method, url, **kwargs)
        try: payload = response.json()
        except ValueError: payload = response.text[:2500]
        self.trace.append({
            'method': method.upper(), 'url': str(url),
            'query': _sanitize(kwargs.get('params')),
            'request_body': _sanitize(kwargs.get('json')),
            'request_headers': _sanitize(kwargs.get('headers') or {}),
            'actual_http_status': response.status_code,
            'actual_response': _sanitize(payload),
        })
        return response

    def get(self, url, **kwargs): return self.request_api('GET', url, **kwargs)
    def post(self, url, **kwargs): return self.request_api('POST', url, **kwargs)
    def patch(self, url, **kwargs): return self.request_api('PATCH', url, **kwargs)
    def request_raw(self, method, url, **kwargs): return self.request_api(method, url, **kwargs)


@pytest.fixture
def api(client, request):
    return EvidenceClient(client, request)


def signin(api, role='creator'):
    email = EMAILS[role]
    assert email, f'No seeded email for role {role}'
    body = expect(api.post('/api/v1/auth/login', json={'email': email, 'password': DEV_PASSWORD}), 200)
    return {'Authorization': 'Bearer ' + body['access_token']}


def invalid_jwt():
    return {'Authorization': 'Bearer not.a.valid.jwt'}


def _html_extras(item, report):
    try:
        import pytest_html
    except ImportError:
        return
    audit = getattr(item, '_approved_qa', None)
    case_id = item.callspec.params.get('case_id', '') if hasattr(item,'callspec') else ''
    case = BY_ID.get(case_id, {})
    trace = audit.trace if audit is not None else []
    # pytest-html expects trusted HTML here; escape content to avoid injection.
    evidence = {
        'id': case_id, 'endpoint': f"{case.get('method','')} {case.get('path','')}",
        'scenario': case.get('scenario',''), 'expected_result': case.get('expected_result',''),
        'actual_http_exchanges': trace,
        'outcome': report.outcome,
        'assertion_failure': str(report.longrepr)[:4000] if report.failed else None,
    }
    extras = list(getattr(report, 'extras', []))
    pretty = html.escape(json.dumps(evidence, indent=2, ensure_ascii=False, default=str))
    extras.append(pytest_html.extras.html('<details><summary>Expected vs Actual API evidence</summary><pre style="white-space:pre-wrap">'+pretty+'</pre></details>'))
    report.extras = extras


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == 'call':
        _html_extras(item, report)
