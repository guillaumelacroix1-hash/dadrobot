"""Persistance SQLite : débats, tours, calibrages, postulats, sources."""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

from .config import DB_PATH


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def now() -> float:
    return time.time()


def init_db() -> None:
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS debates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'en cours',  -- en cours / en pause / en calibrage / terminé
                round INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                debate_id INTEGER NOT NULL,
                round INTEGER NOT NULL,
                phase TEXT NOT NULL,        -- cadrage / position / critique / convergence / protocole / garde-fou
                agent_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS calibrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                debate_id INTEGER NOT NULL,
                round INTEGER NOT NULL,
                note TEXT NOT NULL,
                payload TEXT,               -- JSON : ce qui a été changé
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS postulates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                version INTEGER NOT NULL DEFAULT 1,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS postulate_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                postulate_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                version INTEGER NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                kind TEXT NOT NULL,         -- pdf / texte / web / youtube / media
                title TEXT NOT NULL,
                origin TEXT,                -- URL ou nom de fichier
                chunks INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS highlights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                debate_id INTEGER,
                turn_id INTEGER,
                text TEXT NOT NULL,
                note TEXT,
                created_at REAL NOT NULL
            );
            """
        )


# --------------------------------------------------------------------- débats
def create_debate(question: str) -> int:
    t = now()
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO debates (question, status, round, created_at, updated_at) "
            "VALUES (?, 'en cours', 0, ?, ?)",
            (question, t, t),
        )
        return int(cur.lastrowid)


def set_debate_status(debate_id: int, status: str) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE debates SET status=?, updated_at=? WHERE id=?",
            (status, now(), debate_id),
        )


def set_debate_round(debate_id: int, rnd: int) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE debates SET round=?, updated_at=? WHERE id=?",
            (rnd, now(), debate_id),
        )


def get_debate(debate_id: int) -> dict[str, Any] | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM debates WHERE id=?", (debate_id,)).fetchone()
        return dict(row) if row else None


def list_debates() -> list[dict[str, Any]]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM debates ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


# ----------------------------------------------------------------------- tours
def add_turn(debate_id: int, rnd: int, phase: str, agent_id: str,
             agent_name: str, content: str) -> dict[str, Any]:
    t = now()
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO turns (debate_id, round, phase, agent_id, agent_name, content, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (debate_id, rnd, phase, agent_id, agent_name, content, t),
        )
        tid = int(cur.lastrowid)
    return {"id": tid, "debate_id": debate_id, "round": rnd, "phase": phase,
            "agent_id": agent_id, "agent_name": agent_name, "content": content,
            "created_at": t}


def get_turns(debate_id: int) -> list[dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM turns WHERE debate_id=? ORDER BY id", (debate_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ------------------------------------------------------------------ calibrages
def add_calibration(debate_id: int, rnd: int, note: str, payload: dict | None = None) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO calibrations (debate_id, round, note, payload, created_at) "
            "VALUES (?,?,?,?,?)",
            (debate_id, rnd, note, json.dumps(payload or {}), now()),
        )


def get_calibrations(debate_id: int) -> list[dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM calibrations WHERE debate_id=? ORDER BY id", (debate_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ------------------------------------------------------------------- postulats
def add_postulate(text: str) -> int:
    t = now()
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO postulates (text, active, version, created_at, updated_at) "
            "VALUES (?,1,1,?,?)",
            (text, t, t),
        )
        pid = int(cur.lastrowid)
        c.execute(
            "INSERT INTO postulate_versions (postulate_id, text, version, created_at) "
            "VALUES (?,?,1,?)",
            (pid, text, t),
        )
        return pid


def update_postulate(postulate_id: int, text: str | None = None,
                     active: bool | None = None) -> None:
    with _conn() as c:
        row = c.execute("SELECT * FROM postulates WHERE id=?", (postulate_id,)).fetchone()
        if not row:
            return
        new_version = row["version"]
        new_text = row["text"]
        if text is not None and text != row["text"]:
            new_version = row["version"] + 1
            new_text = text
            c.execute(
                "INSERT INTO postulate_versions (postulate_id, text, version, created_at) "
                "VALUES (?,?,?,?)",
                (postulate_id, text, new_version, now()),
            )
        new_active = row["active"] if active is None else int(active)
        c.execute(
            "UPDATE postulates SET text=?, active=?, version=?, updated_at=? WHERE id=?",
            (new_text, new_active, new_version, now(), postulate_id),
        )


def list_postulates(active_only: bool = False) -> list[dict[str, Any]]:
    q = "SELECT * FROM postulates"
    if active_only:
        q += " WHERE active=1"
    q += " ORDER BY id"
    with _conn() as c:
        return [dict(r) for r in c.execute(q).fetchall()]


def postulate_versions(postulate_id: int) -> list[dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM postulate_versions WHERE postulate_id=? ORDER BY version DESC",
            (postulate_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# --------------------------------------------------------------------- sources
def add_source(agent_id: str, kind: str, title: str, origin: str, chunks: int) -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO sources (agent_id, kind, title, origin, chunks, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (agent_id, kind, title, origin, chunks, now()),
        )
        return int(cur.lastrowid)


def list_sources(agent_id: str | None = None) -> list[dict[str, Any]]:
    with _conn() as c:
        if agent_id:
            rows = c.execute(
                "SELECT * FROM sources WHERE agent_id=? ORDER BY created_at DESC",
                (agent_id,),
            ).fetchall()
        else:
            rows = c.execute("SELECT * FROM sources ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


# ------------------------------------------------------------------- pépites
def add_highlight(text: str, debate_id: int | None = None,
                  turn_id: int | None = None, note: str = "") -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO highlights (debate_id, turn_id, text, note, created_at) "
            "VALUES (?,?,?,?,?)",
            (debate_id, turn_id, text, note, now()),
        )
        return int(cur.lastrowid)


def list_highlights() -> list[dict[str, Any]]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM highlights ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def delete_highlight(highlight_id: int) -> None:
    with _conn() as c:
        c.execute("DELETE FROM highlights WHERE id=?", (highlight_id,))


def list_protocols() -> list[dict[str, Any]]:
    """Toutes les Fiches Protocole produites (sorties concrètes des débats)."""
    with _conn() as c:
        rows = c.execute(
            "SELECT t.*, d.question AS debate_question FROM turns t "
            "JOIN debates d ON d.id = t.debate_id "
            "WHERE t.phase='protocole' ORDER BY t.created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
