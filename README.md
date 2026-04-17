# ACEest Fitness & Gym – DevOps CI/CD Pipeline

> **Assignment 1 – Introduction to DevOps (CSIZG514/SEZG514)**  
> ACEest Functional Fitness Management System – Flask Web Application

---

## Project Overview

This repository implements a full DevOps CI/CD pipeline for the **ACEest Fitness & Gym** management web application. The application is built with **Flask (Python)** and the pipeline automates testing, linting, Docker image assembly, and build verification using **GitHub Actions** and **Jenkins**.

---

## Repository Structure

```
aceest-devops/
├── app.py                        ← Main Flask application (all routes & business logic)
├── requirements.txt              ← Python dependencies
├── Dockerfile                    ← Docker container definition
├── Jenkinsfile                   ← Jenkins pipeline configuration
├── README.md                     ← This file
├── templates/
│   ├── base.html                 ← Shared HTML layout
│   ├── login.html                ← Login page
│   ├── dashboard.html            ← Main dashboard
│   ├── clients.html              ← Client listing
│   ├── add_client.html           ← Add/update client form
│   ├── client_detail.html        ← Individual client page
│   └── add_workout.html          ← Log workout form
├── tests/
│   └── test_app.py               ← Pytest test suite (30+ tests)
└── .github/
    └── workflows/
        └── main.yml              ← GitHub Actions CI/CD pipeline
```

---

## Local Setup & Execution

### Prerequisites

- Python 3.11 or newer
- pip (Python package manager)
- Git

### Step 1: Clone the Repository

```bash
git clone https://github.com/2024tm93524/ACEestFitness.git
cd aceest-devops
```

### Step 2: Create a Virtual Environment (recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
python.exe -m pip install --upgrade pip
```

### Step 4: Run the Application

```bash
python app.py
```

Open your browser and go to: **http://localhost:5000**

Default login: `admin` / `admin123`

---

## Running Tests Manually

### Install Test Dependencies

```bash
pip install pytest pytest-flask
```

### Run All Tests

```bash
pytest tests/ -v
```

### Run with Coverage Report

```bash
pip install pytest-cov
pytest tests/ -v --cov=app --cov-report=term-missing
```

### Expected Output

```
tests/test_app.py::test_health_endpoint PASSED
tests/test_app.py::test_root_redirects_to_login PASSED
tests/test_app.py::test_login_page_loads PASSED
tests/test_app.py::test_login_with_valid_credentials PASSED
... (30+ tests, all passing)
```

---

## Docker – Build & Run

### Build the Docker Image

```bash
docker build -t aceest-fitness:latest .
```

### Run the Container

```bash
docker run -p 5000:5000 aceest-fitness:latest
```

Open browser at: **http://localhost:5000**

### Run Tests Inside the Container

```bash
# Start container with bash
docker run -it aceest-fitness:latest bash

# Inside container:
pytest tests/ -v
```

### Stop the Container

```bash
docker ps                         # find container ID
docker stop <container_id>
```

---

## Jenkins BUILD Setup

Jenkins is used as the **primary BUILD environment** — it pulls code from GitHub, runs linting, executes tests, and builds the Docker image.

### Step 1: Install Jenkins

**On Windows (using Docker — easiest method):**

```bash
docker run -d -p 8080:8080 -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  --name jenkins jenkins/jenkins:lts
```

Open Jenkins at: **http://localhost:8080**

Get the initial password:
```bash
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

### Step 2: Configure Jenkins

1. Open http://localhost:8080
2. Enter the initial admin password
3. Click "Install suggested plugins"
4. Create your admin user
5. Install the **Pipeline** plugin (Manage Jenkins → Plugins → Available)

### Step 3: Create a Pipeline Job

1. Click **New Item**
2. Name it `aceest-fitness`
3. Select **Pipeline** → click OK
4. Under **Pipeline Definition**: select `Pipeline script from SCM`
5. SCM: `Git`
6. Repository URL: `https://github.com/2024tm93524/ACEestFitness.git`
7. Branch: `*/main`
8. Script Path: `Jenkinsfile`
9. Click **Save**

### Step 4: Trigger a Build

Click **Build Now** in the Jenkins job dashboard.

Jenkins will run these stages (as defined in `Jenkinsfile`):
1. **Checkout** – pulls latest code from GitHub
2. **Setup Python** – creates virtualenv, installs dependencies
3. **Lint Check** – runs flake8 syntax validation
4. **Unit Tests** – runs pytest suite
5. **Docker Build** – builds the Docker image

---

## GitHub Actions CI/CD Pipeline

The pipeline is defined in `.github/workflows/main.yml` and is automatically triggered on every **push** or **pull request** to the `main` branch.

### Pipeline Stages

| Stage | Description |
|-------|-------------|
| **Build & Lint** | Installs dependencies, runs flake8 syntax check |
| **Unit Tests** | Runs the full pytest suite |
| **Docker Build** | Builds Docker image and runs a health check against it |

### Viewing Pipeline Results

1. Push your code to GitHub
2. Click the **Actions** tab in your GitHub repository
3. Each workflow run shows the status of all 3 jobs

### Pipeline Logic Explained

```
Push to main
     │
     ▼
┌─────────────────┐
│  Build & Lint   │  ← Fails here = syntax error in code
└────────┬────────┘
         │ (passes)
         ▼
┌─────────────────┐
│   Unit Tests    │  ← Fails here = broken functionality
└────────┬────────┘
         │ (passes)
         ▼
┌─────────────────┐
│  Docker Build   │  ← Fails here = Dockerfile issue
└─────────────────┘
```

Jobs run sequentially (`needs:` keyword) — a failing stage stops the pipeline.

---

## Application Features

| Feature | Description |
|---------|-------------|
| **Login System** | Role-based authentication (Admin / Staff) |
| **Client Management** | Add, view, and manage gym clients with full profiles |
| **Fitness Programs** | Fat Loss, Muscle Gain, Beginner — with calorie calculations |
| **Workout Logging** | Record workout sessions per client |
| **Progress Tracking** | Log weekly adherence percentages |
| **REST API** | JSON endpoints (`/api/programs`, `/api/clients`) |
| **Health Check** | `/health` endpoint for pipeline verification |

---
