"""Approved notifications API tests: 36 case IDs across 4 endpoints."""
from __future__ import annotations
from datetime import datetime
import pytest
from .conftest import (NOTIFS,expect,page,parameters,signin,invalid_jwt,require_notification_shape)


@pytest.fixture
def inbox(seeded_db):
    """Only test-data setup. No direct database assertions or infrastructure tests.

    Alex (contributor): 3 unread + 1 previously read
    Sofia (creator): 1 unread
    Ada (admin): 1 unread
    """
    def add(user_id,title,at,read_at=None):
        with seeded_db.cursor() as cur:
            cur.execute(
                "INSERT INTO notification (user_id,event_id,notification_type,title,message,opportunity_id,read_at,created_at) "
                "VALUES (%s,UUID(),'opportunity_created',%s,'QA fixture notification',15,%s,%s)",
                (user_id,title,read_at,at)
            )
            return cur.lastrowid
    return {
        'oldest':add(5,'oldest','2026-10-10 09:00:00'),
        'read':add(5,'read','2026-10-11 09:00:00','2026-10-11 10:00:00'),
        'middle':add(5,'middle','2026-10-12 09:00:00'),
        'newest':add(5,'newest','2026-10-13 09:00:00'),
        'sofia':add(4,'sofia','2026-10-13 09:00:00'),
        'admin':add(1,'admin','2026-10-13 09:00:00'),
    }


def listing(api,headers,params=None):return page(api.get(NOTIFS,headers=headers,params=params))

def titles(items):return [it['title'] for it in items]

def count(api,headers):
    body=expect(api.get(NOTIFS+'/unread-count',headers=headers),200)
    assert set(body)=={'unread_count'} and isinstance(body['unread_count'],int) and body['unread_count']>=0
    return body['unread_count']

def mark(api,headers,notification_id):return api.patch(f'{NOTIFS}/{notification_id}/read',headers=headers)


def error(api,method,path,status,code,headers=None,params=None):
    return expect(api.request_raw(method,path,headers=headers,params=params),status,code)


@pytest.mark.parametrize('case_id',parameters('NOTIF-'))
def test_list_notifications(case_id,api,inbox):
    n=int(case_id.split('-')[-1]); h=signin(api,'contributor')
    if n==1:
        p=listing(api,h)
        assert p['total']==4 and p['limit']==20 and p['offset']==0
        assert titles(p['items'])==['newest','middle','read','oldest']
        for row in p['items']:require_notification_shape(row)
        assert len([x for x in p['items'] if x['is_read']])==1
    elif n==2:
        for role,expected in [('other_creator','sofia'),('admin','admin')]:
            b=listing(api,signin(api,role))
            assert titles(b['items'])==[expected]
    elif n==3:error(api,'GET',NOTIFS,401,'AUTH_REQUIRED')
    elif n==4:
        error(api,'GET',NOTIFS,401,'INVALID_TOKEN',invalid_jwt())
    elif n==5:
        alex=listing(api,h);sofia=listing(api,signin(api,'other_creator'))
        assert set(titles(alex['items']))=={'oldest','read','middle','newest'}
        assert titles(sofia['items'])==['sofia']
        assert {x['notification_id'] for x in alex['items']}.isdisjoint(x['notification_id'] for x in sofia['items'])
    elif n==6:
        p=listing(api,h,{'unread_only':'true'})
        assert p['total']==3 and titles(p['items'])==['newest','middle','oldest']
        assert all(not it['is_read'] and it['read_at'] is None for it in p['items'])
    elif n==7:
        p=listing(api,h)
        dates=[datetime.fromisoformat(it['created_at'].replace('Z','+00:00')) for it in p['items']]
        assert dates==sorted(dates,reverse=True)
        for a,b in zip(p['items'],p['items'][1:]):
            if a['created_at']==b['created_at']: assert a['notification_id']>b['notification_id']
    elif n==8:
        p=listing(api,h,{'limit':2,'offset':2})
        assert titles(p['items'])==['read','oldest']
        assert p['total']==4 and p['limit']==2 and p['offset']==2
    elif n==9:
        p=listing(api,signin(api,'creator'))
        assert p=={'items':[],'total':0,'limit':20,'offset':0}
    elif n==10:
        for params in ({'limit':0},{'limit':101},{'offset':-1}):
            error(api,'GET',NOTIFS,422,'VALIDATION_ERROR',headers=h,params=params)
    else:raise AssertionError('Unknown NOTIF case '+case_id)


@pytest.mark.parametrize('case_id',parameters('UCNT-'))
def test_unread_count(case_id,api,inbox):
    n=int(case_id.split('-')[-1]);h=signin(api,'contributor')
    if n==1:assert count(api,h)==3
    elif n==2:assert count(api,signin(api,'creator'))==0
    elif n==3:
        p=listing(api,h)
        assert len(p['items'])==4 and sum(not it['is_read'] for it in p['items'])==count(api,h)==3
    elif n==4:
        assert count(api,signin(api,'other_creator'))==1
        assert count(api,signin(api,'admin'))==1
    elif n==5:error(api,'GET',NOTIFS+'/unread-count',401,'AUTH_REQUIRED')
    elif n==6:error(api,'GET',NOTIFS+'/unread-count',401,'INVALID_TOKEN',invalid_jwt())
    elif n==7:
        assert count(api,h)==3 and count(api,signin(api,'other_creator'))==1
    elif n==8:
        before=count(api,h)
        assert expect(mark(api,h,inbox['middle']),200)['is_read']
        assert count(api,h)==before-1
    else:raise AssertionError('Unknown UCNT case '+case_id)


@pytest.mark.parametrize('case_id',parameters('READ-'))
def test_mark_notification_read(case_id,api,inbox):
    n=int(case_id.split('-')[-1]);h=signin(api,'contributor')
    if n==1:
        obj=expect(mark(api,h,inbox['newest']),200)
        require_notification_shape(obj)
        assert obj['notification_id']==inbox['newest'] and obj['is_read'] and obj['read_at'] is not None
    elif n==2:
        for role,key in (('contributor','newest'),('other_creator','sofia'),('admin','admin')):
            obj=expect(mark(api,signin(api,role),inbox[key]),200)
            assert obj['notification_id']==inbox[key] and obj['is_read']
        assert count(api,h)==2
        assert count(api,signin(api,'other_creator'))==0
        assert count(api,signin(api,'admin'))==0
    elif n==3:
        a=expect(mark(api,h,inbox['newest']),200)
        b=expect(mark(api,h,inbox['newest']),200)
        assert a['read_at']==b['read_at'] and a['read_at'] is not None
        assert count(api,h)==2
    elif n==4:
        obj=expect(mark(api,h,inbox['read']),200)
        assert obj['read_at']=='2026-10-11T10:00:00Z'
    elif n==5:
        before=count(api,h)
        expect(mark(api,h,inbox['middle']),200)
        assert count(api,h)==before-1
        p=listing(api,h)
        assert sum(not x['is_read'] for x in p['items'])==2
    elif n==6:error(api,'PATCH',f"{NOTIFS}/{inbox['newest']}/read",401,'AUTH_REQUIRED')
    elif n==7:error(api,'PATCH',f"{NOTIFS}/{inbox['newest']}/read",401,'INVALID_TOKEN',invalid_jwt())
    elif n==8:
        other=signin(api,'other_creator');before=count(api,other)
        error(api,'PATCH',f"{NOTIFS}/{inbox['sofia']}/read",404,'NOTIFICATION_NOT_FOUND',h)
        assert count(api,other)==before
    elif n==9:error(api,'PATCH',f'{NOTIFS}/999999/read',404,'NOTIFICATION_NOT_FOUND',h)
    elif n==10:
        for value in ('0','abc'):
            error(api,'PATCH',f'{NOTIFS}/{value}/read',422,'VALIDATION_ERROR',h)
    else:raise AssertionError('Unknown READ case '+case_id)


@pytest.mark.parametrize('case_id',parameters('ALLREAD-'))
def test_mark_all_read(case_id,api,inbox):
    n=int(case_id.split('-')[-1]);h=signin(api,'contributor')
    path=NOTIFS+'/read-all'
    if n==1:
        result=expect(api.post(path,headers=h),200)
        assert result=={'marked_read':3} and count(api,h)==0
    elif n==2:
        creator=signin(api,'creator');result=expect(api.post(path,headers=creator),200)
        assert result=={'marked_read':0} and count(api,creator)==0
    elif n==3:
        before=next(x for x in listing(api,h)['items'] if x['title']=='read')['read_at']
        result=expect(api.post(path,headers=h),200)
        after=listing(api,h)['items']
        assert result=={'marked_read':3} and all(x['is_read'] for x in after)
        assert next(x for x in after if x['title']=='read')['read_at']==before
    elif n==4:
        assert expect(api.post(path,headers=h),200)=={'marked_read':3}
        assert expect(api.post(path,headers=h),200)=={'marked_read':0}
        assert count(api,h)==0
    elif n==5:
        other=signin(api,'other_creator')
        other_before=listing(api,other)
        assert expect(api.post(path,headers=h),200)=={'marked_read':3}
        assert count(api,h)==0
        assert count(api,other)==1 and listing(api,other)==other_before
    elif n==6:
        for role,expected in [('contributor',3),('other_creator',1),('admin',1)]:
            headers=signin(api,role)
            assert expect(api.post(path,headers=headers),200)=={'marked_read':expected}
            assert count(api,headers)==0
    elif n==7:error(api,'POST',path,401,'AUTH_REQUIRED')
    elif n==8:error(api,'POST',path,401,'INVALID_TOKEN',invalid_jwt())
    else:raise AssertionError('Unknown ALLREAD case '+case_id)
