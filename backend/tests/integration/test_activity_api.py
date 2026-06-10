from tests.conftest import auth


def test_activity_logs_created_and_status_change(client, customer_token, agent_token):
    tid = client.post("/tickets", json={"title": "t", "description": "d"},
                      headers=auth(customer_token)).json()["id"]
    client.patch(f"/tickets/{tid}", json={"status": "in_progress"}, headers=auth(agent_token))
    r = client.get(f"/tickets/{tid}/activity", headers=auth(customer_token))
    types = [e["event_type"] for e in r.json()]
    assert "created" in types
    assert "status_changed" in types


def test_activity_access_controlled(client, customer_token, agent_token):
    tid = client.post("/tickets", json={"title": "t", "description": "d"},
                      headers=auth(agent_token)).json()["id"]
    r = client.get(f"/tickets/{tid}/activity", headers=auth(customer_token))
    assert r.status_code == 403
