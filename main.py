"""REST wrapper for KP registry SQLite server."""
import sqlite3
from typing import List

from fastapi import Depends, FastAPI, Query

app = FastAPI()


def get_db():
    """Get SQLite connection."""
    try:
        db = sqlite3.connect('kps.db')
        yield db
    finally:
        db.close()


@app.get("/kp")
def find_knowledge_providers(
        source_type: List[str] = Query(..., example=['a']),
        edge_type: List[str] = Query(..., example=['related to']),
        target_type: List[str] = Query(..., example=['b']),
        db=Depends(get_db)
):
    """Find a KP matching spec."""
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

    return [row[0] for row in c.fetchall()]
