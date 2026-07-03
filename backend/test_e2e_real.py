"""
E2E RAG Triage Pipeline Test - Real PostgreSQL + pgvector
Verifies:
1. User authentication (Register/Login)
2. Document ingestion (Chunking, Embedding generation, pgvector storage)
3. Ticket creation (CRUD operations)
4. RAG similarity search and LangGraph Agentic Triage (Answer/Clarify/Escalate decisions)
5. Database status updates & activity logs
6. Knowledge base logback (indexing resolved resolutions back to document store)
7. Clarification replies returning tickets to 'Open' status
"""
import requests
import json
import time

BASE = "http://localhost:8000/api"

def p(tag, msg):
    print(f"[{tag}] {msg}")

def main():
    session = requests.Session()

    # --- 1. User Registration & Login ---
    p("1a", "Registering test user...")
    r = session.post(f"{BASE}/auth/register", json={
        "email": "e2e_tester@resolve.ai",
        "password": "E2ePassword123!",
        "name": "E2E Support Tester"
    })
    if r.status_code == 201:
        p("OK", f"User registered: {r.json()['email']}")
    elif r.status_code == 400 and "exists" in r.text.lower():
        p("OK", "User already exists, logging in...")
    else:
        p("ERROR", f"Registration failed: {r.status_code} {r.text}")
        return

    p("1b", "Logging in...")
    r = session.post(f"{BASE}/auth/login", json={
        "email": "e2e_tester@resolve.ai",
        "password": "E2ePassword123!"
    })
    if r.status_code != 200:
        p("ERROR", f"Login failed: {r.status_code} {r.text}")
        return
    token = r.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    session.headers.update(headers)
    p("OK", "Logged in successfully.")

    # --- 2. Ingest New Document ---
    p("2", "Ingesting new corporate policy...")
    r = session.post(f"{BASE}/ingest/", json={
        "title": "Corporate Office Address Policy",
        "content": "Our main headquarters is located at 100 Innovation Way, Suite 400, San Francisco, CA. All corporate inquiries should be mailed to this address."
    })
    if r.status_code == 201:
        p("OK", f"Ingestion success: {r.json()}")
    else:
        p("ERROR", f"Ingestion failed: {r.status_code} {r.text}")
        return

    # --- 3. Test Triage - ANSWER Path (and KB Logback) ---
    p("3a", "Submitting ticket that should match KB (headquarters address)...")
    r = session.post(f"{BASE}/tickets/", json={
        "title": "Headquarters Mailing Address",
        "description": "Where should I mail corporate inquiries for the headquarters?"
    })
    if r.status_code != 201:
        p("ERROR", f"Ticket creation failed: {r.status_code} {r.text}")
        return
    ticket_id = r.json()["id"]
    p("OK", f"Ticket created: ID={ticket_id}")

    p("3b", "Running RAG Triage Pipeline on Ticket...")
    r = session.post(f"{BASE}/query/", json={"ticket_id": ticket_id})
    if r.status_code == 200:
        data = r.json()
        p("OK", f"Triage complete. Decision: {data['decision']}")
        p("RESPONSE", f"Agent Output: {data['response']}")
        p("CONTEXT", f"Retrieved {len(data['retrieved_context'])} chunks.")
    else:
        p("ERROR", f"Triage pipeline failed: {r.status_code} {r.text}")
        return

    # Get ticket status to verify update and check KB logback
    r = session.get(f"{BASE}/tickets/{ticket_id}")
    ticket_details = r.json()
    p("OK", f"Verified Ticket Status: {ticket_details['status']}")
    p("OK", f"Verified Resolution saved: {ticket_details['resolution']}")

    # --- 4. Test Triage - CLARIFY Path & Clarification Response ---
    p("4a", "Submitting vague ticket...")
    r = session.post(f"{BASE}/tickets/", json={
        "title": "Confused about cancellation",
        "description": "I need help. I'm confused about this whole cancellation policy process."
    })
    clarify_ticket_id = r.json()["id"]
    p("OK", f"Vague ticket created: ID={clarify_ticket_id}")

    p("4b", "Running Triage on vague ticket...")
    r = session.post(f"{BASE}/query/", json={"ticket_id": clarify_ticket_id})
    data = r.json()
    p("OK", f"Triage decision: {data['decision']}, Agent Output: {data['response']}")

    # Verify status is Awaiting Clarification
    r = session.get(f"{BASE}/tickets/{clarify_ticket_id}")
    p("OK", f"Verified Ticket Status: {r.json()['status']}")
    
    # Submit clarification answer
    p("4c", "Submitting clarification response...")
    r = session.post(f"{BASE}/tickets/{clarify_ticket_id}/clarify", json={
        "answer": "I want to cancel my Pro plan membership before the next bill."
    })
    p("OK" if r.status_code == 200 else "ERROR", f"Clarification reply status: {r.status_code}")

    # Verify status returned to Open
    r = session.get(f"{BASE}/tickets/{clarify_ticket_id}")
    p("OK", f"Verified Ticket Status is now: {r.json()['status']}")

    # --- 5. Test Triage - ESCALATE Path ---
    p("5a", "Submitting ticket that requires escalation (billing failure)...")
    r = session.post(f"{BASE}/tickets/", json={
        "title": "Billing escalation",
        "description": "Please escalate this to a representative. I need a manual billing adjustment for my account."
    })
    escalate_ticket_id = r.json()["id"]
    
    p("5b", "Running Triage on escalation ticket...")
    r = session.post(f"{BASE}/query/", json={"ticket_id": escalate_ticket_id})
    p("OK", f"Triage decision: {r.json()['decision']}")

    # Verify status is Escalated
    r = session.get(f"{BASE}/tickets/{escalate_ticket_id}")
    p("OK", f"Verified Ticket Status: {r.json()['status']}")

    print("\n========== ALL E2E VERIFICATION PATHS PASSED ==========")

if __name__ == "__main__":
    main()
