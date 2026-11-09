import logging
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from ..config import config

logger = logging.getLogger(__name__)

_mongo_client: Optional[MongoClient] = None
_mongo_db: Optional[Database] = None
_is_connected: Optional[bool] = None

def get_mongo_client() -> Optional[MongoClient]:
    """Get or create singleton PyMongo client with fast failover."""
    global _mongo_client, _is_connected
    if not config.use_mongodb:
        _is_connected = False
        return None

    if _mongo_client is not None:
        return _mongo_client

    try:
        client = MongoClient(
            config.mongodb_uri,
            serverSelectionTimeoutMS=2000,
            connectTimeoutMS=2000,
            socketTimeoutMS=3000
        )
        # Test connection with ping
        client.admin.command("ping")
        _mongo_client = client
        _is_connected = True
        logger.info(f"Connected to MongoDB at {config.mongodb_uri}")
        return _mongo_client
    except Exception as e:
        logger.warning(f"Could not connect to MongoDB ({config.mongodb_uri}): {e}. Falling back to in-memory store.")
        _mongo_client = None
        _is_connected = False
        return None

def get_mongo_db() -> Optional[Database]:
    """Return database reference if connected, else None."""
    global _mongo_db
    if _mongo_db is not None:
        return _mongo_db

    client = get_mongo_client()
    if client is not None:
        _mongo_db = client[config.mongodb_db_name]
        return _mongo_db
    return None

def is_mongo_connected() -> bool:
    """Return True if successfully connected to MongoDB."""
    global _is_connected
    if _is_connected is None:
        get_mongo_client()
    return bool(_is_connected)
