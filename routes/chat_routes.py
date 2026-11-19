"""API endpoints: chat streaming, history, and export."""
import re
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse
from pymongo.errors import PyMongoError

from database import get_conversations
from schemas import ChatRequest
from services import openai_service

router = APIRouter(prefix="/api")

DB_ERROR = "Database error. Is MongoDB running?"


# ---------- helpers ----------
def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    """MongoDB returns naive UTC datetimes; mark them as UTC for the browser."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def parse_id(conversation_id: str) -> ObjectId:
    try:
        return ObjectId(conversation_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=400, detail="Invalid conversation id.")


async def find_conversation(conversation_id: str) -> dict:
    object_id = parse_id(conversation_id)
    try:
        conversation = await get_conversations().find_one({"_id": object_id})
    except PyMongoError:
        raise HTTPException(status_code=503, detail=DB_ERROR)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation


def serialize_message(message: dict) -> dict:
    return {
        "role": message["role"],
        "content": message["content"],
        "timestamp": iso(message["timestamp"]),
    }


# ---------- chat ----------
@router.post("/chat/stream")
async def chat_stream(payload: ChatRequest):
    collection = get_conversations()

    # 1. Load the existing conversation (or prepare a new one)
    existing = None
    if payload.conversation_id:
        existing = await find_conversation(payload.conversation_id)
    history = list(existing["messages"]) if existing else []

    user_message = {"role": "user", "content": payload.message, "timestamp": now()}
    history.append(user_message)

    # 2. Start the OpenAI stream first, so errors return a proper HTTP status
    try:
        stream = await openai_service.create_stream(history, payload.tone)
    except Exception as exc:
        status, message = openai_service.describe_error(exc)
        raise HTTPException(status_code=status, detail=message)

    # 3. Save the user's prompt
    try:
        if existing:
            conversation_id = existing["_id"]
            await collection.update_one(
                {"_id": conversation_id},
                {
                    "$push": {"messages": user_message},
                    "$set": {"updated_at": now(), "tone": payload.tone},
                },
            )
        else:
            title = payload.message[:50] + ("..." if len(payload.message) > 50 else "")
            result = await collection.insert_one(
                {
                    "title": title,
                    "tone": payload.tone,
                    "messages": [user_message],
                    "created_at": now(),
                    "updated_at": now(),
                }
            )
            conversation_id = result.inserted_id
    except PyMongoError:
        raise HTTPException(status_code=503, detail=DB_ERROR)

    # 4. Stream the answer to the browser, then save it
    async def generate():
        parts: list[str] = []
        try:
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    parts.append(text)
                    yield text
        except Exception as exc:
            _, message = openai_service.describe_error(exc)
            yield f"\n\n⚠️ {message}"

        if parts:
            ai_message = {"role": "assistant", "content": "".join(parts), "timestamp": now()}
            try:
                await collection.update_one(
                    {"_id": conversation_id},
                    {"$push": {"messages": ai_message}, "$set": {"updated_at": now()}},
                )
            except PyMongoError:
                pass  # The user already has the answer on screen

    return StreamingResponse(
        generate(),
        media_type="text/plain; charset=utf-8",
        headers={
            "X-Conversation-Id": str(conversation_id),
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------- history ----------
@router.get("/conversations")
async def list_conversations():
    try:
        cursor = (
            get_conversations()
            .find({}, {"title": 1, "updated_at": 1})
            .sort("updated_at", -1)
            .limit(100)
        )
        items = await cursor.to_list(length=100)
    except PyMongoError:
        raise HTTPException(status_code=503, detail=DB_ERROR)
    return [
        {"id": str(c["_id"]), "title": c["title"], "updated_at": iso(c["updated_at"])}
        for c in items
    ]


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    conversation = await find_conversation(conversation_id)
    return {
        "id": str(conversation["_id"]),
        "title": conversation["title"],
        "tone": conversation.get("tone", "professional"),
        "messages": [serialize_message(m) for m in conversation["messages"]],
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    object_id = parse_id(conversation_id)
    try:
        result = await get_conversations().delete_one({"_id": object_id})
    except PyMongoError:
        raise HTTPException(status_code=503, detail=DB_ERROR)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"deleted": True}


# ---------- export ----------
@router.get("/conversations/{conversation_id}/export")
async def export_conversation(conversation_id: str):
    conversation = await find_conversation(conversation_id)

    lines = [f"Chat: {conversation['title']}", "=" * 50, ""]
    for message in conversation["messages"]:
        speaker = "You" if message["role"] == "user" else "AI"
        stamp = message["timestamp"].strftime("%Y-%m-%d %H:%M:%S UTC")
        lines.append(f"[{stamp}] {speaker}:")
        lines.append(message["content"])
        lines.append("")

    filename = re.sub(r"[^A-Za-z0-9_-]+", "_", conversation["title"]).strip("_")[:40] or "chat"
    return PlainTextResponse(
        "\n".join(lines),
        headers={"Content-Disposition": f'attachment; filename="{filename}.txt"'},
    )
