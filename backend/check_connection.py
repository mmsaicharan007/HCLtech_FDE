"""Connection diagnostic that never prints the connection URI or password."""
from backend.db import connect


def main():
    try:
        with connect() as conn:
            conn.execute('SELECT 1').fetchone()
        print('SUCCESS: database connection and query worked.')
        return 0
    except Exception as exc:
        message = str(exc).lower()
        if 'password authentication failed' in message:
            reason = 'Authentication failed. Check the saved database password.'
        elif 'reset by peer' in message or 'closed the connection' in message:
            reason = 'Connection reset before a query could run. Check the network path and database network restrictions.'
        elif 'timeout' in message:
            reason = 'Connection timed out. Check the network path and database network restrictions.'
        elif 'resolve' in message or 'name or service' in message:
            reason = 'Database hostname could not be resolved.'
        else:
            reason = 'Connection/configuration error. No credentials have been printed.'
        print('FAILED:', reason)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
