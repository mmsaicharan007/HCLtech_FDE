"""Run with python -m backend.evaluate; examples are a smoke set, not a benchmark."""
import json
from backend.search import DATA, TicketSearch
from backend.hybrid import HybridSearch


def main():
    keyword, hybrid = TicketSearch(), HybridSearch()
    queries = json.loads((DATA / 'new_tickets_example.json').read_text())['new_tickets']
    expected = {'NT-2': 'T-1201', 'NT-3': 'T-1303'}
    report = []
    for query in queries:
        row = {'query': query['ticket_id'], 'expected_direct_match': expected.get(query['ticket_id']),
               'note': 'Partial or unfamiliar issue; review applicability' if query['ticket_id'] not in expected else 'Direct match'}
        for name, engine in [('keyword', keyword), ('hybrid', hybrid)]:
            result = engine.search(query['subject'], query['description'], limit=3)
            row[name] = [m['ticket']['ticket_id'] for m in result['matches']]
        report.append(row)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
