# ─────────────────────────────────────────────
# Stage 1: Build image
# Uses Python 3.12 slim — small and secure base
# ─────────────────────────────────────────────
FROM python:3.12-slim

# Metadata
LABEL maintainer="ACEest DevOps Team"
LABEL description="ACEest Fitness & Gym Flask Web Application"

# Don't write .pyc files; send stdout/stderr straight to terminal
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set a non-root working directory inside the container
WORKDIR /app

# ── Install dependencies first (separate layer = faster rebuilds) ──
# Copy only requirements first so Docker caches this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy the rest of the application ──
COPY . .

# Initialise the database (creates tables + seeds admin user)
RUN python -c "from app import init_db; init_db()"

# Expose Flask's default port
EXPOSE 5000

# ── Run the app ──
# Use python directly (simple & straightforward for this assignment)
CMD ["python", "app.py"]
