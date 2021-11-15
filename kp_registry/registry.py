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
                'infores TEXT, '
                'maturity TEXT, '
                'details TEXT, '
                'UNIQUE(id, url) '
            ) + ')'
        )
        await self.db.execute(
            'CREATE TABLE IF NOT EXISTS operations( ' + (
                'kp TEXT, '
                'subject_category TEXT, '
                'predicate TEXT, '
                'object_category TEXT, '
                'UNIQUE(kp, subject_category, predicate, object_category) '
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
            "infores": kp["infores"],
            "maturity": kp["maturity"],
            **json.loads(kp["details"]),
            "operations": [{
                "subject_category": row["subject_category"],
                "predicate": row["predicate"],
                "object_category": row["object_category"],
            } for row in rows]
        }

    async def add(self, **kps):
        """Add KP(s)."""
        values = [
            (
                uid,
                kp['url'],
                kp['infores'],
                kp['maturity'],
                json.dumps(kp.get('details', {})),
            )
            for uid, kp in kps.items()
        ]
        # Insert rows of data
        try:
            await self.db.executemany(
                'INSERT INTO knowledge_providers VALUES (?, ?, ?, ?, ?)',
                values
            )
        except sqlite3.IntegrityError as err:
            if 'UNIQUE constraint failed' in str(err):
                raise HTTPException(400, 'KP already exists')
            raise err
        values = [
            (
                uid,
                op['subject_category'],
                op['predicate'],
                op['object_category'],
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
            subject_category,
            predicate,
            object_category,
            maturity,
            **kwargs,
    ):
        """Search for KPs matching a pattern."""
        statement = (
            """
            SELECT knowledge_providers.id, knowledge_providers.url, knowledge_providers.infores,
            knowledge_providers.maturity, knowledge_providers.details,
            operations.subject_category, operations.object_category, operations.predicate
            FROM operations
            JOIN knowledge_providers
            ON knowledge_providers.id = operations.kp
            """
        )
        conditions = []
        values = []
        if subject_category:
            conditions.append("subject_category in ({0})".format(
                ", ".join("?" for _ in subject_category)
            ))
            values.extend(list(subject_category))
        if predicate:
            conditions.append("predicate in ({0})".format(
                ", ".join("?" for _ in predicate)
            ))
            values.extend(list(predicate))
        if object_category:
            conditions.append("object_category in ({0})".format(
                ", ".join("?" for _ in object_category)
            ))
            values.extend(list(object_category))
        if conditions:
            statement += " WHERE " + " AND ".join(conditions)
        cursor = await self.db.execute(
            statement,
            values,
        )

        # maturity is list of enums
        allowed_maturity = [m.value for m in maturity]
        results = await cursor.fetchall()
        kps_with_ops = {}
        for row in results:
            kp_name = row["infores"]
            kp_maturity = row["maturity"]
            if kp_maturity not in allowed_maturity:
                # maturity not allowed, skipping
                continue
            if kp_name not in kps_with_ops:
                kps_with_ops[kp_name] = {
                    'url': row['url'],
                    'title': row['id'],
                    'infores': row['infores'],
                    'maturity': kp_maturity,
                    'operations': []
                }
            else:
                # kp already in list, need to find the best maturity level
                existing_maturity = allowed_maturity.index(kps_with_ops[kp_name]["maturity"])
                new_maturity = allowed_maturity.index(kp_maturity)
                if new_maturity < existing_maturity:
                    # if better maturity, replace existing kp
                    kps_with_ops[kp_name] = {
                        'url': row['url'],
                        'title': row['id'],
                        'infores': row['infores'],
                        'maturity': kp_maturity,
                        'operations': []
                    }
                elif new_maturity > existing_maturity:
                    # worse kp maturity, skip
                    continue
            # Append to operations list
            kps_with_ops[kp_name]['operations'].append({
                'subject_category': row['subject_category'],
                'object_category': row['object_category'],
                'predicate': row['predicate']
            })
        
        # switch keys from infores to title
        kps_with_ops = { val["title"]: kps_with_ops[key] for key, val in kps_with_ops.items() }
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
