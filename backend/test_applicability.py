import unittest
from backend.applicability import assess, signals


def candidate(subject='API returns 500', category='api', cosine=.9, outcome='unknown'):
    return {'ticket': {'subject': subject, 'description': '', 'category': category},
            'cosine_similarity': cosine, 'outcome': outcome}


class ApplicabilityTests(unittest.TestCase):
    def test_exact_signals(self):
        self.assertEqual(signals('Snowflake HTTP 429 ERR_AUTH')['errors'], ['429', 'ERR_AUTH'])

    def test_unseen_integration_blocks_useful_claim(self):
        matches = [candidate('HubSpot integration failed')]
        result, _ = assess(matches, 'Snowflake integration failed', None, .75, .25)
        self.assertEqual(result, 'no_useful_match')
        self.assertTrue(matches[0]['differences'])

    def test_error_mismatch(self):
        result, _ = assess([candidate()], 'API returns 429', None, .75, .25)
        self.assertEqual(result, 'no_useful_match')

    def test_bad_category_does_not_exclude_case(self):
        matches = [candidate()]
        result, _ = assess(matches, 'API returns 500', 'billing', .75, .25)
        self.assertEqual(result, 'useful_cases')
        self.assertTrue(matches[0]['differences'])

    def test_failed_resolution_is_not_useful(self):
        result, _ = assess([candidate(outcome='confirmed_unresolved')], 'API returns 500', None, .75, .25)
        self.assertEqual(result, 'related_cases')

    def test_low_similarity_and_empty(self):
        for matches in ([], [candidate(cosine=.1)]):
            self.assertEqual(assess(matches, 'test', None, .75, .25)[0], 'no_useful_match')


if __name__ == '__main__':
    unittest.main()
