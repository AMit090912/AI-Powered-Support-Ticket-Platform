from tests.conftest import auth


def test_register_returns_201_and_user(client):
    r = client.post("/auth/register", json={
        "email": "a@x.com", "password": "secret1", "full_name": "A", "role": "customer"})
    assert r.status_code == 201
    assert r.json()["email"] == "a@x.com"
    assert "hashed_password" not in r.json()


def test_duplicate_email_returns_409(client):
    body = {"email": "a@x.com", "password": "secret1", "full_name": "A", "role": "customer"}
    client.post("/auth/register", json=body)
    r = client.post("/auth/register", json=body)
    assert r.status_code == 409


def test_login_returns_token(client):
    client.post("/auth/register", json={
        "email": "a@x.com", "password": "secret1", "full_name": "A", "role": "customer"})
    r = client.post("/auth/login", json={"email": "a@x.com", "password": "secret1"})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"


def test_login_wrong_password_401(client):
    client.post("/auth/register", json={
        "email": "a@x.com", "password": "secret1", "full_name": "A", "role": "customer"})
    r = client.post("/auth/login", json={"email": "a@x.com", "password": "nope"})
    assert r.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/auth/me").status_code == 401


def test_me_returns_current_user(client, customer_token):
    r = client.get("/auth/me", headers=auth(customer_token))
    assert r.status_code == 200
    assert r.json()["role"] == "customer"
