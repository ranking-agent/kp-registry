"""REST wrapper for KP registry SQLite server."""
from collections import defaultdict
import sqlite3
from typing import Dict, List

import aiosqlite
from fastapi import Body, Depends, FastAPI, Query, HTTPException
from pydantic import AnyUrl, BaseModel

app = FastAPI(
    title='Knowledge Provider Registry',
    description='Registry of Translator knowledge providers',
    version='1.0.0',
)


class KP(BaseModel):
    """Knowledge provider."""

    source_type: str
    edge_type: str
    target_type: str


async def get_db():
    """Get SQLite connection."""
    async with aiosqlite.connect('data/kps.db') as db:
        yield db


example = {
    'http://my_kp_url': [{
        'source_type': 'disease',
        'edge_type': 'related to',
        'target_type': 'gene',
    }],
}


@app.get('/kps')
async def get_all_knowledge_providers(
        db=Depends(get_db),
):
    """Get all knowledge providers."""
    statement = 'SELECT * FROM knowledge_providers'
    cursor = await db.execute(
        statement,
    )
    rows = await cursor.fetchall()
    kps = defaultdict(list)
    for row in rows:
        kps[row[0]].append({
            'source_type': row[1],
            'edge_type': row[2],
            'target_type': row[3],
        })
    return kps


@app.get('/kps/{url:path}')
async def get_knowledge_provider(
        url: AnyUrl,
        db=Depends(get_db),
):
    """Get a knowledge provider by url."""
    statement = '''
        SELECT source_type, edge_type, target_type FROM knowledge_providers
        WHERE url=?
        '''
    cursor = await db.execute(
        statement,
        (str(url),),
    )
    rows = await cursor.fetchall()
    return [{
        'source_type': row[0],
        'edge_type': row[1],
        'target_type': row[2],
    } for row in rows]


@app.post('/kps')
async def add_knowledge_provider(
        kps: Dict[AnyUrl, List[KP]] = Body(..., example=example),
        db=Depends(get_db),
):
    """Add a knowledge provider."""
    values = [
        (url, kp.source_type, kp.edge_type, kp.target_type)
        for url, kps in kps.items() for kp in kps
    ]
    # Create table
    await db.execute('''
    CREATE TABLE IF NOT EXISTS knowledge_providers(
        url text,
        source_type text,
        edge_type text,
        target_type text,
        UNIQUE(url, source_type, edge_type, target_type)
    )''')
    # Insert rows of data
    try:
        await db.executemany(
            'INSERT INTO knowledge_providers VALUES (?, ?, ?, ?)',
            values
        )
    except sqlite3.IntegrityError as err:
        if 'UNIQUE constraint failed' in str(err):
            raise HTTPException(400, 'KP already exists')
        raise err
    await db.commit()


@app.delete('/kps/{url:path}')
async def remove_knowledge_provider(
        url: AnyUrl,
        db=Depends(get_db),
):
    """Delete a knowledge provider."""
    await db.execute(
        '''DELETE FROM knowledge_providers
            WHERE url=?''',
        (url,),
    )
    await db.commit()


@app.post('/search')
async def search_for_knowledge_providers(
        source_type: List[str] = Body(..., example=['drug']),
        edge_type: List[str] = Body(..., example=['related_to']),
        target_type: List[str] = Body(..., example=['named_thing']),
        db=Depends(get_db),
):
    """Search for knowledge providers matching a specification."""
    source_bindings = ', '.join('?' for _ in range(len(source_type)))
    edge_bindings = ', '.join('?' for _ in range(len(edge_type)))
    target_bindings = ', '.join('?' for _ in range(len(target_type)))
    statement = f'''
        SELECT DISTINCT url FROM knowledge_providers
        WHERE source_type in ({source_bindings})
        AND edge_type in ({edge_bindings})
        AND target_type in ({target_bindings})
        '''
    cursor = await db.execute(
        statement,
        list(source_type) + list(edge_type) + list(target_type)
    )

    results = await cursor.fetchall()
    return [row[0] for row in results]


@app.post('/clear')
async def clear_kps(
    db=Depends(get_db),
):
    """Clear all registered KPs."""
    await db.execute(
        '''DELETE FROM knowledge_providers''',
    )
    await db.commit()
