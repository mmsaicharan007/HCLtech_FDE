import os
from datetime import date
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator
from backend.search import DATA, TicketSearch
import json
from backend.db import connect  # Loads local .env without exposing credentials.


@asynccontextmanager
async def lifespan(app):
    configured = os.getenv('HISTORY_REFERENCE_DATE')
    from backend.hybrid import HybridSearch
    engine = TicketSearch if os.getenv('SEARCH_MODE', 'hybrid') == 'keyword' else HybridSearch
    if os.getenv('SEARCH_BACKEND', 'json') == 'postgres':
        from backend.postgres_search import PostgresSearch
        engine = PostgresSearch
    app.state.search = engine(reference_date=date.fromisoformat(configured) if configured else None)
    yield


app = FastAPI(title='HCLTech Support API', lifespan=lifespan)


class SearchRequest(BaseModel):
    subject: str = Field(default='', max_length=1000)
    description: str = Field(default='', max_length=20000)
    category: str | None = Field(default=None, max_length=100)
    limit: int = Field(default=5, ge=1, le=50)

    @model_validator(mode='after')
    def require_text(self):
        if not (self.subject.strip() or self.description.strip()):
            raise ValueError('Provide a subject or description')
        return self


@app.get('/health')
def health():
    return {'status': 'ok', 'tickets': len(app.state.search.tickets)}


@app.post('/search')
def search(request: SearchRequest):
    return app.state.search.search(**request.model_dump())


@app.get('/tickets/{ticket_id}')
def ticket(ticket_id: str):
    if hasattr(app.state.search, 'get_ticket'):
        record = app.state.search.get_ticket(ticket_id)
        if record:
            return record
        raise HTTPException(404, 'Ticket not found in active history')
    for record in app.state.search.tickets:
        if record['ticket_id'] == ticket_id:
            return record
    raise HTTPException(404, 'Ticket not found in active history')


@app.get('/examples')
def examples():
    return json.loads((DATA / 'new_tickets_example.json').read_text(encoding='utf-8'))
