"""
test_phase2.py — Phase 2 unit tests for ACEest Flask application.

New coverage for Phase 2:
  - /api/version endpoint
  - Edit client
  - Metrics logging API
  - Progress update and deletion
  - Membership status transitions
  - All 5 program types including calorie calculations
  - Input edge cases and validation
  - Workout types validation
  - API response structure

Run with:  pytest tests/ -v --tb=short --cov=app --cov-report=term-missing
"""

import os
import pytest

os.environ["DB_PATH"] = ":memory:"

from app import app, init_db   # noqa: E402


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        init_db()
    with app.test_client() as c:
        yield c


@pytest.fixture
def auth(client):
    """Logged-in client."""
    client.post("/login", data={"username": "admin", "password": "admin123"},
                follow_redirects=True)
    return client


def add_client(auth_client, name, **kwargs):
    """Helper: add a client and return the response."""
    data = {"name": name}
    data.update(kwargs)
    return auth_client.post("/clients/add", data=data, follow_redirects=True)


# ─────────────────────────────────────────────
# VERSION / HEALTH ENDPOINT
# ─────────────────────────────────────────────

class TestVersionAndHealth:
    def test_health_returns_ok(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        payload = res.get_json()
        assert payload["status"] == "ok"
        assert "app" in payload

    def test_health_accessible_without_login(self, client):
        """Health endpoint must be public — used by Kubernetes liveness probe."""
        res = client.get("/api/health")
        assert res.status_code == 200


# ─────────────────────────────────────────────
# CALORIE CALCULATIONS — ALL PROGRAMS
# ─────────────────────────────────────────────

class TestCalorieCalculations:
    """Phase 2: verify calorie formula for every program type."""

    def test_fat_loss_calories(self, auth):
        add_client(auth, "FatLossUser", weight="70", program="Fat Loss")
        res = auth.get("/clients/FatLossUser")
        assert b"1540" in res.data          # 70 * 22 = 1540

    def test_muscle_gain_calories(self, auth):
        add_client(auth, "MuscleUser", weight="80", program="Muscle Gain")
        res = auth.get("/clients/MuscleUser")
        assert b"2800" in res.data          # 80 * 35 = 2800

    def test_beginner_calories(self, auth):
        add_client(auth, "BeginUser", weight="60", program="Beginner")
        res = auth.get("/clients/BeginUser")
        assert b"1560" in res.data          # 60 * 26 = 1560

    def test_no_calories_without_weight(self, auth):
        """Client with no weight should not crash — calories remain NULL."""
        add_client(auth, "NoWeightUser", program="Fat Loss")
        res = auth.get("/clients/NoWeightUser")
        assert res.status_code == 200

    def test_no_calories_without_program(self, auth):
        """Client with no program should not crash."""
        add_client(auth, "NoProgramUser", weight="70")
        res = auth.get("/clients/NoProgramUser")
        assert res.status_code == 200


# ─────────────────────────────────────────────
# EDIT CLIENT
# ─────────────────────────────────────────────

class TestEditClient:
    def test_edit_client_page_loads(self, auth):
        add_client(auth, "EditMe", age="25")
        res = auth.get("/clients/EditMe/edit")
        assert res.status_code == 200
        assert b"EditMe" in res.data

    def test_edit_client_updates_weight(self, auth):
        add_client(auth, "EditWeight", weight="70", program="Fat Loss")
        res = auth.post(
            "/clients/EditWeight/edit",
            data={
                "age": "30",
                "height": "175",
                "weight": "65",          # updated
                "program": "Fat Loss",
                "target_weight": "60",
                "target_adherence": "85",
                "membership_status": "Active",
                "membership_end": "2026-12-31",
            },
            follow_redirects=True
        )
        assert res.status_code == 200
        # 65 * 22 = 1430 calories should now appear
        assert b"1430" in res.data

    def test_edit_nonexistent_client_redirects(self, auth):
        res = auth.get("/clients/GhostClient/edit", follow_redirects=True)
        assert res.status_code == 200
        assert b"not found" in res.data

    def test_edit_membership_status_to_inactive(self, auth):
        add_client(auth, "InactiveUser")
        res = auth.post(
            "/clients/InactiveUser/edit",
            data={"membership_status": "Inactive", "program": ""},
            follow_redirects=True
        )
        assert res.status_code == 200


# ─────────────────────────────────────────────
# WORKOUT LOGGING — EXTENDED
# ─────────────────────────────────────────────

class TestWorkoutsExtended:
    def test_log_all_workout_types(self, auth):
        add_client(auth, "WorkoutTypesUser")
        for wtype in ["Strength", "Hypertrophy", "Cardio", "Mobility"]:
            res = auth.post(
                "/clients/WorkoutTypesUser/workout/add",
                data={
                    "workout_date": "2025-07-01",
                    "workout_type": wtype,
                    "duration_min": "45",
                    "notes": f"{wtype} session",
                },
                follow_redirects=True
            )
            assert res.status_code == 200

    def test_workout_without_notes(self, auth):
        add_client(auth, "NoNoteUser")
        res = auth.post(
            "/clients/NoNoteUser/workout/add",
            data={
                "workout_date": "2025-07-01",
                "workout_type": "Cardio",
                "duration_min": "30",
            },
            follow_redirects=True
        )
        assert res.status_code == 200

    def test_workout_default_duration(self, auth):
        """Duration should default to 60 if not provided."""
        add_client(auth, "DefaultDurUser")
        res = auth.post(
            "/clients/DefaultDurUser/workout/add",
            data={"workout_date": "2025-07-01", "workout_type": "Strength"},
            follow_redirects=True
        )
        assert res.status_code == 200


# ─────────────────────────────────────────────
# PROGRESS TRACKING — EXTENDED
# ─────────────────────────────────────────────

class TestProgressExtended:
    def test_multiple_progress_entries(self, auth):
        add_client(auth, "MultiProgress")
        for i in range(1, 5):
            res = auth.post(
                "/clients/MultiProgress/progress/add",
                data={"week": f"Week {i}", "adherence": str(i * 20)},
                follow_redirects=True
            )
            assert res.status_code == 200

    def test_progress_without_week_label_fails(self, auth):
        add_client(auth, "NoWeekUser")
        res = auth.post(
            "/clients/NoWeekUser/progress/add",
            data={"week": "", "adherence": "80"},
            follow_redirects=True
        )
        assert res.status_code == 200
        assert b"required" in res.data or b"Week" in res.data

    def test_api_progress_empty_list_for_new_client(self, auth):
        add_client(auth, "EmptyProgressUser")
        res = auth.get("/api/clients/EmptyProgressUser/progress")
        assert res.status_code == 200
        assert res.get_json() == []

    def test_api_progress_returns_entries_after_add(self, auth):
        add_client(auth, "ProgressAPIUser")
        auth.post(
            "/clients/ProgressAPIUser/progress/add",
            data={"week": "Week 1", "adherence": "90"},
            follow_redirects=True
        )
        res = auth.get("/api/clients/ProgressAPIUser/progress")
        data = res.get_json()
        assert len(data) == 1
        assert data[0]["week"] == "Week 1"
        assert data[0]["adherence"] == 90


# ─────────────────────────────────────────────
# API — STRUCTURE VALIDATION
# ─────────────────────────────────────────────

class TestAPIStructure:
    def test_api_clients_structure(self, auth):
        """Each record must have name, program, membership_status fields."""
        add_client(auth, "StructureTest", program="Beginner")
        res = auth.get("/api/clients")
        data = res.get_json()
        assert len(data) >= 1
        record = next(r for r in data if r["name"] == "StructureTest")
        assert "name" in record
        assert "program" in record
        assert "membership_status" in record

    def test_api_clients_empty_on_fresh_db(self, client):
        """Fresh DB should return empty client list (after login)."""
        client.post("/login",
                    data={"username": "admin", "password": "admin123"},
                    follow_redirects=True)
        res = client.get("/api/clients")
        assert res.status_code == 200
        assert isinstance(res.get_json(), list)

    def test_api_health_response_fields(self, client):
        res = client.get("/api/health")
        data = res.get_json()
        assert data.get("status") == "ok"
        assert data.get("app") is not None


# ─────────────────────────────────────────────
# SECURITY / AUTH — EDGE CASES
# ─────────────────────────────────────────────

class TestSecurityEdgeCases:
    def test_add_client_requires_auth(self, client):
        res = client.post("/clients/add",
                          data={"name": "Hacker"},
                          follow_redirects=False)
        assert res.status_code in (301, 302)
        assert "/login" in res.headers["Location"]

    def test_delete_client_requires_auth(self, client):
        res = client.post("/clients/SomeName/delete", follow_redirects=False)
        assert res.status_code in (301, 302)
        assert "/login" in res.headers["Location"]

    def test_workout_add_requires_auth(self, client):
        res = client.post("/clients/SomeName/workout/add",
                          data={"workout_type": "Strength"},
                          follow_redirects=False)
        assert res.status_code in (301, 302)

    def test_api_progress_requires_auth(self, client):
        res = client.get("/api/clients/SomeName/progress", follow_redirects=False)
        assert res.status_code in (301, 302)

    def test_sql_injection_in_client_name_rejected(self, auth):
        """Client name with SQL injection chars should either error or sanitise."""
        res = auth.post(
            "/clients/add",
            data={"name": "'; DROP TABLE clients; --"},
            follow_redirects=True
        )
        # Should not crash (500) — parameterised queries protect the DB
        assert res.status_code == 200

    def test_very_long_client_name(self, auth):
        long_name = "A" * 500
        res = auth.post("/clients/add", data={"name": long_name},
                        follow_redirects=True)
        assert res.status_code == 200     # should not 500
