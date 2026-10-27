import unittest
from unittest.mock import patch
from app.sources import rows_as_dicts,load_case_data
from app.fixtures import get_case
from app.providers import ProviderError
import json

class SourceTests(unittest.TestCase):
    def test_column_order_is_taken_from_headers(self):
        self.assertEqual(rows_as_dicts({'headers':['b','a'],'data':[['2','1']]}),[{'b':'2','a':'1'}])

    def test_truncated_and_malformed_results_are_rejected(self):
        for result in ({'headers':['a','a'],'data':[]},{'headers':['a'],'data':[['1','2']]},
                       {'headers':['a'],'data':[['1']]*1000}):
            with self.subTest(result_shape=len(result.get('data',[]))):
                with self.assertRaises(ProviderError): rows_as_dicts(result)

    def test_zetaris_rows_are_used_instead_of_local_fixture(self):
        case=get_case('case-vs-item')
        changed={name:[dict(row,external_marker='from-real-query')] for name,rows in case['data']['sources'].items() for row in rows}
        responses=[{'headers':['record_json'],'data':[[json.dumps(row)] for row in rows]} for rows in changed.values()]
        with patch('app.sources.zetaris_query',side_effect=responses) as query:
            data,info=load_case_data(case,backend='zetaris')
        self.assertEqual(query.call_count,3)
        self.assertEqual(info['backend'],'zetaris')
        self.assertTrue(all(row['external_marker']=='from-real-query' for rows in data['sources'].values() for row in rows))

    def test_query_failure_never_falls_back(self):
        with patch('app.sources.zetaris_query',side_effect=ProviderError('unavailable')):
            with self.assertRaises(ProviderError): load_case_data(get_case('case-vs-item'),backend='zetaris')

if __name__=='__main__': unittest.main()
