"""Exercise the real ASGI application including startup and request validation."""
import asyncio
import os
import httpx
from backend.main import app


async def main():
    os.environ['SEARCH_MODE'] = 'hybrid'
    os.environ['SEARCH_BACKEND'] = 'json'
    os.environ['USE_SYNTHETIC_FEEDBACK'] = '0'
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            assert (await client.get('/health')).json()['tickets'] == 40
            assert (await client.post('/search', json={})).status_code == 422
            assert (await client.post('/search', json={'subject': 'test', 'limit': 51})).status_code == 422
            assert (await client.get('/tickets/missing')).status_code == 404
            examples = (await client.get('/examples')).json()['new_tickets']
            for example in examples:
                response = await client.post('/search', json={'subject': example['subject'], 'description': example['description']})
                assert response.status_code == 200
                result = response.json()
                assert result['method'] == 'hybrid_rrf'
                assert len(result['matches']) <= 5
                assert all(m['outcome'] == 'unknown' for m in result['matches'])
                expected = {'NT-2': 'T-1201', 'NT-3': 'T-1303'}.get(example['ticket_id'])
                if expected:
                    assert result['matches'][0]['ticket']['ticket_id'] == expected, result
            print('Hybrid API validation passed: startup, four examples, invalid inputs, missing ticket, outcome provenance.')
            engine = app.state.search
            import json
            from pathlib import Path
            attempts = json.loads(Path(__file__).with_name('synthetic_feedback.json').read_text())['attempts']
            engine.feedback = {a['ticket_id']: a for a in attempts}
            response = await client.post('/search', json={'subject': 'Charged twice', 'description': 'Two identical monthly charges'})
            assert response.json()['matches'][0]['outcome_source'] == 'synthetic_demo'
            result = engine.search('Dashboard widgets overlap on smaller screens', 'Widgets overlap on a small laptop', limit=50)
            failed = next(m for m in result['matches'] if m['ticket']['ticket_id'] == 'T-1202')
            assert failed['outcome'] == 'confirmed_unresolved'
            assert failed['applicability'] != 'useful_candidate'
            print('Synthetic feedback checks passed: source labels and failed-resolution downgrade.')


if __name__ == '__main__':
    asyncio.run(main())
