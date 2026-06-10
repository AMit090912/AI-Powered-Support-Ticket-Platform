from tests.conftest import auth


def _ticket(client, token):
    return client.post("/tickets", json={"title": "t", "description": "d"}, headers=auth(token)).json()["id"]


def test_owner_can_add_and_list_comments(client, customer_token):
    tid = _ticket(client, customer_token)
    r = client.post(f"/tickets/{tid}/comments", json={"body": "hello"}, headers=auth(customer_token))
    assert r.status_code == 201
    lst = client.get(f"/tickets/{tid}/comments", headers=auth(customer_token))
    assert len(lst.json()) == 1
    assert lst.json()[0]["body"] == "hello"
    assert lst.json()[0]["author"]["email"] == "cust@x.com"


def test_agent_can_comment_on_any_ticket(client, customer_token, agent_token):
    tid = _ticket(client, customer_token)
    r = client.post(f"/tickets/{tid}/comments", json={"body": "agent here"}, headers=auth(agent_token))
    assert r.status_code == 201


def test_other_customer_cannot_comment(client, customer_token, agent_token):
    tid = client.post("/tickets", json={"title": "a", "description": "b"},
                      headers=auth(agent_token)).json()["id"]
    r = client.post(f"/tickets/{tid}/comments", json={"body": "x"}, headers=auth(customer_token))
    assert r.status_code == 403


def test_empty_comment_rejected(client, customer_token):
    tid = _ticket(client, customer_token)
    r = client.post(f"/tickets/{tid}/comments", json={"body": ""}, headers=auth(customer_token))
    assert r.status_code == 422
