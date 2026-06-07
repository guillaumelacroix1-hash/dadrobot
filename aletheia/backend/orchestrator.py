"""Moteur de débat : déroulé des tours + pilotage temps réel.

Un débat tourne dans une tâche asyncio. Il diffuse ses tours aux abonnés
(WebSocket) et peut être mis en pause, calibré et relancé à tout moment.
À la fin de chaque tour, il se met en pause automatiquement pour laisser
l'humain tester dans le réel, puis reprend sur « relancer ».
"""
from __future__ import annotations

import asyncio

from . import db, llm, rag
from .agents import load_agents, praticiens, process_agent
from .memory import Blackboard

OBJECTIVE = (
    "Comment éveiller le plein potentiel humain — perception, conscience, "
    "capacités latentes — sans présupposer la forme du résultat ?"
)

FICHE_INSTRUCTION = (
    "Transforme la meilleure piste en FICHE PROTOCOLE testable, avec ces sections : "
    "Nom · Objectif visé · Matériel · Durée · Déroulé pas-à-pas · "
    "Ce qu'on cherche à observer (signes mesurables) · Précautions (sécurité) · "
    "Variante à tester au prochain tour."
)


class StopDebate(Exception):
    pass


def shared_frame(question: str) -> str:
    posts = db.list_postulates(active_only=True)
    lines = "\n".join(f"- {p['text']}" for p in posts) or "- (aucun postulat défini)"
    return (
        f"OBJECTIF COMMUN (étoile polaire) : {OBJECTIVE}\n\n"
        f"POSTULATS ACTIFS (cadre partagé, à garder en tête) :\n{lines}\n\n"
        f"SUJET DE LA SESSION : {question}"
    )


class DebateRuntime:
    def __init__(self, debate_id: int, question: str):
        self.debate_id = debate_id
        self.question = question
        self.subscribers: set[asyncio.Queue] = set()
        self.resume_event = asyncio.Event()
        self.resume_event.set()
        self.stop_flag = False
        self.bb = Blackboard(debate_id)
        self.task: asyncio.Task | None = None

    # ----------------------------------------------------------- diffusion
    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self.subscribers.discard(q)

    async def emit(self, msg: dict) -> None:
        for q in list(self.subscribers):
            await q.put(msg)

    async def emit_turn(self, rnd, phase, agent, content) -> dict:
        turn = db.add_turn(self.debate_id, rnd, phase, agent.id,
                           f"{agent.icon} {agent.name}", content)
        await self.emit({"type": "turn", **turn})
        return turn

    # ----------------------------------------------------------- contrôle
    async def _gate(self) -> None:
        if self.stop_flag:
            raise StopDebate
        if not self.resume_event.is_set():
            db.set_debate_status(self.debate_id, "en pause")
            await self.emit({"type": "status", "status": "en pause"})
            await self.resume_event.wait()
            if self.stop_flag:
                raise StopDebate
            db.set_debate_status(self.debate_id, "en cours")
            await self.emit({"type": "status", "status": "en cours"})

    def pause(self) -> None:
        self.resume_event.clear()

    def resume(self) -> None:
        self.resume_event.set()

    def stop(self) -> None:
        self.stop_flag = True
        self.resume_event.set()

    # ------------------------------------------------------------ prise de parole
    async def _speak(self, agent, rnd, phase, instruction, use_rag=True) -> None:
        await self._gate()
        await self.emit({"type": "thinking", "agent": f"{agent.icon} {agent.name}",
                         "phase": phase})
        user = shared_frame(self.question)
        ctx = self.bb.context_block()
        if ctx:
            user += f"\n\nÉTAT DU DÉBAT :\n{ctx}"
        if use_rag and agent.role == "praticien":
            rag_ctx = rag.context_for(agent.id, self.question)
            if rag_ctx:
                user += (f"\n\nEXTRAITS DE TES SOURCES (en complément de tes "
                         f"connaissances, cite-les si utile) :\n{rag_ctx}")
            else:
                user += ("\n\n(Aucune source déposée pour l'instant : appuie-toi sur "
                         "tes propres connaissances de ta spécialité.)")
        user += f"\n\nCONSIGNE : {instruction}"
        system = agent.persona or f"Tu es {agent.name}, spécialiste de {agent.domain}."
        if agent.orientation:
            system += ("\n\nORIENTATION PARTICULIÈRE (consigne de l'humain, propre à toi, "
                       f"à suivre dans tes interventions) :\n{agent.orientation}")
        try:
            content = await llm.chat(agent.provider, agent.model, system, user,
                                     agent.temperature, agent.top_p)
        except llm.LLMError as e:
            content = f"⚠️ Modèle indisponible ({agent.name}) : {e}"
        await self.emit_turn(rnd, phase, agent, content)

    # ----------------------------------------------------------------- run
    async def run(self) -> None:
        try:
            while not self.stop_flag:
                rnd = (db.get_debate(self.debate_id) or {}).get("round", 0) + 1
                db.set_debate_round(self.debate_id, rnd)
                await self.emit({"type": "round_start", "round": rnd})

                agents = load_agents()
                prats = praticiens(agents)
                mod = process_agent(agents, "moderateur")
                exp = process_agent(agents, "experimentateur")
                avc = process_agent(agents, "avocat_du_diable")

                if mod:
                    await self._speak(mod, rnd, "cadrage",
                                      "Ouvre la session : rappelle l'objectif et les "
                                      "postulats, puis formule la sous-question du tour "
                                      "(4-6 lignes).", use_rag=False)
                for a in prats:
                    await self._speak(a, rnd, "position",
                                      "Donne ta position depuis ta spécialité sur la "
                                      "sous-question (8-12 lignes).")
                for a in prats:
                    await self._speak(a, rnd, "critique",
                                      "Réagis aux positions des autres : 2 accords, "
                                      "2 tensions, 1 angle mort. NE te rallie PAS à la "
                                      "majorité par confort : si tu n'es pas convaincu, "
                                      "dis-le et défends ta position de minorité. Concis.")
                if mod:
                    await self._speak(mod, rnd, "convergence",
                                      "Extrais les 2-3 pistes les plus prometteuses du "
                                      "tour (numérote-les). Ajoute une ligne RAPPORT "
                                      "MINORITAIRE : les avis dissidents qui méritent "
                                      "d'être gardés, même s'ils ne font pas consensus.",
                                      use_rag=False)
                if exp:
                    await self._speak(exp, rnd, "protocole", FICHE_INSTRUCTION,
                                      use_rag=False)
                if avc:
                    await self._speak(avc, rnd, "garde-fou",
                                      "Signale risques, biais et points invérifiables "
                                      "des pistes et du protocole. Bref et franc.",
                                      use_rag=False)

                await self.bb.refresh_summary()
                await self.emit({"type": "round_done", "round": rnd})
                # Pause automatique : place au test dans le réel.
                self.resume_event.clear()
                await self._gate()
        except StopDebate:
            pass
        finally:
            status = "terminé" if self.stop_flag else "en pause"
            db.set_debate_status(self.debate_id, status)
            await self.emit({"type": "status", "status": status})


class DebateManager:
    def __init__(self):
        self.runtimes: dict[int, DebateRuntime] = {}

    def start(self, question: str) -> int:
        debate_id = db.create_debate(question)
        rt = DebateRuntime(debate_id, question)
        self.runtimes[debate_id] = rt
        rt.task = asyncio.create_task(rt.run())
        return debate_id

    def get(self, debate_id: int) -> DebateRuntime | None:
        return self.runtimes.get(debate_id)

    def pause(self, debate_id: int) -> bool:
        rt = self.get(debate_id)
        if rt:
            rt.pause()
            return True
        return False

    def resume(self, debate_id: int) -> bool:
        rt = self.get(debate_id)
        if rt:
            rt.resume()
            return True
        return False

    def stop(self, debate_id: int) -> bool:
        rt = self.get(debate_id)
        if rt:
            rt.stop()
            return True
        db.set_debate_status(debate_id, "terminé")
        return False

    async def calibrate(self, debate_id: int, note: str, payload: dict | None = None) -> None:
        rnd = (db.get_debate(debate_id) or {}).get("round", 0)
        db.add_calibration(debate_id, rnd, note, payload)
        rt = self.get(debate_id)
        if rt:
            await rt.emit({"type": "calibration", "round": rnd, "note": note})

    async def intervene(self, debate_id: int, text: str, kind: str = "ressenti") -> dict:
        """Humain dans la boucle : injecte un message qui sera vu par les agents
        au tour suivant (le contexte est relu depuis la base)."""
        rnd = (db.get_debate(debate_id) or {}).get("round", 0)
        label = {"ressenti": "🧑 Humain (ressenti)",
                 "orientation": "🧑 Humain (orientation)",
                 "source": "🧑 Humain (apport)"}.get(kind, "🧑 Humain")
        turn = db.add_turn(debate_id, rnd, "humain", "humain", label, text)
        rt = self.get(debate_id)
        if rt:
            await rt.emit({"type": "turn", **turn})
        return turn


manager = DebateManager()
