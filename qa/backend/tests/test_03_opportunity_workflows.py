"""Approved My / Get / Create / Patch / Publish scenarios: HTTP behavior only."""
from __future__ import annotations
from datetime import datetime
import pytest
from .conftest import (OPPS,expect,page,ids,signin,invalid_jwt,parameters,
                       valid_minimal,valid_complete,require_opportunity_shape)


def status_error(api,method,path,status,code,*,headers=None,body=None):
    options={'headers':headers}
    if body is not None:options['json']=body
    return expect(api.request_raw(method,path,**options),status,code)


def mine(api,headers,params=None):
    return page(api.get(OPPS+'/mine',headers=headers,params=params))


def create(api,headers,body=None):
    return expect(api.post(OPPS,headers=headers,json=body if body is not None else valid_minimal()),201)


def new_draft(api,headers,body=None):
    return create(api,headers,body)['opportunity_id']


def assert_draft_still(api,opportunity_id,headers):
    obj=expect(api.get(f'{OPPS}/{opportunity_id}',headers=headers),200)
    assert obj['status']=='draft' and obj['published_at'] is None
    return obj


@pytest.mark.parametrize('case_id',parameters('MINE-'))
def test_mine(case_id,api,seeded_db):
    n=int(case_id.split('-')[-1]); h=signin(api)
    if n==1:
        p=mine(api,h)
        assert p['total']==5 and set(ids(p['items']))=={1,2,3,4,14}
        for it in p['items']:
            require_opportunity_shape(it)
            assert it['organization']['organization_id']==1
    elif n==2:status_error(api,'GET',OPPS+'/mine',401,'AUTH_REQUIRED')
    elif n==3:status_error(api,'GET',OPPS+'/mine',403,'ROLE_FORBIDDEN',headers=signin(api,'contributor'))
    elif n==4:
        p=mine(api,h,{'organization_id':3})
        assert p['total']==5 and all(it['organization']['organization_id']==1 for it in p['items'])
    elif n==5:
        # Arrange all four statuses in the isolated test fixture, then assert via HTTP only.
        with seeded_db.cursor() as cur:
            cur.execute("UPDATE opportunity SET status='closed' WHERE opportunity_id=1")
            cur.execute("UPDATE opportunity SET status='cancelled' WHERE opportunity_id=2")
        p=mine(api,h)
        assert p['total']==5 and set(ids(p['items']))=={1,2,3,4,14}
        assert {it['status'] for it in p['items']}=={'draft','open','closed','cancelled'}
    elif n==6:
        p=mine(api,h,{'status':'draft'})
        assert ids(p['items'])==[14] and all(it['status']=='draft' for it in p['items'])
    elif n==7:
        p=mine(api,h,{'q':'inventory spreadsheet'})
        assert 2 in ids(p['items'])
        assert all('inventory spreadsheet' in it['title'].lower() or 'inventory spreadsheet' in it['description'].lower() for it in p['items'])
    elif n==8:
        p=mine(api,h,{'category':'knowledge','skill':'spreadsheets','work_mode':'remote'})
        assert p['items']
        for it in p['items']:
            assert it['organization']['organization_id']==1 and it['category']['code']=='knowledge'
            assert it['work_mode']=='remote' and 'spreadsheets' in {s['code'] for s in it['skills']}
    elif n==9:
        p=mine(api,h,{'sort':'newest','limit':5,'offset':0})
        assert p['total']==5 and len(p['items'])==5 and p['offset']==0 and p['limit']==5
        timestamps=[datetime.fromisoformat((it['published_at'] or it['created_at']).replace('Z','+00:00')) for it in p['items']]
        assert timestamps==sorted(timestamps,reverse=True)
    elif n==10:status_error(api,'GET',OPPS+'/mine?status=pending',422,'VALIDATION_ERROR',headers=h)
    else:raise AssertionError('Unknown MINE case '+case_id)


@pytest.mark.parametrize('case_id',parameters('GET-'))
def test_get_opportunity(case_id,api):
    n=int(case_id.split('-')[-1]); path=lambda i:f'{OPPS}/{i}'
    if n==1:
        b=expect(api.get(path(1)),200)
        require_opportunity_shape(b)
        assert b['opportunity_id']==1 and b['status']=='open' and b['category']['code']=='knowledge'
        assert b['organization']['organization_id']==1 and b['skills']
    elif n==2:
        for role in ('creator','contributor','admin'):
            b=expect(api.get(path(1),headers=signin(api,role)),200)
            assert b['opportunity_id']==1 and b['status']=='open'
    elif n==3:
        b=expect(api.get(path(14),headers=signin(api)),200)
        assert b['status']=='draft' and b['published_at'] is None
        require_opportunity_shape(b)
        assert b['organization']['organization_id']==1
    elif n==4:status_error(api,'GET',path(14),404,'OPPORTUNITY_NOT_FOUND')
    elif n==5:status_error(api,'GET',path(14),404,'OPPORTUNITY_NOT_FOUND',headers=signin(api,'other_creator'))
    elif n==6:assert expect(api.get(path(11)),200)['status']=='closed'
    elif n==7:
        b=expect(api.get(path(10)),200)
        assert b['status']=='open' and b['opportunity_id']==10
        assert b['application_deadline'] is not None
        assert 10 not in ids(page(api.get(OPPS,params={'limit':100}))['items'])
    elif n==8:status_error(api,'GET',path(999999),404,'OPPORTUNITY_NOT_FOUND')
    elif n==9:status_error(api,'GET',path(0),422,'VALIDATION_ERROR')
    elif n==10:status_error(api,'GET',path(1),401,'INVALID_TOKEN',headers=invalid_jwt())
    else:raise AssertionError('Unknown GET case '+case_id)


@pytest.mark.parametrize('case_id',parameters('CREATE-'))
def test_create_opportunity(case_id,api,seeded_db):
    n=int(case_id.split('-')[-1]);h=signin(api)
    if n==1:
        b=create(api,h)
        assert b['opportunity_id']>0 and b['status']=='draft'
        assert b['published_at'] is None and b['skills']==[]
        assert b['requirements'] is None and b['work_mode'] is None
    elif n==2:
        body=valid_complete(); b=create(api,h,body)
        require_opportunity_shape(b)
        for k in ('title','description','requirements','location','work_mode','start_date','end_date','compensation_type','applicant_limit','working_conditions','safety_information','accessibility_details'):
            assert b[k]==body[k], (k,b.get(k),body[k])
        assert b['expected_hours']==8 and b['compensation_amount']==160
        assert b['category']['code']=='community'
        assert [s['code'] for s in b['skills']]==['inventory','spreadsheets']
        assert b['application_deadline']=='2027-02-16T06:59:00Z'
    elif n==3:
        b=create(api,h)
        assert_draft_still(api,b['opportunity_id'],h)
        public=page(api.get(OPPS,params={'limit':100}))
        assert b['opportunity_id'] not in ids(public['items'])
    elif n==4:
        b=create(api,h)
        assert b['organization']['organization_id']==1
        p=mine(api,h)
        assert b['opportunity_id'] in ids(p['items'])
    elif n==5:status_error(api,'POST',OPPS,401,'AUTH_REQUIRED',body=valid_minimal())
    elif n==6:status_error(api,'POST',OPPS,401,'INVALID_TOKEN',headers=invalid_jwt(),body=valid_minimal())
    elif n==7:
        for role in ('contributor','admin'):
            status_error(api,'POST',OPPS,403,'ROLE_FORBIDDEN',headers=signin(api,role),body=valid_minimal())
    elif n==8:
        # Seed setup only: change role for a contributor with no organization.
        with seeded_db.cursor() as cur:cur.execute("UPDATE user_account SET role='creator' WHERE user_id=6")
        r=api.post(OPPS,headers=signin_raw(api,'jordan.lee@grow8.dev'),json=valid_minimal())
        expect(r,409,'ORGANIZATION_REQUIRED')
    elif n==9:
        for field in ('title','description','category'):
            payload=valid_minimal();payload.pop(field)
            status_error(api,'POST',OPPS,422,'VALIDATION_ERROR',headers=h,body=payload)
    elif n==10:
        for updates in ({'title':'ab'},{'title':'x'*201},{'description':''}):
            status_error(api,'POST',OPPS,422,'VALIDATION_ERROR',headers=h,body=valid_minimal()|updates)
    elif n==11:
        status_error(api,'POST',OPPS,422,'UNKNOWN_CATEGORY',headers=h,body=valid_minimal()|{'category':'unknown-category'})
    elif n==12:
        error=status_error(api,'POST',OPPS,422,'UNKNOWN_SKILL',headers=h,body=valid_minimal()|{'skills':['unknown-skill']})
        assert 'unknown-skill' in error['error']['details']['unknown_skills']
    elif n==13:
        b=create(api,h,valid_minimal()|{'skills':['inventory','inventory','spreadsheets']})
        assert [s['code'] for s in b['skills']]==['inventory','spreadsheets']
    elif n==14:
        status_error(api,'POST',OPPS,422,'VALIDATION_ERROR',headers=h,body=valid_minimal()|{'skills':['inventory']*21})
    elif n==15:
        status_error(api,'POST',OPPS,422,'VALIDATION_ERROR',headers=h,body=valid_minimal()|{'start_date':'2027-05-05','end_date':'2027-05-04'})
    elif n==16:
        for updates in ({'expected_hours':0},{'applicant_limit':0},{'compensation_amount':-1}):
            status_error(api,'POST',OPPS,422,'VALIDATION_ERROR',headers=h,body=valid_minimal()|updates)
    elif n==17:
        for updates in ({'work_mode':'office-only'},{'compensation_type':'cryptocurrency'},{'application_deadline':'2027-04-01T10:00:00'}):
            status_error(api,'POST',OPPS,422,'VALIDATION_ERROR',headers=h,body=valid_minimal()|updates)
    elif n==18:
        for updates in ({'organization_id':3},{'status':'open'},{'published_at':'2027-01-01T00:00:00Z'}):
            status_error(api,'POST',OPPS,422,'VALIDATION_ERROR',headers=h,body=valid_minimal()|updates)
    else:raise AssertionError('Unknown CREATE case '+case_id)


def signin_raw(api,email):
    from .conftest import DEV_PASSWORD
    body=expect(api.post('/api/v1/auth/login',json={'email':email,'password':DEV_PASSWORD}),200)
    return {'Authorization':'Bearer '+body['access_token']}


@pytest.mark.parametrize('case_id',parameters('PATCH-'))
def test_patch_opportunity(case_id,api):
    n=int(case_id.split('-')[-1]);h=signin(api)
    draft_id=new_draft(api,h,valid_complete())
    path=f'{OPPS}/{draft_id}'
    if n==1:
        before=expect(api.get(path,headers=h),200)
        after=expect(api.patch(path,json={'title':'Approved QA Updated Title'},headers=h),200)
        assert after['title']=='Approved QA Updated Title' and after['status']=='draft'
        for field in ('description','category','skills','requirements','start_date','end_date','compensation_type','expected_hours'):
            assert after[field]==before[field],field
        assert expect(api.get(path,headers=h),200)['title']==after['title']
    elif n==2:
        updates={'description':'Updated description by QA','expected_hours':14,'work_mode':'hybrid'}
        result=expect(api.patch(path,json=updates,headers=h),200)
        assert all(result[k]==v for k,v in updates.items())
        assert expect(api.get(path,headers=h),200)['expected_hours']==14
    elif n==3:
        result=expect(api.patch(path,json={'category':'knowledge','skills':['data-entry','spreadsheets']},headers=h),200)
        assert result['category']['code']=='knowledge'
        assert [s['code'] for s in result['skills']]==['data-entry','spreadsheets']
    elif n==4:status_error(api,'PATCH',path,401,'AUTH_REQUIRED',body={'title':'Unauthorized edit'})
    elif n==5:status_error(api,'PATCH',path,403,'ROLE_FORBIDDEN',headers=signin(api,'contributor'),body={'title':'Unauthorized edit'})
    elif n==6:
        status_error(api,'PATCH',path,404,'OPPORTUNITY_NOT_FOUND',headers=signin(api,'other_creator'),body={'title':'Unauthorized edit'})
    elif n==7:
        expect(api.post(path+'/publish',headers=h),200)
        status_error(api,'PATCH',path,409,'OPPORTUNITY_NOT_DRAFT',headers=h,body={'title':'Bad edit'})
        assert expect(api.get(path,headers=h),200)['title']!='Bad edit'
    elif n==8:status_error(api,'PATCH',f'{OPPS}/999999',404,'OPPORTUNITY_NOT_FOUND',headers=h,body={'title':'Missing record'})
    elif n==9:status_error(api,'PATCH',path,422,'VALIDATION_ERROR',headers=h,body={'title':None})
    elif n==10:
        error=status_error(api,'PATCH',path,422,'INVALID_DATES',headers=h,body={'end_date':'2027-02-28'})
        assert expect(api.get(path,headers=h),200)['end_date']=='2027-03-20'
    else:raise AssertionError('Unknown PATCH case '+case_id)


@pytest.mark.parametrize('case_id',parameters('PUB-'))
def test_publish_opportunity(case_id,api):
    n=int(case_id.split('-')[-1]);h=signin(api)
    if n in (1,4,5,9):
        body=valid_complete()
        if n==4:body.update(compensation_type='unpaid',compensation_amount=None)
        if n==5:body['application_deadline']='2026-10-01T00:00:00Z'
        draft_id=new_draft(api,h,body)
    else:
        draft_id=14
    path=f'{OPPS}/{draft_id}/publish'
    if n==1:
        response=expect(api.post(path,headers=h),200)
        assert response['status']=='open' and response['published_at']
        assert expect(api.get(f'{OPPS}/{draft_id}'),200)['status']=='open'
        assert draft_id in ids(page(api.get(OPPS,params={'limit':100}))['items'])
    elif n==2:
        error=status_error(api,'POST',path,422,'OPPORTUNITY_INCOMPLETE',headers=h)
        assert error['error']['details']['missing_fields']
        assert_draft_still(api,draft_id,h)
    elif n==3:
        for kind in ('paid','stipend'):
            i=new_draft(api,h,valid_complete(compensation_type=kind,compensation_amount=None))
            err=status_error(api,'POST',f'{OPPS}/{i}/publish',422,'OPPORTUNITY_INCOMPLETE',headers=h)
            assert 'compensation_amount' in err['error']['details']['missing_fields']
    elif n==4:
        b=expect(api.post(path,headers=h),200)
        assert b['status']=='open' and b['compensation_type']=='unpaid' and b['compensation_amount'] is None
    elif n==5:
        status_error(api,'POST',path,422,'DEADLINE_PASSED',headers=h)
        assert_draft_still(api,draft_id,h)
    elif n==6:status_error(api,'POST',path,401,'AUTH_REQUIRED')
    elif n==7:
        for role in ('contributor','admin'):
            status_error(api,'POST',path,403,'ROLE_FORBIDDEN',headers=signin(api,role))
    elif n==8:status_error(api,'POST',path,404,'OPPORTUNITY_NOT_FOUND',headers=signin(api,'other_creator'))
    elif n==9:
        assert expect(api.post(path,headers=h),200)['status']=='open'
        status_error(api,'POST',path,409,'OPPORTUNITY_NOT_DRAFT',headers=h)
    elif n==10:status_error(api,'POST',f'{OPPS}/999999/publish',404,'OPPORTUNITY_NOT_FOUND',headers=h)
    else:raise AssertionError('Unknown PUB case '+case_id)
