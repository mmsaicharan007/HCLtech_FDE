"""Credentials are loaded locally and never logged."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')


def connect():
    import psycopg
    from psycopg.rows import dict_row
    url = os.getenv('DATABASE_URL')
    if not url:
        raise RuntimeError('Set DATABASE_URL in the local .env file. See backend/DATABASE.md.')
    conn = psycopg.connect(url, sslmode='require', connect_timeout=10,
                           prepare_threshold=None, row_factory=dict_row)
    conn.execute('SET search_path TO support, public, extensions')
    return conn


def vector_literal(vector):
    import math
    values = [float(v) for v in vector]
    if len(values) != 384 or not all(math.isfinite(v) for v in values):
        raise ValueError('Expected 384 finite embedding values')
    return '[' + ','.join(str(v) for v in values) + ']'
