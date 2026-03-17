"""Integration tests for the backup manager."""

import os
import gzip
import hashlib
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["ENCRYPTION_KEY"] = "Sx_Zd9AEzXhJz22Qzq5fSPb2KYXjnIJ2ZdIjk1aiQyY="
os.environ["JWT_SECRET"] = "test-jwt-secret-for-unit-tests"
os.environ["MONGO_URL"] = "mongodb://localhost:27017"
os.environ["DB_NAME"] = "keyforge_test"

from cryptography.fernet import Fernet
from backend.backup.manager import BackupManager


class _AsyncCursorMock:
    """Mock async cursor that supports ``async for doc in cursor``."""

    def __init__(self, docs):
        self._docs = list(docs)
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._docs):
            raise StopAsyncIteration
        doc = self._docs[self._index]
        self._index += 1
        return doc


def _make_mock_backup_db(collections_map=None):
    """Build a mock DB with collections returning given docs.

    collections_map: dict of collection_name -> list[dict]
    """
    if collections_map is None:
        collections_map = {
            "users": [{"_id": "id1", "username": "alice"}],
            "credentials": [{"_id": "id2", "name": "key-1"}],
        }

    mock_db = MagicMock()
    mock_db.list_collection_names = AsyncMock(
        return_value=list(collections_map.keys())
    )

    _coll_cache = {}

    def getitem(name):
        if name not in _coll_cache:
            coll = MagicMock()
            docs = collections_map.get(name, [])
            coll.find = MagicMock(return_value=_AsyncCursorMock(docs))
            coll.insert_one = AsyncMock()
            coll.insert_many = AsyncMock()
            coll.drop = AsyncMock()
            coll.find_one = AsyncMock(return_value=None)
            coll.update_one = AsyncMock()
            coll.delete_one = AsyncMock()
            _coll_cache[name] = coll
        return _coll_cache[name]

    mock_db.__getitem__ = MagicMock(side_effect=getitem)
    return mock_db


# ── create / verify cycle ────────────────────────────────────────────────


class TestBackupCreateVerify:
    """BackupManager.create_backup and verify_backup."""

    @pytest.mark.asyncio
    async def test_create_backup_returns_metadata(self):
        mock_db = _make_mock_backup_db()
        result = await BackupManager.create_backup(mock_db, user_id="u1")

        assert "backup_id" in result
        assert "checksum" in result
        assert result["status"] == "completed"
        assert "encryption_key" in result
        assert result["total_documents"] == 2  # 1 user + 1 credential
        assert set(result["collections"]) == {"users", "credentials"}

    @pytest.mark.asyncio
    async def test_create_and_verify_roundtrip(self):
        mock_db = _make_mock_backup_db()
        meta = await BackupManager.create_backup(mock_db, user_id="u1")

        # Retrieve the encrypted data that was stored
        insert_call = mock_db["backup_data"].insert_one
        stored_doc = insert_call.call_args[0][0]

        import base64
        encrypted_bytes = base64.b64decode(stored_doc["data"])

        verify_result = await BackupManager.verify_backup(
            encrypted_bytes, meta["encryption_key"]
        )

        assert verify_result["is_valid"] is True
        assert verify_result["total_documents"] == 2
        assert set(verify_result["collections"]) == {"users", "credentials"}


# ── checksum validation ──────────────────────────────────────────────────


class TestChecksumValidation:
    """Checksum in backup metadata matches the compressed data."""

    @pytest.mark.asyncio
    async def test_checksum_matches(self):
        mock_db = _make_mock_backup_db()
        meta = await BackupManager.create_backup(mock_db, user_id="u1")

        # The checksum in metadata should be a 64-char hex SHA-256
        checksum = meta["checksum"]
        assert len(checksum) == 64
        assert all(c in "0123456789abcdef" for c in checksum)

    @pytest.mark.asyncio
    async def test_verify_with_wrong_key_fails(self):
        mock_db = _make_mock_backup_db()
        meta = await BackupManager.create_backup(mock_db, user_id="u1")

        insert_call = mock_db["backup_data"].insert_one
        stored_doc = insert_call.call_args[0][0]

        import base64
        encrypted_bytes = base64.b64decode(stored_doc["data"])

        wrong_key = Fernet.generate_key().decode()
        verify_result = await BackupManager.verify_backup(encrypted_bytes, wrong_key)
        assert verify_result["is_valid"] is False
