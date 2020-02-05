"""REST wrapper for KP registry SQLite server."""
import sqlite3
from typing import Dict, List

from fastapi import Body, Depends, FastAPI, Query
from pydantic import AnyUrl, BaseModel

app = FastAPI()


class KP(BaseModel):
    """Knowledge provider."""

    source_type: str
    edge_type: str
    target_type: str


def get_db():
    """Get SQLite connection."""
    try:
        db = sqlite3.connect('kps.db')
        yield db
    finally:
        db.close()


example = {
    'my_kp_url': {
        'source_type': 'disease',
        'edge_type': 'related to',
        'target_type': 'gene',
    },
}


@app.get('/kps')
def get_all_knowledge_providers(
        db=Depends(get_db),
):
    """Get all knowledge providers."""
    statement = 'SELECT * FROM knowledge_providers'
    c = db.cursor()
    c.execute(
        statement,
    )
    results = c.fetchall()
    return {
        kp[0]: {
            'source_type': kp[1],
            'edge_type': kp[2],
            'target_type': kp[3],
        }
        for kp in results
    }


@app.get('/kps/{url:path}')
def get_knowledge_provider(
        url: AnyUrl,
        db=Depends(get_db),
):
    """Get a knowledge provider by url."""
    statement = '''
        SELECT source_type, edge_type, target_type FROM knowledge_providers
        WHERE url=?
        '''
    c = db.cursor()
    print(str(url))
    c.execute(
        statement,
        (str(url),),
    )
    results = c.fetchone()
    return {
        'source_type': results[0],
        'edge_type': results[1],
        'target_type': results[2],
    }


@app.post('/kps')
def add_knowledge_provider(
        kps: Dict[str, KP] = Body(..., example=example),
        db=Depends(get_db),
):
    """Add a knowledge provider."""
    values = [
        (url, kp.source_type, kp.edge_type, kp.target_type)
        for url, kp in kps.items()
    ]
    with db:
        # Create table
        db.execute('''CREATE TABLE IF NOT EXISTS knowledge_providers
                    (url text UNIQUE, source_type text, edge_type text, target_type text)''')
        # Insert rows of data
        db.executemany('INSERT INTO knowledge_providers VALUES (?, ?, ?, ?)', values)


@app.get('/search')
def search_for_knowledge_providers(
        source_type: List[str] = Query(..., example=['a']),
        edge_type: List[str] = Query(..., example=['related to']),
        target_type: List[str] = Query(..., example=['b']),
        db=Depends(get_db),
):
    """Search for knowledge providers matching a specification."""
    source_bindings = ', '.join('?' for _ in range(len(source_type)))
    edge_bindings = ', '.join('?' for _ in range(len(edge_type)))
    target_bindings = ', '.join('?' for _ in range(len(target_type)))
    statement = f'''
        SELECT url FROM knowledge_providers
        WHERE source_type in ({source_bindings})
        AND edge_type in ({edge_bindings})
        AND target_type in ({target_bindings})
        '''
    c = db.cursor()
    c.execute(
        statement,
        list(source_type) + list(edge_type) + list(target_type)
    )

    results = c.fetchall()
    return [row[0] for row in results]
