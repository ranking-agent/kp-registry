"""REST wrapper for KP registry SQLite server."""
from typing import Dict, List

import aiosqlite
from fastapi import Body, Depends, FastAPI, Query
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
    'http://my_kp_url': {
        'source_type': 'disease',
        'edge_type': 'related to',
        'target_type': 'gene',
    },
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
    results = await cursor.fetchall()
    return {
        kp[0]: {
            'source_type': kp[1],
            'edge_type': kp[2],
            'target_type': kp[3],
        }
        for kp in results
    }


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
    results = await cursor.fetchone()
    return {
        'source_type': results[0],
        'edge_type': results[1],
        'target_type': results[2],
    }


@app.post('/kps')
async def add_knowledge_provider(
        kps: Dict[AnyUrl, KP] = Body(..., example=example),
        db=Depends(get_db),
):
    """Add a knowledge provider."""
    values = [
        (url, kp.source_type, kp.edge_type, kp.target_type)
        for url, kp in kps.items()
    ]
    # Create table
    await db.execute('''CREATE TABLE IF NOT EXISTS knowledge_providers
                (url text UNIQUE, source_type text, edge_type text, target_type text)''')
    # Insert rows of data
    await db.executemany('INSERT INTO knowledge_providers VALUES (?, ?, ?, ?)', values)
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
        SELECT url FROM knowledge_providers
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
