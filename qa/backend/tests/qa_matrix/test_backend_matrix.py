"""Grow8 QA matrix: source-traceable scenario tests against grow8_test only.

This module uses the project's existing seeded_db fixture, which rebuilds *only*
`grow8_test` on each test. Never use this module against the development database.
Rows not supported by the current product or by controlled fixtures are reported
as SKIPPED with a precise reason, rather than as spurious PASSED tests.
"""
import json
import re
from datetime import datetime
from pathlib import Path

import pytest

ROOT = "/api/v1/opportunities"
CASES = json.loads((Path(__file__).parent / "cases.json").read_text(encoding="utf-8"))
VALID = {
    "title": "QA Matrix Description Capture",
    "description": "Keep careful records for Grow8 automated verification.",
    "category": "knowledge",
    "skills": ["data-entry", "spreadsheets"],
    "requirements": "Attention to detail.",
    "location": "Calgary, Alberta",
    "work_mode": "remote",
    "start_date": "2027-03-01",
    "end_date": "2027-03-20",
    "expected_hours": 8,
    "compensation_type": "paid",
    "compensation_amount": 160,
    "compensation_details": "Paid after verification.",
    "applicant_limit": 4,
    "application_deadline": "2027-02-15T23:59:00-07:00",
    "working_conditions": "Flexible remote schedule.",
    "safety_information": "No on-site hazards.",
    "accessibility_details": "Assistive software permitted.",
}
MINIMUM = {k: VALID[k] for k in ("title", "description", "category")}
NON_NULL_FIELDS = ("title", "description", "category", "skills")
ALLOWED_NULL_FIELDS = tuple(k for k in VALID if k not in NON_NULL_FIELDS)
FIELD_GOOD = {
    "title": "Updated QA Matrix Title",
    "description": "Updated meaningful description",
    "category": "community",
    "skills": ["customer-service"],
    "requirements": "Some experience helpful",
    "location": "Calgary, Alberta",
    "work_mode": "on_site",
    "start_date": "2027-03-02",
    "end_date": "2027-03-21",
    "expected_hours": 12,
    "compensation_type": "stipend",
    "compensation_amount": 20,
    "compensation_details": "Paid for approved hours",
    "applicant_limit": 10,
    "application_deadline": "2027-02-17T10:00:00Z",
    "working_conditions": "Desk work",
    "safety_information": "No chemicals",
    "accessibility_details": "Ramps available",
}


def skipper(reason):
    pytest.skip("Requires separate prerequisite / future product feature: " + reason)


def response_ok(resp, code=200):
    assert resp.status_code == code, f"HTTP {resp.status_code}; expected {code}: {resp.text[:1000]}"
    return resp.json()


def assert_error(resp, code, error_code=None):
    response_ok(resp, code)
    if error_code:
        assert resp.json()["error"]["code"] == error_code, resp.text


def owner(request):
    return request.getfixturevalue("bakery")


def other(request):
    return request.getfixturevalue("events_org")


def contributor(request):
    return request.getfixturevalue("contributor")


def post_draft(client, request, data=None):
    data = MINIMUM if data is None else data
    return response_ok(client.post(ROOT, headers=owner(request), json=data), 201)


def publish_draft(client, request, body=None, headers=None):
    draft = post_draft(client, request, body or VALID)
    res = client.post(f"{ROOT}/{draft['opportunity_id']}/publish", headers=headers or owner(request))
    return res, draft


def get_path(obj, path):
    cur = obj
    for k in path.split('.'):
        if k.endswith('[]'):
            cur = cur[k[:-2]]
        elif isinstance(cur, list):
            cur = [v[k] for v in cur]
        else:
            cur = cur[k]
    return cur


def list_items(client, params=None, headers=None):
    r = client.get(ROOT, params=params or {'limit': 100}, headers=headers or {})
    return response_ok(r)['items']


def handle_health(c, client, request):
    n = c['scenario']
    if 'unavailable' in n:
        skipper('dependency fault injection must run in dedicated isolated service')
    r = client.get('/health')
    if 'No credentials' in n:
        assert r.status_code != 401
    else:
        response_ok(r)
        assert r.json()['checks'] == {'mysql':'ok','rabbitmq':'ok'}


def handle_auth(c, client, request):
    n = c['scenario']; endpoint = c['endpoint']
    if endpoint.endswith('/me'):
        if 'Missing' in n:
            assert_error(client.get(endpoint),401,'AUTH_REQUIRED');return
        if 'Malformed' in n:
            assert_error(client.get(endpoint, headers={'Authorization':'Bearer not-a-jwt'}),401);return
        if 'Non-bearer' in n:
            assert client.get(endpoint, headers={'Authorization':'Basic abc'}).status_code == 401;return
        if 'Expired' in n or 'Unknown user' in n or 'Inactive' in n:
            skipper('special signed JWT and/or inactive-user isolated fixture not configured')
        body=response_ok(client.get(endpoint, headers=owner(request)))
        assert body['email']=='maple.bakery@grow8.dev' and body['role']=='creator'
        assert not {'password','password_hash'} & body.keys()
        return
    if c['id'] == 'BE-AUTH-001':
        skipper('qa.creator@grow8.dev is not in the isolated grow8_test seed; add it to isolated fixture before claiming coverage')
    base={'email':'maple.bakery@grow8.dev','password':'Grow8Dev!2026'}
    if 'normalization' in n:
        base['email']='  MAPLE.BAKERY@GROW8.DEV  '
    elif 'Unknown email' in n:
        base['email']='no-such-user@example.test'
    elif 'Wrong password' in n:
        base['password']='wrong-pass'
    elif 'Inactive user' in n:
        skipper('needs isolated inactive-user fixture')
    elif 'Email absent' in n:
        del base['email']
    elif 'Password absent' in n:
        del base['password']
    elif 'Email empty' in n:
        base['email']=''
    elif 'Password empty' in n:
        base['password']=''
    elif 'Email >255' in n:
        base['email']='a'*256
    elif 'Password >128' in n:
        base['password']='p'*129
    elif 'Wrong field types' in n:
        base={'email':42,'password':['nope']}
    elif 'SQL injection' in n:
        base['email']="' OR 1=1 --"
    elif 'Malformed email semantics' in n:
        base['email']='not-an-email'
    elif 'Login maps' in n:
        role=n.split()[-2]
        look={'creator':'maple.bakery@grow8.dev','contributor':'alex.chen@grow8.dev'}
        if role not in look:
            skipper('admin seeded credential requires confirmation')
        base['email']=look[role]
    resp=client.post(endpoint,json=base)
    if any(a in n for a in ('Unknown','Wrong password','SQL injection','Malformed email semantics')):
        assert_error(resp,401,'INVALID_CREDENTIALS');return
    if any(a in n for a in ('absent','empty','>','field types')):
        assert_error(resp,422,'VALIDATION_ERROR');return
    data=response_ok(resp)
    assert data['access_token'] and data['token_type']=='bearer' and data['expires_in'] > 0
    assert 'password' not in str(data).lower() and 'password_hash' not in str(data)
    if 'Login maps' in n:
        assert data['user']['role']==n.split()[-2]
    else:
        assert data['user']['role']=='creator'


def handle_reference(c, client, request):
    n=c['scenario']; path=c['endpoint']; rows=response_ok(client.get(path))
    assert isinstance(rows,list) and len(rows)>0
    if 'field in each item' in n:
        f=c['field']
        assert all(f in row and (isinstance(row[f],str) or (f=='description' and row[f] is None)) for row in rows)
    if 'duplicates' in n:
        codes=[x['code'] for x in rows]
        assert len(codes)==len(set(codes))
    if 'list available' in n:
        assert all('code' in x and 'name' in x for x in rows)


def _list_params(n):
    t={
        'Search title case-insensitively': {'q':'SPREADSHEET'},
        'Search description': {'q':'recipes'},
        'Search organization': {'q':'Food Bank'},
        'Search percent literally': {'q':'%'},
        'Search underscore literally': {'q':'_'},
        'Max length': {'q':'a'*100},'Over max': {'q':'a'*101},'Empty value':{'q':''},
        'Valid category':{'category':'knowledge'},'No matching category':{'category':'unknown'},
        'Single valid skill':{'skill':'data-entry'},'Repeated values OR semantics':[('skill','photography'),('skill','translation')],
        'Unknown skill':{'skill':'unlisted-code'},
        'Remote':{'work_mode':'remote'},'On-site':{'work_mode':'on_site'},'Hybrid':{'work_mode':'hybrid'},'Bad enum':{'work_mode':'teleport'},
        'Paid':{'compensation_type':'paid'},'Unpaid':{'compensation_type':'unpaid'},'Stipend':{'compensation_type':'stipend'},
        'Valid org':{'organization_id':1},'Nonexistent org':{'organization_id':999999},'Zero org':{'organization_id':0},
        'Inclusive lower bound':{'min_hours':5},'Inclusive upper bound':{'max_hours':10},
        'Equal bounds':{'min_hours':10,'max_hours':10},'Reversed bounds':{'min_hours':11,'max_hours':10},
        'Negative':{},'Aware time':{'deadline_before':'2027-01-01T00:00:00Z'},
        'Naive time invalid':{'deadline_before':'2027-01-01T00:00:00'},
        'Earlier than all':{'deadline_before':'2000-01-01T00:00:00Z'},
        'Default limit':{},'Minimum page':{'limit':1},'Maximum page':{'limit':100},
        'Zero':{},'Too large':{'limit':101},'Default offset':{},
        'Offset second page':{'limit':3,'offset':3},'Beyond total':{'offset':999999},
        'Filter intersection':{'category':'knowledge','work_mode':'remote'},
        'Filter + sort + pagination':{'category':'knowledge','sort':'title','limit':2,'offset':2},
        'Only open and unexpired':{'limit':100},'Page total independent of limit':{'limit':1},
        'Long description unusual characters':{'q':'%_é'},
        'Unrecognized sort':{'sort':'shuffled'},
    }
    if n.startswith('Sort '): return {'sort':n[len('Sort '):], 'limit':100}
    if n=='Negative':return {'min_hours':-1}
    if n=='Zero' or n=='Negative' or n=='Invalid' or n=='Bad enum':return {}
    return t.get(n)


def handle_list(c, client, request):
    n=c['scenario']; f=c['field'];params=_list_params(n)
    if n=='Negative': params={'min_hours' if f=='min_hours' else 'max_hours':-1}
    if n=='Zero': params={'limit':0}
    if n=='Invalid status': params={'status':'archived'}
    if n=='Negative' and f=='offset': params={'offset':-1}
    if params is None and n!='Public browse returns page':
        skipper('scenario-specific query fixture not available: '+n)
    r=client.get(ROOT,params=params or {})
    if c['expected'].startswith('422'):
        assert_error(r,422);return
    data=response_ok(r)
    assert set(('items','total','limit','offset')).issubset(data)
    assert data['total']>=len(data['items']) and len(data['items'])<=data['limit']
    items=data['items']
    if n=='Public browse returns page' or n=='Only open and unexpired':
        assert all(o['status']=='open' for o in items)
    elif 'Search ' in n and n not in ('Search percent literally','Search underscore literally'):
        q=params['q'].lower()
        assert all(q in (o['title']+' '+o['description']+' '+o['organization']['name']).lower() for o in items)
    elif n in ('Search percent literally','Search underscore literally','No matching category','Unknown skill','Nonexistent org','Beyond total','Earlier than all'):
        assert not items
    elif f=='category' and params.get('category')=='knowledge':
        assert all(o['category']['code']=='knowledge' for o in items)
    elif f=='skill' and params and isinstance(params,dict) and 'skill' in params:
        assert all('data-entry' in [sk['code'] for sk in o['skills']] for o in items)
    elif n=='Repeated values OR semantics':
        assert all({'photography','translation'} & {sk['code'] for sk in o['skills']} for o in items)
    elif f=='work_mode':
        assert all(o['work_mode']==params['work_mode'] for o in items)
    elif f=='compensation_type':
        assert all(o['compensation_type']==params['compensation_type'] for o in items)
    elif f=='organization_id' and params.get('organization_id')==1:
        assert all(o['organization']['organization_id']==1 for o in items)
    elif f=='min_hours':
        assert all(o['expected_hours']>=float(params['min_hours']) for o in items)
    elif f=='max_hours':
        assert all(o['expected_hours']<=float(params['max_hours']) for o in items)
    elif f=='min_hours/max_hours':
        assert all(o['expected_hours']==10 for o in items)
    elif f=='deadline_before':
        assert all(o['application_deadline'] < '2027-01-01T00:00:00Z' for o in items)
    elif n=='Offset second page':
        fst=response_ok(client.get(ROOT,params={'limit':3,'offset':0}))['items']
        assert not {v['opportunity_id'] for v in items}&{v['opportunity_id'] for v in fst}
    elif n=='Page total independent of limit':
        assert data['total']==response_ok(client.get(ROOT,params={'limit':100}))['total']
    elif n.startswith('Sort '):
        key=params['sort']; sortkeys={'hours':'expected_hours','-hours':'expected_hours','title':'title',
                                     'deadline':'application_deadline','-deadline':'application_deadline',
                                     'compensation':'compensation_amount','-compensation':'compensation_amount',
                                     'newest':'published_at','oldest':'published_at'}
        values=[o[sortkeys[key]] for o in items]
        if key in ('newest','oldest'):
            values=[o['published_at'] or o['created_at'] for o in items]
        if key in ('compensation','-compensation'):
            values=[v or 0 for v in values]
        assert values==sorted(values,reverse=key.startswith('-') or key=='newest')
    elif n=='Filter intersection':
        assert all(o['category']['code']=='knowledge' and o['work_mode']=='remote' for o in items)
    elif n=='Default limit': assert data['limit']==20
    elif n=='Default offset': assert data['offset']==0
    elif n=='Minimum page': assert data['limit']==1
    elif n=='Maximum page': assert data['limit']==100


def handle_mine(c, client, request):
    n=c['scenario'];headers=owner(request);params={}
    if 'Anonymous' in n:headers={}
    elif 'Contributor' in n:headers=contributor(request)
    elif 'Admin' in n:skipper('admin fixture not provisioned')
    elif n=='No organization case':skipper('needs isolated Creator without organization fixture')
    elif n=='Status draft': params={'status':'draft'}
    elif n=='Status open': params={'status':'open'}
    elif n=='Repeat status OR':params=[('status','draft'),('status','open')]
    elif n=='Invalid status':params={'status':'archived'}
    elif n in ('Ignored organization_id','Restrict owner across query'):params={'organization_id':3}
    elif n=='Mine accepts category filter':params={'category':'knowledge'}
    elif n=='Mine supports pagination':params={'limit':2,'offset':2}
    resp=client.get(ROOT+'/mine',headers=headers,params=params)
    if 'Anonymous' in n: assert_error(resp,401);return
    if 'Contributor' in n:assert_error(resp,403);return
    if n=='Invalid status':assert_error(resp,422);return
    data=response_ok(resp)
    ids={o['organization']['organization_id'] for o in data['items']}
    assert ids <= {1},f'Cross-org leak: {ids}'
    if n=='Status draft':assert all(o['status']=='draft' for o in data['items'])
    if n=='Status open':assert all(o['status']=='open' for o in data['items'])
    if n=='Repeat status OR':assert all(o['status'] in ['draft','open'] for o in data['items'])
    if n=='Mine accepts category filter':assert all(o['category']['code']=='knowledge' for o in data['items'])
    if n=='Mine supports pagination': assert data['limit']==2 and data['offset']==2
    if n=='Ignored organization_id': assert ids <= {1}


def handle_get(c, client, request):
    n=c['scenario']; id='1'; headers={}
    if n.startswith('Draft'):
        id='14'
        if 'owner visible' in n:headers=owner(request)
        elif 'other' in n:headers=other(request)
    elif 'Missing' in n:id='999999'
    elif 'zero' in n:id='0'
    elif 'negative' in n:id='-1'
    elif 'alphabetic' in n:id='abc'
    elif 'Closed' in n:id='11'
    elif 'Cancelled' in n:skipper('no cancelled seed opportunity')
    res=client.get(f'{ROOT}/{id}',headers=headers)
    if ('hidden' in n or 'Missing' in n):assert_error(res,404);return
    if 'Invalid' in n:assert_error(res,422);return
    data=response_ok(res)
    assert data['opportunity_id']==int(id)


def handle_read(c, client, request):
    n=c['field'];data=response_ok(client.get(ROOT+'/1'))
    value=get_path(data,n)
    assert value is not None if n in ('opportunity_id','title','description','status','category.code','category.name',
                                       'organization.organization_id','organization.name','organization.organization_type',
                                       'skills[].code','skills[].name','created_at','updated_at') else True
    if n.endswith('id') and not isinstance(value,list):assert isinstance(value,int)
    if n in ('expected_hours','compensation_amount') and value is not None:assert isinstance(value,(int,float))
    if n in ('skills[].code','skills[].name'):assert isinstance(value,list) and all(isinstance(v,str) for v in value)
    if n in ('category.code','category.name','organization.name','title','description'):
        assert isinstance(value,str) and bool(value)
    if n=='status':assert value in ('draft','open','closed','cancelled')
    if n=='work_mode' and value:assert value in ('remote','on_site','hybrid')
    if n=='compensation_type' and value:assert value in ('paid','stipend','unpaid')


def _create_payload_for_case(c):
    n=c['scenario'];f=c['field'];body=dict(MINIMUM)
    if n=='Complete draft remains draft until publish':return dict(VALID),201
    if n=='Minimum draft creation':return body,201
    if n=='Unauthenticated creation' or n=='Contributor cannot create':return body,None
    if n=='Creator without org': skipper('needs dedicated orphan Creator fixture')
    if n=='Unexpected field': body['not_supported']=True;return body,422
    if n=='Missing title':body.pop('title');return body,422
    if n=='Missing description':body.pop('description');return body,422
    if n=='Missing category':body.pop('category');return body,422
    if n=='Duplicate skill codes':body['skills']=['data-entry','data-entry'];return body,201
    if n=='Forbidden ID injection':body['organization_id']=9999;return body,422
    if n=='Forbidden status injection':body['status']='open';return body,422
    if n=='Whitespace title':body['title']='   ';return body,422
    if n=='Money >10 digits':body['compensation_amount']=99999999999;return body,422
    if n=='Hours precision >6 digits':body['expected_hours']=1234567;return body,422
    overrides={
        'Valid 3-char title':('title','ABC',201),'Title below minimum':('title','AB',422),
        'Title >200':('title','a'*201,422),'Unicode description':('description','Details in 中文 accents',201),
        'Blank description':('description','',422),'Over 10000 characters':('description','x'*10001,422),
        'Knowledge category':('category','knowledge',201),'Unknown category':('category','unknown',422),
        'Null category':('category',None,422),'Known skills array':('skills',['data-entry','spreadsheets'],201),
        'Unknown code':('skills',['not-real'],422),'Over 20 skills':('skills',['data-entry']*21,422),
        'Valid requirements':('requirements','Experience useful',201),'Blank requirements':('requirements','',422),
        'Over 10000':('requirements','x'*10001,422),
        'On-site location':('location','Calgary Alberta',201),'Blank location':('location','',422),
        'Over 255':('location','a'*256,422),'Remote':('work_mode','remote',201),
        'Unknown work mode':('work_mode','virtual-reality',422),'Explicit null':(f,None,201),
        'Valid date':('start_date','2027-05-01',201),'Malformed date':(f,'not-a-date',422),
        'Start date after end':('start_date','2027-05-31',422),
        'Equal to start':('end_date','2027-05-01',201),
        'Before start':('end_date','2027-01-01',422),
        'Positive decimal':('expected_hours',0.01,201),'Zero':('expected_hours',0,422),
        'More than 2 decimals':('expected_hours',1.234,422),'Paid':('compensation_type','paid',201),
        'Unknown type':('compensation_type','bonus',422),'Valid zero':('compensation_amount',0,201),
        'Negative':('compensation_amount',-0.01,422),'Too many decimals':('compensation_amount',1.234,422),
        'Explanatory compensation terms':('compensation_details','Reimbursed via organizer',201),
        'Blank string':(f,'',422),'Over 500 chars':('compensation_details','a'*501,422),
        'Minimum 1':('applicant_limit',1,201),'Over 65535':('applicant_limit',65536,422),
        'Timezone-aware deadline':('application_deadline','2027-02-15T23:59:00-07:00',201),
        'Timezone absent':('application_deadline','2027-02-15T23:59:00',422),
        'Invalid date string':('application_deadline','invalid',422),
        'Valid working conditions':('working_conditions','Remote, quiet desk',201),
        'Valid safety info':('safety_information','Office ergonomics',201),
        'Valid accessibility info':('accessibility_details','Screen reader supported',201),
    }
    if n not in overrides:skipper('no verified fixture for '+n)
    k,v,status=overrides[n];body[k]=v
    if n in ('Start date after end','Equal to start','Before start'):
        body['start_date']='2027-05-01';body['end_date']='2027-05-20'
        if n=='Start date after end': body['start_date']='2027-05-31'
        elif n=='Equal to start':body['end_date']=body['start_date']
        else:body['end_date']='2027-01-01'
    return body,status


def handle_create(c, client, request):
    n=c['scenario'];body,status=_create_payload_for_case(c)
    headers=owner(request)
    if n=='Unauthenticated creation':headers={};status=401
    elif n=='Contributor cannot create':headers=contributor(request);status=403
    res=client.post(ROOT,json=body,headers=headers)
    assert res.status_code==status, f'{n}: actual {res.status_code}, expected {status}: {res.text}'
    if status==201:
        obj=res.json();assert obj['status']=='draft' and obj['published_at'] is None
        assert obj['organization']['organization_id']==1
        if n=='Duplicate skill codes':assert len(obj['skills'])==1
        if n=='Complete draft remains draft until publish':
            assert obj['compensation_type']=='paid' and obj['expected_hours']==8


def handle_patch(c, client, request):
    n=c['scenario'];field=c['field'];id='14';headers=owner(request);body={}
    if n.startswith('Update valid field '):
        field=n[len('Update valid field '):];body={field:FIELD_GOOD[field]}
    elif n.startswith('Explicit null behavior '):
        field=n[len('Explicit null behavior '):];body={field:None}
    elif n=='Owner patches draft title':body={'title':'Changed valid title'}
    elif 'No authorization' in n:headers={};body={'title':'Changed title'}
    elif 'Contributor JWT' in n:headers=contributor(request);body={'title':'Changed title'}
    elif 'Other owner draft' in n:id='15';body={'title':'Changed title'}
    elif 'Other owner published' in n:id='8';body={'title':'Changed title'}
    elif 'Published status' in n:id='1';body={'title':'Changed title'}
    elif 'Unknown id' in n:id='999999';body={'title':'Changed title'}
    elif 'Invalid id' in n:id='0';body={'title':'Changed title'}
    elif 'Empty patch' in n:body={}
    elif 'Unknown property' in n:body={'owner_user_id':123}
    elif 'Combined date inconsistency' in n:body={'end_date':'2020-01-01'}
    else:skipper('undefined PATCH fixture: '+n)
    res=client.patch(f'{ROOT}/{id}',json=body,headers=headers)
    if n.startswith('Explicit null behavior'):
        expected=422 if field in NON_NULL_FIELDS else 200
    elif n.startswith('Update valid field') or n=='Owner patches draft title':expected=200
    elif n=='No authorization':expected=401
    elif n=='Contributor JWT' or n=='Other owner published':expected=403
    elif n in ('Other owner draft','Unknown id'):expected=404
    elif n=='Published status':expected=409
    elif n=='Empty patch':expected=200
    else:expected=422
    assert res.status_code==expected,f'{n}: expected {expected}, got {res.status_code}: {res.text}'
    if expected==200 and body:
        obj=res.json()
        if field=='category':assert obj['category']['code']==body[field]
        elif field=='skills':assert [sk['code'] for sk in obj['skills']]==body[field]
        elif field=='application_deadline': assert obj[field] is not None if body[field] is not None else obj[field] is None
        else:assert obj.get(field)==body[field], (obj.get(field),body[field])
        assert obj['status']=='draft'


def handle_publish(c, client, request):
    n=c['scenario'];f=c['field']
    body=dict(VALID);headers=owner(request)
    if n.startswith('Reject incomplete draft lacking '):body[n.split('lacking ',1)[1]]=None
    elif n=='Conditional compensation rule paid':body['compensation_type']='paid';body['compensation_amount']=None
    elif n=='Conditional compensation rule stipend':body['compensation_type']='stipend';body['compensation_amount']=None
    elif n=='Conditional compensation rule unpaid':body['compensation_type']='unpaid';body['compensation_amount']=None
    elif n=='Past deadline':body['application_deadline']='2020-01-01T00:00:00Z'
    elif n=='Exactly now deadline':body['application_deadline']='2026-10-16T12:00:00Z'
    elif n=='Missing work mode':body['work_mode']=None
    elif n=='On-site without location':body['work_mode']='on_site';body['location']=None
    elif n=='Unpaid positive compensation':body['compensation_type']='unpaid';body['compensation_amount']=250
    elif n=='Deadline after work end':body['start_date']='2027-03-01';body['end_date']='2027-03-02';body['application_deadline']='2027-03-15T00:00:00Z'
    elif n=='Start in past':body['start_date']='2020-01-01';body['end_date']='2027-03-20'
    elif n in ('Cannot publish other draft','Cannot publish other open','Contributor forbidden','Anonymous forbidden','Nonexistent draft','Cannot republish','Publish complete valid owned draft'):
        pass
    else:skipper('complex event/staging fixture needs separate test: '+n)
    if n=='Cannot publish other draft':id=15
    elif n=='Cannot publish other open':id=8
    elif n=='Nonexistent draft':id=999999
    elif n=='Cannot republish':id=1
    else:id=post_draft(client,request,body)['opportunity_id']
    if n=='Contributor forbidden':headers=contributor(request)
    if n=='Anonymous forbidden':headers={}
    r=client.post(f'{ROOT}/{id}/publish',headers=headers)
    if n.startswith('Reject incomplete'):
        assert_error(r,422,'OPPORTUNITY_INCOMPLETE')
        assert n.split('lacking ',1)[1] in r.json()['error']['details']['missing_fields'];return
    if n in ('Conditional compensation rule paid','Conditional compensation rule stipend'):
        assert_error(r,422,'OPPORTUNITY_INCOMPLETE');return
    expected={
        'Past deadline':422,'Exactly now deadline':422,'Cannot publish other draft':404,
        'Cannot publish other open':403,'Cannot republish':409,
        'Contributor forbidden':403,'Anonymous forbidden':401,'Nonexistent draft':404,
    }.get(n,200)
    assert r.status_code==expected,f'{n}: {r.status_code} expected {expected}: {r.text}'
    if expected==200:assert r.json()['status']=='open' and r.json()['published_at']


def handle_event(c,client,request):
    n=c['scenario'];pub=request.getfixturevalue('publisher')
    if n=='Consumer processing':skipper('real consumer handler not implemented in uploaded source')
    if n=='RabbitMQ outage after commit':skipper('requires injected broker failure in isolated app')
    r,draft=publish_draft(client,request,headers={**owner(request),'X-Request-ID':'qa-123'})
    response_ok(r)
    assert len(pub.events)==1
    event=pub.events[0]
    assert event.event_type=='OPPORTUNITY_CREATED' and event.payload['opportunity_id']==draft['opportunity_id']
    if n=='Event payload':assert event.payload['category_code']=='knowledge'
    if n=='Request ID propagation': assert r.headers['X-Request-ID']=='qa-123' and event.correlation_id=='qa-123'
    if n=='Event exactly once':
        again=client.post(f'{ROOT}/{draft["opportunity_id"]}/publish',headers=owner(request))
        assert_error(again,409)
        assert len(pub.events)==1
    if n=='Event after commit':
        obj=response_ok(client.get(f'{ROOT}/{draft["opportunity_id"]}'))
        assert obj['status']=='open'


def handle_contract(c,client,request):
    # Parameter contracts not duplicated as fake pass conditions. Build meaningful
    # assertions on exact request field, or explicitly report prerequisite missing.
    endpoint=c['endpoint'];field=c['field'];method=c['method']
    if endpoint==ROOT and method=='GET':
        matching={'q':'query','skill':'query','work_mode':'query','compensation_type':'query',
                  'min_hours':'query','max_hours':'query','deadline_before':'query','sort':'query'}
        if field not in matching: skipper('no deterministic parameter value configured: '+field)
        params={'q':'spreadsheets','skill':'data-entry','work_mode':'remote',
                'compensation_type':'paid','min_hours':0,'max_hours':100,
                'deadline_before':'2027-01-01T00:00:00Z','sort':'title'}
        obj=response_ok(client.get(ROOT,params={field:params[field]}))
        assert obj['limit']>0 and isinstance(obj['items'],list)
        return
    if endpoint.endswith('/mine'):
        obj=response_ok(client.get(endpoint,headers=owner(request)))
        assert all(x['organization']['organization_id']==1 for x in obj['items'])
        return
    if endpoint=='/api/v1/auth/me':
        obj=response_ok(client.get(endpoint,headers=owner(request)))
        assert obj['role']=='creator';return
    skipper('contract requires specific fixture; not a generic HTTP 200 check: '+field)


def handle_xui(c,client,request):
    skipper('frontend/browser integration requires Playwright; backend-only suite cannot validate React UI')

HANDLERS={
    'HLTH':handle_health,'AUTH':handle_auth,'REF':handle_reference,'LIST':handle_list,
    'MINE':handle_mine,'GET':handle_get,'READ':handle_read,'CREATE':handle_create,
    'PATCH':handle_patch,'PUB':handle_publish,'EVT':handle_event,
    'CONTRACT':handle_contract,'XUI':handle_xui,
}

@pytest.mark.parametrize(
    'case',
    [pytest.param(c, marks=[getattr(pytest.mark, c['suite'].lower())]) for c in CASES],
    ids=[c['id'] for c in CASES],
)
def test_backend_case(case,request):
    """Each workbook test ID has a distinct pytest result; skip ≠ pass."""
    # Any fixture requesting `client` resets only grow8_test, never dev DB.
    if case['area']=='XUI': skipper('full browser integration uses Playwright, not backend-only tests')
    if case['id']=='BE-EVT-006':skipper('RabbitMQ consumer processing not implemented in this source snapshot')
    client=request.getfixturevalue('client')
    HANDLERS[case['area']](case,client,request)
