from typing import Any

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import BaseMessage

from .nodes import (
    plan_research,
    web_research,
    extract_entities,
    build_profile,
    store_results,
    should_continue,
    chat_node,
)
from .state import ResearchState, ChatState


def build_research_graph() -> CompiledStateGraph:  # type: ignore[type-arg]
    graph = StateGraph(ResearchState)

    graph.add_node("plan_research", plan_research)  # type: ignore[arg-type]
    graph.add_node("web_research", web_research)  # type: ignore[arg-type]
    graph.add_node("extract_entities", extract_entities)  # type: ignore[arg-type]
    graph.add_node("build_profile", build_profile)  # type: ignore[arg-type]
    graph.add_node("store_results", store_results)  # type: ignore[arg-type]

    graph.set_entry_point("plan_research")
    graph.add_edge("plan_research", "web_research")
    graph.add_edge("web_research", "extract_entities")
    graph.add_edge("extract_entities", "build_profile")
    graph.add_conditional_edges("build_profile", should_continue)
    graph.add_edge("store_results", END)

    return graph.compile()


def build_chat_graph() -> CompiledStateGraph:  # type: ignore[type-arg]
    graph = StateGraph(ChatState)

    graph.add_node("chat", chat_node)  # type: ignore[arg-type]

    graph.set_entry_point("chat")
    graph.add_edge("chat", END)

    return graph.compile()
