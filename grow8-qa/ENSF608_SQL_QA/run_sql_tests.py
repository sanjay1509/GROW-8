"""GROW8 ENSF 608 independent SQL verification; no application changes.
Runs only against a disposable local MySQL container. Never connects to the dev DB.
"""
from __future__ import annotations
import argparse, csv, datetime as dt, hashlib, html, json, pathlib, re, secrets, subprocess, sys, time
from collections import Counter
from decimal import Decimal

HERE = pathlib.Path(__file__).resolve().parent
BASE = 'ENSF608-Final-Artifacts'
SOURCE_COMMIT = '59c7f71885ad064033ddfa7c21c11ab5152278f7'
SOURCE_FILES = {
 '04-implementation/01_create_schema.sql':'afe0b0e635bdabccb73efd7f818bd8544412eed9',
 '04-implementation/02_populate_reference_and_core_data.sql':'4332eb2ed06dc25f4d00089e26ccb28800e259a5',
 '04-implementation/03_populate_workflow_history.sql':'b32133f3b2bd5aa7d0eebd617e672b98118da387',
 '05-operations/grow8_operations.sql':'815ca4904fc2754aaef80762140e2f802fdc319a',
 '05-operations/Operations-Evidence.md':'484818c8a0edf1b8d22a9c94c34f8bc315b59bb8',
}
FIXED_UTC = '2026-11-26 15:06:50'
CLOCK_SQL = f"SET time_zone = '+00:00'; SET timestamp = UNIX_TIMESTAMP('{FIXED_UTC}');\n"
MARKER = re.compile(r'^-- \[([A-Z]+-\d+(?: run)?)\] (.+)$')
PART = re.compile(r'^-- PART \d+ - ')
HEADING = re.compile(r'^### ([A-Z]+-\d+(?: run)?)\s*$')
CATALOG = json.loads((HERE/'sql_cases.json').read_text(encoding='utf-8'))
RUBRIC = json.loads((HERE/'rubric_map.json').read_text(encoding='utf-8'))
BY_REF = {c['ref']: c for c in CATALOG}


def git_blob(text):
    raw=text.encode('utf-8')
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def parse_sql(text):
    """Parser for the team's documented line-delimited SQL + DELIMITER blocks.
    Keeps stored procedure bodies intact and session/transaction order unchanged.
    Standalone setup statements and rollback are explicit control groups.
    """
    groups=[]; current=None; delimiter=';'; buf=[]
    def control():
        return {'ref':None,'purpose':'Session / transaction control','sql':[]}
    for raw in text.splitlines():
        line=raw.rstrip(); stripped=line.strip()
        if not buf:
            marker=MARKER.match(line)
            if marker:
                current={'ref':marker[1],'purpose':marker[2],'sql':[]}; groups.append(current); continue
            if PART.match(line):
                current=None; continue
            if stripped.upper().startswith('DELIMITER '):
                delimiter=stripped.split()[1]; continue
            if not stripped or stripped.startswith('--'): continue
        buf.append(line)
        if stripped.endswith(delimiter):
            statement='\n'.join(buf).strip()[:-len(delimiter)].rstrip(); buf=[]
            if re.fullmatch(r'(START\s+TRANSACTION|ROLLBACK|COMMIT)', statement, re.I):
                group=control(); group['sql'].append(statement); groups.append(group); current=None
            else:
                if current is None:
                    current=control(); groups.append(current)
                current['sql'].append(statement)
    if buf: raise ValueError('Unterminated SQL statement in source')
    return groups


def markdown_cells(line):
    # Same rendering convention as the team's evidence generator (escaped pipes).
    return [x.strip().replace(r'\|','|') for x in re.split(r'(?<!\\)\|',line.strip()[1:-1])]


def baseline_tables(text):
    result={}; current=None; in_code=False; lines=text.splitlines(); i=0
    while i<len(lines):
        line=lines[i]
        if line.startswith('```'): in_code=not in_code; i+=1; continue
        if not in_code:
            h=HEADING.match(line)
            if h: current=h[1]; result.setdefault(current,[])
            if current and line.startswith('|') and i+1<len(lines) and re.fullmatch(r'[|:\- ]+',lines[i+1].strip()):
                cols=markdown_cells(line); i+=2; rows=[]
                while i<len(lines) and lines[i].startswith('|'):
                    rows.append(markdown_cells(lines[i])); i+=1
                result[current].append({'columns':cols,'rows':rows}); continue
        i+=1
    return result


def preflight(repo):
    root=repo.resolve()/BASE; sources={}; hashes={}
    for path,want in SOURCE_FILES.items():
        f=root/path
        if not f.is_file(): raise FileNotFoundError(f'Missing {f}. Use a checkout of team main at {SOURCE_COMMIT}.')
        value=f.read_text(encoding='utf-8-sig'); hashes[path]=git_blob(value); sources[path]=value
        if hashes[path]!=want:
            raise ValueError(f'Source version mismatch: {path}\nExpected Git blob {want}, found {hashes[path]}. Review changed source/catalog rather than trusting old expected results.')
    ops=sources['05-operations/grow8_operations.sql']; report=sources['05-operations/Operations-Evidence.md']
    groups=parse_sql(ops); tables=baseline_tables(report)
    expected=[c['ref'] for c in CATALOG if not c['ref'].startswith('S-')]
    # OP-22 is the post-ROLLBACK check, after all integrity cases.
    expected.remove('OP-22')
    expected.append('OP-22')
    found=[g['ref'] for g in groups if g['ref'] is not None]
    if found!=expected: raise ValueError(f'Catalog/source mismatch: expected {expected}, found {found}')
    for ref in found:
        c=BY_REF[ref]; g=next(g for g in groups if g['ref']==ref)
        if not g['sql'] or not g['purpose']: raise ValueError(f'Empty operation or description: {ref}')
        if not c.get('routine') and not c.get('error') and not tables.get(ref): raise ValueError(f'Missing reference result set: {ref}')
    if len(CATALOG)!=76 or len({c['id'] for c in CATALOG})!=76 or len({r['ref'] for r in RUBRIC})!=25: raise ValueError('Invalid catalog or distinct rubric inventory')
    expected_counts={'INSERT':2,'UPDATE':2,'DELETE':2,'Basic SELECT with filtering':4,'ORDER BY / DISTINCT / LIMIT':2,'Aggregate functions':3,'GROUP BY (one HAVING)':2,'INNER JOIN':3,'LEFT / RIGHT JOIN':2,'Combined JOIN and aggregation':1,'Stored procedures':2}
    if Counter(r['category'] for r in RUBRIC)!=expected_counts: raise ValueError('Rubric mapping category totals differ from required quotas')
    # The source hashes lock the reviewed statement-to-category mapping. Check mapped verbs as an extra guard.
    for row in RUBRIC:
        c=BY_REF[row['ref']]; sql=c.get('sql') or '\n'.join(next(g['sql'] for g in groups if g['ref']==row['ref']))
        rules={'INSERT':r'(?im)^\s*INSERT\s+INTO\b','UPDATE':r'(?im)^\s*UPDATE\b','DELETE':r'(?im)^\s*DELETE\s+FROM\b','Basic SELECT with filtering':r'(?is)SELECT\b.*\bWHERE\b','ORDER BY / DISTINCT / LIMIT':r'(?i)\b(ORDER BY|DISTINCT|LIMIT)\b','Aggregate functions':r'(?i)\b(COUNT|SUM|AVG|MIN|MAX)\s*\(','GROUP BY (one HAVING)':r'(?i)\bGROUP BY\b','INNER JOIN':r'(?i)\bJOIN\b','LEFT / RIGHT JOIN':r'(?i)\b(LEFT|RIGHT)\s+JOIN\b','Combined JOIN and aggregation':r'(?is)\bJOIN\b.*\bGROUP BY\b','Stored procedures':r'(?i)\bCREATE\s+PROCEDURE\b'}
        if not re.search(rules[row['category']],sql): raise ValueError(f"Rubric SQL pattern missing: {row['ref']}")
    if not re.search(r'(?i)\bHAVING\b',BY_REF['S-5']['sql']): raise ValueError('HAVING case missing')
    return sources,hashes,groups,tables


def docker(*args, input=None, timeout=180):
    return subprocess.run(['docker',*args],input=input,text=True,encoding='utf-8',errors='replace',capture_output=True,timeout=timeout)


def require(r,label):
    if r.returncode: raise RuntimeError(f'{label}: {r.stderr.strip() or r.stdout.strip()}')
    return r


def raw_cell(v):
    if v is None: return 'NULL'
    if isinstance(v,bytes): return v.decode('utf-8','replace')
    return str(v)


def report_cell(v):
    s=str(v).replace('\n',' ')
    return s if len(s)<=90 else s[:89]+'…'


def matches(actual,expected,ref):
    if len(actual)!=len(expected): return False, f'Result-set count {len(actual)} vs {len(expected)}'
    for j,(a,e) in enumerate(zip(actual,expected),1):
        if a['columns']!=e['columns']: return False,f'Result set {j}: column names differ'
        ar=[[report_cell(v) for v in row] for row in a['rows']]; er=[list(row) for row in e['rows']]
        # The view's listed-skill created_at is generated when seeding and is not a business-key value.
        if ref=='V-5':
            idx=a['columns'].index('created_at'); listed=a['columns'].index('is_listed')
            for rows in (ar,er):
                for row in rows:
                    if row[listed]=='1':
                        if not re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?',row[idx]): return False,'V-5 listed skill creation timestamp is missing/invalid'
                        row[idx]='<listed timestamp>'
                    elif row[idx]!='NULL': return False,'V-5 earned-only skill has a listed timestamp'
        if a.get('ordered'):
            equal=ar==er
        else:
            equal=Counter(map(tuple,ar))==Counter(map(tuple,er))
        if not equal: return False,f'Result set {j}: values or row count differ from reference ({len(ar)} actual, {len(er)} expected)'
    return True, f'{len(actual)} result set(s) match expected columns and values'


def execute(conn,sql,db_error):
    entry={'sql':sql,'tables':[],'affected_rows':None,'error':None}
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            entry['affected_rows']=cur.rowcount
            while True:
                if cur.description:
                    entry['tables'].append({'columns':[c[0] for c in cur.description], 'rows':[[raw_cell(x) for x in row] for row in cur.fetchall()], 'ordered':bool(re.search(r'\bORDER\s+BY\b',sql,re.I)) or bool(re.match(r'CALL\s+sp_(contributor_summary|find_open_opportunities)',sql,re.I))})
                if not cur.nextset(): break
    except db_error as exc:
        entry['error']={'code':exc.args[0] if exc.args else None,'message':str(exc.args[1] if len(exc.args)>1 else exc)}
    return entry


def snapshot(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME")
        names=[r[0] for r in cur.fetchall()]
        result={}
        for name in names:
            cur.execute('SELECT * FROM `'+name.replace('`','``')+'`')
            rows=sorted(json.dumps([raw_cell(x) for x in row],ensure_ascii=False) for row in cur.fetchall())
            result[name]={'count':len(rows),'sha256':hashlib.sha256('\n'.join(rows).encode()).hexdigest()}
        return result


def table_html(t):
    e=html.escape
    return '<div class="scroll"><table><tr>'+''.join('<th>'+e(x)+'</th>' for x in t['columns'])+'</tr>'+''.join('<tr>'+''.join('<td>'+e(x)+'</td>' for x in r)+'</tr>' for r in t['rows'])+'</table></div><p>'+str(len(t['rows']))+' row(s)</p>'


def save_evidence(folder,c,status,note,entries,expected,version,seconds,extra=None):
    e=html.escape
    path=folder/(c['id']+'.html')
    parts=[f'<h1>{e(c["id"])} · {e(c["ref"])}</h1>',f'<p class="status {status.lower()}">{e(status)} | {seconds:.3f} s</p>',f'<p><b>Purpose:</b> {e(c["purpose"])}</p>',f'<p><b>Expected:</b> {e(c["expected"])}</p>',f'<p><b>Actual verification:</b> {e(note)}</p>',f'<p>Executed {e(dt.datetime.now().astimezone().isoformat())} · MySQL {e(version)} · fixed SQL reference clock {FIXED_UTC} UTC · source {SOURCE_COMMIT}</p>']
    if expected:
        parts.append('<h2>Expected result sets</h2><p>Reference: team Operations-Evidence.md (or explicit seed-based expected rows for supplemental queries). Not this run’s evidence.</p>')
        parts += [table_html(t) for t in expected]
    for i,entry in enumerate(entries,1):
        # Redact the synthetic seed password hash in displayed SQL; no runtime credential is captured.
        sql=re.sub(r'\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}','[development password hash redacted]',entry['sql'])
        parts.append(f'<h2>Statement {i}</h2><pre>{e(sql)}</pre>')
        if entry['error']: parts.append(f'<p><b>MySQL error {e(str(entry["error"]["code"]))}:</b> {e(entry["error"]["message"])}</p>')
        else: parts.append(f'<p>Execution successful; driver row count: {e(str(entry["affected_rows"]))}.</p>')
        parts += [table_html(t) for t in entry['tables']]
    if extra is not None: parts.append('<h2>Additional assertion details</h2><pre>'+e(json.dumps(extra,ensure_ascii=False,indent=2))+'</pre>')
    path.write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>'+e(c['id'])+'</title><style>body{font:15px Segoe UI,Arial,sans-serif;margin:32px;color:#213047;background:#fff}h1,h2{color:#17436a}pre{white-space:pre-wrap;background:#edf2f7;padding:12px;border-radius:4px}table{border-collapse:collapse}th,td{padding:7px 10px;border:1px solid #cbd5e1;text-align:left;vertical-align:top}th{background:#e2e8f0}.scroll{overflow-x:auto}.status{font-weight:bold}.pass{color:#14753b}.fail{color:#b91c1c}.blocked{color:#a16207}</style><body>'+''.join(parts)+'</body></html>',encoding='utf8')
    return str(path.relative_to(folder.parent).as_posix())


def export_results(out,rows,meta):
    with (out/'case-results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['Test ID','Source block','Actual result','Status','Evidence','Seconds']); w.writeheader(); w.writerows(rows)
    (out/'run-metadata.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding='utf8')
    # This optional dependency runs on the student's computer, not in the database container.
    try:
        from openpyxl import load_workbook
        wb=load_workbook(HERE/'ENSF608_SQL_Test_Suite.xlsx'); ws=wb['SQL Tests']; by={r['Test ID']:r for r in rows}
        for i in range(5,5+len(CATALOG)):
            rid=ws.cell(i,1).value; r=by[rid]
            for j,k in [(6,'Actual result'),(7,'Status'),(8,'Evidence'),(9,'Seconds')]: ws.cell(i,j).value=r[k]
            if r['Evidence']:
                ws.cell(i,8).hyperlink=r['Evidence']; ws.cell(i,8).style='Hyperlink'
            ws.cell(i,6).alignment=__import__('openpyxl').styles.Alignment(wrap_text=True,vertical='top')
        wb['Test Summary']['B4']=meta.get('executed_at','')
        wb['Test Summary']['B5']=meta.get('mysql_version','Not available')
        wb.save(out/'ENSF608_SQL_Test_Results.xlsx')
    except Exception as exc:
        print('Workbook export unavailable; CSV and evidence are retained:',exc,flush=True)


def organized_sql(sources):
    index='\n'.join(f"-- {r['category']} | {r['ref']} | {r['statement']} | {r['execution_id']}" for r in RUBRIC)
    return ('-- ENSF 608 SQL rubric index (25 distinct operations; do not reorder the dependent workflow)\n'
            '-- Team operations preserved, followed by independent read-only additions.\n'
            '-- ONLY run on a disposable freshly seeded grow8_608 database. Use mysql --force for expected errors.\n'
            +index+'\n\n'+CLOCK_SQL+'\n'+sources['05-operations/grow8_operations.sql']+'\n\n'+(HERE/'Supplemental_Queries.sql').read_text(encoding='utf-8'))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',required=True,type=pathlib.Path); ap.add_argument('--image',default='mysql:8.0.46'); ap.add_argument('--check-only',action='store_true'); args=ap.parse_args()
    try: sources,hashes,groups,baseline=preflight(args.repo)
    except Exception as exc: print('SOURCE CHECK BLOCKED:',exc); return 2
    print(f'Source checked: {len([g for g in groups if g["ref"]])} team blocks + 5 supplemental queries; 25 distinct rubric mappings. No database executed yet.',flush=True)
    if args.check_only:
        prepared=HERE/'prepared'; prepared.mkdir(exist_ok=True)
        target=prepared/'grow8_operations_by_category.sql'; target.write_text(organized_sql(sources),encoding='utf-8')
        print('Organized SQL artifact:',target,'(not executed)'); return 0
    try: import pymysql
    except ImportError: print('Install dependencies: python -m pip install -r requirements.txt'); return 2
    stamp=dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f'); out=HERE/'reports'/stamp; evidence=out/'Evidence'; evidence.mkdir(parents=True)
    name='grow8-608-sqlqa-'+secrets.token_hex(6); pwd=secrets.token_hex(24); created=False; conn=None; done={}; version='Not available'; blocker=None; first_snapshot={}; final_snapshot={}
    meta={'executed_at':dt.datetime.now().astimezone().isoformat(),'source_commit':SOURCE_COMMIT,'source_blob_hashes':hashes,'fixed_clock_utc':FIXED_UTC,'container':name,'image':args.image,'scope':'Independent local replay. Team operations and baseline are credited separately.'}
    (out/'grow8_operations_by_category.sql').write_text(organized_sql(sources),encoding='utf8')
    try:
        require(docker('info',timeout=30),'Docker unavailable')
        require(docker('run','-d','--name',name,'--label','grow8.sqlqa=true','-p','127.0.0.1::3306','-e','MYSQL_ROOT_PASSWORD='+pwd,'-e','MYSQL_ROOT_HOST=%','-e','MYSQL_DATABASE=grow8_608',args.image,timeout=600),'Create disposable MySQL'); created=True
        print('Waiting for isolated MySQL initialization...',flush=True)
        for _ in range(120):
            r=docker('exec','-e','MYSQL_PWD='+pwd,name,'mysql','-uroot','--protocol=TCP','-h127.0.0.1','-N','-B','-e','SELECT 1;',timeout=15)
            if r.returncode==0 and r.stdout.strip()=='1': break
            time.sleep(2)
        else: raise RuntimeError('MySQL did not become ready')
        port=int(require(docker('port',name,'3306/tcp'),'Read disposable port').stdout.strip().splitlines()[0].rsplit(':',1)[1])
        setup=[]
        for file in list(SOURCE_FILES)[:3]:
            print('Loading',file,flush=True)
            r=require(docker('exec','-i','-e','MYSQL_PWD='+pwd,name,'mysql','-uroot','--protocol=TCP','-h127.0.0.1','--default-character-set=utf8mb4','grow8_608',input=CLOCK_SQL+sources[file],timeout=180),file)
            setup.append(file+'\n'+r.stdout+r.stderr)
        conn=pymysql.connect(host='127.0.0.1',port=port,user='root',password=pwd,database='grow8_608',autocommit=True,charset='utf8mb4',connect_timeout=10,read_timeout=60,write_timeout=60)
        with conn.cursor() as cur:
            cur.execute("SET time_zone = '+00:00'"); cur.execute('SET timestamp = UNIX_TIMESTAMP(%s)',(FIXED_UTC,)); cur.execute('SELECT VERSION(), DATABASE(), NOW()'); v,db,clock=cur.fetchone(); version=str(v)
            if db!='grow8_608' or str(clock)!=FIXED_UTC: raise RuntimeError('Disposable database or fixed clock check failed')
        (out/'setup.txt').write_text('MySQL '+version+'\n'+'\n'.join(setup),encoding='utf8'); first_snapshot=snapshot(conn)
        if len(first_snapshot)!=21: raise RuntimeError(f'Expected 21 base tables, found {len(first_snapshot)}')
        groups=groups+[{'ref':c['ref'],'sql':[c['sql'].rstrip(';')],'purpose':c['purpose']} for c in CATALOG if c['ref'].startswith('S-')]
        for g in groups:
            ref=g['ref']; started=time.monotonic(); entries=[execute(conn,sql,pymysql.MySQLError) for sql in g['sql']]
            errors=[x['error'] for x in entries if x['error']]
            if ref is None:
                if errors: raise RuntimeError('Session/transaction control failed: '+str(errors))
                continue
            c=BY_REF[ref]; actual=[t for entry in entries for t in entry['tables']]; expected=baseline.get(ref,[]); extra=None
            if c.get('columns'): expected=[{'columns':c['columns'],'rows':c['rows']}]
            if c.get('error'):
                code,token=c['error']; ok=len(errors)==1 and errors[0]['code']==code and token.lower() in errors[0]['message'].lower()
                note=f'Observed {errors[0]["code"]}: {errors[0]["message"]}' if len(errors)==1 else f'Expected one rejection; observed {len(errors)} errors.'
                if not ok: note='Expected error signature mismatch. '+note
            elif errors: ok=False; note='Unexpected SQL error: '+str(errors)
            elif c.get('routine'):
                with conn.cursor() as cur:
                    cur.execute("SELECT ROUTINE_NAME FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA=DATABASE() AND ROUTINE_TYPE='PROCEDURE' AND ROUTINE_NAME=%s",(c['routine'],)); names=cur.fetchall()
                ok=names==((c['routine'],),) or list(names)==[(c['routine'],)]; note=f'Procedure metadata found: {c["routine"]}' if ok else 'Procedure not found in metadata'; extra={'metadata_rows':list(names)}
            else:
                ok,note=matches(actual,expected,ref)
                if ref=='OP-22':
                    final_snapshot=snapshot(conn); changed=[n for n in sorted(set(first_snapshot)|set(final_snapshot)) if first_snapshot.get(n)!=final_snapshot.get(n)]; ok=ok and not changed; note+='; all 21 base-table row hashes unchanged' if not changed else '; changed tables: '+', '.join(changed); extra={'before':first_snapshot,'after':final_snapshot,'changed_tables':changed}
            status='Pass' if ok else 'Fail'; seconds=round(time.monotonic()-started,3)
            link=save_evidence(evidence,c,status,note,entries,expected,version,seconds,extra)
            done[c['id']]={'Test ID':c['id'],'Source block':ref,'Actual result':note,'Status':status,'Evidence':link,'Seconds':seconds}; print(c['id'],ref,status,flush=True)
    except Exception as exc:
        blocker=str(exc).replace(pwd,'[redacted]'); (out/'setup-failure.txt').write_text(blocker,encoding='utf8'); print('BLOCKED:',blocker,flush=True)
    finally:
        if conn:
            try: conn.close()
            except Exception: pass
        if created:
            try: require(docker('rm','-f','-v',name,timeout=60),'Remove disposable container')
            except Exception as exc: print('Cleanup warning: only remove this specific QA container:',name,str(exc)); meta['cleanup_warning']=name
        rows=[done.get(c['id'],{'Test ID':c['id'],'Source block':c['ref'],'Actual result':'No completed execution'+(': '+blocker if blocker else ''),'Status':'Not run','Evidence':'','Seconds':0}) for c in CATALOG]
        meta.update(mysql_version=version,blocker=blocker,counts=dict(Counter(r['Status'] for r in rows)))
        export_results(out,rows,meta)
        print('Results:',meta['counts'],'\nFolder:',out,flush=True)
    return 0 if not blocker and all(r['Status']=='Pass' for r in rows) else 1


if __name__=='__main__': sys.exit(main())
