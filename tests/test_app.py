"""
test_app.py — Unit tests for ACEest Flask application.

Run with:  pytest tests/test_app.py -v
"""

import os
import pytest

# Point the app at an in-memory / temp database before importing
os.environ["DB_PATH"] = ":memory:"

# Now import the app
from app import app, init_db


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────
@pytest.fixture
def client():
    """Create a test client with a fresh in-memory database."""
    app.config["TESTING"]       = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        init_db()          # create tables + default admin

    with app.test_client() as c:
        yield c


@pytest.fixture
def logged_in_client(client):
    """Returns a test client that is already logged in as admin."""
    client.post("/login", data={"username": "admin", "password": "admin123"},
                follow_redirects=True)
    return client


# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────
class TestHealth:
    def test_health_endpoint_returns_ok(self, client):
        """GET /api/health should return 200 and status ok."""
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "ok"
        assert "app" in data


# ─────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────
class TestAuthentication:
    def test_root_redirects_unauthenticated_user_to_login(self, client):
        """Unauthenticated GET / should redirect to /login."""
        res = client.get("/", follow_redirects=False)
        assert res.status_code in (301, 302)
        assert "/login" in res.headers["Location"]

    def test_login_page_loads(self, client):
        """GET /login should return 200."""
        res = client.get("/login")
        assert res.status_code == 200
        assert b"ACEest" in res.data

    def test_valid_login_redirects_to_dashboard(self, client):
        """POST /login with correct credentials should redirect to dashboard."""
        res = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False
        )
        assert res.status_code in (301, 302)
        assert "/dashboard" in res.headers["Location"]

    def test_invalid_login_stays_on_login_page(self, client):
        """POST /login with wrong password should stay on login page."""
        res = client.post(
            "/login",
            data={"username": "admin", "password": "wrongpass"},
            follow_redirects=True
        )
        assert res.status_code == 200
        # Should show error message
        assert b"Invalid" in res.data

    def test_logout_clears_session(self, logged_in_client):
        """GET /logout should redirect to login."""
        res = logged_in_client.get("/logout", follow_redirects=False)
        assert res.status_code in (301, 302)
        assert "/login" in res.headers["Location"]

    def test_dashboard_requires_login(self, client):
        """GET /dashboard without login should redirect to /login."""
        res = client.get("/dashboard", follow_redirects=False)
        assert res.status_code in (301, 302)
        assert "/login" in res.headers["Location"]


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────
class TestDashboard:
    def test_dashboard_loads_for_logged_in_user(self, logged_in_client):
        """GET /dashboard after login should return 200."""
        res = logged_in_client.get("/dashboard")
        assert res.status_code == 200
        assert b"Dashboard" in res.data

    def test_dashboard_shows_client_count(self, logged_in_client):
        """Dashboard should include stats section."""
        res = logged_in_client.get("/dashboard")
        assert res.status_code == 200
        assert b"Total Clients" in res.data


# ─────────────────────────────────────────────
# CLIENT MANAGEMENT
# ─────────────────────────────────────────────
class TestClientManagement:
    def test_add_client_page_loads(self, logged_in_client):
        """GET /clients/add should return 200."""
        res = logged_in_client.get("/clients/add")
        assert res.status_code == 200
        assert b"Add New Client" in res.data

    def test_add_client_successfully(self, logged_in_client):
        """POST /clients/add with valid data should create client."""
        res = logged_in_client.post(
            "/clients/add",
            data={
                "name": "Test User",
                "age": "30",
                "height": "175",
                "weight": "75",
                "program": "Fat Loss",
                "target_weight": "68",
                "target_adherence": "80",
                "membership_end": "2025-12-31",
            },
            follow_redirects=True
        )
        assert res.status_code == 200
        assert b"Test User" in res.data

    def test_add_client_without_name_fails(self, logged_in_client):
        """POST /clients/add without a name should fail gracefully."""
        res = logged_in_client.post(
            "/clients/add",
            data={"name": "", "age": "25"},
            follow_redirects=True
        )
        assert res.status_code == 200
        # Should stay on add page and show error
        assert b"required" in res.data or b"Add New Client" in res.data

    def test_client_detail_page_loads(self, logged_in_client):
        """After adding a client, the detail page should load."""
        # First add a client
        logged_in_client.post(
            "/clients/add",
            data={"name": "Detail User", "age": "25", "program": "Beginner"},
            follow_redirects=True
        )
        # Then view the detail page
        res = logged_in_client.get("/clients/Detail User")
        assert res.status_code == 200
        assert b"Detail User" in res.data

    def test_duplicate_client_name_rejected(self, logged_in_client):
        """Adding the same client name twice should show an error."""
        data = {"name": "Dup Client", "age": "28"}
        logged_in_client.post("/clients/add", data=data, follow_redirects=True)
        res = logged_in_client.post(
            "/clients/add", data=data, follow_redirects=True
        )
        assert res.status_code == 200
        assert b"already exists" in res.data

    def test_nonexistent_client_redirects(self, logged_in_client):
        """Viewing a client that doesn't exist should redirect to dashboard."""
        res = logged_in_client.get("/clients/NoSuchPerson", follow_redirects=True)
        assert res.status_code == 200
        assert b"not found" in res.data

    def test_delete_client(self, logged_in_client):
        """POST /clients/<name>/delete should remove the client."""
        logged_in_client.post(
            "/clients/add",
            data={"name": "ToDelete"},
            follow_redirects=True
        )
        res = logged_in_client.post(
            "/clients/ToDelete/delete",
            follow_redirects=True
        )
        assert res.status_code == 200
        assert b"ToDelete" not in res.data or b"deleted" in res.data


# ─────────────────────────────────────────────
# WORKOUTS
# ─────────────────────────────────────────────
class TestWorkouts:
    def _add_client(self, c, name="WorkoutClient"):
        c.post("/clients/add", data={"name": name}, follow_redirects=True)
        return name

    def test_log_workout_successfully(self, logged_in_client):
        """POST /clients/<name>/workout/add should log a workout."""
        name = self._add_client(logged_in_client)
        res = logged_in_client.post(
            f"/clients/{name}/workout/add",
            data={
                "workout_date": "2025-06-01",
                "workout_type": "Strength",
                "duration_min": "60",
                "notes": "Great session"
            },
            follow_redirects=True
        )
        assert res.status_code == 200
        assert b"Workout logged" in res.data or b"2025-06-01" in res.data


# ─────────────────────────────────────────────
# PROGRESS TRACKING
# ─────────────────────────────────────────────
class TestProgress:
    def _add_client(self, c, name="ProgressClient"):
        c.post("/clients/add", data={"name": name}, follow_redirects=True)
        return name

    def test_add_progress_entry(self, logged_in_client):
        """POST /clients/<name>/progress/add should add a progress entry."""
        name = self._add_client(logged_in_client)
        res = logged_in_client.post(
            f"/clients/{name}/progress/add",
            data={"week": "Week 1", "adherence": "85"},
            follow_redirects=True
        )
        assert res.status_code == 200
        assert b"Week 1" in res.data or b"Progress entry added" in res.data


# ─────────────────────────────────────────────
# JSON API
# ─────────────────────────────────────────────
class TestAPI:
    def test_api_clients_requires_login(self, client):
        """GET /api/clients without login should redirect."""
        res = client.get("/api/clients", follow_redirects=False)
        assert res.status_code in (301, 302)

    def test_api_clients_returns_json(self, logged_in_client):
        """GET /api/clients should return a JSON list."""
        res = logged_in_client.get("/api/clients")
        assert res.status_code == 200
        assert res.content_type == "application/json"
        data = res.get_json()
        assert isinstance(data, list)

    def test_api_progress_returns_json(self, logged_in_client):
        """GET /api/clients/<name>/progress should return JSON."""
        logged_in_client.post(
            "/clients/add",
            data={"name": "APIUser"},
            follow_redirects=True
        )
        res = logged_in_client.get("/api/clients/APIUser/progress")
        assert res.status_code == 200
        assert isinstance(res.get_json(), list)


# ─────────────────────────────────────────────
# CALORIE CALCULATION
# ─────────────────────────────────────────────
class TestCalorieCalculation:
    def test_calories_calculated_for_fat_loss(self, logged_in_client):
        """Fat Loss: 75 kg × 22 = 1650 kcal should appear in detail page."""
        logged_in_client.post(
            "/clients/add",
            data={"name": "CalTest", "weight": "75", "program": "Fat Loss"},
            follow_redirects=True
        )
        res = logged_in_client.get("/clients/CalTest")
        assert res.status_code == 200
        assert b"1650" in res.data

    def test_calories_calculated_for_muscle_gain(self, logged_in_client):
        """Muscle Gain: 80 kg × 35 = 2800 kcal should appear in detail page."""
        logged_in_client.post(
            "/clients/add",
            data={"name": "MuscleTest", "weight": "80", "program": "Muscle Gain"},
            follow_redirects=True
        )
        res = logged_in_client.get("/clients/MuscleTest")
        assert res.status_code == 200
        assert b"2800" in res.data
