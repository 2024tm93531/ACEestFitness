pipeline {
    agent any

    environment {
        IMAGE_NAME    = "aceest-fitness"
        CONTAINER_NAME = "aceest-fitness-app"
        HOST_PORT     = "5000"
        CONTAINER_PORT = "5000"
        // Tag using build number + short Git SHA for full traceability
        IMAGE_TAG     = "v${BUILD_NUMBER}-${GIT_COMMIT[0..6]}"
        LATEST_TAG    = "latest"
        // Rollback: keep last N successful image tags in a file
        TAG_HISTORY_FILE = "/var/jenkins_home/aceest-fitness-tags.txt"
        MAX_HISTORY   = "5"
    }

    stages {

        // ─────────────────────────────────────────────
        // STAGE 1 — Checkout
        // ─────────────────────────────────────────────
        stage('Checkout') {
            steps {
                echo '=== Pulling latest code from GitHub ==='
                checkout scm
                script {
                    // Capture full commit SHA now that checkout is done
                    env.GIT_SHORT_SHA = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
                    env.IMAGE_TAG = "v${BUILD_NUMBER}-${env.GIT_SHORT_SHA}"
                    echo "Build tag: ${env.IMAGE_TAG}"
                }
            }
        }

        // ─────────────────────────────────────────────
        // STAGE 2 — Python environment
        // ─────────────────────────────────────────────
        stage('Setup Python Environment') {
            steps {
                echo '=== Installing Python and dependencies ==='
                sh '''
                    apt-get update -y
                    apt-get install -y python3 python3-pip python3-venv
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        // ─────────────────────────────────────────────
        // STAGE 3 — Lint
        // ─────────────────────────────────────────────
        stage('Lint Check') {
            steps {
                echo '=== Running flake8 syntax check ==='
                sh '''
                    . venv/bin/activate
                    pip install flake8
                    flake8 app.py --select=E9,F63,F7,F82 --show-source
                '''
            }
        }

        // ─────────────────────────────────────────────
        // STAGE 4 — Unit Tests
        // ─────────────────────────────────────────────
        stage('Unit Tests') {
            steps {
                echo '=== Running Pytest unit tests ==='
                sh '''
                    . venv/bin/activate
                    pytest tests/ -v --tb=short
                '''
            }
        }

        // ─────────────────────────────────────────────
        // STAGE 5 — Docker Build + Tag
        // ─────────────────────────────────────────────
        stage('Docker Build & Tag') {
            steps {
                echo "=== Building Docker image: ${env.IMAGE_NAME}:${env.IMAGE_TAG} ==="
                sh """
                    # Build with versioned tag
                    docker build -t ${IMAGE_NAME}:${env.IMAGE_TAG} .

                    # Also tag as latest for convenience
                    docker tag ${IMAGE_NAME}:${env.IMAGE_TAG} ${IMAGE_NAME}:${LATEST_TAG}

                    echo "✅ Image tagged as:"
                    echo "   ${IMAGE_NAME}:${env.IMAGE_TAG}"
                    echo "   ${IMAGE_NAME}:${LATEST_TAG}"
                """
            }
        }

        // ─────────────────────────────────────────────
        // STAGE 6 — Save tag to rollback history
        // ─────────────────────────────────────────────
        stage('Update Tag History') {
            steps {
                echo '=== Saving image tag to rollback history ==='
                sh """
                    # Prepend the new tag at the top of the history file
                    touch ${TAG_HISTORY_FILE}
                    echo "${env.IMAGE_TAG}" | cat - ${TAG_HISTORY_FILE} > /tmp/tag_history_tmp
                    mv /tmp/tag_history_tmp ${TAG_HISTORY_FILE}

                    # Keep only the last MAX_HISTORY entries
                    head -n ${MAX_HISTORY} ${TAG_HISTORY_FILE} > /tmp/tag_history_tmp
                    mv /tmp/tag_history_tmp ${TAG_HISTORY_FILE}

                    echo "=== Current tag history ==="
                    cat ${TAG_HISTORY_FILE}
                """
            }
        }

        // ─────────────────────────────────────────────
        // STAGE 7 — Deploy (stop old, run latest image)
        // ─────────────────────────────────────────────
        stage('Deploy Latest Image') {
            steps {
                echo "=== Deploying ${env.IMAGE_NAME}:${env.IMAGE_TAG} ==="
                sh """
                    # Stop and remove any existing container gracefully
                    if [ \$(docker ps -aq -f name=${CONTAINER_NAME}) ]; then
                        echo "Stopping existing container: ${CONTAINER_NAME}"
                        docker stop ${CONTAINER_NAME} || true
                        docker rm   ${CONTAINER_NAME} || true
                    fi

                    # Run the freshly built image
                    docker run -d \\
                        --name ${CONTAINER_NAME} \\
                        --restart unless-stopped \\
                        -p ${HOST_PORT}:${CONTAINER_PORT} \\
                        -e APP_ENV=production \\
                        ${IMAGE_NAME}:${env.IMAGE_TAG}

                    echo "✅ Container '${CONTAINER_NAME}' is running on port ${HOST_PORT}"
                    docker ps -f name=${CONTAINER_NAME}
                """
            }
        }

        // ─────────────────────────────────────────────
        // STAGE 8 — Health Check
        // ─────────────────────────────────────────────
        stage('Health Check') {
            steps {
                echo '=== Verifying container is healthy ==='
                sh """
                    echo "Waiting 10 seconds for app to start..."
                    sleep 10

                    STATUS=\$(docker inspect --format='{{.State.Status}}' ${CONTAINER_NAME} 2>/dev/null || echo "not_found")

                    if [ "\$STATUS" = "running" ]; then
                        echo "✅ Container is running — Health check passed"
                    else
                        echo "❌ Container status: \$STATUS — Health check FAILED"
                        exit 1
                    fi
                """
            }
        }

        // ─────────────────────────────────────────────
        // STAGE 9 — Cleanup old images (keep last N)
        // ─────────────────────────────────────────────
        stage('Cleanup Old Images') {
            steps {
                echo '=== Removing Docker images not in tag history ==='
                sh """
                    # List all local tags for this image
                    ALL_TAGS=\$(docker images ${IMAGE_NAME} --format '{{.Tag}}' | grep -v 'latest' || true)

                    # Keep tags present in history file
                    KEEP_TAGS=\$(cat ${TAG_HISTORY_FILE})

                    for tag in \$ALL_TAGS; do
                        if ! echo "\$KEEP_TAGS" | grep -qx "\$tag"; then
                            echo "Removing old image: ${IMAGE_NAME}:\$tag"
                            docker rmi ${IMAGE_NAME}:\$tag || true
                        fi
                    done

                    echo "=== Remaining images ==="
                    docker images ${IMAGE_NAME}
                """
            }
        }
    }

    // ─────────────────────────────────────────────────
    // POST — Success / Failure / Rollback instructions
    // ─────────────────────────────────────────────────
    post {
        success {
            echo """
✅ BUILD SUCCESSFUL
   Image  : ${env.IMAGE_NAME}:${env.IMAGE_TAG}
   Running: ${env.CONTAINER_NAME} → localhost:${env.HOST_PORT}
   All stages passed!
"""
        }

        failure {
            echo '❌ BUILD FAILED — Initiating automatic rollback...'
            sh """
                # Read the second line of tag history (previous stable build)
                ROLLBACK_TAG=\$(sed -n '2p' ${TAG_HISTORY_FILE} || echo "")

                if [ -z "\$ROLLBACK_TAG" ]; then
                    echo "⚠️  No previous image found for rollback. Manual intervention required."
                    exit 1
                fi

                echo "🔄 Rolling back to: ${IMAGE_NAME}:\$ROLLBACK_TAG"

                # Stop the failed/current container
                docker stop ${CONTAINER_NAME} || true
                docker rm   ${CONTAINER_NAME} || true

                # Re-launch with previous stable image
                docker run -d \\
                    --name ${CONTAINER_NAME} \\
                    --restart unless-stopped \\
                    -p ${HOST_PORT}:${CONTAINER_PORT} \\
                    -e APP_ENV=production \\
                    ${IMAGE_NAME}:\$ROLLBACK_TAG

                echo "✅ Rollback complete — running \$ROLLBACK_TAG"
                docker ps -f name=${CONTAINER_NAME}
            """
        }

        always {
            echo '=== Pipeline finished — cleaning up workspace ==='
            cleanWs()
        }
    }
}
