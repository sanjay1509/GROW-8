"""Offline runner-unit tests. Not MySQL or GROW8 execution evidence."""
import unittest
from run_sql_tests import parse_sql, baseline_tables, matches, CATALOG, RUBRIC, git_blob

class RunnerLogic(unittest.TestCase):
    def test_delimiter_and_control(self):
        source='''USE grow8_608;
-- PART 1 - STORED PROCEDURES
DELIMITER $$
-- [SP-1] Test procedure
DROP PROCEDURE IF EXISTS demo $$
CREATE PROCEDURE demo()
BEGIN
 SELECT 1;
END $$
DELIMITER ;
-- PART 2 - RETRIEVAL QUERIES
SET @as_of = '2026-11-26';
-- [Q-1] Read result
SELECT 1;
-- PART 3 - DATA MODIFICATION
START TRANSACTION;
-- [OP-1] Modify data
UPDATE demo_table SET n=1;
ROLLBACK;
-- [OP-22] Verify rollback
SELECT 1;
'''
        groups=parse_sql(source)
        self.assertEqual([g['ref'] for g in groups],[None,'SP-1',None,'Q-1',None,'OP-1',None,'OP-22'])
        self.assertEqual(len(groups[1]['sql']),2)
        self.assertIn('SELECT 1;',groups[1]['sql'][1])
        self.assertEqual(groups[-2]['sql'],['ROLLBACK'])
    def test_reference_parser_and_order(self):
        text='''### Q-1
```sql
SELECT 1;
```
| id | name |
|---|---|
| 1 | A \\| B |
| 2 | C |
*2 rows*
'''
        baseline=baseline_tables(text)['Q-1']
        self.assertEqual(baseline[0]['rows'][0],['1','A | B'])
        a=[{'columns':['id','name'],'rows':[['2','C'],['1','A | B']],'ordered':False}]
        self.assertTrue(matches(a,baseline,'Q-1')[0]); a[0]['ordered']=True
        self.assertFalse(matches(a,baseline,'Q-1')[0]);a[0]['ordered']=False;a[0]['rows'][0][1]='wrong'
        self.assertFalse(matches(a,baseline,'Q-1')[0])
    def test_timestamp_normalization(self):
        e=[{'columns':['is_listed','created_at'],'rows':[['1','2026-11-26 15:06:50'],['0','NULL']]}]
        a=[{'columns':e[0]['columns'],'rows':[['1','2026-11-27 15:06:50'],['0','NULL']],'ordered':True}]
        self.assertTrue(matches(a,e,'V-5')[0]);a[0]['rows'][0][1]='NULL';self.assertFalse(matches(a,e,'V-5')[0])
    def test_inventory(self):
        self.assertEqual(len(CATALOG),76);self.assertEqual(len(set(c['id'] for c in CATALOG)),76)
        self.assertEqual(len(RUBRIC),25);self.assertEqual(len(set(x['ref'] for x in RUBRIC)),25)
        self.assertEqual(sum('error' in c for c in CATALOG),19)
if __name__=='__main__':unittest.main()
