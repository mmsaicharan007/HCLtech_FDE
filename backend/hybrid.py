"""Local vector retrieval with normalized embeddings and reciprocal rank fusion."""
import hashlib
import json
from pathlib import Path
from backend.search import TicketSearch, tokens


class HybridSearch(TicketSearch):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        import numpy as np
        from sentence_transformers import SentenceTransformer
        self.np = np
        self.model_name = 'sentence-transformers/all-MiniLM-L6-v2'
        cache = Path(__file__).resolve().parents[1] / '.cache'
        cache.mkdir(exist_ok=True)
        self.model = SentenceTransformer(self.model_name, cache_folder=str(cache / 'models'), device='cpu')
        texts = [t['subject'] + '\n' + t['description'] for t in self.tickets]
        digest = hashlib.sha256(json.dumps([self.model_name, texts]).encode()).hexdigest()
        target = cache / (digest + '.npy')
        if target.exists():
            self.vectors = np.load(target, allow_pickle=False)
        else:
            self.vectors = self.model.encode(texts, normalize_embeddings=True)
            np.save(target, self.vectors)

    def search(self, subject, description, category=None, limit=5):
        baseline = super().search(subject, description, category=None, limit=50)
        if not tokens(subject + ' ' + description) or not self.tickets:
            baseline.update(method='hybrid_rrf', matches=[])
            return baseline
        vector = self.model.encode([subject + '\n' + description], normalize_embeddings=True)[0]
        similarities = self.vectors @ vector
        semantic = sorted(range(len(self.tickets)), key=lambda i: (-float(similarities[i]), self.tickets[i]['ticket_id']))[:50]
        keyword = {m['ticket']['ticket_id']: (rank, m) for rank, m in enumerate(baseline['matches'], 1)}
        semantic_ranks = {self.tickets[i]['ticket_id']: rank for rank, i in enumerate(semantic, 1)}
        candidates = set(keyword) | set(semantic_ranks)
        results = []
        for i, ticket in enumerate(self.tickets):
            key = ticket['ticket_id']
            if key not in candidates:
                continue
            kr, original = keyword.get(key, (None, {}))
            sr = semantic_ranks.get(key)
            score = (1 / (60 + kr) if kr else 0) + (1 / (60 + sr) if sr else 0)
            category_match = bool(category and category == ticket['category'])
            if category_match:
                score *= 1.15
            results.append({'ticket': ticket, 'score': round(score, 6),
                            'cosine_similarity': round(float(similarities[i]), 4),
                            'keyword_rank': kr, 'semantic_rank': sr,
                            'matched_terms': original.get('matched_terms', []),
                            'category_match': category_match, 'outcome': 'unknown',
                            'outcome_source': 'not_provided'})
        results.sort(key=lambda m: (-m['score'], m['ticket']['ticket_id']))
        baseline.update(matches=results[:limit], method='hybrid_rrf', model=self.model_name,
                        assessment='candidates_require_review',
                        notice='Scores are retrieval signals, not fix probabilities. No-match thresholds remain uncalibrated.')
        return baseline
