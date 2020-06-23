"""KP registry."""
from collections import defaultdict
import logging

import aiosqlite
from fastapi import HTTPException
import sqlite3

LOGGER = logging.getLogger(__name__)


class Registry():
    """KP registry."""

    def __init__(self, uri):
        """Initialize."""
        self.db = None
        self.uri = uri

    async def __aenter__(self):
        """Enter context."""
        self.db = await aiosqlite.connect(self.uri)
        await self.setup()
        return self

    async def __aexit__(self, *args):
        """Exit context."""
        tmp_db = self.db
        self.db = None
        await tmp_db.close()

    async def setup(self):
        """Set up database table."""
        await self.db.execute(
            'CREATE TABLE IF NOT EXISTS knowledge_providers( ' + (
                'url text, '
                'source_type text, '
                'edge_type text, '
                'target_type text, '
                'UNIQUE(url, source_type, edge_type, target_type) '
            ) + ')'
        )
        await self.db.commit()

    async def get_all(self):
        """Get all KPs."""
        statement = 'SELECT * FROM knowledge_providers'
        cursor = await self.db.execute(
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

    async def get_one(self, url):
        """Get a specific KP."""
        statement = (
            'SELECT source_type, edge_type, target_type '
            'FROM knowledge_providers '
            'WHERE url=?'
        )
        cursor = await self.db.execute(
            statement,
            (str(url),),
        )
        rows = await cursor.fetchall()
        return [{
            'source_type': row[0],
            'edge_type': row[1],
            'target_type': row[2],
        } for row in rows]

    async def add(self, kps):
        """Add KP(s)."""
        values = [
            (url, kp['source_type'], kp['edge_type'], kp['target_type'])
            for url, kps in kps.items() for kp in kps
        ]
        # Insert rows of data
        try:
            await self.db.executemany(
                'INSERT INTO knowledge_providers VALUES (?, ?, ?, ?)',
                values
            )
        except sqlite3.IntegrityError as err:
            if 'UNIQUE constraint failed' in str(err):
                raise HTTPException(400, 'KP already exists')
            raise err
        await self.db.commit()

    async def delete_one(self, url):
        """Delete a specific KP."""
        await self.db.execute(
            'DELETE FROM knowledge_providers '
            'WHERE url=?',
            (url,),
        )
        await self.db.commit()

    async def search(self, source_type, edge_type, target_type):
        """Search for KPs matching a pattern."""
        source_bindings = ', '.join('?' for _ in range(len(source_type)))
        edge_bindings = ', '.join('?' for _ in range(len(edge_type)))
        target_bindings = ', '.join('?' for _ in range(len(target_type)))
        statement = (
            'SELECT DISTINCT url FROM knowledge_providers '
            f'WHERE source_type in ({source_bindings}) '
            f'AND edge_type in ({edge_bindings}) '
            f'AND target_type in ({target_bindings})'
        )
        cursor = await self.db.execute(
            statement,
            list(source_type) + list(edge_type) + list(target_type)
        )

        results = await cursor.fetchall()
        return [row[0] for row in results]

    async def delete_all(self):
        """Delete all KPs."""
        await self.db.execute(
            'DELETE FROM knowledge_providers',
        )
        await self.db.commit()
