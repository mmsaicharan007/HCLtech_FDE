"""PostgreSQL full-text ranking plus exact cosine retrieval; not BM25."""
import os
from datetime import date
from pathlib import Path
from backend.db import connect, vector_literal
from backend.search import tokens
from backend.applicability import assess


class PostgresSearch:
    def __init__(self, reference_date=None):
        from sentence_transformers import SentenceTransformer
        self.model_name = 'sentence-transformers/all-MiniLM-L6-v2'
        self.reference_date = reference_date or date.today()
        self.strong_threshold = float(os.getenv('STRONG_MATCH_THRESHOLD', '.75'))
        self.related_threshold = float(os.getenv('RELATED_MATCH_THRESHOLD', '.25'))
        if not 0 <= self.related_threshold < self.strong_threshold <= 1:
            raise ValueError('Invalid applicability thresholds')
        self.synthetic = os.getenv('USE_SYNTHETIC_FEEDBACK') == '1'
        with connect() as conn:
            conn.execute('SELECT ticket_id FROM support.tickets LIMIT 1')
        self.model = SentenceTransformer(self.model_name, cache_folder=str(Path(__file__).resolve().parents[1]/'.cache'/'models'), device='cpu')

    def _window(self):
        return (self.reference_date, self.reference_date)

    @property
    def tickets(self):
        # Used only by legacy evaluation/health integrations; search itself stays in SQL.
        with connect() as conn:
            rows = conn.execute('''SELECT ticket_id,category,subject,description,tags,created_at,status
                FROM support.tickets WHERE created_at BETWEEN %s::date - interval '12 months' AND %s::date''', self._window()).fetchall()
        return rows

    def get_ticket(self, ticket_id):
        with connect() as conn:
            row = conn.execute('''SELECT t.ticket_id,t.category,t.subject,t.description,t.tags,t.created_at,t.status,
                a.notes AS resolution_notes FROM support.tickets t
                LEFT JOIN support.resolution_attempts a ON a.attempt_id=t.ticket_id || '-source-1'
                WHERE t.ticket_id=%s AND t.created_at BETWEEN %s::date - interval '12 months' AND %s::date''',
                (ticket_id,*self._window())).fetchone()
        return row

    def search(self, subject, description, category=None, limit=5):
        text = subject+'\n'+description
        terms = sorted(set(tokens(text)))
        response = {'matches':[], 'method':'postgres_fts_vector_rrf','model':self.model_name,
                    'reference_date':self.reference_date.isoformat(),'history_months':12,
                    'assessment':'no_useful_match','synthetic_feedback_enabled':self.synthetic,
                    'thresholds':{'strong':self.strong_threshold,'related':self.related_threshold},
                    'notice':'PostgreSQL keyword ranking differs from BM25. Applicability heuristics require validation on database results.'}
        if not terms:
            return response
        embedding = vector_literal(self.model.encode([text],normalize_embeddings=True)[0])
        with connect() as conn:
            window = self._window()
            response['searched_tickets'] = conn.execute("SELECT count(*) AS n FROM support.tickets WHERE created_at BETWEEN %s::date - interval '12 months' AND %s::date",window).fetchone()['n']
            # OR query retains partial lexical matches; tokens are alphanumeric and parameterized.
            lexical = conn.execute('''SELECT ticket_id, ts_rank(search_document,to_tsquery('english',%s)) AS score
                FROM support.tickets WHERE created_at BETWEEN %s::date - interval '12 months' AND %s::date
                AND search_document @@ to_tsquery('english',%s)
                ORDER BY score DESC,ticket_id LIMIT 50''',(' | '.join(terms),*window,' | '.join(terms))).fetchall()
            semantic = conn.execute('''SELECT ticket_id FROM support.tickets
                WHERE created_at BETWEEN %s::date - interval '12 months' AND %s::date
                AND embedding_model=%s ORDER BY embedding <=> %s::vector,ticket_id LIMIT 50''',
                (*window,self.model_name,embedding)).fetchall()
            kr = {r['ticket_id']:i for i,r in enumerate(lexical,1)}
            sr = {r['ticket_id']:i for i,r in enumerate(semantic,1)}
            ids = sorted(set(kr)|set(sr))
            rows = conn.execute('''SELECT t.ticket_id,t.category,t.subject,t.description,t.tags,t.created_at,t.status,
                a.attempt_id,a.notes AS resolution_notes,
                1-(t.embedding <=> %s::vector) AS cosine_similarity,
                f.outcome,f.source AS outcome_source
                FROM support.tickets t
                LEFT JOIN support.resolution_attempts a ON a.attempt_id=t.ticket_id || '-source-1'
                LEFT JOIN LATERAL (SELECT outcome,source FROM support.outcome_feedback
                    WHERE attempt_id=a.attempt_id AND (source='user' OR %s)
                    ORDER BY CASE source WHEN 'user' THEN 0 ELSE 1 END LIMIT 1) f ON true
                WHERE t.ticket_id=ANY(%s) AND t.embedding_model=%s''',
                (embedding,self.synthetic,ids,self.model_name)).fetchall()
        matches=[]
        for row in rows:
            key=row['ticket_id']
            cosine=float(row.pop('cosine_similarity'))
            outcome=row.pop('outcome') or 'unknown'
            source=row.pop('outcome_source') or 'not_provided'
            attempt=row.pop('attempt_id')
            score=(1/(60+kr[key]) if key in kr else 0)+(1/(60+sr[key]) if key in sr else 0)
            same=bool(category and category==row['category'])
            score *= (1.15 if same else 1) * (1.05 if outcome=='confirmed_resolved' else .8 if outcome=='confirmed_unresolved' else 1)
            row['created_at']=row['created_at'].isoformat()
            matches.append({'ticket':row,'score':round(score,6),'cosine_similarity':round(cosine,4),
                            'keyword_rank':kr.get(key),'semantic_rank':sr.get(key),'category_match':same,
                            'matched_terms':sorted(set(terms)&set(tokens(row['subject']+' '+row['description']))),
                            'outcome':outcome,'outcome_source':source,'resolution_attempt_id':attempt})
        matches.sort(key=lambda m:(-m['score'],m['ticket']['ticket_id']))
        matches=matches[:50]
        assessment, extracted=assess(matches,text,category,self.strong_threshold,self.related_threshold)
        response.update(matches=matches[:limit],assessment=assessment,query_signals=extracted)
        return response
