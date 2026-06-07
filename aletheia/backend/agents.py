"""Chargement et gestion des agents (fichiers YAML dans agents/).

Un agent = un modèle + une persona + ses réglages (« leviers ») + sa base de
sources. Les agents sont créables / modifiables à chaud depuis le tableau de bord.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

import yaml

from .config import AGENTS_DIR, SOURCES_DIR


@dataclass
class Agent:
    id: str
    name: str
    role: str = "praticien"          # praticien | processus
    icon: str = "🧠"
    provider: str = "openrouter"     # openrouter | groq | anthropic
    model: str = "meta-llama/llama-3.1-8b-instruct:free"
    temperature: float = 0.7
    top_p: float = 0.95
    max_context: int = 8000
    domain: str = ""
    persona: str = ""
    orientation: str = ""            # consigne perso (orienter/désorienter) injectée pour CET agent
    order: int = 100                 # ordre de prise de parole
    learning: bool = True            # mémoire évolutive : apprend des débats passés

    @property
    def sources_dir(self):
        return SOURCES_DIR / self.id


def _path(agent_id: str):
    return AGENTS_DIR / f"{agent_id}.yaml"


def load_agents() -> list[Agent]:
    agents: list[Agent] = []
    if not AGENTS_DIR.exists():
        return agents
    for f in sorted(AGENTS_DIR.glob("*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        data.setdefault("id", f.stem)
        agents.append(Agent(**{k: v for k, v in data.items() if k in Agent.__annotations__}))
    agents.sort(key=lambda a: (a.role != "praticien", a.order, a.name))
    return agents


def load_agent(agent_id: str) -> Agent | None:
    p = _path(agent_id)
    if not p.exists():
        return None
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    data.setdefault("id", agent_id)
    return Agent(**{k: v for k, v in data.items() if k in Agent.__annotations__})


def save_agent(agent: Agent) -> None:
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    agent.sources_dir.mkdir(parents=True, exist_ok=True)
    data = asdict(agent)
    _path(agent.id).write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def update_levers(agent_id: str, changes: dict[str, Any]) -> Agent | None:
    """Modifie les leviers d'un agent (modèle, température, persona...)."""
    agent = load_agent(agent_id)
    if agent is None:
        return None
    allowed = {"name", "icon", "provider", "model", "temperature", "top_p",
               "max_context", "domain", "persona", "orientation", "order", "role",
               "learning"}
    for k, v in changes.items():
        if k in allowed:
            setattr(agent, k, v)
    save_agent(agent)
    return agent


def delete_agent(agent_id: str) -> bool:
    p = _path(agent_id)
    if p.exists():
        p.unlink()
        return True
    return False


def praticiens(agents: list[Agent]) -> list[Agent]:
    return [a for a in agents if a.role == "praticien"]


def process_agent(agents: list[Agent], agent_id: str) -> Agent | None:
    for a in agents:
        if a.id == agent_id:
            return a
    return None
