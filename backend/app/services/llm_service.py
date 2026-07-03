import json
import logging
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

def generate_llm_response(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    """
    Sends a prompt to the LLM (NVIDIA NIM) or falls back to mock responses.
    """
    if not settings.NVIDIA_NIM_API_KEY:
        logger.info("NVIDIA_NIM_API_KEY not configured. Using local rule-based fallback response.")
        return _local_mock_llm_response(system_prompt, user_prompt, json_mode)
        
    try:
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=settings.NVIDIA_NIM_API_KEY
        )
        
        extra_args = {}
        if json_mode:
            extra_args["response_format"] = {"type": "json_object"}
            
        response = client.chat.completions.create(
            model=settings.NIM_LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=1024,
            **extra_args
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logger.warning(f"Error calling NVIDIA NIM LLM API: {e}. Falling back to rule-based mock responses.")
        return _local_mock_llm_response(system_prompt, user_prompt, json_mode)

def _local_mock_llm_response(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    """
    Heuristic-based local fallback mock LLM engine.
    Analyses user inputs and retrieves appropriate responses to simulate a real agent.
    """
    # Extract the query part specifically to avoid matching keywords inside the retrieved context
    if "\n\ncontext:" in user_prompt.lower():
        query_part = user_prompt.lower().split("\n\ncontext:")[0]
    elif "\n\nretrieved context:" in user_prompt.lower():
        query_part = user_prompt.lower().split("\n\nretrieved context:")[0]
    else:
        query_part = user_prompt.lower()

    # 1. Check if the prompt is asking to parse / evaluate a query (this is what the agent evaluator does)
    if "decision" in system_prompt.lower() or "route" in system_prompt.lower() or json_mode:
        # Determine the decision path
        # Check for clarification signals
        if any(w in query_part for w in ["confused", "how", "what do you mean", "explain", "why"]):
            decision = "Clarify"
            content = "Could you please provide more details or specify your order ID so I can assist you better?"
        # Check for escalation signals
        elif any(w in query_part for w in ["escalate", "human", "agent", "refund", "manager", "representative", "billing"]):
            decision = "Escalate"
            content = "This issue requires manual intervention. I have escalated this ticket to a human support agent."
        else:
            decision = "Answer"
            if "headquarters" in query_part or "address" in query_part:
                content = "Our main headquarters is located at 100 Innovation Way, Suite 400, San Francisco, CA. Please mail all corporate inquiries to this address."
            else:
                content = "Based on our company policy, we support standard refunds within 30 days of purchase."
            
        return json.dumps({
            "decision": decision,
            "content": content
        })

    # 2. General text responses
    if "clarify" in system_prompt.lower():
        return "Could you please elaborate on your request or provide your account username?"
    elif "escalate" in system_prompt.lower():
        return "Your ticket has been escalated to our senior human agent team for manual review."
    else:
        if "headquarters" in query_part or "address" in query_part:
            return "Our main headquarters is located at 100 Innovation Way, Suite 400, San Francisco, CA. Please mail all corporate inquiries to this address."
        return "Here is a standard answer based on the knowledge base: Standard subscription plans renew automatically every month unless cancelled at least 24 hours prior to the billing date."
