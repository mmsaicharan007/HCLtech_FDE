"""Read-only database evaluation; requires a completed demo import."""
import json
import os
from datetime import date
from pathlib import Path
from backend.db import connect
from backend.postgres_search import PostgresSearch


def main():
    configured = os.getenv('HISTORY_REFERENCE_DATE', '2025-11-30')
    engine = PostgresSearch(reference_date=date.fromisoformat(configured))
    cases = json.loads(Path(__file__).with_name('evaluation_cases.json').read_text())['cases']
    rows=[]
    for case in cases:
        result=engine.search(case['subject'],case['description'],case.get('category'),3)
        ids=[m['ticket']['ticket_id'] for m in result['matches']]
        rows.append({'id':case['id'],'split':case['split'],'expected':case['expected'],'actual':result['assessment'],
                     'expected_tickets':case['relevant'],'top3':ids})
    with connect() as conn:
        counts={table:conn.execute('SELECT count(*) AS n FROM support.'+table).fetchone()['n']
                for table in ('tickets','resolution_attempts','outcome_feedback')}
    labeled=[r for r in rows if r['expected_tickets']]
    report={'counts':counts,'reference_date':configured,'cases':rows,
            'direct_cases':len(labeled),
            'relevant_in_top3':sum(bool(set(r['expected_tickets']) & set(r['top3'])) for r in labeled),
            'assessment_correct':sum(r['expected']==r['actual'] for r in rows),
            'note':'Read-only validation; compare counts across two explicit imports to check idempotence.'}
    Path(__file__).with_name('database_evaluation_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
