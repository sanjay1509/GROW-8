"""Append genuine Playwright CSV results to a COPY of the QA workbook."""
import csv, sys
from pathlib import Path
from collections import Counter
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment
if len(sys.argv)!=4:
    raise SystemExit('Usage: python import-results.py baseline.xlsx case-results.csv output.xlsx')
src, report, output = map(Path,sys.argv[1:]);
if src.resolve()==output.resolve() or output.exists():
    raise SystemExit('Use a new output filename; the original is not overwritten.')
rows=list(csv.DictReader(report.open(encoding='utf-8-sig',newline='')))
if not rows: raise SystemExit('No actual execution records in report')
w=load_workbook(src); e=w['Execution Results']
coverage={r['Test Case ID']:r for r in csv.DictReader((Path(__file__).parent/'automation-map.csv').open(encoding='utf-8-sig'))}
seen=set(); result_rows=[]
for r in rows:
    key=r['Test Case ID']; meta=coverage.get(key)
    if not meta or key in seen: raise SystemExit('Unknown or duplicate case ID: '+key)
    seen.add(key)
    st=r['Status'];
    if st not in {'Pass','Fail','Skipped','Blocked'}: raise SystemExit('Invalid execution status: '+st)
    detail=r['Actual Results']
    if st=='Pass' and meta['Coverage limitation']!='None identified in static review':
        detail+=' Partial coverage: '+meta['Coverage limitation']
    number=int(key.split('-')[1]); mode=('Browser fixture (mocked API where configured)' if key.startswith('UI-') and 46<=number<=107 else 'In-process API / isolated MySQL; fake event publisher' if key.startswith('API-') and 59<=number<=295 else 'Live automation')
    if key in {'API-060','API-061','API-062','API-063','API-068'}: mode='In-process API; simulated dependency fault'
    evidence='; '.join(str(report.parent / x.strip()) for x in r['Evidence'].split(';') if x.strip()) or str(report.parent / ('legacy-api.html' if 59<=number<=295 and key.startswith('API-') else 'html/index.html'))
    result_rows.append([r['Run UTC'],key,st,key.split('-')[0],mode,None,'Automated assertions only; commit '+r['Commit'],detail,evidence])
start=e.max_row+2
for i,row in enumerate(result_rows,start):
    for j,v in enumerate(row,1):
        c=e.cell(i,j,v);c.alignment=Alignment(vertical='top',wrap_text=True)
    e.row_dimensions[i].height=55
    sh=w['UI Tests' if row[3]=='UI' else 'API Tests']; target=next((n for n in range(4,sh.max_row+1) if sh.cell(n,1).value==row[1]),None)
    if target:
        # H actual, I evidence, J status of automated run (not full manual-case certification).
        for col,origin in [('H','H'),('I','I'),('J','C')]:sh[f'{col}{target}']=f"='Execution Results'!{origin}{i}"
# Append a visibly separate summary so original run/date rows stay unchanged.
end=start+len(result_rows)+2
e.cell(end,1,'NEW AUTOMATED RUN SUMMARY').font=Font(bold=True)
for k,layer in enumerate(('UI','API'),end+1):
    c=Counter(x[2] for x in result_rows if x[3]==layer)
    for j,v in enumerate([rows[0]['Run UTC'],layer,c['Pass'],c['Fail'],c['Skipped'],c['Blocked'],len([x for x in coverage if x.startswith(layer+'-')])-sum(c.values()),'Automated assertions only — see coverage map',str(report)],1):e.cell(k,j,v)
w.save(output);print(f'Wrote {len(result_rows)} genuine execution records to {output}')
