"""
Ticket CRUD tests: create, list, get by id, delete.
Filter and search query param tests.
"""


def test_create_ticket(client, auth_headers):
    res = client.post("/api/tickets/", headers=auth_headers, json={
        "title": "Cannot access my account",
        "description": "I keep getting a 403 error when trying to log into the portal.",
        "category": "General",
        "urgency": "High"
    })
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Cannot access my account"
    assert data["status"] == "Open"
    return data["id"]


def test_list_tickets(client, auth_headers):
    # Create a ticket first
    client.post("/api/tickets/", headers=auth_headers, json={
        "title": "List test ticket",
        "description": "Testing list endpoint with enough detail here.",
        "category": "General",
        "urgency": "Low"
    })

    res = client.get("/api/tickets/", headers=auth_headers)
    assert res.status_code == 200
    tickets = res.json()
    assert isinstance(tickets, list)
    assert len(tickets) >= 1


def test_list_tickets_filter_by_status(client, auth_headers):
    res = client.get("/api/tickets/?status=Open", headers=auth_headers)
    assert res.status_code == 200
    tickets = res.json()
    for t in tickets:
        assert t["status"] == "Open"


def test_list_tickets_search(client, auth_headers):
    # Create a uniquely-titled ticket
    client.post("/api/tickets/", headers=auth_headers, json={
        "title": "UniqueXYZ billing inquiry",
        "description": "Looking for help with billing details and payment methods.",
        "category": "General",
        "urgency": "Medium"
    })

    res = client.get("/api/tickets/?search=UniqueXYZ", headers=auth_headers)
    assert res.status_code == 200
    results = res.json()
    assert any("UniqueXYZ" in t["title"] for t in results)


def test_get_ticket_by_id(client, auth_headers):
    # Create a ticket
    create_res = client.post("/api/tickets/", headers=auth_headers, json={
        "title": "Get by ID test",
        "description": "This ticket is used to test the get-by-id endpoint.",
        "category": "General",
        "urgency": "Low"
    })
    ticket_id = create_res.json()["id"]

    res = client.get(f"/api/tickets/{ticket_id}", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == ticket_id
    assert data["title"] == "Get by ID test"


def test_get_ticket_not_found(client, auth_headers):
    res = client.get("/api/tickets/999999", headers=auth_headers)
    assert res.status_code == 404


def test_delete_ticket(client, auth_headers):
    # Create and then delete
    create_res = client.post("/api/tickets/", headers=auth_headers, json={
        "title": "Delete me",
        "description": "This ticket should be deleted by the delete test case.",
        "category": "General",
        "urgency": "Low"
    })
    ticket_id = create_res.json()["id"]

    del_res = client.delete(f"/api/tickets/{ticket_id}", headers=auth_headers)
    assert del_res.status_code in [200, 204]

    # Should no longer exist
    get_res = client.get(f"/api/tickets/{ticket_id}", headers=auth_headers)
    assert get_res.status_code == 404


def test_unauthenticated_access(client):
    res = client.get("/api/tickets/")
    assert res.status_code == 401
