import json
import logging
from typing import TypedDict, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from app.services.llm_service import generate_llm_response

logger = logging.getLogger(__name__)

# 1. Define State structure
class AgentState(TypedDict):
    query: str
    context: str
    decision: Optional[str]
    response: Optional[str]

# 2. Node Functions

def evaluator_node(state: AgentState) -> Dict[str, Any]:
    """
    Evaluator Node: Analyzes the query and retrieved context quality to decide the next path.
    """
    query = state["query"]
    context = state["context"]
    
    system_prompt = (
        "You are an AI Support Ticket Evaluator. Analyze the user's support query and retrieved context.\n"
        "Categorize the query into one of three triage paths:\n"
        "1. 'Answer': If the retrieved context is relevant and has sufficient info to fully answer the query.\n"
        "2. 'Clarify': If the query is vague, missing details, or requires clarifying questions to resolve.\n"
        "3. 'Escalate': If the query is completely unrelated to the company policies in the context, or explicitly requests human agents/billing updates.\n\n"
        "Respond ONLY with a JSON object: {\"decision\": \"Answer\" | \"Clarify\" | \"Escalate\", \"rationale\": \"brief rationale\"}"
    )
    user_prompt = f"Query: {query}\n\nRetrieved Context:\n{context}"
    
    response_str = generate_llm_response(system_prompt, user_prompt, json_mode=True)
    
    decision = "Answer"
    rationale = ""
    try:
        data = json.loads(response_str)
        decision = data.get("decision", "Answer")
        rationale = data.get("rationale", "")
        # Validate decision value
        if decision not in {"Answer", "Clarify", "Escalate"}:
            decision = "Answer"
    except Exception as e:
        logger.warning(f"Failed to parse evaluator response JSON: {response_str}. Exception: {e}")
        # Local keyword heuristics as fallback
        query_lower = query.lower()
        if any(w in query_lower for w in ["confused", "how", "what do you mean", "explain", "why"]):
            decision = "Clarify"
        elif any(w in query_lower for w in ["escalate", "human", "agent", "refund", "manager", "representative", "billing"]):
            decision = "Escalate"
        else:
            decision = "Answer"
            
    logger.info(f"Evaluator decision: {decision}. Rationale: {rationale}")
    return {"decision": decision}

def answer_node(state: AgentState) -> Dict[str, Any]:
    """
    Answer Node: Drafts a helpful customer support response using context.
    """
    query = state["query"]
    context = state["context"]
    
    system_prompt = (
        "You are an AI customer support specialist. Write a professional, friendly, and complete resolution "
        "answering the customer's query using the provided knowledge base context. Stick only to facts in the context."
    )
    user_prompt = f"Customer Query: {query}\n\nContext:\n{context}"
    
    response = generate_llm_response(system_prompt, user_prompt, json_mode=False)
    return {"response": response}

def clarify_node(state: AgentState) -> Dict[str, Any]:
    """
    Clarify Node: Drafts a polite request for clarification or missing details.
    """
    query = state["query"]
    
    system_prompt = (
        "You are a helpful AI customer support specialist. The user's query is either missing details or too vague. "
        "Ask a polite follow-up question to clarify their specific request (e.g. asking for order number, account email, or specific error codes)."
    )
    user_prompt = f"Vague Customer Query: {query}"
    
    response = generate_llm_response(system_prompt, user_prompt, json_mode=False)
    return {"response": response}

def escalate_node(state: AgentState) -> Dict[str, Any]:
    """
    Escalate Node: Prepares the customer for escalation to a human agent.
    """
    query = state["query"]
    
    system_prompt = (
        "You are a professional AI customer support specialist. The customer's request requires manual intervention, "
        "is complex, or specifically asks for a human. Let the customer know politely that you are escalating this "
        "ticket to a human support representative who will reach out via email shortly."
    )
    user_prompt = f"Customer Escalation Request: {query}"
    
    response = generate_llm_response(system_prompt, user_prompt, json_mode=False)
    return {"response": response}

# 3. Build & Compile LangGraph Workflow

def route_decision(state: AgentState) -> str:
    """
    Router function to guide transition from Evaluator to appropriate outcome node.
    """
    decision = state.get("decision", "Answer")
    if decision == "Clarify":
        return "clarify"
    elif decision == "Escalate":
        return "escalate"
    else:
        return "answer"

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("evaluator", evaluator_node)
workflow.add_node("answer", answer_node)
workflow.add_node("clarify", clarify_node)
workflow.add_node("escalate", escalate_node)

# Entry Point
workflow.set_entry_point("evaluator")

# Conditional Edges from Evaluator
workflow.add_conditional_edges(
    "evaluator",
    route_decision,
    {
        "answer": "answer",
        "clarify": "clarify",
        "escalate": "escalate"
    }
)

# Standard Edges to End
workflow.add_edge("answer", END)
workflow.add_edge("clarify", END)
workflow.add_edge("escalate", END)

# Compile LangGraph app
compiled_agent = workflow.compile()

def run_agent_triage(query: str, context: str) -> dict:
    """
    Runs the full LangGraph agent workflow.
    Returns: {"decision": "Answer"|"Clarify"|"Escalate", "response": str}
    """
    initial_state = {
        "query": query,
        "context": context,
        "decision": None,
        "response": None
    }
    
    final_state = compiled_agent.invoke(initial_state)
    return {
        "decision": final_state.get("decision", "Answer"),
        "response": final_state.get("response", "Could not process request.")
    }
