"""Live database API checks. Requires the imported synthetic dataset."""
import asyncio
import os
from datetime import date
import httpx
from backend.main import app


async def main():
    os.environ['SEARCH_BACKEND'] = 'postgres'
    os.environ['HISTORY_REFERENCE_DATE'] = '2025-11-30'
    os.environ['USE_SYNTHETIC_FEEDBACK'] = '0'
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            assert (await client.get('/health')).json()['tickets'] == 40
            ticket = (await client.get('/tickets/T-1303')).json()
            assert ticket['resolution_notes']
            assert (await client.get('/tickets/missing')).status_code == 404
            assert (await client.post('/search',json={})).status_code == 422
            for example in (await client.get('/examples')).json()['new_tickets']:
                result = await client.post('/search',json={'subject':example['subject'],'description':example['description']})
                assert result.status_code == 200
                body = result.json()
                assert body['method'] == 'postgres_fts_vector_rrf'
                assert all(m['outcome']=='unknown' for m in body['matches'])
                expected = {'NT-2':'T-1201','NT-3':'T-1303'}.get(example['ticket_id'])
                if expected:
                    assert body['matches'][0]['ticket']['ticket_id']==expected
                if example['ticket_id']=='NT-4':
                    assert body['assessment']=='no_useful_match'
            engine = app.state.search
            engine.synthetic = True
            result = engine.search('Dashboard widgets overlap on smaller screens','Widgets overlap on a small laptop',limit=50)
            failed = next(m for m in result['matches'] if m['ticket']['ticket_id']=='T-1202')
            assert failed['outcome']=='confirmed_unresolved'
            assert failed['outcome_source']=='synthetic_demo'
            assert failed['applicability']!='useful_candidate'
            engine.reference_date=date(2020,1,1)
            assert len(engine.tickets)==0
            assert engine.get_ticket('T-1303') is None
            assert engine.search('charged twice','duplicate monthly charge')['matches']==[]
    print('Database API checks passed: examples, resolutions, invalid input, missing ticket, feedback modes, and date filtering.')


if __name__=='__main__':
    asyncio.run(main())
