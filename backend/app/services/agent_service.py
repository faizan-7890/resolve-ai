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
    critique_feedback: Optional[str]
    critique_count: int

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

def writer_node(state: AgentState) -> Dict[str, Any]:
    """
    Writer Node: Drafts or refines a helpful customer support response using context.
    """
    query = state["query"]
    context = state["context"]
    feedback = state.get("critique_feedback", None)
    
    system_prompt = (
        "You are an AI customer support specialist writer. Write a professional, friendly, and complete resolution "
        "answering the customer's query using the provided knowledge base context. Stick only to facts in the context.\n"
    )
    if feedback:
        system_prompt += (
            f"An Auditor audited your previous draft and rejected it with the following feedback:\n"
            f"'{feedback}'\n"
            f"Please revise your draft to address this feedback, ensuring it remains strictly grounded in the context facts."
        )
        
    user_prompt = f"Customer Query: {query}\n\nContext:\n{context}"
    if state.get("response"):
        user_prompt += f"\n\nPrevious Draft:\n{state['response']}"
        
    response = generate_llm_response(system_prompt, user_prompt, json_mode=False)
    return {"response": response}

def auditor_node(state: AgentState) -> Dict[str, Any]:
    """
    Auditor Node: Critiques the draft response against policy facts to prevent hallucinations.
    """
    query = state["query"]
    context = state["context"]
    response = state["response"]
    count = state.get("critique_count", 0) + 1
    
    system_prompt = (
        "You are an AI Support Ticket Auditor. Audit the drafted support response against the query and retrieved context.\n"
        "Verify that:\n"
        "1. Every claim in the draft is directly supported by the context. (No hallucination/speculation).\n"
        "2. The draft directly answers the customer query.\n\n"
        "If it meets all criteria, respond ONLY with a JSON object: {\"passed\": true, \"feedback\": \"\"}\n"
        "If it fails (e.g. references a refund or address not in context, or is incomplete), respond ONLY with JSON: "
        "{\"passed\": false, \"feedback\": \"detailed reason of what is incorrect or missing\"}"
    )
    user_prompt = f"Customer Query: {query}\n\nRetrieved Context:\n{context}\n\nDrafted Response:\n{response}"
    
    feedback_str = generate_llm_response(system_prompt, user_prompt, json_mode=True)
    
    passed = True
    feedback = ""
    try:
        data = json.loads(feedback_str)
        passed = data.get("passed", True)
        feedback = data.get("feedback", "")
    except Exception as e:
        logger.warning(f"Failed to parse auditor response JSON: {feedback_str}. Exception: {e}")
        passed = True
        feedback = ""
        
    logger.info(f"Critique Round {count}: Passed={passed}. Feedback: {feedback}")
    return {"critique_feedback": feedback, "critique_count": count, "decision": "Done" if passed else "Retry"}

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
        return "writer"

def route_critique(state: AgentState) -> str:
    """
    Router function from Auditor to check if loop back is needed or complete.
    """
    decision = state.get("decision", "Done")
    count = state.get("critique_count", 0)
    
    if decision == "Retry" and count < 2:
        return "retry"
    else:
        return "end"

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("evaluator", evaluator_node)
workflow.add_node("writer", writer_node)
workflow.add_node("auditor", auditor_node)
workflow.add_node("clarify", clarify_node)
workflow.add_node("escalate", escalate_node)

# Entry Point
workflow.set_entry_point("evaluator")

# Conditional Edges from Evaluator
workflow.add_conditional_edges(
    "evaluator",
    route_decision,
    {
        "writer": "writer",
        "clarify": "clarify",
        "escalate": "escalate"
    }
)

# Standard Edges
workflow.add_edge("writer", "auditor")

# Conditional Edges from Auditor
workflow.add_conditional_edges(
    "auditor",
    route_critique,
    {
        "retry": "writer",
        "end": END
    }
)

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
        "response": None,
        "critique_feedback": None,
        "critique_count": 0
    }
    
    final_state = compiled_agent.invoke(initial_state)
    
    decision = final_state.get("decision", "Answer")
    if decision in {"Done", "Retry"}:
        decision = "Answer"
        
    return {
        "decision": decision,
        "response": final_state.get("response", "Could not process request.")
    }


async def stream_agent_triage(query: str, context: str):
    """
    Async generator that runs the LangGraph agent and yields SSE-format JSON events
    at each node transition for real-time frontend streaming.

    Yields strings in the format: 'data: <json>\\n\\n'
    """
    import asyncio

    def _emit(event: dict) -> str:
        return f"data: {json.dumps(event)}\n\n"

    # Step 1: Retrieval context notice
    chunk_count = len([c for c in context.split("[Doc:") if c.strip()])
    yield _emit({"step": "retrieval", "status": "done", "detail": f"Retrieved {chunk_count} knowledge base chunk(s)."})
    await asyncio.sleep(0)

    # Step 2: Evaluator
    yield _emit({"step": "evaluator", "status": "running", "detail": "Evaluating query and triage path..."})
    await asyncio.sleep(0)

    initial_state: AgentState = {
        "query": query,
        "context": context,
        "decision": None,
        "response": None,
        "critique_feedback": None,
        "critique_count": 0
    }

    # Run evaluator
    eval_result = evaluator_node(initial_state)
    decision = eval_result.get("decision", "Answer")
    yield _emit({"step": "evaluator", "status": "done", "decision": decision})
    await asyncio.sleep(0)

    current_state: AgentState = {**initial_state, **eval_result}

    # Step 3: Route to writer / clarify / escalate
    if decision == "Clarify":
        yield _emit({"step": "clarify", "status": "running", "detail": "Drafting clarification question..."})
        await asyncio.sleep(0)
        clarify_result = clarify_node(current_state)
        current_state = {**current_state, **clarify_result}
        yield _emit({"step": "clarify", "status": "done"})
        await asyncio.sleep(0)

    elif decision == "Escalate":
        yield _emit({"step": "escalate", "status": "running", "detail": "Preparing escalation message..."})
        await asyncio.sleep(0)
        escalate_result = escalate_node(current_state)
        current_state = {**current_state, **escalate_result}
        yield _emit({"step": "escalate", "status": "done"})
        await asyncio.sleep(0)

    else:
        # Writer → Auditor loop (max 2 retries)
        for attempt in range(3):
            yield _emit({"step": "writer", "status": "running", "detail": f"Drafting support response (attempt {attempt + 1})..."})
            await asyncio.sleep(0)
            writer_result = writer_node(current_state)
            current_state = {**current_state, **writer_result}
            yield _emit({"step": "writer", "status": "done"})
            await asyncio.sleep(0)

            yield _emit({"step": "auditor", "status": "running", "detail": "Auditing draft for accuracy..."})
            await asyncio.sleep(0)
            auditor_result = auditor_node(current_state)
            current_state = {**current_state, **auditor_result}
            passed = current_state.get("decision") != "Retry"
            yield _emit({
                "step": "auditor",
                "status": "done",
                "passed": passed,
                "feedback": current_state.get("critique_feedback", "") if not passed else ""
            })
            await asyncio.sleep(0)

            if passed or attempt >= 1:
                break

    # Final outcome
    final_decision = current_state.get("decision", "Answer")
    if final_decision in {"Done", "Retry"}:
        final_decision = decision  # use evaluator's original decision

    yield _emit({
        "step": "complete",
        "status": "done",
        "decision": final_decision,
        "response": current_state.get("response", "Could not process request.")
    })
