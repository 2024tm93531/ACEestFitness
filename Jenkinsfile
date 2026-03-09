pipeline {
    agent any

    environment {
        IMAGE_NAME = "aceest-fitness"
        BUILD_TAG  = "v1.${BUILD_NUMBER}"
    }

    stages {

        stage('Checkout') {
            steps {
                echo '=== Pulling latest code from GitHub ==='
                checkout scm
            }
        }

        stage('Setup Python Environment') {
            steps {
                echo '=== Installing Python and dependencies ==='
                sh '''
                    apt-get update -y -qq
                    apt-get install -y python3 python3-pip python3-venv -qq
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip -q
                    pip install -r requirements.txt -q
                '''
            }
        }

        stage('Lint Check') {
            steps {
                echo '=== Running flake8 syntax check ==='
                sh '''
                    . venv/bin/activate
                    pip install flake8 -q
                    flake8 app.py --select=E9,F63,F7,F82 --show-source
                '''
            }
        }

        stage('Unit Tests') {
            steps {
                echo '=== Running Pytest unit tests ==='
                sh '''
                    . venv/bin/activate
                    pip install pytest pytest-flask -q
                    pytest tests/ -v --tb=short
                '''
            }
        }

        stage('Docker Build & Tag') {
            steps {
                echo "=== Building Docker image: ${IMAGE_NAME}:${BUILD_TAG} ==="
                sh '''
                    docker build -t ${IMAGE_NAME}:${BUILD_TAG} -t ${IMAGE_NAME}:latest .
                    echo "=== Images built and tagged ==="
                    docker images | grep ${IMAGE_NAME}
                '''
            }
        }

        stage('Deploy Latest Image') {
            steps {
                echo '=== Stopping old container and deploying latest ==='
                sh '''
                    docker stop aceest-app 2>/dev/null || true
                    docker rm aceest-app 2>/dev/null || true

                    docker run -d \
                        --name aceest-app \
                        -p 5000:5000 \
                        ${IMAGE_NAME}:latest

                    echo "=== App deployed at http://localhost:5000 ==="
                    docker ps | grep aceest-app
                '''
            }
        }

        stage('Rollback Check') {
            steps {
                echo '=== Verifying deployment health ==='
                sh '''
                    sleep 5
                    if docker ps | grep -q aceest-app; then
                        echo "Deployment SUCCESS - container is healthy"
                        docker ps | grep aceest-app
                    else
                        echo "Container crashed - triggering rollback..."

                        # Exclude current bad tag, sort numerically, pick highest = last stable
                        PREV_TAG=$(docker images ${IMAGE_NAME} \
                            --format "{{.Tag}}" \
                            | grep "^v1\\." \
                            | grep -v "^${BUILD_TAG}$" \
                            | sort -t. -k2 -rn \
                            | head -1)

                        if [ -n "$PREV_TAG" ]; then
                            echo "Rolling back to ${IMAGE_NAME}:${PREV_TAG}"
                            docker stop aceest-app 2>/dev/null || true
                            docker rm   aceest-app 2>/dev/null || true
                            docker run -d \
                                --name aceest-app \
                                -p 5000:5000 \
                                --restart unless-stopped \
                                ${IMAGE_NAME}:${PREV_TAG}
                            echo "Rollback complete - running ${PREV_TAG}"
                        else
                            echo "No previous image found for rollback"
                            exit 1
                        fi
                    fi
                '''
            }
        }
    }

    post {
        success {
            echo "BUILD SUCCESSFUL - Deployed ${IMAGE_NAME}:${BUILD_TAG}"
        }
        failure {
            echo "BUILD FAILED - Check the logs above for errors."
        }
        always {
            echo '=== Pipeline finished ==='
            sh 'docker images | grep aceest-fitness || true'
        }
    }
}
