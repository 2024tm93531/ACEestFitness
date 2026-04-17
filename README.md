# ACEest Fitness & Gym — DevOps CI/CD Assignment (Phase 2)

A Flask-based gym management web application with a fully automated CI/CD pipeline covering containerisation, static analysis, and five Kubernetes deployment strategies.

---

## Project Structure

```
ACEestFitness/
├── app.py                        # Flask application (core)
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Multi-stage production image
├── Jenkinsfile                   # Phase 2 Jenkins pipeline (parameterised)
├── sonar-project.properties      # SonarQube configuration
│
├── tests/
│   ├── test_app.py               # Phase 1 unit tests
│   └── test_phase2.py            # Phase 2 extended tests
│
├── k8s/
│   ├── namespace.yaml            # aceest namespace
│   ├── configmap.yaml            # ConfigMap + Secret
│   ├── blue-green/
│   │   ├── blue-deployment.yaml
│   │   ├── green-deployment.yaml
│   │   └── service-switch.yaml
│   ├── canary/
│   │   └── canary-deployment.yaml
│   ├── shadow/
│   │   └── shadow-deployment.yaml
│   ├── ab-testing/
│   │   └── ab-deployment.yaml
│   └── rolling-update/
│       └── rolling-update.yaml   # Includes HPA
│
└── .github/workflows/
    └── main.yml                  # GitHub Actions pipeline
```

---

## Quick Start (Local)

```bash
pip install -r requirements.txt
python app.py           # runs on http://localhost:5000
# Default login: admin / admin123
```

### Run Tests

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## CI/CD Pipeline Overview

```
GitHub Push
    │
    ▼
Checkout Code
    │
    ▼
Python Env Setup (venv)
    │
    ▼
Lint — flake8 (E9, F63, F7, F82)
    │
    ▼
Unit Tests — pytest (test-results.xml + coverage.xml)
    │
    ▼
SonarQube Analysis + Quality Gate
    │
    ▼
Docker Build & Tag  →  Push to Docker Hub
    │
    ▼
Kubernetes Deploy (strategy parameter)
    │
    ▼
Post-Deploy Health Check → Auto-Rollback on failure
```

---

## Deployment Strategies

### 1. Rolling Update (default)
Kubernetes replaces pods one at a time. `maxUnavailable: 0` ensures zero downtime.

```bash
kubectl apply -f k8s/rolling-update/rolling-update.yaml -n aceest
kubectl rollout status deployment/aceest-rolling -n aceest
# Rollback:
kubectl rollout undo deployment/aceest-rolling -n aceest
```

### 2. Blue-Green
Two identical environments. Traffic switches instantly between them via a Service selector update.

```bash
kubectl apply -f k8s/blue-green/blue-deployment.yaml  -n aceest
kubectl apply -f k8s/blue-green/green-deployment.yaml -n aceest
# Test green on port 30081, then switch:
# Edit service-switch.yaml: version: blue → version: green
kubectl apply -f k8s/blue-green/service-switch.yaml -n aceest
# Rollback: revert selector back to blue
```

### 3. Canary Release
New version receives a small slice of traffic (default 10%) via replica ratio.

```bash
kubectl apply -f k8s/canary/canary-deployment.yaml -n aceest
# Scale canary from 1 to 9 replicas to promote:
kubectl scale deployment aceest-canary --replicas=9 -n aceest
kubectl scale deployment aceest-stable --replicas=1 -n aceest
# Rollback:
kubectl delete deployment aceest-canary -n aceest
```

### 4. Shadow Deployment
Production handles all real traffic. An Nginx sidecar mirrors every request to the shadow pod — users see zero impact.

```bash
kubectl apply -f k8s/shadow/shadow-deployment.yaml -n aceest
# Monitor shadow logs:
kubectl logs -l version=shadow -c shadow-app -n aceest -f
# Remove shadow:
kubectl delete deployment aceest-shadow -n aceest
```

### 5. A/B Testing
Variant A (control) and Variant B (test) run simultaneously. Users with cookie `ab_group=b` are routed to Variant B via Nginx Ingress.

```bash
kubectl apply -f k8s/ab-testing/ab-deployment.yaml -n aceest
# Test Variant B:
curl -H "Cookie: ab_group=b" http://<cluster-ip>/
# Rollback Variant B:
kubectl delete deployment aceest-variant-b -n aceest
```

---

## Jenkins Pipeline Parameters

| Parameter         | Default          | Description                                      |
|-------------------|------------------|--------------------------------------------------|
| `DEPLOY_STRATEGY` | `rolling-update` | One of: rolling-update, blue-green, canary, shadow, ab-testing |
| `DOCKER_TAG`      | `v2.BUILD_NUMBER`| Custom image tag (leave blank to auto-generate)  |
| `ROLLBACK_ON_FAIL`| `true`           | Auto-rollback on post-deploy health check failure |
| `CANARY_WEIGHT`   | `10`             | Canary traffic % (canary strategy only)          |

### Jenkins Credentials Required

| ID                    | Type              | Value                     |
|-----------------------|-------------------|---------------------------|
| `dockerhub-username`  | Secret text       | Your Docker Hub username  |
| `dockerhub-credentials` | Username/Password | Docker Hub login         |
| `sonar-token`         | Secret text       | SonarQube auth token      |

---

## SonarQube Setup

1. Run SonarQube: `docker run -d -p 9000:9000 sonarqube:lts-community`
2. Login at `http://localhost:9000` (admin / admin)
3. Create project key: `aceest-fitness`
4. Generate token → add to Jenkins as `sonar-token`
5. Install **SonarQube Scanner** plugin in Jenkins
6. Configure server in Jenkins → Manage Jenkins → Configure System → SonarQube servers

---

## Minikube (Local Kubernetes)

```bash
minikube start
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
# Replace YOUR_DOCKERHUB_USERNAME in YAML files, then:
kubectl apply -f k8s/rolling-update/rolling-update.yaml -n aceest
minikube service aceest-rolling-service -n aceest
```

---

## Docker Hub

```bash
docker build -t <your-username>/aceest-fitness:v2.0 .
docker push <your-username>/aceest-fitness:v2.0
docker push <your-username>/aceest-fitness:latest
```

---

## Application Endpoints

| Endpoint                        | Auth | Description                  |
|---------------------------------|------|------------------------------|
| `GET /`                         | No   | Redirects to login/dashboard |
| `GET /login`                    | No   | Login page                   |
| `GET /dashboard`                | Yes  | Client overview              |
| `GET /clients/add`              | Yes  | Add client form              |
| `GET /clients/<name>`           | Yes  | Client detail page           |
| `GET /clients/<name>/edit`      | Yes  | Edit client form             |
| `POST /clients/<name>/delete`   | Yes  | Delete client                |
| `POST /clients/<name>/workout/add` | Yes | Log workout              |
| `POST /clients/<name>/progress/add` | Yes | Add progress entry      |
| `GET /api/health`               | No   | Liveness/readiness probe     |
| `GET /api/clients`              | Yes  | JSON list of all clients     |
| `GET /api/clients/<name>/progress` | Yes | JSON progress entries    |
