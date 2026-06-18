from fastapi import FastAPI, Request
import sqlite3
import json
import requests

app = FastAPI()

BOT_TOKEN = "8794977561:AAHt67WcJGbGDxuy3paiG5BI60fALJUtKJA"
OWNER_CHAT_ID = 1066587629

db = sqlite3.connect("messages.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    update_type TEXT,
    business_connection_id TEXT,
    chat_id INTEGER,
    message_id INTEGER,
    username TEXT,
    full_name TEXT,
    text TEXT,
    is_deleted INTEGER DEFAULT 0,
    raw_json TEXT
)
""")
db.commit()

def notify(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": OWNER_CHAT_ID,
        "text": text
    }, timeout=10)

def get_sender_info(chat_id, message_id):
    cur.execute("""
        SELECT username, full_name, text
        FROM logs
        WHERE chat_id = ? AND message_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (chat_id, message_id))
    row = cur.fetchone()
    if row:
        username, full_name, text = row
        sender = f"@{username}" if username else (full_name or "Неизвестный пользователь")
        return sender, text or "[текст не найден]"
    return "Неизвестный пользователь", "[текст не найден]"

@app.get("/")
async def home():
    return {"status": "ok"}

@app.post("/webhook")
async def webhook(request: Request):
    update = await request.json()

    if "business_message" in update:
        msg = update["business_message"]
        user = msg.get("from", {})
        text = msg.get("text") or msg.get("caption") or ""
        cur.execute(
            """
            INSERT INTO logs (
                update_type, business_connection_id, chat_id, message_id,
                username, full_name, text, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "business_message",
                msg.get("business_connection_id"),
                msg.get("chat", {}).get("id"),
                msg.get("message_id"),
                user.get("username"),
                f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                text,
                json.dumps(update, ensure_ascii=False),
            ),
        )
        db.commit()

    if "edited_business_message" in update:
        msg = update["edited_business_message"]
        user = msg.get("from", {})
        text = msg.get("text") or msg.get("caption") or ""
        sender = f"@{user.get('username')}" if user.get("username") else f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()

        cur.execute(
            """
            INSERT INTO logs (
                update_type, business_connection_id, chat_id, message_id,
                username, full_name, text, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "edited_business_message",
                msg.get("business_connection_id"),
                msg.get("chat", {}).get("id"),
                msg.get("message_id"),
                user.get("username"),
                f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                text,
                json.dumps(update, ensure_ascii=False),
            ),
        )
        db.commit()

        notify(f"✏️ {sender} изменил сообщение:\n\n{text}")

    if "deleted_business_messages" in update:
        data = update["deleted_business_messages"]
        chat_id = data.get("chat", {}).get("id")
        ids = data.get("message_ids", [])

        for mid in ids:
            sender, deleted_text = get_sender_info(chat_id, mid)

            cur.execute(
                """
                INSERT INTO logs (
                    update_type, business_connection_id, chat_id, message_id,
                    username, full_name, text, is_deleted, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "deleted_business_messages",
                    data.get("business_connection_id"),
                    chat_id,
                    mid,
                    None,
                    sender,
                    deleted_text,
                    1,
                    json.dumps(update, ensure_ascii=False),
                ),
            )

            notify(f"🗑 {sender} удалил сообщение:\n\n{deleted_text}")

        db.commit()

    return {"ok": True}
