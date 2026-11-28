"""ENSF 608 SQL-077..126; isolated independent run; merges the unchanged prior 76 results.
Requires the existing, corrected run_sql_tests.py and its catalog in the same folder.
"""
from __future__ import annotations
import argparse, csv, datetime as dt, hashlib, io, json, pathlib, re, secrets, sys, threading, time, zipfile
from collections import Counter
import run_sql_tests as base
HERE=pathlib.Path(__file__).resolve().parent
CASES=json.loads((HERE/'extended_cases.json').read_text(encoding='utf8'))
FIELDS=['Test ID','Source block','Actual result','Status','Evidence','Seconds']

def baseline_archive(path):
    with zipfile.ZipFile(path) as z:
        names={pathlib.PurePosixPath(n).name:n for n in z.namelist() if not n.endswith('/')}
        read=lambda n:z.read(names[n])
        meta=json.loads(read('run-metadata.json'))
        rows=list(csv.DictReader(io.StringIO(read('case-results.csv').decode('utf-8-sig'))))
        if [r['Test ID'] for r in rows]!=[f'SQL-{i:03}' for i in range(1,77)] or any(r['Status']!='Pass' for r in rows): raise ValueError('Baseline must contain the original 76 passing cases in ID order')
        if meta['source_blob_hashes']!=base.SOURCE_FILES: raise ValueError('Prior evidence source differs from current reviewed version')
        if meta.get('counts')!={'Pass':76} or meta.get('blocker'): raise ValueError('Baseline metadata not a completed passing run')
        evidence={r['Test ID']:read(r['Test ID']+'.html') for r in rows}
        for r in rows:
            if r['Evidence']!='Evidence/'+r['Test ID']+'.html' or b'<html' not in evidence[r['Test ID']]: raise ValueError('Invalid baseline evidence link')
        return rows,meta,evidence,read('ENSF608_SQL_Test_Results.xlsx'),read('grow8_operations_by_category.sql')

def verify_catalog():
    assert [c['id'] for c in CASES]==[f'SQL-{i:03}' for i in range(77,127)]
    for c in CASES:
        assert c['requirements'] and c['purpose'] and c['expected']
        assert bool(c['steps']) != bool(c.get('special'))
        for s in c['steps']:
            assert not re.match(r'\s*(DROP|TRUNCATE|ALTER|CREATE|COMMIT|USE)\b',s['sql'],re.I),s
            assert not ('rows' in s and 'error' in s)
    assert sum(c.get('special')=='capacity_race' for c in CASES)==1

def check_step(entry, step):
    e=entry['error']; want=step.get('error')
    if want:
        return (bool(e and e['code']==want[0] and want[1].lower() in e['message'].lower()), f"expected error {want[0]} ({want[1]}); observed {e}")
    if e: return False,'Unexpected SQL error: '+str(e)
    if 'rows' in step:
        actual=[r for t in entry['tables'] for r in t['rows']]
        return (len(entry['tables'])==1 and actual==step['rows'],f"Expected {step['rows']}; actual {actual}")
    if 'affected' in step: return entry['affected_rows']==step['affected'],f"Expected affected {step['affected']}; actual {entry['affected_rows']}"
    return True,'Statement succeeded'

def clock(conn):
    with conn.cursor() as cur:
        cur.execute("SET time_zone='+00:00'"); cur.execute('SET timestamp=UNIX_TIMESTAMP(%s)',(base.FIXED_UTC,)); cur.execute("SET SESSION innodb_lock_wait_timeout=12"); cur.execute("SET SESSION sql_mode='STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION'")

def race(connect,conn,db_error):
    # Opportunity 6 is a seeded two-place opportunity with zero applications.
    # Commit a single fixture on the disposable database, then race for the final place.
    entries=[]; extra={}; a=b=None; worker=None; result={}; started=threading.Event(); done=threading.Event(); fixture=False
    def execute(c,sql):
        item=base.execute(c,sql,db_error); entries.append(item)
        if item['error']: raise RuntimeError(str(item['error']))
        return item
    try:
        start=execute(conn,'SELECT applicant_limit,(SELECT COUNT(*) FROM application WHERE opportunity_id=6) AS application_count FROM opportunity WHERE opportunity_id=6')
        if start['tables'][0]['rows']!=[['2','0']]: raise RuntimeError('Race fixture is not the reviewed seed state')
        execute(conn,'INSERT INTO application(opportunity_id,contributor_id) VALUES(6,5)'); fixture=True
        a=connect(); b=connect(); clock(a); clock(b)
        execute(a,'START TRANSACTION'); execute(a,'INSERT INTO application(opportunity_id,contributor_id) VALUES(6,6)')
        def contender():
            try:
                # Explicit transaction; no auto-commit until successful insertion.
                with b.cursor() as cur: cur.execute('START TRANSACTION')
                started.set(); result['entry']=base.execute(b,'INSERT INTO application(opportunity_id,contributor_id) VALUES(6,7)',db_error)
                if not result['entry']['error']: b.commit()
                else: b.rollback()
            except Exception as ex: result['exception']=str(ex)
            finally: done.set()
        worker=threading.Thread(target=contender,daemon=True); worker.start()
        if not started.wait(5): raise RuntimeError('Contender did not start')
        waited=not done.wait(0.7); extra['contender_not_finished_before_commit']=waited
        execute(a,'COMMIT');
        if not done.wait(20): raise RuntimeError('Contender did not finish after commit')
        if 'exception' in result: raise RuntimeError(result['exception'])
        entry=result['entry']; entries.append(entry); e=entry['error']; extra['contender_error']=e
        last=execute(conn,"SELECT COUNT(*) AS active_applications, SUM(contributor_id=6) AS winner, SUM(contributor_id=7) AS loser FROM application WHERE opportunity_id=6 AND contributor_id IN (6,7) AND status IN ('pending','accepted')")
        total=execute(conn,"SELECT COUNT(*) AS all_active FROM application WHERE opportunity_id=6 AND status IN ('pending','accepted')")
        ok=waited and bool(e and e['code']==1644 and 'applicant_limit_reached' in e['message']) and last['tables'][0]['rows']==[['1','1','0']] and total['tables'][0]['rows']==[['2']]
        return ok, 'First contender committed, second rejected; exactly one new active application' if ok else 'Concurrency assertion failed', entries,extra
    finally:
        if a:
            try:a.rollback()
            finally:a.close()
        if worker:worker.join(timeout=15)
        if b:b.close()
        if fixture:
            cleanup=base.execute(conn,'DELETE FROM application WHERE opportunity_id=6 AND contributor_id IN (5,6,7)',db_error); entries.append(cleanup)
            if cleanup['error']:raise RuntimeError('Race cleanup failed: '+str(cleanup['error']))

def export(out, prior, new, meta):
    from openpyxl import load_workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from copy import copy
    rows,oldmeta,files,book,sql=prior
    for k,v in files.items():(out/'Evidence'/(k+'.html')).write_bytes(v)
    (out/'grow8_operations_by_category.sql').write_bytes(sql)
    allrows=rows+new
    with (out/'case-results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(allrows)
    (out/'run-metadata.json').write_text(json.dumps({'baseline_run':oldmeta,'extension_run':meta,'combined_counts':dict(Counter(r['Status'] for r in allrows)),'note':'Combined results from two separate executions; original evidence unchanged.'},indent=2),encoding='utf8')
    wb=load_workbook(io.BytesIO(book));ws=wb['SQL Tests']; lookup={r['Test ID']:r for r in allrows}
    for c,r in zip(CASES,new):
        row=[c['id'],c['ref'],c['category'],c['purpose'],c['expected'],r['Actual result'],r['Status'],r['Evidence'],r['Seconds']];ws.append(row);i=ws.max_row
        for j in range(1,10):
            ws.cell(i,j)._style=copy(ws.cell(80,j)._style);ws.cell(i,j).alignment=Alignment(wrap_text=True,vertical='top')
        ws.row_dimensions[i].height=76
        ws.cell(i,7).fill=PatternFill('solid',fgColor={'Pass':'D9EAD3','Fail':'F4CCCC','Not run':'FFF2CC'}[r['Status']]);
        if r['Evidence']:ws.cell(i,8).hyperlink=r['Evidence'];ws.cell(i,8).style='Hyperlink'
    ws['A2']='ENSF 608 · Group 2 · 76 historical + 50 extension checks';ws['A3']='Separate executions; original evidence retained. New checks use rollback isolation.';ws.auto_filter.ref='A4:I130'
    su=wb['Test Summary'];su['A3']='Combined evidence from two separate runs; not a single uninterrupted 126-test execution.';su['A4']='Baseline run';su['B4']=oldmeta['executed_at'];su['A5']='Extension run';su['B5']=meta['executed_at'];su['A29']='76 baseline tests + 50 extension tests. SQL rubric counts remain 25; requirement coverage is not identical to pass rate.'
    for i in range(8,12):su.cell(i,2).value=su.cell(i,2).value.replace('80','130')
    su['A12']='Pass / total inventory'
    # Conservative RTM: previous coverage conclusions remain historical; new execution counts are separate.
    original=load_workbook(HERE/'baseline_rtm.xlsx',data_only=True)['RTM'];rtm=wb.create_sheet('RTM');rtm.append(['Requirement','Feature','Requirement statement','Original test IDs','Baseline assessment','New SQL IDs','Extension outcome','Extension checks / remaining review'])
    for row in list(original.values)[4:]:
        rid=row[0];mapped=[c for c in CASES if rid in c['requirements']];ids=[c['id'] for c in mapped];cnt=Counter(lookup[i]['Status'] for i in ids)
        rtm.append([rid,row[1],row[2],row[3],row[4],', '.join(ids) or '—',', '.join(f'{v} {k}' for k,v in cnt.items()) or 'No additional SQL case','; '.join(c['purpose'] for c in mapped)+ '\nBaseline outstanding review: '+str(row[7])])
    for cell in rtm[1]:cell.font=Font(bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='17436A');cell.alignment=Alignment(wrap_text=True)
    for col,w in zip('ABCDEFGH',[16,28,62,38,24,36,24,75]):rtm.column_dimensions[col].width=w
    for row in rtm.iter_rows(min_row=2):
        rtm.row_dimensions[row[0].row].height=100
        for cell in row:cell.alignment=Alignment(vertical='top',wrap_text=True)
    rtm.freeze_panes='C2';rtm.auto_filter.ref=rtm.dimensions
    wb.save(out/'ENSF608_SQL_Test_Results_126.xlsx')

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True,type=pathlib.Path);p.add_argument('--image',default='mysql:8.0.46');p.add_argument('--check-only',action='store_true');p.add_argument('--baseline',type=pathlib.Path,default=HERE/'baseline_76.zip');a=p.parse_args()
    try:
        verify_catalog();sources,hashes,groups,expected=base.preflight(a.repo);prior=baseline_archive(a.baseline)
    except Exception as e:print('SOURCE CHECK BLOCKED:',e);return 2
    print('Source checks passed: 76 prior evidence cases + 50 additional cases; no new database execution yet.',flush=True)
    if a.check_only:return 0
    try:import pymysql
    except ImportError:print('Install requirements.txt first');return 2
    out=HERE/'reports'/('extended-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f'));evidence=out/'Evidence';evidence.mkdir(parents=True);pwd=secrets.token_hex(24);name='grow8-608-ext-'+secrets.token_hex(6);created=False;conn=None;new=[];version='unknown';blocker=None
    meta={'executed_at':dt.datetime.now().astimezone().isoformat(),'source_blob_hashes':hashes,'source_commit':base.SOURCE_COMMIT,'fixed_clock_utc':base.FIXED_UTC,'container':name,'image':a.image}
    try:
        base.require(base.docker('info',timeout=30),'Docker unavailable');base.require(base.docker('run','-d','--name',name,'--label','grow8.sqlqa=true','-p','127.0.0.1::3306','-e','MYSQL_ROOT_PASSWORD='+pwd,'-e','MYSQL_ROOT_HOST=%','-e','MYSQL_DATABASE=grow8_608',a.image,timeout=600),'Create disposable MySQL');created=True
        for _ in range(120):
            r=base.docker('exec','-e','MYSQL_PWD='+pwd,name,'mysql','-uroot','--protocol=TCP','-h127.0.0.1','-N','-B','-e','SELECT 1;',timeout=15)
            if r.returncode==0 and r.stdout.strip()=='1':break
            time.sleep(2)
        else:raise RuntimeError('MySQL not ready')
        port=int(base.require(base.docker('port',name,'3306/tcp'),'Read port').stdout.strip().splitlines()[0].rsplit(':',1)[1]);setup=[]
        for f in list(base.SOURCE_FILES)[:3]:
            print('Loading',f,flush=True);r=base.require(base.docker('exec','-i','-e','MYSQL_PWD='+pwd,name,'mysql','-uroot','--protocol=TCP','-h127.0.0.1','--default-character-set=utf8mb4','grow8_608',input=base.CLOCK_SQL+sources[f]),f);setup.append(f+'\n'+r.stdout+r.stderr)
        def connect():return pymysql.connect(host='127.0.0.1',port=port,user='root',password=pwd,database='grow8_608',autocommit=True,charset='utf8mb4',connect_timeout=10,read_timeout=35,write_timeout=35)
        conn=connect();clock(conn)
        with conn.cursor() as cur:
            cur.execute('SELECT VERSION(),DATABASE(),NOW()');v,db,now=cur.fetchone();version=str(v);assert db=='grow8_608' and str(now)==base.FIXED_UTC
        (out/'setup.txt').write_text('MySQL '+version+'\n'+'\n'.join(setup),encoding='utf8');initial=base.snapshot(conn)
        for c in CASES:
            t=time.monotonic();entries=[];notes=[];extra={'requirements':c['requirements'],'expected_steps':c['steps']};ok=True
            try:
                if c.get('special'):
                    ok,note,entries,detail=race(connect,conn,pymysql.MySQLError);notes.append(note);extra.update(detail)
                else:
                    conn.begin()
                    try:
                        for step in c['steps']:
                            entry=base.execute(conn,step['sql'],pymysql.MySQLError);entries.append(entry);valid,note=check_step(entry,step);notes.append(note)
                            if not valid:ok=False;break
                    finally:conn.rollback()
                unchanged=base.snapshot(conn)==initial;extra['base_table_row_hashes_restored']=unchanged;ok=ok and unchanged
                if not unchanged:notes.append('Baseline contents changed; subsequent cases cannot safely run.')
            except Exception as e:ok=False;notes.append(str(e).replace(pwd,'[redacted]'));conn.rollback();unchanged=base.snapshot(conn)==initial;extra['base_table_row_hashes_restored']=unchanged
            status='Pass' if ok else 'Fail';sec=round(time.monotonic()-t,3);note='; '.join(notes)
            link=base.save_evidence(evidence,c,status,note,entries,[],version,sec,extra)
            new.append(dict(zip(FIELDS,[c['id'],c['ref'],note,status,link,sec])));print(c['id'],status,flush=True)
            if not unchanged:raise RuntimeError('Isolation failed; remaining cases blocked')
    except Exception as e:blocker=str(e).replace(pwd,'[redacted]');(out/'setup-failure.txt').write_text(blocker,encoding='utf8');print('BLOCKED:',blocker,flush=True)
    finally:
        if conn:conn.close()
        if created:
            try:base.require(base.docker('rm','-f','-v',name,timeout=60),'Remove isolated container')
            except Exception:meta['cleanup_warning']=name
        seen={r['Test ID'] for r in new};new.extend(dict(zip(FIELDS,[c['id'],c['ref'],'Not executed'+(': '+blocker if blocker else ''),'Not run','',0])) for c in CASES if c['id'] not in seen)
        meta.update(mysql_version=version,counts=dict(Counter(r['Status'] for r in new)),blocker=blocker)
        export(out,prior,new,meta);print('Extension results:',meta['counts'],'\nFolder:',out,flush=True)
    return 0 if not blocker and all(r['Status']=='Pass' for r in new) else 1
if __name__=='__main__':sys.exit(main())
