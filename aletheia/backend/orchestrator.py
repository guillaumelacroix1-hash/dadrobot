"""Moteur de débat : déroulé des tours + pilotage temps réel.

Un débat tourne dans une tâche asyncio. Il diffuse ses tours aux abonnés
(WebSocket) et peut être mis en pause, calibré et relancé à tout moment.
À la fin de chaque tour, il se met en pause automatiquement pour laisser
l'humain tester dans le réel, puis reprend sur « relancer ».
"""
from __future__ import annotations

import asyncio
import re

from . import db, llm, rag
from .agents import load_agents, praticiens, process_agent
from .memory import Blackboard

OBJECTIVE = (
    "Comment éveiller le plein potentiel humain — perception, conscience, "
    "capacités latentes — sans présupposer la forme du résultat ?"
)
# La « mission » (esprit précurseur / interdisciplinarité) est désormais un POSTULAT
# éditable (onglet Postulats), injecté via la liste des postulats — voir shared_frame().

# Tous les N tours, le Synthétiseur propose la version la plus aboutie.
CYCLE = 3


def parse_agent_selection(text: str, all_prats: list) -> list:
    """Lit la ligne 'AGENTS À SOLLICITER : id1, id2…' du cadrage. Repli : tous."""
    ids = {a.id for a in all_prats}
    m = re.search(r"AGENTS? À SOLLICITER\s*[:=]\s*(.+)", text or "", re.IGNORECASE)
    if not m:
        return all_prats
    chosen = {tok.strip().lower() for tok in re.split(r"[,;/]| et ", m.group(1))}
    picked = [a for a in all_prats if a.id in (ids & chosen)]
    return picked if len(picked) >= 3 else all_prats


def parse_consensus(text: str) -> tuple[int | None, str]:
    """Lit la ligne 'CONSENSUS: NN/100 (état: …)' de la convergence."""
    score = None
    m = re.search(r"CONSENSUS\s*[:=]\s*(\d{1,3})", text or "", re.IGNORECASE)
    if m:
        score = max(0, min(100, int(m.group(1))))
    state = ""
    for kw in ("chambre d'écho", "chambre d'echo", "blocage", "convergence"):
        if kw in (text or "").lower():
            state = "chambre d'écho" if "cho" in kw else kw
            break
    return score, state


def parse_nuggets(text: str) -> list[dict]:
    """Lit les pépites candidates (+ leur contexte) proposées à la convergence."""
    out, cur = [], None
    for line in (text or "").splitlines():
        m = re.match(r"\s*P[ÉE]PITE\s+CANDIDATE\s*[:=]\s*(.+)", line, re.IGNORECASE)
        if m:
            if cur:
                out.append(cur)
            cur = {"text": m.group(1).strip(" *-—:").strip(), "context": ""}
            continue
        if cur is not None:
            cm = re.match(r"\s*CONTEXTE\s*[:=]\s*(.+)", line, re.IGNORECASE)
            if cm:
                cur["context"] = cm.group(1).strip(" *-—:").strip()
    if cur:
        out.append(cur)
    return [n for n in out if n["text"]][:3]


async def explain_highlight(text: str, debate_id: int) -> str:
    """2-3 phrases de contexte pour une pépite épinglée à la main (générées par Claude)."""
    question = (db.get_debate(debate_id) or {}).get("question", "")
    system = ("Tu documentes les idées clés d'un débat. Réponds en 2-3 phrases claires, "
              "en français, sans préambule ni formule d'introduction.")
    user = (f"SUJET DU DÉBAT : {question}\n\nIDÉE ÉPINGLÉE :\n{text}\n\n"
            "Explique brièvement : ce que cette idée veut dire, d'où elle vient et "
            "pourquoi elle est notable.")
    try:
        return await llm.chat("anthropic", "claude-sonnet-4-6", system, user,
                              temperature=0.4, max_tokens=220)
    except Exception:  # noqa: BLE001
        return ""


async def consolidate_learnings(debate_id: int) -> int:
    """À la clôture d'un débat : chaque praticien en mode apprentissage tire 1-3 prises
    de conscience (de ses interventions, des critiques, des tests réels) qu'il gardera
    pour ses prochains débats. Retourne le nombre d'agents mis à jour."""
    d = db.get_debate(debate_id)
    turns = db.get_turns(debate_id) if d else []
    if not turns:
        return 0
    logs = db.get_testlogs(debate_id)
    tlog = "\n".join(f"- {l['text']}" + (f" → {l['outcome']}" if l["outcome"] else "")
                     for l in logs) or "(aucun retour de test réel)"
    distil = "\n".join(f"[{t['phase']}] {t['content']}" for t in turns
                       if t["phase"] in ("convergence", "synthese"))[:2500]
    agents = {a.id: a for a in load_agents()}
    participated = {t["agent_id"] for t in turns}
    count = 0
    for aid in participated:
        a = agents.get(aid)
        if not a or a.role != "praticien" or not getattr(a, "learning", True):
            continue
        mine = "\n".join(f"[{t['phase']}] {t['content']}" for t in turns
                         if t["agent_id"] == aid)[:2500]
        system = a.persona or f"Tu es {a.name}, spécialiste de {a.domain}."
        user = (f"DÉBAT QUI S'ACHÈVE : {d['question']}\n\n"
                f"DISTILLATION (convergence / synthèse) :\n{distil or '(n/d)'}\n\n"
                f"TES PROPRES INTERVENTIONS :\n{mine or '(n/d)'}\n\n"
                f"RETOURS DE TESTS RÉELS DE L'HUMAIN (priment sur la théorie) :\n{tlog}\n\n"
                "Formule 1 à 3 PRISES DE CONSCIENCE concises (une phrase chacune, en puces) "
                "que tu retiens pour tes PROCHAINS débats : ce qui a affiné ou changé ta "
                "compréhension, au vu des critiques et surtout des tests réels. Pas de "
                "préambule — uniquement les puces.")
        try:
            txt = (await llm.chat(a.provider, a.model, system, user,
                                  temperature=0.5, max_tokens=240)).strip()
        except Exception:  # noqa: BLE001
            continue
        if txt:
            db.add_learning(aid, debate_id, txt)
            count += 1
    return count


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
    def __init__(self, debate_id: int, question: str,
                 participants: list[str] | None = None,
                 moderator_selects: bool = True,
                 auto_advance: bool = True,
                 consensus_target: int = 75,
                 max_rounds: int = 8):
        self.debate_id = debate_id
        self.question = question
        self.participants = set(participants) if participants else None
        self.moderator_selects = moderator_selects
        self.auto_advance = auto_advance          # enchaîner les tours jusqu'au consensus
        self.consensus_target = consensus_target  # seuil (%) qui déclenche l'arrêt
        self.max_rounds = max_rounds              # garde-fou : nb de tours max en auto
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
    def _testlog_block(self) -> str:
        logs = db.get_testlogs(self.debate_id)
        if not logs:
            return ""
        lines = [f"- {l['text']}" + (f" → {l['outcome']}" if l["outcome"] else "")
                 for l in logs[-5:]]
        return ("RETOURS DE TESTS RÉELS DE L'HUMAIN (à prendre au sérieux, ils priment "
                "sur la théorie) :\n" + "\n".join(lines))

    async def _speak(self, agent, rnd, phase, instruction, use_rag=True) -> dict | None:
        await self._gate()
        await self.emit({"type": "thinking", "agent": f"{agent.icon} {agent.name}",
                         "phase": phase})
        user = shared_frame(self.question)
        ctx = self.bb.context_block()
        if ctx:
            user += f"\n\nÉTAT DU DÉBAT :\n{ctx}"
        tlog = self._testlog_block()
        if tlog:
            user += f"\n\n{tlog}"
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
        if agent.role == "praticien":
            system += (
                "\n\nPOSTURE DE TRAVAIL : ce cénacle GÉNÈRE des hypothèses concrètes et "
                "testables. Explore l'idée à fond, sans réflexe de débunkage ni disclaimers "
                "à répétition. Reste intellectuellement honnête : distingue clairement ce qui "
                "est établi de ce qui est spéculatif, mais propose des pistes même non prouvées "
                "— l'absence de preuve publique ne vaut pas preuve du contraire. Sois à la fois "
                "audacieux et rigoureux.")
            if getattr(agent, "learning", True):
                learns = db.list_learnings(agent.id, exclude_debate=self.debate_id)
                if learns:
                    mem = "\n".join(l["text"] for l in learns)
                    system += ("\n\nTES PRISES DE CONSCIENCE DES DÉBATS PRÉCÉDENTS (acquis à "
                               f"intégrer, fruit de ton expérience passée) :\n{mem}")
        try:
            content = await llm.chat(agent.provider, agent.model, system, user,
                                     agent.temperature, agent.top_p)
        except llm.LLMError as e:
            content = f"⚠️ Modèle indisponible ({agent.name}) : {e}"
        return await self.emit_turn(rnd, phase, agent, content)

    # ----------------------------------------------------------------- run
    async def run(self) -> None:
        try:
            while not self.stop_flag:
                rnd = (db.get_debate(self.debate_id) or {}).get("round", 0) + 1
                db.set_debate_round(self.debate_id, rnd)
                await self.emit({"type": "round_start", "round": rnd})
                round_consensus = None

                agents = load_agents()
                all_prats = praticiens(agents)
                if self.participants:
                    chosen = [a for a in all_prats if a.id in self.participants]
                    if chosen:
                        all_prats = chosen
                mod = process_agent(agents, "moderateur")
                exp = process_agent(agents, "experimentateur")
                avc = process_agent(agents, "avocat_du_diable")
                syn = process_agent(agents, "synthetiseur")

                # Cadrage + (option) sélection dynamique des intervenants.
                prats = all_prats
                if mod:
                    ids = ", ".join(a.id for a in all_prats)
                    sel_line = ""
                    if self.moderator_selects:
                        sel_line = (" Termine par une ligne « AGENTS À SOLLICITER : … » en "
                                    f"choisissant parmi [{ids}] les 3 à 6 praticiens les plus "
                                    "pertinents pour CE tour (garde de la diversité de points "
                                    "de vue).")
                    cadre = await self._speak(
                        mod, rnd, "cadrage",
                        "Ouvre la session : rappelle l'objectif et les postulats, puis "
                        "formule la sous-question du tour (4-6 lignes)." + sel_line,
                        use_rag=False)
                    if self.moderator_selects and rnd > 1 and cadre:
                        prats = parse_agent_selection(cadre["content"], all_prats)

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
                    conv = await self._speak(
                        mod, rnd, "convergence",
                        "Extrais les 2-3 pistes les plus prometteuses du tour "
                        "(numérote-les). Ajoute une ligne RAPPORT MINORITAIRE (avis "
                        "dissidents à garder). Si une piste est VRAIMENT prometteuse "
                        "(testable concrètement avec un signe observable, nouvelle, et "
                        "soutenue par plusieurs spécialités OU née d'une tension féconde), "
                        "signale-la sur sa propre ligne « PÉPITE CANDIDATE : <une phrase "
                        "claire> », suivie d'une ligne « CONTEXTE : <2-3 phrases : ce que ça "
                        "veut dire, d'où ça vient dans le débat, pourquoi c'est notable> » "
                        "(0 à 2 pépites maximum, seulement si ça le mérite vraiment). "
                        "Termine par une ligne "
                        "« CONSENSUS : NN/100 (état: convergence | blocage | chambre "
                        "d'écho) » évaluant honnêtement où en est le cercle.",
                        use_rag=False)
                    if conv:
                        score, state = parse_consensus(conv["content"])
                        round_consensus = score
                        db.add_metric(self.debate_id, rnd, score, state)
                        await self.emit({"type": "consensus", "round": rnd,
                                         "consensus": score, "state": state})
                        for n in parse_nuggets(conv["content"]):
                            db.add_highlight(n["text"], self.debate_id, conv["id"],
                                             note="Modérateur · candidate", status="candidate",
                                             context=n["context"])
                            await self.emit({"type": "nugget", "text": n["text"]})
                if exp:
                    await self._speak(exp, rnd, "protocole", FICHE_INSTRUCTION,
                                      use_rag=False)
                if avc:
                    await self._speak(avc, rnd, "garde-fou",
                                      "Signale risques, biais et points invérifiables "
                                      "des pistes et du protocole. Bref et franc.",
                                      use_rag=False)

                # Synthèse de cycle : tous les CYCLE tours, la meilleure version à ce jour.
                if syn and rnd % CYCLE == 0:
                    await self._speak(
                        syn, rnd, "synthese",
                        "Relis l'ensemble du débat (résumé + tours récents + retours de "
                        "tests) et propose LA VERSION LA PLUS ABOUTIE de la technique à "
                        "ce stade : un protocole unique, intégré et concret, qui combine "
                        "le meilleur de toutes les pistes. Mentionne ce qu'il reste à "
                        "valider.", use_rag=False)

                await self.bb.refresh_summary()
                await self.emit({"type": "round_done", "round": rnd})
                # Enchaîner le tour suivant, ou s'arrêter pour laisser tester dans le réel ?
                stop_here, reason = True, "fin de tour"
                if self.auto_advance:
                    if round_consensus is not None and round_consensus >= self.consensus_target:
                        reason = f"consensus {round_consensus}% atteint (cible {self.consensus_target}%)"
                    elif rnd >= self.max_rounds:
                        reason = f"{self.max_rounds} tours atteints sans consensus suffisant"
                    else:
                        stop_here = False        # on enchaîne directement le tour suivant
                if stop_here:
                    await self.emit({"type": "autopause", "reason": reason})
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

    def start(self, question: str, participants: list[str] | None = None,
              moderator_selects: bool = True, auto_advance: bool = True,
              consensus_target: int = 75, max_rounds: int = 8) -> int:
        debate_id = db.create_debate(question)
        rt = DebateRuntime(debate_id, question, participants, moderator_selects,
                           auto_advance, consensus_target, max_rounds)
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

    async def resume(self, debate_id: int) -> bool:
        rt = self.get(debate_id)
        if rt and rt.task and not rt.task.done():
            rt.resume()
            return True
        # Plus de moteur vivant (après Stop ou redémarrage du serveur) : on en
        # recrée un et on relance — run() repart au tour suivant en lisant la base.
        d = db.get_debate(debate_id)
        if not d:
            return False
        rt = DebateRuntime(debate_id, d["question"])
        self.runtimes[debate_id] = rt
        db.set_debate_status(debate_id, "en cours")
        rt.task = asyncio.create_task(rt.run())
        return True

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
