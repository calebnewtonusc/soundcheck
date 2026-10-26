from fastapi.testclient import TestClient

from backend import main


def test_room_members_on_one_wifi_are_never_rate_limited():
    # 2026-10-26 load test: friends on one dorm WiFi share an IP and each
    # poll once a second; the old per-IP cap blocked the room in a minute.
    main.lookups.clear()
    with TestClient(main.app) as c:
        code = c.post("/api/rooms").json()["code"]
        creds = [c.post(f"/api/rooms/{code}/join-sample", json={"name": f"P{i}"}).json() for i in range(12)]
        for _ in range(20):
            for cr in creds:
                assert c.get(f"/api/rooms/{code}", params=cr).status_code == 200


def test_strangers_guessing_codes_are_limited():
    main.lookups.clear()
    with TestClient(main.app) as c:
        code = c.post("/api/rooms").json()["code"]
        codes = [c.get(f"/api/rooms/{code}").status_code for _ in range(main.LOOKUP_LIMIT + 5)]
        assert codes[-1] == 429
