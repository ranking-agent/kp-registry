"""KP registry."""
from collections import defaultdict
import json
import logging
import sqlite3

import aiosqlite
from fastapi import HTTPException

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
        self.db.row_factory = sqlite3.Row
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
                'id TEXT, '
                'url TEXT, '
                'details TEXT, '
                'UNIQUE(id, url) '
            ) + ')'
        )
        await self.db.execute(
            'CREATE TABLE IF NOT EXISTS operations( ' + (
                'kp TEXT, '
                'source_type TEXT, '
                'edge_type TEXT, '
                'target_type TEXT, '
                'UNIQUE(kp, source_type, edge_type, target_type) '
            ) + ')'
        )
        await self.db.commit()

    async def get_all(self):
        """Get all KPs."""
        kps = dict()
        statement = 'SELECT * FROM knowledge_providers'
        cursor = await self.db.execute(
            statement,
        )
        rows = await cursor.fetchall()
        for row in rows:
            kps[row["id"]] = {
                'url': row['url'],
                'details': json.loads(row['details']),
                'operations': [],
            }
        statement = 'SELECT * FROM operations'
        cursor = await self.db.execute(
            statement,
        )
        rows = await cursor.fetchall()
        for row in rows:
            kps[row["kp"]]["operations"].append({
                'source_type': row['source_type'],
                'edge_type': row['edge_type'],
                'target_type': row['target_type'],
            })
        return kps

    async def get_one(self, uid):
        """Get a specific KP."""
        statement = (
            'SELECT * '
            'FROM knowledge_providers '
            'WHERE id=?'
        )
        cursor = await self.db.execute(
            statement,
            (str(uid),),
        )
        kp = await cursor.fetchone()
        statement = (
            'SELECT * '
            'FROM operations '
            'WHERE kp=?'
        )
        cursor = await self.db.execute(
            statement,
            (kp["id"],),
        )
        rows = await cursor.fetchall()
        return [{
            'source_type': row['source_type'],
            'edge_type': row['edge_type'],
            'target_type': row['target_type'],
            'details': json.loads(kp['details']),
        } for row in rows]

    async def add(self, **kps):
        """Add KP(s)."""
        values = [
            (
                uid,
                kp['url'],
                json.dumps(kp.get('details', {})),
            )
            for uid, kp in kps.items()
        ]
        # Insert rows of data
        try:
            await self.db.executemany(
                'INSERT INTO knowledge_providers VALUES (?, ?, ?)',
                values
            )
        except sqlite3.IntegrityError as err:
            if 'UNIQUE constraint failed' in str(err):
                raise HTTPException(400, 'KP already exists')
            raise err
        values = [
            (
                uid,
                op['source_type'],
                op['edge_type'],
                op['target_type'],
            )
            for uid, kp in kps.items() for op in kp["operations"]
        ]
        # Insert rows of data
        try:
            await self.db.executemany(
                'INSERT INTO operations VALUES (?, ?, ?, ?)',
                values
            )
        except sqlite3.IntegrityError as err:
            if 'UNIQUE constraint failed' in str(err):
                raise HTTPException(400, 'KP already exists')
            raise err
        await self.db.commit()

    async def delete_one(self, uid):
        """Delete a specific KP."""
        await self.db.execute(
            'DELETE FROM knowledge_providers '
            'WHERE id=?',
            (uid,),
        )
        await self.db.execute(
            'DELETE FROM operations '
            'WHERE kp=?',
            (uid,),
        )
        await self.db.commit()

    async def search(self, source_type, edge_type, target_type):
        """Search for KPs matching a pattern."""
        source_bindings = ', '.join('?' for _ in range(len(source_type)))
        edge_bindings = ', '.join('?' for _ in range(len(edge_type)))
        target_bindings = ', '.join('?' for _ in range(len(target_type)))
        statement = (
            'SELECT DISTINCT id, url, details FROM operations '
            'JOIN knowledge_providers '
            'ON knowledge_providers.id = operations.kp '
            f'WHERE source_type in ({source_bindings}) '
            f'AND edge_type in ({edge_bindings}) '
            f'AND target_type in ({target_bindings}) '
        )
        cursor = await self.db.execute(
            statement,
            list(source_type) + list(edge_type) + list(target_type)
        )

        results = await cursor.fetchall()
        return {
            row['id']: {
                'url': row['url'],
                **json.loads(row['details']),
            }
            for row in results
        }

    async def delete_all(self):
        """Delete all KPs."""
        await self.db.execute(
            'DELETE FROM knowledge_providers',
        )
        await self.db.execute(
            'DELETE FROM operations',
        )
        await self.db.commit()
