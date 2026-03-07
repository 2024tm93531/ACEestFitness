#  ACEest Fitness & Gym — DevOps Assignment 1

A Flask web application for Fitness and Gym Management, built as part of the assignment. Demonstrates a complete CI/CD pipeline using Git, Docker, GitHub Actions, and Jenkins.

---

##  Project Structure

```
aceest-fitness/
├── app.py                          # Flask application (main source code)
├── requirements.txt                # Python dependencies
├── README.md                       # This file
```

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

```

---

##  Git Version Control Strategy

This project follows a branching strategy:

| Branch      | Purpose                              |
|-------------|--------------------------------------|
| `main`      | Stable, production-ready code        |


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

