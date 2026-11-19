"""MongoDB connection (async, using Motor)."""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

import config

_client: AsyncIOMotorClient | None = None


async def connect_to_mongo() -> None:
    """Create the client and make sure the server is reachable."""
    global _client
    _client = AsyncIOMotorClient(config.MONGODB_URI, serverSelectionTimeoutMS=5000)
    await _client.admin.command("ping")
    await get_conversations().create_index("updated_at")


async def close_mongo() -> None:
    if _client is not None:
        _client.close()


def get_conversations() -> AsyncIOMotorCollection:
    if _client is None:
        raise RuntimeError("Database is not connected.")
    return _client[config.MONGODB_DB_NAME]["conversations"]
