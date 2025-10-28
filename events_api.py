# events_api.py  — Blueprint version
import os, json, hashlib
from flask import Blueprint, request, jsonify
import psycopg

events_bp = Blueprint("events", __name__)
DB_URL = os.getenv("RUSTY_DB_URL")

def connect():
    return psycopg.connect(DB_URL, autocommit=True)

def get_or_create_session(cur, bot, session_external_id, ua, ip):
    ip_hash = hashlib.sha256(ip.encode("utf-8")).hexdigest() if ip else None
    cur.execute("""
        SELECT id FROM chat_session
        WHERE bot=%s AND session_external_id=%s
        ORDER BY started_at DESC LIMIT 1
    """, (bot, session_external_id))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("""
        INSERT INTO chat_session (bot, session_external_id, user_agent, ip_hash)
        VALUES (%s,%s,%s,%s)
        RETURNING id
    """, (bot, session_external_id, ua, ip_hash))
    return cur.fetchone()[0]

@events_bp.post("/events/gpt")
def log_gpt_event():
    payload = request.get_json(force=True)
    bot = payload.get("bot", "pool-guide")
    session_external_id = payload.get("session_external_id") or payload.get("conversation_id")
    messages = payload.get("messages", [])
    actions  = payload.get("actions", [])
    sources  = payload.get("sources", [])
    model    = payload.get("model")
    latency  = payload.get("latency_ms")
    usage    = payload.get("token_usage", {}) or {}

    ua = request.headers.get("User-Agent", "")
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")

    with connect() as conn:
        with conn.cursor() as cur:
            session_id = get_or_create_session(cur, bot, session_external_id, ua, ip)

            for m in messages:
                cur.execute("""
                    INSERT INTO chat_message
                      (session_id, role, content, model, tokens_prompt, tokens_completion, latency_ms, metadata)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    session_id,
                    m.get("role"),
                    m.get("content",""),
                    model,
                    usage.get("prompt"),
                    usage.get("completion"),
                    latency,
                    json.dumps({"sources": sources})
                ))

            for a in actions:
                if a.get("type") == "cta":
                    cur.execute("""
                        INSERT INTO cta_event (session_id, cta_key, cta_label, url, outcome, metadata)
                        VALUES (%s,%s,%s,%s,%s,%s)
                    """, (
                        session_id,
                        a.get("key"),
                        a.get("label"),
                        a.get("url"),
                        a.get("outcome","clicked"),
                        json.dumps({"bot": bot})
                    ))

    return jsonify({"ok": True})

@events_bp.get("/health")
def health():
    try:
        with connect() as _:
            pass
        return {"status":"ok"}
    except Exception as e:
        return {"status":"db_error","detail":str(e)}, 500
