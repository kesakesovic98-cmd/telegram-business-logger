from fastapi import FastAPI, Request
import sqlite3
import json
import requests
import os

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

@app.get("/")
async def home():
    return {"status": "ok"}

@app.post("/webhook")
async def webhook(request: Request):
    update = await request.json()

    if "business_message" in update:
        msg = update["business_message"]
        text = msg.get("text") or msg.get("caption") or ""
        cur.execute(
            "INSERT INTO logs (update_type, business_connection_id, chat_id, message_id, text, raw_json) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "business_message",
                msg.get("business_connection_id"),
                msg.get("chat", {}).get("id"),
                msg.get("message_id"),
                text,
                json.dumps(update, ensure_ascii=False),
            ),
        )
        db.commit()

    if "edited_business_message" in update:
        msg = update["edited_business_message"]
        text = msg.get("text") or msg.get("caption") or ""
        cur.execute(
            "INSERT INTO logs (update_type, business_connection_id, chat_id, message_id, text, raw_json) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "edited_business_message",
                msg.get("business_connection_id"),
                msg.get("chat", {}).get("id"),
                msg.get("message_id"),
                text,
                json.dumps(update, ensure_ascii=False),
            ),
        )
        db.commit()
        notify(f"✏️ Собеседник изменил сообщение:\n\n{text}")

    if "deleted_business_messages" in update:
        data = update["deleted_business_messages"]
        ids = data.get("message_ids", [])
        for mid in ids:
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
        notify(f"🗑 Собеседник удалил сообщение.\nID: {', '.join(map(str, ids))}")

    return {"ok": True}
