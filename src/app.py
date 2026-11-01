"""Montagem das peças (composition root): dados, repositórios, tools, memória e orquestrador."""
from __future__ import annotations

from src.agent.orchestrator import AgentOrchestrator
from src.agent.tool_registry import ToolRegistry
from src.config import Settings
from src.data.loader import load_dataset
from src.data.repositories import OrderRepository, ProductRepository
from src.llm.base import LLMClient
from src.policies.sectioner import load_sections
from src.services.memory import Memory


def build_orchestrator(settings: Settings, llm: LLMClient) -> AgentOrchestrator:
    dataset = load_dataset(settings.raw_data_dir)
    memory = Memory(settings.history_db_path)
    registry = ToolRegistry(
        products=ProductRepository(dataset),
        orders=OrderRepository(dataset),
        policy_sections=load_sections(settings.policy_pdf),
        memory=memory,
        today_fn=lambda: settings.today,
        now_fn=lambda: settings.now,
    )
    return AgentOrchestrator(llm, registry, memory, max_iterations=settings.max_tool_iterations,
                             now_fn=lambda: settings.now)
