import re
from app.auth.security import validate_password_strength, verify_password, hash_password


def get_token(client, path="/login"):
    resp = client.get(path)
    match = re.search(r'name="csrf_token"\s+value="([a-f0-9]+)"', resp.text)
    return match.group(1) if match else ""


def test_password_validation_rules():
    # Length < 8
    ok, err = validate_password_strength("Short1")
    assert not ok
    assert "8 characters" in err

    # No numbers
    ok, err = validate_password_strength("NoNumbersHere")
    assert not ok
    assert "number" in err

    # No letters
    ok, err = validate_password_strength("1234567890")
    assert not ok
    assert "letter" in err

    # Valid
    ok, err = validate_password_strength("ValidPass123")
    assert ok
    assert err == ""


def test_signup_success_and_login(client):
    csrf = get_token(client, "/signup")
    resp = client.post(
        "/signup",
        data={
            "username": "newcoder",
            "email": "newcoder@test.com",
            "password": "Password123",
            "confirm_password": "Password123",
            "name": "New Coder",
            "csrf_token": csrf
        },
        follow_redirects=False
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"

    # Verify session cookie was set
    assert "session" in resp.cookies


def test_signup_password_mismatch(client):
    csrf = get_token(client, "/signup")
    resp = client.post(
        "/signup",
        data={
            "username": "coder2",
            "email": "coder2@test.com",
            "password": "Password123",
            "confirm_password": "Password456",
            "name": "Coder",
            "csrf_token": csrf
        }
    )
    assert resp.status_code == 400
    assert "do not match" in resp.text


def test_login_invalid_credentials(client, test_user):
    csrf = get_token(client, "/login")
    resp = client.post(
        "/login",
        data={
            "identifier": "testuser",
            "password": "WrongPassword123",
            "csrf_token": csrf,
            "next": "/"
        }
    )
    assert resp.status_code == 401
    assert "Invalid credentials" in resp.text


def test_login_success(client, test_user):
    csrf = get_token(client, "/login")
    resp = client.post(
        "/login",
        data={
            "identifier": "testuser@example.com",
            "password": "Password123",
            "csrf_token": csrf,
            "next": "/"
        },
        follow_redirects=False
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"


def test_protected_routes_redirect_guest(client):
    resp = client.get("/history", follow_redirects=False)
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]

    resp = client.get("/profile", follow_redirects=False)
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]

    resp = client.get("/compare", follow_redirects=False)
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]


def test_logout(auth_client):
    resp = auth_client.get("/logout", follow_redirects=False)
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]
