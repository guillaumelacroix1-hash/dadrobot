"""Couche d'appel aux modèles : OpenRouter, Groq (OpenAI-compatible) et Claude.

Un seul point d'entrée `chat()` qui route selon le `provider` de l'agent.
Les erreurs (clé manquante, réseau) sont remontées proprement pour être
affichées dans le débat plutôt que de faire planter le serveur.

Les statuts transitoires (429 = quota momentané, 5xx = serveur amont) sont
réessayés avec un back-off exponentiel : les modèles gratuits sont souvent
throttlés quelques secondes avant de répondre normalement.
"""
from __future__ import annotations

import asyncio
import re

import httpx

from . import config

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

# Statuts qu'on réessaie (quota momentané / indisponibilité du serveur amont).
RETRYABLE = {429, 500, 502, 503, 504, 529}

# Les modèles « raisonneurs » (Qwen3, R1…) émettent leur réflexion entre
# <think>…</think> : on la retire avant affichage dans le débat.
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _clean(text: str) -> str:
    return _THINK_RE.sub("", text or "").strip()


class LLMError(RuntimeError):
    """Erreur d'appel modèle, transformée en message lisible dans le débat."""


async def _post_retry(client, url, headers, payload, tries: int = 4):
    """POST avec back-off exponentiel sur les statuts transitoires (429/5xx).

    Respecte l'en-tête `Retry-After` s'il est fourni, plafonné à 8 s.
    """
    delay = 1.0
    resp = None
    for attempt in range(tries):
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code in RETRYABLE and attempt < tries - 1:
            retry_after = resp.headers.get("retry-after")
            try:
                wait = float(retry_after) if retry_after else delay
            except ValueError:
                wait = delay
            await asyncio.sleep(min(wait, 8.0))
            delay *= 2
            continue
        return resp
    return resp


async def chat(
    provider: str,
    model: str,
    system: str,
    user: str,
    temperature: float = 0.7,
    top_p: float = 0.95,
    max_tokens: int = 1200,
) -> str:
    provider = (provider or "openrouter").lower()
    try:
        if provider == "anthropic":
            return await _anthropic(model, system, user, temperature, max_tokens)
        if provider == "groq":
            return await _openai_compat(
                GROQ_URL, config.GROQ_API_KEY, model, system, user,
                temperature, top_p, max_tokens,
            )
        # défaut : openrouter
        return await _openai_compat(
            OPENROUTER_URL, config.OPENROUTER_API_KEY, model, system, user,
            temperature, top_p, max_tokens,
            extra_headers={
                "HTTP-Referer": "https://github.com/guillaumelacroix1-hash/dadrobot",
                "X-Title": "Aletheia",
            },
        )
    except LLMError:
        raise
    except httpx.HTTPStatusError as e:
        raise LLMError(f"{provider}: HTTP {e.response.status_code} — {e.response.text[:200]}")
    except Exception as e:  # noqa: BLE001
        raise LLMError(f"{provider}: {e}")


async def _openai_compat(
    url: str, api_key: str, model: str, system: str, user: str,
    temperature: float, top_p: float, max_tokens: int,
    extra_headers: dict | None = None,
) -> str:
    if not api_key:
        raise LLMError(f"clé API manquante pour {url.split('/')[2]}")
    # User-Agent explicite : l'edge de Groq renvoie 403 sur le UA par défaut des
    # clients Python (urllib/httpx). Sans rapport pour OpenRouter, mais inoffensif.
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
               "User-Agent": "Mozilla/5.0 (compatible; Aletheia/1.0)"}
    if extra_headers:
        headers.update(extra_headers)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        r = await _post_retry(client, url, headers, payload)
        r.raise_for_status()
        data = r.json()
    return _clean(data["choices"][0]["message"]["content"])


async def _anthropic(
    model: str, system: str, user: str, temperature: float, max_tokens: int,
) -> str:
    if not config.ANTHROPIC_API_KEY:
        raise LLMError("ANTHROPIC_API_KEY manquante")
    headers = {
        "x-api-key": config.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    async with httpx.AsyncClient(timeout=120) as client:
        r = await _post_retry(client, ANTHROPIC_URL, headers, payload)
        r.raise_for_status()
        data = r.json()
    parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
    return _clean("".join(parts))
