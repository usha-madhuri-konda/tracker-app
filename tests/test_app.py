PASSWORD = "correct-horse-battery"


def sign_up_and_log_in(client, username):
    client.post("/register", data={"username": username, "password": PASSWORD})
    return client.post(
        "/login",
        data={"username": username, "password": PASSWORD},
        follow_redirects=True,
    )


def test_healthz_needs_no_login(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"


def test_api_requires_login(client):
    response = client.get("/entries")
    assert response.status_code == 401
    assert response.get_json() == {"error": "authentication required"}


def test_register_and_login_reach_the_home_page(client):
    response = sign_up_and_log_in(client, "alice")
    assert response.status_code == 200
    assert "Add a learning entry" in response.get_data(as_text=True)


def test_wrong_password_is_rejected(client):
    client.post("/register", data={"username": "alice", "password": PASSWORD})
    response = client.post(
        "/login",
        data={"username": "alice", "password": "not-the-password"},
        follow_redirects=True,
    )
    assert "Invalid username or password." in response.get_data(as_text=True)
    assert client.get("/entries").status_code == 401


def test_create_and_list_entries(client):
    sign_up_and_log_in(client, "alice")
    created = client.post("/entries", json={"topic": "Docker", "hours_spent": 2})
    assert created.status_code == 201
    listed = client.get("/entries").get_json()
    assert [e["topic"] for e in listed] == ["Docker"]


def test_entry_without_topic_is_rejected(client):
    sign_up_and_log_in(client, "alice")
    response = client.post("/entries", json={"hours_spent": 1})
    assert response.status_code == 400


def test_users_cannot_see_each_others_entries(client, other_client):
    sign_up_and_log_in(client, "alice")
    entry_id = client.post("/entries", json={"topic": "Private"}).get_json()["id"]

    sign_up_and_log_in(other_client, "bob")
    assert other_client.get(f"/entries/{entry_id}").status_code == 404
    assert other_client.delete(f"/entries/{entry_id}").status_code == 404
    assert other_client.get("/entries").get_json() == []


def test_stage_can_be_created_and_updated(client):
    sign_up_and_log_in(client, "alice")
    created = client.post("/stages", json={"company": "Acme", "stage_name": "Applied"})
    assert created.status_code == 201
    stage_id = created.get_json()["id"]

    updated = client.put(f"/stages/{stage_id}", json={"stage_name": "Interview"})
    assert updated.status_code == 200
    assert updated.get_json()["stage_name"] == "Interview"

def test_database_connections_are_checked_before_use(client):
    options = client.application.config["SQLALCHEMY_ENGINE_OPTIONS"]
    assert options["pool_pre_ping"] is True
