"""Browse Opportunities: all 61 approved cases, HTTP-only assertions."""
from __future__ import annotations
from datetime import datetime
import pytest
from .conftest import OPPS,expect,page,parameters,signin,ids,require_opportunity_shape

PUBLIC={1,2,3,4,5,6,7,8,9,12,13}

def listing(api,params=None,headers=None):
    return page(api.get(OPPS,params=params,headers=headers),limit=(dict(params).get('limit') if isinstance(params,dict) and 'limit' in params else None))

def items(api,params=None,headers=None): return listing(api,params,headers)['items']

def only(items,field,value):
    assert items, f'No fixture rows matched requested {field}={value}'
    assert all(it[field]==value for it in items), [(it['opportunity_id'],it[field]) for it in items]

def stamp(s):
    return datetime.fromisoformat(s.replace('Z','+00:00'))

def key_fn(it,sort):
    if sort in ('deadline','-deadline'):return stamp(it['application_deadline'])
    if sort in ('newest','oldest'):return stamp(it['published_at'] or it['created_at'])
    if sort in ('hours','-hours'):return it['expected_hours']
    if sort in ('compensation','-compensation'):return it['compensation_amount'] or 0
    if sort=='title':return it['title'].lower()
    raise AssertionError(sort)

def ordered(seq,sort):
    vals=[key_fn(it,sort) for it in seq]
    assert vals==sorted(vals,reverse=sort in ('-deadline','newest','-hours','-compensation')), vals


def invalid(api,**kwargs):
    return expect(api.get(OPPS,params=kwargs),422,'VALIDATION_ERROR')


@pytest.mark.parametrize('case_id',parameters('OPP-LIST-'))
def test_browse_opportunities(case_id,api):
    n=int(case_id.split('-')[-1])
    if n==1:
        p=listing(api)
        assert p['total']==11 and p['limit']==20 and p['offset']==0
    elif n==2:assert set(ids(listing(api)['items']))==PUBLIC
    elif n==3:
        baseline=ids(items(api))
        for role in ('creator','contributor','admin'):
            assert ids(items(api,headers=signin(api,role)))==baseline
    elif n==4:
        p=listing(api,{'limit':100})
        assert set(ids(p['items']))==PUBLIC
        assert all(it['status']=='open' for it in p['items'])
    elif n==5:
        got=items(api,{'limit':100})
        assert 10 not in ids(got)
        assert all(stamp(it['application_deadline'])>stamp('2026-10-16T12:00:00Z') for it in got)
    elif n==6:
        p=listing(api);assert p['items']
        for it in p['items']: require_opportunity_shape(it)
    elif n==7:
        got=items(api,{'q':'inventory spreadsheet'})
        assert 2 in ids(got) and all('inventory spreadsheet' in it['title'].lower() or 'inventory spreadsheet' in it['description'].lower() or 'inventory spreadsheet' in it['organization']['name'].lower() for it in got)
    elif n==8:
        got=items(api,{'q':'handwritten recipe'})
        assert 1 in ids(got) and all('handwritten recipe' in ' '.join((it['description'],it['title'],it['organization']['name'])).lower() for it in got)
    elif n==9:
        got=items(api,{'q':'food bank'})
        assert set(ids(got))=={5,6,7}
    elif n==10:
        assert ids(items(api,{'q':'SPREADSHEET'}))==ids(items(api,{'q':'spreadsheet'}))
        assert ids(items(api,{'q':'spreadsheet'}))
    elif n==11:
        assert ids(items(api,{'q':'spread'}))==ids(items(api,{'q':'SPREAD'}))
        assert items(api,{'q':'spread'})
    elif n in (12,13):
        symbol='%' if n==12 else '_'
        assert listing(api,{'q':symbol})['total']==0
    elif n==14:
        got=items(api,{'category':'knowledge'})
        assert got and all(it['category']['code']=='knowledge' for it in got)
    elif n==15:assert listing(api,{'category':'not-a-category'})['total']==0
    elif n==16:
        got=items(api,{'skill':['inventory']}); assert got
        assert all('inventory' in [s['code'] for s in it['skills']] for it in got)
    elif n==17:
        got=items(api,[('skill','photography'),('skill','translation')])
        assert set(ids(got))=={3,7,12}
        assert all({'photography','translation'} & {s['code'] for s in it['skills']} for it in got)
    elif n==18:
        got=items(api,[('skill','photography'),('skill','photography')]); assert got
        assert len(ids(got))==len(set(ids(got)))
        assert ids(got)==ids(items(api,{'skill':'photography'}))
    elif n==19: assert listing(api,{'skill':'this-is-not-a-skill'})['total']==0
    elif n in (20,21,22):
        mode={20:'remote',21:'on_site',22:'hybrid'}[n]
        only(items(api,{'work_mode':mode}),'work_mode',mode)
    elif n==23:
        for compensation in ('paid','stipend','unpaid'):
            only(items(api,{'compensation_type':compensation}),'compensation_type',compensation)
    elif n==24:
        got=items(api,{'organization_id':1}); assert got
        assert all(it['organization']['organization_id']==1 for it in got)
    elif n==25:
        got=items(api,{'min_hours':20});assert got
        assert all(it['expected_hours']>=20 for it in got)
    elif n==26:
        got=items(api,{'max_hours':15});assert got
        assert all(it['expected_hours']<=15 for it in got)
    elif n==27:
        got=items(api,{'min_hours':20,'max_hours':25});assert got
        assert all(20<=it['expected_hours']<=25 for it in got)
    elif n==28:invalid(api,min_hours=30,max_hours=15)
    elif n==29:
        deadline='2026-11-13T00:00:00Z';got=items(api,{'deadline_before':deadline})
        assert got and all(stamp(it['application_deadline'])<stamp(deadline) for it in got)
    elif n==30:
        a=ids(items(api,{'deadline_before':'2026-11-13T00:00:00Z'}))
        b=ids(items(api,{'deadline_before':'2026-11-12T17:00:00-07:00'}))
        assert a==b and a
    elif n==31:
        p=listing(api,{'q':'unfindable-query-119922','limit':1})
        assert p['items']==[] and p['total']==0
    elif 32<=n<=40:
        sorts={32:'deadline',33:'-deadline',34:'newest',35:'oldest',36:'hours',37:'-hours',38:'compensation',39:'-compensation',40:'title'}
        sort=sorts[n];got=items(api,{'sort':sort,'limit':100})
        assert len(got)==11
        ordered(got,sort)
        # Sorting ties are resolved by ascending opportunity_id.
        for a,b in zip(got,got[1:]):
            if key_fn(a,sort)==key_fn(b,sort):assert a['opportunity_id']<b['opportunity_id']
    elif n==41:assert listing(api)['limit']==20
    elif n==42:assert listing(api)['offset']==0
    elif n==43:
        p=listing(api,{'limit':1});assert len(p['items'])==1 and p['limit']==1
    elif n==44:
        p=listing(api,{'limit':100});assert len(p['items'])==11 and p['limit']==100
    elif n==45:
        a=listing(api,{'limit':4,'offset':0});b=listing(api,{'limit':4,'offset':4})
        assert a['total']==b['total']==11 and len(a['items'])==len(b['items'])==4
        assert set(ids(a['items'])).isdisjoint(ids(b['items']))
    elif n==46:
        p=listing(api,{'offset':999})
        assert p['items']==[] and p['total']==11 and p['offset']==999
    elif n==47:
        a=items(api,{'sort':'-hours','limit':100});b=items(api,{'sort':'-hours','limit':100})
        assert ids(a)==ids(b)
        ties=[(x,y) for x,y in zip(a,a[1:]) if x['expected_hours']==y['expected_hours']]
        assert ties, 'Need at least one equal-hours fixture pair'
        assert all(x['opportunity_id']<y['opportunity_id'] for x,y in ties)
    elif n==48:invalid(api,limit=0)
    elif n==49:invalid(api,limit=101)
    elif n==50:invalid(api,offset=-1)
    elif n==51:invalid(api,q='')
    elif n==52:invalid(api,q='z'*101)
    elif n==53:invalid(api,work_mode='not-supported')
    elif n==54:invalid(api,compensation_type='crypto')
    elif n==55:invalid(api,sort='random')
    elif n==56:invalid(api,organization_id=0)
    elif n==57:invalid(api,deadline_before='2026-11-13T00:00:00')
    elif n==58:
        for name in ('min_hours','max_hours'): invalid(api,**{name:-1})
    elif n==59:
        p=listing(api,{'category':'knowledge','skill':'spreadsheets','work_mode':'remote'})
        assert p['items']
        for it in p['items']:
            assert it['category']['code']=='knowledge' and it['work_mode']=='remote'
            assert 'spreadsheets' in {s['code'] for s in it['skills']}
    elif n==60:
        cutoff='2026-12-01T00:00:00Z'
        p=listing(api,{'compensation_type':'paid','min_hours':10,'max_hours':25,'deadline_before':cutoff})
        assert p['items']
        for it in p['items']:
            assert it['compensation_type']=='paid' and 10<=it['expected_hours']<=25
            assert stamp(it['application_deadline'])<stamp(cutoff)
    elif n==61:
        params={'q':'spreadsheet','category':'knowledge','sort':'title','limit':1,'offset':0}
        p=listing(api,params)
        assert p['total']>=1 and len(p['items'])==1 and p['limit']==1 and p['offset']==0
        for it in p['items']:
            assert it['category']['code']=='knowledge'
            assert 'spreadsheet' in ' '.join((it['title'],it['description'],it['organization']['name'])).lower()
    else:raise AssertionError('Unhandled OPP-LIST case '+case_id)
