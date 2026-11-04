"""Tune development thresholds and report separate synthetic holdout results."""
import copy
import json
from pathlib import Path
from backend.search import TicketSearch
from backend.hybrid import HybridSearch
from backend.applicability import assess


def main():
    root = Path(__file__).parent
    cases = json.loads((root / 'evaluation_cases.json').read_text())['cases']
    keyword, hybrid = TicketSearch(), HybridSearch()
    raw = {c['id']: hybrid.search(c['subject'], c['description'], c.get('category'), 50) for c in cases}
    def prediction(c, strong, related):
        return assess(copy.deepcopy(raw[c['id']]['matches']), c['subject']+' '+c['description'], c.get('category'), strong, related)[0]
    dev = [c for c in cases if c['split']=='development']
    settings=[]
    for strong in (.5,.55,.6,.65,.7,.75):
        for related in (.25,.3,.35,.4,.45):
            if related>=strong:
                continue
            loss=sum(3 if prediction(c,strong,related)=='useful_cases' and c['expected']!='useful_cases' else int(prediction(c,strong,related)!=c['expected']) for c in dev)
            settings.append((loss,-strong,related))
    loss,negative_strong,related=min(settings)
    strong=-negative_strong
    rows=[]
    for c in cases:
        kw=keyword.search(c['subject'],c['description'],c.get('category'),3)
        matches=copy.deepcopy(raw[c['id']]['matches'])
        assessment,_=assess(matches,c['subject']+' '+c['description'],c.get('category'),strong,related)
        rows.append({'id':c['id'],'split':c['split'],'expected':c['expected'],'actual':assessment,'relevant':c['relevant'], 'keyword_top3':[m['ticket']['ticket_id'] for m in kw['matches']], 'hybrid_top3':[m['ticket']['ticket_id'] for m in matches[:3]], 'top_cosine':max((m['cosine_similarity'] for m in matches),default=0)})
    summary={}
    for split in ('development','holdout'):
        subset=[r for r in rows if r['split']==split]
        labeled=[r for r in subset if r['relevant']]
        summary[split]={'assessment_correct':sum(r['expected']==r['actual'] for r in subset),'total':len(subset),'false_useful':sum(r['actual']=='useful_cases' and r['expected']!='useful_cases' for r in subset),'direct_cases':len(labeled),'keyword_recall_at3':sum(bool(set(r['relevant']) & set(r['keyword_top3'])) for r in labeled)/max(1,len(labeled)), 'hybrid_recall_at3':sum(bool(set(r['relevant']) & set(r['hybrid_top3'])) for r in labeled)/max(1,len(labeled))}
    report={'limitations':'Small authored synthetic set; holdout excluded from threshold selection. Not production accuracy.', 'thresholds':{'strong':strong,'related':related},'development_weighted_loss':loss,'summary':summary,'cases':rows}
    (root/'evaluation_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'thresholds':report['thresholds'],'summary':summary},indent=2))

if __name__=='__main__':
    main()
