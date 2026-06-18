from fastapi import FastAPI, Request
import sqlite3, json

app = FastAPI()

db = sqlite3.connect("messages.db", check_same_thread=False)
cur = db.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    update_type TEXT,
    business_connection_id TEXT,
    chat_id INTEGER,
    message_id INTEGER,
    text TEXT,
    is_deleted INTEGER DEFAULT 0,
    raw_json TEXT
)
""")
db.commit()

@app.get("/")
async def home():
    return {"status": "ok"}

@app.post("/webhook")
async def webhook(request: Request):
    update = await request.json()

    if "business_message" in update:
        msg = update["business_message"]
        cur.execute(
            "INSERT INTO logs (update_type, business_connection_id, chat_id, message_id, text, raw_json) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "business_message",
                msg.get("business_connection_id"),
                msg.get("chat", {}).get("id"),
                msg.get("message_id"),
                msg.get("text") or msg.get("caption") or "",
                json.dumps(update, ensure_ascii=False),
            ),
        )
        db.commit()

    if "edited_business_message" in update:
        msg = update["edited_business_message"]
        cur.execute(
            "INSERT INTO logs (update_type, business_connection_id, chat_id, message_id, text, raw_json) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "edited_business_message",
                msg.get("business_connection_id"),
                msg.get("chat", {}).get("id"),
                msg.get("message_id"),
                msg.get("text") or msg.get("caption") or "",
                json.dumps(update, ensure_ascii=False),
            ),
        )
        db.commit()

    if "deleted_business_messages" in update:
        data = update["deleted_business_messages"]
        for mid in data.get("message_ids", []):
            cur.execute(
                "INSERT INTO logs (update_type, business_connection_id, chat_id, message_id, is_deleted, raw_json) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "deleted_business_messages",
                    data.get("business_connection_id"),
                    data.get("chat", {}).get("id"),
                    mid,
                    1,
                    json.dumps(update, ensure_ascii=False),
                ),
            )
        db.commit()

    return {"ok": True}
