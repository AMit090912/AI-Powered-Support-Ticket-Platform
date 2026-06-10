from tests.conftest import auth


def test_analytics_requires_agent(client, customer_token):
    assert client.get("/analytics/summary", headers=auth(customer_token)).status_code == 403


def test_analytics_summary_counts(client, customer_token, agent_token):
    for i in range(2):
        client.post("/tickets", json={"title": f"t{i}", "description": "d"}, headers=auth(customer_token))
    r = client.get("/analytics/summary", headers=auth(agent_token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 2
    assert "by_category" in body and "by_priority" in body
