"""테스트 공통 도우미"""


def signup(client, email="kim@example.com", name="김대리", password="password123"):
    r = client.post("/api/auth/signup", json={"email": email, "password": password, "name": name})
    assert r.status_code == 201, r.text
    data = r.json()
    return {"Authorization": f"Bearer {data['token']}"}, data["user"]


def make_team(client, headers, name="기획팀"):
    r = client.post("/api/teams", json={"name": name}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def join_team(client, headers, code):
    return client.post("/api/teams/join", json={"invite_code": code}, headers=headers)
