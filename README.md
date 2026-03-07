#  ACEest Fitness & Gym — DevOps Assignment 1

A Flask web application for Fitness and Gym Management, built as part of the assignment. Demonstrates a complete CI/CD pipeline using Git, Docker, GitHub Actions, and Jenkins.

---

##  Project Structure

```
aceest-fitness/
├── app.py                          # Flask application (main source code)
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Container definition
├── README.md                       # This file
├── templates/                      # HTML pages (Jinja2)
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── add_client.html
│   ├── client_detail.html
│   └── edit_client.html
├── tests/
    └── test_app.py                 # Pytest unit tests

---

##  Local Setup & Running the App

### Prerequisites
- Python 3.10 or higher installed
- Git installed

### Step 1 — Clone the repository
```bash
git clone https://github.com/2024tm93531/ACEestFitness.git
cd aceest-fitness
```

### Step 2 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 3 — Run the application
```bash
python app.py
```

### Step 4 — Open in browser
```
http://localhost:5000
```

**Default login credentials:**
- Username: `admin`
- Password: `admin123`

---

## 🧪 Running Tests Manually

```bash
# Run all tests with verbose output
pytest tests/test_app.py -v

# Run a specific test class
pytest tests/test_app.py::TestAuthentication -v

# Run with coverage report
pip install pytest-cov
pytest tests/test_app.py --cov=app --cov-report=term-missing
```

---

##  Docker — Build & Run

### Build the image
```bash
docker build -t aceest-fitness:latest .
```

### Run the container
```bash
docker run -p 5000:5000 aceest-fitness:latest
```

### Run tests inside the container
```bash
docker run --rm -e DB_PATH=":memory:" aceest-fitness:latest \
  python -m pytest tests/test_app.py -v
```

### Open in browser
```
http://localhost:5000
```

---

##  Git Version Control Strategy

This project follows a branching strategy:

| Branch      | Purpose                              |
|-------------|--------------------------------------|
| `main`      | Stable, production-ready code        |
| `develop`   | Integration branch for new features  |
| `feature/*` | Individual feature development       |
| `fix/*`     | Bug fix branches                     |

### Commit message format
```
<type>: <short description>
Examples:
feat: add client workout logging
fix: correct calorie calculation for muscle gain
test: add unit tests for progress endpoint
docs: update README with Docker instructions
ci: add GitHub Actions workflow
```

## Tech Stack

- **Backend:** Python 3.12, Flask 3.0
- **Database:** SQLite (zero-config, file-based)
- **Testing:** Pytest
- **Container:** Docker (python:3.12-slim)
