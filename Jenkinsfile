pipeline {
    agent any

    environment {
        IMAGE_NAME      = "aceest-fitness"
        APP_PORT        = "5000"
        CONTAINER_NAME  = "aceest-fitness-app"
        // Semantic version tag: e.g. v1.0.42
        BUILD_VERSION   = "v1.0.${BUILD_NUMBER}"
        // Full image references
        IMAGE_VERSIONED = "${IMAGE_NAME}:${BUILD_VERSION}"
        IMAGE_LATEST    = "${IMAGE_NAME}:latest"
        // Snapshot of the previous latest — used for rollback
        PREV_IMAGE      = "${IMAGE_NAME}:previous"
    }

    stages {

        stage('Checkout') {
            steps {
                echo "Pulling latest code — build ${BUILD_VERSION}"
                git branch: 'main',
                    url: 'https://github.com/2024tm93531/ACEestFitness.git'
            }
        }

        stage('Install Dependencies') {
            steps {
                echo 'Installing Python packages...'
                sh 'python3 -m pip install --break-system-packages -r requirements.txt'
            }
        }

        stage('Lint') {
            steps {
                echo 'Checking syntax...'
                sh 'python3 -m py_compile app.py && echo "Lint PASSED"'
            }
        }

        stage('Test') {
            steps {
                echo 'Running unit tests...'
                sh 'python3 -m pytest tests/test_app.py -v --tb=short'
            }
        }

        stage('Tag Previous as Rollback') {
            steps {
                echo 'Preserving current latest as rollback target...'
                sh """
                    if docker image inspect ${IMAGE_LATEST} > /dev/null 2>&1; then
                        docker tag ${IMAGE_LATEST} ${PREV_IMAGE}
                        echo "Saved ${IMAGE_LATEST} as ${PREV_IMAGE}"
                    else
                        echo "No existing latest image — skipping snapshot"
                    fi
                """
            }
        }

        stage('Docker Build') {
            steps {
                echo "Building image ${IMAGE_VERSIONED}..."
                sh """
                    docker build \\
                        --label "build.version=${BUILD_VERSION}" \\
                        --label "build.number=${BUILD_NUMBER}" \\
                        --label "git.commit=${GIT_COMMIT}" \\
                        -t ${IMAGE_VERSIONED} \\
                        -t ${IMAGE_LATEST} \\
                        .
                """
                echo "Tagged as ${IMAGE_VERSIONED} and ${IMAGE_LATEST}"
            }
        }

        stage('Verify Image') {
            steps {
                echo 'Verifying built image...'
                sh """
                    docker image inspect ${IMAGE_VERSIONED} > /dev/null 2>&1 && \\
                        echo "Image ${IMAGE_VERSIONED} verified" || \\
                        (echo "Image verification failed" && exit 1)
                """
                sh "docker image ls ${IMAGE_NAME} --format 'Tag: {{.Tag}} | Size: {{.Size}} | Created: {{.CreatedAt}}'"
            }
        }

        stage('Deploy Container') {
            steps {
                echo "Deploying container: ${CONTAINER_NAME} on port ${APP_PORT}..."
                sh """
                    # Stop and remove any existing container with the same name
                    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}\$"; then
                        echo "Stopping existing container: ${CONTAINER_NAME}"
                        docker stop ${CONTAINER_NAME} || true
                        docker rm   ${CONTAINER_NAME} || true
                        echo "Old container removed"
                    fi

                    # Start the new container
                    docker run -d \\
                        --name ${CONTAINER_NAME} \\
                        --restart unless-stopped \\
                        -p ${APP_PORT}:${APP_PORT} \\
                        -e FLASK_ENV=production \\
                        -l "app.version=${BUILD_VERSION}" \\
                        ${IMAGE_VERSIONED}

                    echo "Container ${CONTAINER_NAME} started"
                """
            }
        }

        stage('Health Check') {
            steps {
                echo "Waiting for application to be ready on port ${APP_PORT}..."
                sh """
                    # Retry for up to 30 seconds (10 attempts × 3s)
                    RETRIES=10
                    DELAY=3
                    URL="http://localhost:${APP_PORT}/health"

                    for i in \$(seq 1 \$RETRIES); do
                        echo "Health check attempt \$i / \$RETRIES — \$URL"
                        STATUS=\$(curl -s -o /dev/null -w "%{http_code}" \$URL || echo "000")

                        if [ "\$STATUS" = "200" ]; then
                            echo "Application is UP — HTTP \$STATUS"
                            echo "--- Response body ---"
                            curl -s \$URL
                            echo ""
                            exit 0
                        fi

                        echo "Not ready yet (HTTP \$STATUS) — retrying in \${DELAY}s..."
                        sleep \$DELAY
                    done

                    echo "Health check FAILED after \$RETRIES attempts"
                    docker logs ${CONTAINER_NAME} --tail=50
                    exit 1
                """
            }
        }

        stage('Smoke Test') {
            steps {
                echo 'Running smoke tests against live container...'
                sh """
                    BASE="http://localhost:${APP_PORT}"

                    check() {
                        STATUS=\$(curl -s -o /dev/null -w "%{http_code}" "\$1")
                        if [ "\$STATUS" = "\$2" ]; then
                            echo "  PASS  GET \$1 → HTTP \$STATUS"
                        else
                            echo "  FAIL  GET \$1 → expected \$2, got \$STATUS"
                            exit 1
                        fi
                    }

                    check "\$BASE/"                         200
                    check "\$BASE/health"                   200
                    check "\$BASE/workouts"                 200
                    check "\$BASE/workouts/beginner"        200
                    check "\$BASE/workouts/intermediate"    200
                    check "\$BASE/workouts/advanced"        200
                    check "\$BASE/workouts/invalid"         404

                    echo "All smoke tests passed"
                """
            }
        }

    }

    post {

        success {
            script {
                echo """
╔══════════════════════════════════════════════════════╗
║   BUILD SUCCESSFUL & APPLICATION RUNNING             ║
╠══════════════════════════════════════════════════════╣
║  Version   : ${env.BUILD_VERSION}
║  Image     : ${env.IMAGE_VERSIONED}
║  Container : ${env.CONTAINER_NAME}
║  URL       : http://localhost:${env.APP_PORT}
║  Commit    : ${env.GIT_COMMIT?.take(7)}
╚══════════════════════════════════════════════════════╝
                """
            }
            // Keep only the last 3 versioned images to save disk space
            sh """
                docker images ${IMAGE_NAME} --format '{{.Tag}}' | \\
                grep -E '^v[0-9]+\\.[0-9]+\\.[0-9]+\$' | \\
                sort -t. -k3 -n | \\
                head -n -3 | \\
                xargs -r -I {} docker rmi ${IMAGE_NAME}:{} || true
            """
        }

        failure {
            script {
                echo """
╔══════════════════════════════════════════════════════╗
║   BUILD FAILED — Initiating Rollback                 ║
╠══════════════════════════════════════════════════════╣
║  Version : ${env.BUILD_VERSION}
╚══════════════════════════════════════════════════════╝
                """
            }
            sh """
                # ── ROLLBACK: Restore previous image & restart container ──
                if docker image inspect ${PREV_IMAGE} > /dev/null 2>&1; then
                    echo "Rolling back image: ${PREV_IMAGE} → ${IMAGE_LATEST}"
                    docker tag ${PREV_IMAGE} ${IMAGE_LATEST}

                    # Restart the container from the restored image
                    docker stop ${CONTAINER_NAME} || true
                    docker rm   ${CONTAINER_NAME} || true
                    docker run -d \\
                        --name ${CONTAINER_NAME} \\
                        --restart unless-stopped \\
                        -p ${APP_PORT}:${APP_PORT} \\
                        ${IMAGE_LATEST}

                    echo "Rollback complete — ${CONTAINER_NAME} running previous version"
                else
                    echo "No rollback image found — this may be the first build"
                fi

                # Remove the broken versioned image
                docker rmi ${IMAGE_VERSIONED} || true
            """
        }

        always {
            echo "Build ${BUILD_VERSION} | Result: ${currentBuild.currentResult}"
            // Print running containers for visibility
            sh "docker ps --filter name=${CONTAINER_NAME} --format 'Container: {{.Names}} | Image: {{.Image}} | Status: {{.Status}} | Ports: {{.Ports}}' || true"
        }

    }
}
