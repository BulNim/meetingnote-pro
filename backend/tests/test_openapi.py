"""7. Swagger UI - API 26개 · 6묶음 태그 · Bearer Authorize"""
HTTP_METHODS = {"get", "post", "put", "delete"}

EXPECTED = {
    "auth": 5, "team": 6, "meeting": 6, "todo": 4, "comment": 3, "activity": 2,
}


def operations(client):
    spec = client.get("/openapi.json").json()
    return spec, [
        (method.upper(), path, op)
        for path, item in spec["paths"].items()
        for method, op in item.items()
        if method in HTTP_METHODS
    ]


def test_경로_메서드_조합이_정확히_26개(client):
    _, ops = operations(client)
    assert len(ops) == 26


def test_모든_경로가_api_접두사(client):
    _, ops = operations(client)
    assert all(path.startswith("/api/") for _, path, _ in ops)


def test_태그_6묶음별_개수(client):
    _, ops = operations(client)
    counts = {}
    for _, _, op in ops:
        assert len(op["tags"]) == 1
        counts[op["tags"][0]] = counts.get(op["tags"][0], 0) + 1
    assert counts == EXPECTED


def test_Authorize는_Bearer_JWT(client):
    spec, _ = operations(client)
    schemes = spec["components"]["securitySchemes"]
    assert any(s.get("type") == "http" and s.get("scheme") == "bearer" for s in schemes.values())


def test_docs_화면이_열린다(client):
    r = client.get("/docs")
    assert r.status_code == 200 and "swagger" in r.text.lower()
