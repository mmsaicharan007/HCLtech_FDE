"""Dependency-free keyword baseline. Scores are ranking signals, not confidence."""
import calendar
import json
import math
import re
from collections import Counter
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / 'starter_kit' / 'data'
STOP = set('a an the is are was were to of in on for and or with this that their our customer customers has have had it its from after but as by be been'.split())


def tokens(text):
    return [word for word in re.findall(r'[a-z0-9]+', text.lower()) if word not in STOP]


class TicketSearch:
    def __init__(self, path=DATA / 'tickets.json', reference_date=None):
        records = json.loads(Path(path).read_text(encoding='utf-8'))['tickets']
        # Static demo clock is explicit; production supplies today's date.
        self.reference_date = reference_date or max(date.fromisoformat(t['created_at']) for t in records)
        ref = self.reference_date
        cutoff = date(ref.year - 1, ref.month, min(ref.day, calendar.monthrange(ref.year - 1, ref.month)[1]))
        self.tickets = [t for t in records if cutoff <= date.fromisoformat(t['created_at']) <= ref]
        self.docs = [Counter(tokens(t['subject'] + ' ' + t['description'])) for t in self.tickets]
        self.avg_length = sum(map(lambda d: sum(d.values()), self.docs)) / max(len(self.docs), 1)
        self.df = Counter(term for doc in self.docs for term in doc)

    def search(self, subject, description, category=None, limit=5):
        query = set(tokens(subject + ' ' + description))
        matches = []
        for ticket, doc in zip(self.tickets, self.docs):
            shared = query & doc.keys()
            score = 0.0
            for term in shared:
                frequency = doc[term]
                idf = math.log(1 + (len(self.docs) - self.df[term] + .5) / (self.df[term] + .5))
                score += idf * frequency * 2.5 / (frequency + 1.5 * (.25 + .75 * sum(doc.values()) / self.avg_length))
            if score <= 0:
                continue
            category_match = bool(category and category == ticket['category'])
            if category_match:
                score *= 1.15
            matches.append({'ticket': ticket, 'score': round(score, 4),
                            'matched_terms': sorted(shared), 'category_match': category_match,
                            'outcome': 'unknown', 'outcome_source': 'not_provided',
                            'caveat': 'Recorded resolution; user confirmation is absent from the source dataset.'})
        matches.sort(key=lambda m: (-m['score'], m['ticket']['ticket_id']))
        return {'matches': matches[:limit], 'method': 'bm25_keyword_baseline',
                'reference_date': self.reference_date.isoformat(), 'history_months': 12,
                'searched_tickets': len(self.tickets),
                'assessment': 'candidates_require_review' if matches else 'no_keyword_match',
                'notice': 'Keyword overlap does not establish applicability. No strong-match threshold has been calibrated.'}
