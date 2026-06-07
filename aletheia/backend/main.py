"""Aletheia — application FastAPI : API REST + WebSocket + tableau de bord."""
from __future__ import annotations

import asyncio

from fastapi import (Depends, FastAPI, HTTPException, Request, Response,
                     UploadFile, WebSocket, WebSocketDisconnect)
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import auth, config, db, ingestion, rag
from .agents import (Agent, delete_agent, load_agent, load_agents, save_agent,
                     update_levers)
from .orchestrator import OBJECTIVE, manager

app = FastAPI(title="Aletheia")

DEFAULT_POSTULATES = [
    "La conscience ne se réduit pas à la matière.",
    "Les capacités extra-sensorielles sont réelles et entraînables.",
    "Un pattern commun relie son, fréquence et lumière, exploitable par le cerveau.",
]


def _bootstrap() -> None:
    db.init_db()
    if not db.list_postulates():
        for p in DEFAULT_POSTULATES:
            db.add_postulate(p)


# Initialise dès l'import (robuste, idempotent) et au démarrage du serveur.
_bootstrap()


@app.on_event("startup")
def _startup() -> None:
    _bootstrap()


# ============================================================ Authentification
class LoginIn(BaseModel):
    password: str


@app.post("/api/login")
def login(body: LoginIn, response: Response):
    if not auth.check_password(body.password):
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")
    token = auth.make_token()
    response.set_cookie(auth.COOKIE, token, httponly=True, samesite="lax",
                        max_age=auth.MAX_AGE)
    return {"ok": True, "token": token}


@app.get("/api/me")
def me(request: Request):
    token = request.cookies.get(auth.COOKIE) or request.headers.get("X-Auth-Token")
    return {"authenticated": auth.valid_token(token),
            "password_required": bool(config.APP_PASSWORD)}


@app.get("/api/status", dependencies=[Depends(auth.require_auth)])
def status():
    return {
        "objective": OBJECTIVE,
        "missing_keys": config.missing_keys(),
        "rag_backend": rag.backend_name(),
        "agents": len(load_agents()),
    }


# ====================================================================== Agents
@app.get("/api/agents", dependencies=[Depends(auth.require_auth)])
def get_agents():
    return [a.__dict__ for a in load_agents()]


class AgentIn(BaseModel):
    id: str | None = None
    name: str
    role: str = "praticien"
    icon: str = "🧠"
    provider: str = "openrouter"
    model: str = "meta-llama/llama-3.1-8b-instruct:free"
    temperature: float = 0.7
    top_p: float = 0.95
    max_context: int = 8000
    domain: str = ""
    persona: str = ""
    orientation: str = ""
    order: int = 100


@app.post("/api/agents", dependencies=[Depends(auth.require_auth)])
def create_agent(body: AgentIn):
    agent_id = body.id or body.name.lower().replace(" ", "_")
    if load_agent(agent_id):
        raise HTTPException(status_code=409, detail="Un agent porte déjà cet identifiant")
    data = body.dict()
    data["id"] = agent_id
    agent = Agent(**data)
    save_agent(agent)
    return agent.__dict__


@app.put("/api/agents/{agent_id}", dependencies=[Depends(auth.require_auth)])
def edit_agent(agent_id: str, changes: dict):
    agent = update_levers(agent_id, changes)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent introuvable")
    return agent.__dict__


@app.delete("/api/agents/{agent_id}", dependencies=[Depends(auth.require_auth)])
def remove_agent(agent_id: str):
    if not delete_agent(agent_id):
        raise HTTPException(status_code=404, detail="Agent introuvable")
    return {"ok": True}


# =================================================================== Postulats
class PostulateIn(BaseModel):
    text: str


@app.get("/api/postulates", dependencies=[Depends(auth.require_auth)])
def get_postulates():
    return db.list_postulates()


@app.post("/api/postulates", dependencies=[Depends(auth.require_auth)])
def create_postulate(body: PostulateIn):
    pid = db.add_postulate(body.text)
    return {"id": pid}


@app.put("/api/postulates/{pid}", dependencies=[Depends(auth.require_auth)])
def edit_postulate(pid: int, changes: dict):
    db.update_postulate(pid, text=changes.get("text"), active=changes.get("active"))
    return {"ok": True}


@app.get("/api/postulates/{pid}/versions", dependencies=[Depends(auth.require_auth)])
def postulate_history(pid: int):
    return db.postulate_versions(pid)


# ===================================================================== Sources
@app.get("/api/sources", dependencies=[Depends(auth.require_auth)])
def get_sources(agent_id: str | None = None):
    return db.list_sources(agent_id)


class TextSourceIn(BaseModel):
    agent_id: str
    title: str
    text: str


@app.post("/api/sources/text", dependencies=[Depends(auth.require_auth)])
def add_text_source(body: TextSourceIn):
    return ingestion.ingest_text(body.agent_id, body.title, body.text)


class UrlSourceIn(BaseModel):
    agent_id: str
    url: str
    title: str | None = None


@app.post("/api/sources/web", dependencies=[Depends(auth.require_auth)])
def add_web_source(body: UrlSourceIn):
    try:
        return ingestion.ingest_web(body.agent_id, body.url)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/sources/youtube", dependencies=[Depends(auth.require_auth)])
def add_youtube_source(body: UrlSourceIn):
    try:
        return ingestion.ingest_youtube(body.agent_id, body.url, body.title)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/sources/file", dependencies=[Depends(auth.require_auth)])
async def add_file_source(agent_id: str, title: str, file: UploadFile):
    raw = await file.read()
    name = (file.filename or "").lower()
    try:
        if name.endswith(".pdf"):
            return ingestion.ingest_pdf(agent_id, title, raw)
        if name.endswith((".mp3", ".wav", ".m4a", ".mp4", ".webm", ".ogg")):
            return ingestion.ingest_media(agent_id, title, raw, file.filename or name)
        return ingestion.ingest_text(agent_id, title, raw.decode("utf-8", "ignore"))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))


# ====================================================================== Débats
class DebateIn(BaseModel):
    question: str


@app.get("/api/debates", dependencies=[Depends(auth.require_auth)])
def get_debates():
    return db.list_debates()


@app.post("/api/debates", dependencies=[Depends(auth.require_auth)])
async def start_debate(body: DebateIn):
    debate_id = manager.start(body.question)
    return {"id": debate_id}


@app.get("/api/debates/{debate_id}", dependencies=[Depends(auth.require_auth)])
def debate_detail(debate_id: int):
    d = db.get_debate(debate_id)
    if not d:
        raise HTTPException(status_code=404, detail="Débat introuvable")
    return {"debate": d, "turns": db.get_turns(debate_id),
            "calibrations": db.get_calibrations(debate_id)}


@app.post("/api/debates/{debate_id}/pause", dependencies=[Depends(auth.require_auth)])
def pause_debate(debate_id: int):
    return {"ok": manager.pause(debate_id)}


@app.post("/api/debates/{debate_id}/resume", dependencies=[Depends(auth.require_auth)])
def resume_debate(debate_id: int):
    return {"ok": manager.resume(debate_id)}


@app.post("/api/debates/{debate_id}/stop", dependencies=[Depends(auth.require_auth)])
def stop_debate(debate_id: int):
    return {"ok": manager.stop(debate_id)}


class CalibrationIn(BaseModel):
    note: str
    payload: dict | None = None


@app.post("/api/debates/{debate_id}/calibrate", dependencies=[Depends(auth.require_auth)])
async def calibrate_debate(debate_id: int, body: CalibrationIn):
    await manager.calibrate(debate_id, body.note, body.payload)
    return {"ok": True}


class InterveneIn(BaseModel):
    text: str
    kind: str = "ressenti"   # ressenti | orientation | source


@app.post("/api/debates/{debate_id}/intervene", dependencies=[Depends(auth.require_auth)])
async def intervene(debate_id: int, body: InterveneIn):
    return await manager.intervene(debate_id, body.text, body.kind)


# ============================================== Pépites / sorties des débats
class HighlightIn(BaseModel):
    text: str
    debate_id: int | None = None
    turn_id: int | None = None
    note: str = ""


@app.get("/api/highlights", dependencies=[Depends(auth.require_auth)])
def get_highlights():
    return db.list_highlights()


@app.post("/api/highlights", dependencies=[Depends(auth.require_auth)])
def create_highlight(body: HighlightIn):
    hid = db.add_highlight(body.text, body.debate_id, body.turn_id, body.note)
    return {"id": hid}


@app.delete("/api/highlights/{hid}", dependencies=[Depends(auth.require_auth)])
def remove_highlight(hid: int):
    db.delete_highlight(hid)
    return {"ok": True}


@app.get("/api/outputs", dependencies=[Depends(auth.require_auth)])
def get_outputs():
    """Sorties concrètes : toutes les Fiches Protocole + les pépites épinglées."""
    return {"protocols": db.list_protocols(), "highlights": db.list_highlights()}


# =================================================================== WebSocket
@app.websocket("/ws/debates/{debate_id}")
async def ws_debate(websocket: WebSocket, debate_id: int):
    await websocket.accept()
    # Envoi de l'historique existant.
    for turn in db.get_turns(debate_id):
        await websocket.send_json({"type": "turn", **turn})
    rt = manager.get(debate_id)
    if not rt:
        d = db.get_debate(debate_id)
        await websocket.send_json({"type": "status",
                                   "status": (d or {}).get("status", "terminé")})
        # Pas de runtime actif : on garde la connexion ouverte mais passive.
        try:
            while True:
                await asyncio.sleep(30)
                await websocket.send_json({"type": "ping"})
        except WebSocketDisconnect:
            return
    q = rt.subscribe()
    try:
        while True:
            msg = await q.get()
            await websocket.send_json(msg)
    except WebSocketDisconnect:
        pass
    finally:
        rt.unsubscribe(q)


# =============================================== Tableau de bord (frontend)
if config.FRONTEND_DIR.exists():
    @app.get("/")
    def index():
        return FileResponse(config.FRONTEND_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=config.FRONTEND_DIR), name="static")
else:
    @app.get("/")
    def index_fallback():
        return JSONResponse({"message": "Aletheia API en ligne. Frontend absent."})
