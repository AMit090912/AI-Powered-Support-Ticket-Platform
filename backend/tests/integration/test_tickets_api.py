from tests.conftest import auth


def _create(client, token, title="Cannot login", desc="I forgot my password, locked out"):
    return client.post("/tickets", json={"title": title, "description": desc}, headers=auth(token))


def test_create_ticket_runs_triage(client, customer_token):
    r = _create(client, customer_token)
    assert r.status_code == 201
    body = r.json()
    # rule-based fallback (no GEMINI key in tests) -> account_access
    assert body["category"] == "account_access"
    assert body["status"] == "open"
    assert body["suggested_response"]


def test_customer_only_sees_own_tickets(client, customer_token, agent_token):
    _create(client, customer_token, "Mine", "x")
    client.post("/tickets", json={"title": "AgentTicket", "description": "y"}, headers=auth(agent_token))
    r = client.get("/tickets", headers=auth(customer_token))
    titles = [t["title"] for t in r.json()["items"]]
    assert "Mine" in titles
    assert "AgentTicket" not in titles


def test_agent_sees_all_tickets(client, customer_token, agent_token):
    _create(client, customer_token, "CustTicket", "x")
    r = client.get("/tickets", headers=auth(agent_token))
    assert r.json()["total"] >= 1


def test_search_by_title(client, customer_token):
    _create(client, customer_token, "Billing refund please", "charge twice")
    _create(client, customer_token, "App crash", "it broke")
    r = client.get("/tickets?q=refund", headers=auth(customer_token))
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["title"] == "Billing refund please"


def test_filter_by_status(client, customer_token, agent_token):
    cr = _create(client, customer_token, "ToResolve", "x")
    tid = cr.json()["id"]
    client.patch(f"/tickets/{tid}", json={"status": "resolved"}, headers=auth(agent_token))
    r = client.get("/tickets?status=resolved", headers=auth(agent_token))
    assert all(t["status"] == "resolved" for t in r.json()["items"])
    assert r.json()["total"] >= 1


def test_pagination(client, customer_token):
    for i in range(3):
        _create(client, customer_token, f"T{i}", "x")
    r = client.get("/tickets?page=1&page_size=2", headers=auth(customer_token))
    assert len(r.json()["items"]) == 2
    assert r.json()["total"] == 3


def test_customer_cannot_patch_ticket(client, customer_token):
    tid = _create(client, customer_token).json()["id"]
    r = client.patch(f"/tickets/{tid}", json={"status": "resolved"}, headers=auth(customer_token))
    assert r.status_code == 403


def test_agent_can_assign_ticket(client, customer_token, agent_token):
    tid = _create(client, customer_token).json()["id"]
    agents = client.get("/users/agents", headers=auth(agent_token)).json()
    agent_id = agents[0]["id"]
    r = client.patch(f"/tickets/{tid}", json={"assigned_to_id": agent_id}, headers=auth(agent_token))
    assert r.status_code == 200
    assert r.json()["assigned_to"]["id"] == agent_id


def test_customer_cannot_view_others_ticket(client, customer_token, agent_token):
    tid = client.post("/tickets", json={"title": "secret", "description": "z"},
                      headers=auth(agent_token)).json()["id"]
    r = client.get(f"/tickets/{tid}", headers=auth(customer_token))
    assert r.status_code == 403


def test_get_missing_ticket_404(client, agent_token):
    assert client.get("/tickets/9999", headers=auth(agent_token)).status_code == 404
