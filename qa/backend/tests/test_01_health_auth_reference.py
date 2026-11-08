"""Approved HLTH / AUTH / ME / CAT / SKL cases. One collected test per approved ID."""
from __future__ import annotations
from datetime import UTC, datetime, timedelta
import json

import jwt
import pytest

from app.core.config import JWT_ALGORITHM, get_api_settings
from .conftest import (DEV_PASSWORD, EMAILS, expect, invalid_jwt, parameters, signin)

LOGIN='/api/v1/auth/login'
ME='/api/v1/auth/me'


def token_for(sub='2', role='creator', *, secret=None, alg='HS256', overrides=None):
    now=datetime.now(UTC)
    claims={'sub':sub, 'role':role, 'iat':now, 'exp':now+timedelta(minutes=20)}
    if overrides:
        for k,v in overrides.items():
            if v is None: claims.pop(k,None)
            else: claims[k]=v
    key=secret or get_api_settings().effective_jwt_secret
    return jwt.encode(claims,key,algorithm=alg)


def bearer(token): return {'Authorization': 'Bearer '+token}


def login(api, email=None, password=DEV_PASSWORD, **fields):
    body={'email':EMAILS['creator'] if email is None else email,'password':password}
    body.update(fields)
    return api.post(LOGIN,json=body)


@pytest.mark.parametrize('case_id',parameters('HLTH-'))
def test_health(case_id,api):
    # The five approved dependency-failure cases carry explicit pytest.skip marks in catalog.
    if case_id in ('HLTH-001','HLTH-006','HLTH-007'):
        r=api.get('/health'); b=r.json()
        assert r.status_code in (200,503) if case_id=='HLTH-006' else r.status_code==200, r.text
        assert b['status'] in ('ok','degraded')
        assert set(b['checks'])=={'mysql','rabbitmq'}
        assert set(b['checks'].values()) <= {'ok','unavailable'}
        if case_id!='HLTH-006': assert b=={'status':'ok','checks':{'mysql':'ok','rabbitmq':'ok'}}
    elif case_id=='HLTH-008':
        r=api.get('/health',headers={'X-Request-ID':'qa-approved-request-123'})
        expect(r,200)
        assert r.headers['X-Request-ID']=='qa-approved-request-123'
    elif case_id=='HLTH-009':
        r=api.get('/health',headers={'X-Request-ID':'x'*65})
        expect(r,200)
        assert r.headers['X-Request-ID']!='x'*65
        assert 0<len(r.headers['X-Request-ID'])<=64
    else: raise AssertionError('Unimplemented nondeferred health case: '+case_id)


@pytest.mark.parametrize('case_id',parameters('AUTH-'))
def test_login(case_id,api,seeded_db):
    n=int(case_id.split('-')[-1])
    if n in (1,2,3):
        roles={1:'creator',2:'contributor',3:'admin'};role=roles[n]
        b=expect(login(api,EMAILS[role]),200)
        assert b['user']['role']==role and b['user']['email']==EMAILS[role]
        assert jwt.decode(b['access_token'],get_api_settings().effective_jwt_secret,algorithms=[JWT_ALGORITHM])['sub']==str(b['user']['user_id'])
    elif n in (4,5):
        email=EMAILS['creator'].upper() if n==4 else '  '+EMAILS['creator']+'  '
        b=expect(login(api,email),200)
        assert b['user']['email']==EMAILS['creator']
    elif n==6:
        b=expect(login(api),200)
        assert set(b)=={'access_token','token_type','expires_in','user'}
        assert isinstance(b['access_token'],str) and b['access_token']
        assert b['token_type']=='bearer' and isinstance(b['expires_in'],int) and b['expires_in']>0
        assert set(b['user'])=={'user_id','email','full_name','role'}
    elif n==7:
        a=expect(login(api),200); b=expect(login(api),200)
        for result in (a,b):
            assert jwt.decode(result['access_token'],get_api_settings().effective_jwt_secret,algorithms=[JWT_ALGORITHM])['sub']==str(result['user']['user_id'])
    elif n==8: expect(login(api,password='wrong-password'),401,'INVALID_CREDENTIALS')
    elif n==9: expect(login(api,email='not-registered@grow8.dev'),401,'INVALID_CREDENTIALS')
    elif n==10:
        # Test-data setup, not a database assertion. Only grow8_test is ever altered.
        with seeded_db.cursor() as cur: cur.execute('UPDATE user_account SET is_active=0 WHERE user_id=2')
        expect(login(api),401,'INVALID_CREDENTIALS')
    elif n==11: expect(login(api,password='grow8dev!2026'),401,'INVALID_CREDENTIALS')
    elif n==12: expect(login(api,password=' '+DEV_PASSWORD),401,'INVALID_CREDENTIALS')
    elif n==13: expect(login(api,email="' OR 1=1 --"),401,'INVALID_CREDENTIALS')
    elif n==14: expect(login(api,email='not-an-email'),401,'INVALID_CREDENTIALS')
    elif n==15:
        a=expect(login(api,password='invalid'),401,'INVALID_CREDENTIALS')
        b=expect(login(api,email='absent@grow8.dev'),401,'INVALID_CREDENTIALS')
        assert a==b
    elif n in (16,17,18):
        payload={'password':DEV_PASSWORD} if n==16 else {'email':EMAILS['creator']} if n==17 else {}
        expect(api.post(LOGIN,json=payload),422,'VALIDATION_ERROR')
    elif n==19: expect(login(api,email=''),422,'VALIDATION_ERROR')
    elif n==20: expect(login(api,password=''),422,'VALIDATION_ERROR')
    elif n==21: expect(login(api,email='ab'),422,'VALIDATION_ERROR')
    elif n==22: expect(login(api,email='a'*256),422,'VALIDATION_ERROR')
    elif n==23: expect(login(api,password='x'*129),422,'VALIDATION_ERROR')
    elif n==24:
        for field in ('email','password'):
            expect(login(api,**{field:None}),422,'VALIDATION_ERROR')
    elif n==25:
        for field in ('email','password'):
            for value in (42, [], {}):
                expect(login(api,**{field:value}),422,'VALIDATION_ERROR')
    elif n==26:
        # Raw malformed JSON with correct content type.
        r=api.request_raw('POST',LOGIN, content='{"email":',headers={'Content-Type':'application/json'})
        expect(r,422,'VALIDATION_ERROR')
    elif n==27:
        b=expect(login(api),200)
        c=jwt.decode(b['access_token'],get_api_settings().effective_jwt_secret,algorithms=[JWT_ALGORITHM],options={'require':['sub','role','iat','exp']})
        assert c['sub']==str(b['user']['user_id']) and c['role']=='creator'
        assert c['exp']-c['iat']==b['expires_in']
    elif n==28:
        r=login(api); b=expect(r,200)
        assert not (set(json.dumps(b).lower().split()) & {'password_hash','password','jwt_secret'})
        assert DEV_PASSWORD not in r.text
        assert get_api_settings().effective_jwt_secret not in r.text
        assert set(b['user'])=={'user_id','email','full_name','role'}
    else:raise AssertionError('Unhandled auth case '+case_id)


@pytest.mark.parametrize('case_id',parameters('ME-'))
def test_me(case_id,api,seeded_db):
    n=int(case_id.split('-')[-1])
    if n in (1,2,3):
        role={1:'creator',2:'contributor',3:'admin'}[n]
        b=expect(api.get(ME,headers=signin(api,role)),200)
        assert b['role']==role and b['email']==EMAILS[role]
    elif n==4:
        headers=signin(api); b=expect(api.get(ME,headers=headers),200)
        login_body=expect(login(api),200)
        assert b==login_body['user']
    elif n==5:
        h=signin(api); first=expect(api.get(ME,headers=h),200)
        for _ in range(3): assert expect(api.get(ME,headers=h),200)==first
    elif n==6:
        a=expect(api.get(ME,headers=signin(api,'creator')),200)
        b=expect(api.get(ME,headers=signin(api,'contributor')),200)
        assert a['user_id']!=b['user_id'] and a['role']=='creator' and b['role']=='contributor'
    elif n in (7,8,9,10):
        headers={7:{},8:{'Authorization':''},9:{'Authorization':'Basic abc123'},10:{'Authorization':'Bearer'}}[n]
        expect(api.get(ME,headers=headers),401,'AUTH_REQUIRED')
    elif n==11: expect(api.get(ME,headers=invalid_jwt()),401,'INVALID_TOKEN')
    elif n==12: expect(api.get(ME,headers=bearer(token_for(secret='different-secret'))),401,'INVALID_TOKEN')
    elif n==13:
        t=token_for(); seg=t.split('.'); seg[1]=('A' if seg[1][0]!='A' else 'B')+seg[1][1:]
        expect(api.get(ME,headers=bearer('.'.join(seg))),401,'INVALID_TOKEN')
    elif n==14:
        expect(api.get(ME,headers=bearer(token_for(overrides={'exp':datetime.now(UTC)-timedelta(minutes=1)}))),401,'INVALID_TOKEN')
    elif n in (15,16,17):
        missing={15:'sub',16:'role',17:'exp'}[n]
        expect(api.get(ME,headers=bearer(token_for(overrides={missing:None}))),401,'INVALID_TOKEN')
    elif n==18:expect(api.get(ME,headers=bearer(token_for(sub='not-an-integer'))),401,'INVALID_TOKEN')
    elif n==19:
        # HS384 is validly signed but unsupported by API HS256-only decoder.
        expect(api.get(ME,headers=bearer(token_for(alg='HS384'))),401,'INVALID_TOKEN')
    elif n==20:expect(api.get(ME,headers=bearer(token_for(sub='999999'))),401,'INVALID_TOKEN')
    elif n==21:
        h=signin(api)
        with seeded_db.cursor() as cur: cur.execute('UPDATE user_account SET is_active=0 WHERE user_id=2')
        expect(api.get(ME,headers=h),401,'INVALID_TOKEN')
    elif n==22:
        h=signin(api)
        with seeded_db.cursor() as cur: cur.execute("UPDATE user_account SET full_name='QA Updated Name' WHERE user_id=2")
        assert expect(api.get(ME,headers=h),200)['full_name']=='QA Updated Name'
    elif n==23:
        body=expect(api.get(ME,headers=bearer(token_for(role='admin'))),200)
        assert body['role']=='creator' and body['user_id']==2
    elif n==24:
        r=api.get(ME,headers=signin(api));b=expect(r,200)
        assert set(b)=={'user_id','email','full_name','role'}
        assert DEV_PASSWORD not in r.text and 'password_hash' not in r.text
    else:raise AssertionError('Unhandled me case '+case_id)


@pytest.mark.parametrize('case_id',parameters('CAT-'))
def test_categories(case_id,api):
    n=int(case_id.split('-')[-1]);url='/api/v1/categories'
    baseline=expect(api.get(url),200)
    if n in (1,2): assert isinstance(baseline,list) and {x['code'] for x in baseline}=={'community','knowledge'}
    elif n==3: assert expect(api.get(url,headers=signin(api,'creator')),200)==baseline
    elif n==4:
        for role in ('contributor','admin'):assert expect(api.get(url,headers=signin(api,role)),200)==baseline
    elif n==5:
        for _ in range(2):assert expect(api.get(url),200)==baseline
    elif n==6: assert isinstance(baseline,list) and all(isinstance(x,dict) for x in baseline)
    elif n==7:
        assert baseline
        for x in baseline:
            assert isinstance(x['code'],str) and isinstance(x['name'],str)
            assert isinstance(x['description'],(str,type(None)))
    elif n==8:assert [x['name'] for x in baseline]==sorted(x['name'] for x in baseline)
    elif n==9:assert baseline and all(set(x)=={'code','name','description'} for x in baseline)
    elif n==10:assert len({x['code'] for x in baseline})==len(baseline)
    else:raise AssertionError('Unhandled category case '+case_id)


@pytest.mark.parametrize('case_id',parameters('SKL-'))
def test_skills(case_id,api):
    n=int(case_id.split('-')[-1]);url='/api/v1/skills'
    baseline=expect(api.get(url),200)
    expected={'customer-service','data-cleaning','data-entry','event-setup','food-handling','graphic-design','inventory','photography','social-media','spreadsheets','translation','web-basics'}
    if n in (1,2):assert len(baseline)==12 and {x['code'] for x in baseline}==expected
    elif n==3:assert expect(api.get(url,headers=signin(api,'creator')),200)==baseline
    elif n==4:
        for role in ('contributor','admin'):assert expect(api.get(url,headers=signin(api,role)),200)==baseline
    elif n==5:
        for _ in range(2):assert expect(api.get(url),200)==baseline
    elif n==6:assert isinstance(baseline,list) and all(isinstance(x,dict) for x in baseline)
    elif n==7:assert baseline and all(set(x)=={'code','name'} and all(isinstance(v,str) and v for v in x.values()) for x in baseline)
    elif n==8:assert [x['name'] for x in baseline]==sorted(x['name'] for x in baseline)
    elif n==9:assert len({x['code'] for x in baseline})==len(baseline)
    elif n==10:
        assert len(baseline)==12 and {x['code'] for x in baseline}==expected
        assert next(x for x in baseline if x['code']=='web-basics')['name']=='Web basics (HTML/CSS)'
        assert all(set(x)=={'code','name'} for x in baseline)
    else:raise AssertionError('Unhandled skill case '+case_id)
