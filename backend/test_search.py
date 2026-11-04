import unittest
from backend.search import TicketSearch


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.engine = TicketSearch()

    def test_duplicate_charge(self):
        result = self.engine.search('Charged twice', 'Two charges for a single monthly subscription payment')
        self.assertEqual(result['matches'][0]['ticket']['ticket_id'], 'T-1303')

    def test_empty_and_unrelated(self):
        self.assertEqual(self.engine.search('', '')['matches'], [])
        self.assertEqual(self.engine.search('volcano submarine', '')['matches'], [])

    def test_no_invented_confirmation(self):
        result = self.engine.search('Revenue chart blank', 'White space without bars')
        self.assertEqual(result['matches'][0]['ticket']['ticket_id'], 'T-1201')
        self.assertEqual(result['matches'][0]['outcome'], 'unknown')


if __name__ == '__main__':
    unittest.main()
