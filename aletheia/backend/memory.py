"""Mémoire du débat : tableau noir partagé + résumé roulant.

Évite l'explosion de contexte : au lieu de tout réinjecter, on garde les tours
récents en clair + un résumé condensé des tours plus anciens.
"""
from __future__ import annotations

from . import db, llm

# Modèle utilisé pour résumer (agent de processus, qualité Claude).
SUMMARY_PROVIDER = "anthropic"
SUMMARY_MODEL = "claude-sonnet-4-6"

RECENT_TURNS = 8


class Blackboard:
    def __init__(self, debate_id: int):
        self.debate_id = debate_id
        self.summary = ""

    async def refresh_summary(self) -> None:
        turns = db.get_turns(self.debate_id)
        if len(turns) <= RECENT_TURNS:
            return
        old = turns[:-RECENT_TURNS]
        body = "\n".join(f"[{t['phase']}] {t['agent_name']}: {t['content']}" for t in old)
        try:
            self.summary = await llm.chat(
                SUMMARY_PROVIDER, SUMMARY_MODEL,
                system="Tu condenses fidèlement un débat en cours en notes structurées, "
                       "sans rien inventer. Garde les pistes, tensions et décisions.",
                user=f"Résume ces échanges en 8-12 puces :\n\n{body}",
                temperature=0.3, max_tokens=700,
            )
        except llm.LLMError:
            # Repli sans modèle : résumé brut tronqué.
            self.summary = body[:1500]

    def context_block(self) -> str:
        turns = db.get_turns(self.debate_id)
        recent = turns[-RECENT_TURNS:]
        parts = []
        if self.summary:
            parts.append("RÉSUMÉ DES ÉCHANGES PRÉCÉDENTS :\n" + self.summary)
        if recent:
            parts.append(
                "ÉCHANGES RÉCENTS :\n"
                + "\n".join(f"- {t['agent_name']} ({t['phase']}) : {t['content']}"
                            for t in recent)
            )
        return "\n\n".join(parts)
