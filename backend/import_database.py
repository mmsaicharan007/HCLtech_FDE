"""Explicit, transactional schema setup and repeatable demo import."""
import argparse
import json
from pathlib import Path
from backend.db import connect, vector_literal


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply-schema', action='store_true')
    parser.add_argument('--include-synthetic-feedback', action='store_true')
    args = parser.parse_args()
    from backend.hybrid import HybridSearch
    engine = HybridSearch()
    fixtures = json.loads(Path(__file__).with_name('synthetic_feedback.json').read_text())['attempts']
    fixture_map = {a['ticket_id']: a for a in fixtures}
    with connect() as conn:
        if args.apply_schema:
            conn.execute(Path(__file__).with_name('schema.sql').read_text())
        for ticket, embedding in zip(engine.tickets, engine.vectors):
            conn.execute('''INSERT INTO support.tickets
                (ticket_id,category,subject,description,tags,created_at,status,embedding,embedding_model)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s::vector,%s)
                ON CONFLICT(ticket_id) DO UPDATE SET category=EXCLUDED.category,
                subject=EXCLUDED.subject,description=EXCLUDED.description,tags=EXCLUDED.tags,
                created_at=EXCLUDED.created_at,status=EXCLUDED.status,
                embedding=EXCLUDED.embedding,embedding_model=EXCLUDED.embedding_model''',
                (ticket['ticket_id'],ticket['category'],ticket['subject'],ticket['description'],ticket['tags'],
                 ticket['created_at'],ticket['status'],vector_literal(embedding),engine.model_name))
            attempt = ticket['ticket_id'] + '-source-1'
            conn.execute('''INSERT INTO support.resolution_attempts VALUES (%s,%s,%s)
                ON CONFLICT(attempt_id) DO UPDATE SET notes=EXCLUDED.notes''',
                (attempt,ticket['ticket_id'],ticket['resolution_notes']))
            if args.include_synthetic_feedback:
                feedback = fixture_map[ticket['ticket_id']]
                conn.execute('''INSERT INTO support.outcome_feedback VALUES (%s,%s,%s,%s)
                    ON CONFLICT(attempt_id,source) DO UPDATE SET outcome=EXCLUDED.outcome,comment=EXCLUDED.comment''',
                    (attempt,'synthetic_demo',feedback['outcome'],feedback['comment']))
    print(f'Imported {len(engine.tickets)} tickets transactionally; existing IDs updated without duplication.')


if __name__ == '__main__':
    main()
