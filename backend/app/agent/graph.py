"""LangGraph 拓扑定义。

生产部署可将这些节点替换为异步模型调用；核心业务仍由可测试的 orchestrator 服务承载。
"""
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agent.state import AgentState


def route_after_intent(state: AgentState) -> Literal["clarify", "retrieve"]:
    return "clarify" if state["intent"].mode.value == "clarify" else "retrieve"


def route_after_retrieve(state: AgentState) -> Literal["simple_query", "plan"]:
    return "plan" if state["intent"].mode.value == "analysis" else "simple_query"


def build_topology():
    graph = StateGraph(AgentState)
    identity = lambda state: state
    for node in ("context", "intent", "clarify", "retrieve", "simple_query", "plan", "execute_dag", "analyze", "respond"):
        graph.add_node(node, identity)
    graph.add_edge(START, "context")
    graph.add_edge("context", "intent")
    graph.add_conditional_edges("intent", route_after_intent)
    graph.add_conditional_edges("retrieve", route_after_retrieve)
    graph.add_edge("clarify", END)
    graph.add_edge("simple_query", "respond")
    graph.add_edge("plan", "execute_dag")
    graph.add_edge("execute_dag", "analyze")
    graph.add_edge("analyze", "respond")
    graph.add_edge("respond", END)
    return graph.compile()

