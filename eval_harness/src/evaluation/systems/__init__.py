"""System runner registry (Task 1.4).

``build_system(name, config, retriever, generator)`` returns a ready runner.
"""

from __future__ import annotations

from ..config import Config
from ..generator import Generator
from ..models import SystemName
from ..retriever import Retriever
from .agentic_rag import AgenticRAG
from .base import BaseSystem
from .flare import FLARE
from .reranked_simple import RerankedSimple
from .self_rag import SelfRAG
from .simple_rag import SimpleRAG

SYSTEM_CLASSES: dict[str, type[BaseSystem]] = {
    SystemName.SIMPLE_RAG.value: SimpleRAG,
    SystemName.RERANKED_SIMPLE.value: RerankedSimple,
    SystemName.AGENTIC_RAG.value: AgenticRAG,
    SystemName.SELF_RAG.value: SelfRAG,
    SystemName.FLARE.value: FLARE,
}

ALL_SYSTEMS = list(SYSTEM_CLASSES.keys())


def build_system(name: str, config: Config, retriever: Retriever,
                 generator: Generator) -> BaseSystem:
    if name not in SYSTEM_CLASSES:
        raise ValueError(f"unknown system: {name!r}; choices: {ALL_SYSTEMS}")
    return SYSTEM_CLASSES[name](config, retriever, generator)


__all__ = ["SYSTEM_CLASSES", "ALL_SYSTEMS", "build_system", "BaseSystem",
           "SimpleRAG", "RerankedSimple", "AgenticRAG", "SelfRAG", "FLARE"]
