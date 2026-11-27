import unittest
import run_extended_sql_tests as e
class ExtensionChecks(unittest.TestCase):
    def test_catalog(self): e.verify_catalog()
    def test_prior_archive(self):
        rows,meta,files,*_=e.baseline_archive(e.HERE/'baseline_76.zip');self.assertEqual(len(rows),76);self.assertEqual(len(files),76)
    def test_result_comparison(self):
        step={'rows':[['1']]};self.assertTrue(e.check_step({'error':None,'tables':[{'rows':[['1']]}]},step)[0]);self.assertFalse(e.check_step({'error':None,'tables':[{'rows':[['0']]}]},step)[0])
    def test_error_signature(self):
        step={'error':[1062,'uq_test']};self.assertTrue(e.check_step({'error':{'code':1062,'message':'Duplicate uq_test'}},step)[0]);self.assertFalse(e.check_step({'error':{'code':1062,'message':'Duplicate different_key'}},step)[0]);self.assertFalse(e.check_step({'error':None},step)[0])
    def test_affected_rows(self):
        self.assertTrue(e.check_step({'error':None,'affected_rows':1},{'affected':1})[0]);self.assertFalse(e.check_step({'error':None,'affected_rows':0},{'affected':1})[0])
if __name__=='__main__':unittest.main()
