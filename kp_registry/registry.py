"""KP registry."""
import json
import logging
import sqlite3
from typing import Union

import aiosqlite
from fastapi import HTTPException

LOGGER = logging.getLogger(__name__)


class Registry():
    """KP registry."""

    def __init__(
            self,
            arg: Union[str, aiosqlite.Connection],
    ):
        """Initialize."""
        self.uri = None
        self.db = None
        if isinstance(arg, str):
            self.uri = arg
        else:
            self.db = arg
            self.db.row_factory = sqlite3.Row

    async def __aenter__(self):
        """Enter context."""
        if self.db is None:
            self.db = await aiosqlite.connect(self.uri)
            self.db.row_factory = sqlite3.Row
        await self.setup()
        return self

    async def __aexit__(self, *args):
        """Exit context."""
        if self.uri is not None:
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
            kps[row["id"]] = row["url"]
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
        if kp is None:
            raise HTTPException(404)
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
        return {
            **json.loads(kp["details"]),
            "operations": [{
                "source_type": row["source_type"],
                "edge_type": row["edge_type"],
                "target_type": row["target_type"],
            } for row in rows]
        }

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

    async def search(
            self,
            source_type,
            edge_type,
            target_type,
            **kwargs,
    ):
        """Search for KPs matching a pattern."""
        statement = (
            """
            SELECT knowledge_providers.id, knowledge_providers.url, knowledge_providers.details,
            operations.source_type, operations.target_type, operations.edge_type
            FROM operations
            JOIN knowledge_providers
            ON knowledge_providers.id = operations.kp
            """
        )
        conditions = []
        values = []
        if source_type:
            conditions.append("source_type in ({0})".format(
                ", ".join("?" for _ in source_type)
            ))
            values.extend(list(source_type))
        if edge_type:
            conditions.append("edge_type in ({0})".format(
                ", ".join("?" for _ in edge_type)
            ))
            values.extend(list(edge_type))
        if target_type:
            conditions.append("target_type in ({0})".format(
                ", ".join("?" for _ in target_type)
            ))
            values.extend(list(target_type))
        if conditions:
            statement += " WHERE " + " AND ".join(conditions)
        cursor = await self.db.execute(
            statement,
            values,
        )

        results = await cursor.fetchall()
        kps_with_ops = {}
        for row in results:
            kp_name = row['id']
            if kp_name not in kps_with_ops:
                kps_with_ops[kp_name] = {
                    'url': row['url'],
                    **json.loads(row['details']),
                    'operations': []
                }
            # Append to operations list
            kps_with_ops[kp_name]['operations'].append({
                'source_type': row['source_type'],
                'target_type': row['target_type'],
                'edge_type': row['edge_type']
            })
        return kps_with_ops

    async def delete_all(self):
        """Delete all KPs."""
        await self.db.execute(
            'DELETE FROM knowledge_providers',
        )
        await self.db.execute(
            'DELETE FROM operations',
        )
        await self.db.commit()
