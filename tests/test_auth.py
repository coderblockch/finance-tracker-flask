def test_login_page_ok(client):
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert b"Sign in" in response.data


def test_register_and_login(client, auth):
    response = auth.register()
    assert response.status_code == 200
    assert b"Account created" in response.data

    response = auth.login()
    assert response.status_code == 200
    assert b"Welcome back, tester" in response.data
    assert b"Dashboard" in response.data


def test_register_duplicate_username(client, auth):
    auth.register()
    response = auth.register()
    assert b"already taken" in response.data


def test_login_invalid_password(client, auth):
    auth.register()
    response = auth.login(password="wrong-password")
    assert b"Invalid username or password." in response.data


def test_protected_routes_redirect(client):
    for path in ("/", "/transactions", "/categories", "/summary"):
        response = client.get(path)
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]


def test_logout(client, auth):
    auth.register()
    auth.login()
    response = auth.logout()
    assert response.status_code == 200
    assert b"You have been signed out." in response.data
    follow = client.get("/")
    assert follow.status_code == 302
    assert "/auth/login" in follow.headers["Location"]
