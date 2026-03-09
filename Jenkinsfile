pipeline {
    agent any

    environment {
        IMAGE_NAME      = "aceest-fitness"
        APP_PORT        = "5000"
        CONTAINER_NAME  = "aceest-fitness-app"
        NETWORK_NAME    = "aceest-network"
        BUILD_VERSION   = "v1.0.${BUILD_NUMBER}"
        IMAGE_VERSIONED = "${IMAGE_NAME}:${BUILD_VERSION}"
        IMAGE_LATEST    = "${IMAGE_NAME}:latest"
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
                    # ── Ensure shared Docker network exists ──────────────────
                    if ! docker network inspect ${NETWORK_NAME} > /dev/null 2>&1; then
                        docker network create ${NETWORK_NAME}
                        echo "Created Docker network: ${NETWORK_NAME}"
                    fi

                    # ── Stop and remove old container if present ─────────────
                    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}\$"; then
                        echo "Stopping existing container: ${CONTAINER_NAME}"
                        docker stop ${CONTAINER_NAME} || true
                        docker rm   ${CONTAINER_NAME} || true
                        echo "Old container removed"
                    fi

                    # ── Start new container on the shared network ────────────
                    docker run -d \\
                        --name ${CONTAINER_NAME} \\
                        --network ${NETWORK_NAME} \\
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
                echo "Waiting for application to be ready..."
                sh """
                    # ── Resolve the container's IP on the shared network ─────
                    # This avoids localhost isolation when Jenkins itself
                    # runs inside Docker (curl localhost won't cross containers)
                    CONTAINER_IP=\$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' ${CONTAINER_NAME})
                    echo "Container IP: \$CONTAINER_IP"
                    URL="http://\${CONTAINER_IP}:${APP_PORT}/health"
                    echo "Health check URL: \$URL"

                    RETRIES=15
                    DELAY=3

                    for i in \$(seq 1 \$RETRIES); do
                        echo "Attempt \$i / \$RETRIES — \$URL"

                        # FIX: separate curl and fallback to avoid string concatenation
                        HTTP_CODE=\$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 "\$URL" 2>/dev/null)
                        EXIT_CODE=\$?

                        # If curl itself failed (no connection), default to 000
                        if [ \$EXIT_CODE -ne 0 ]; then
                            HTTP_CODE="000"
                        fi

                        echo "HTTP Status: \$HTTP_CODE"

                        if [ "\$HTTP_CODE" = "200" ]; then
                            echo "Application is UP!"
                            echo "--- /health response ---"
                            curl -s "http://\${CONTAINER_IP}:${APP_PORT}/health"
                            echo ""
                            exit 0
                        fi

                        echo "Not ready (HTTP \$HTTP_CODE) — retrying in \${DELAY}s..."
                        sleep \$DELAY
                    done

                    echo "Health check FAILED after \$RETRIES attempts"
                    echo "--- Container logs (last 50 lines) ---"
                    docker logs ${CONTAINER_NAME} --tail=50
                    exit 1
                """
            }
        }

        stage('Smoke Test') {
            steps {
                echo 'Running smoke tests against live container...'
                sh """
                    CONTAINER_IP=\$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' ${CONTAINER_NAME})
                    BASE="http://\${CONTAINER_IP}:${APP_PORT}"
                    echo "Smoke testing: \$BASE"

                    check() {
                        HTTP_CODE=\$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "\$1" 2>/dev/null)
                        if [ \$? -ne 0 ]; then HTTP_CODE="000"; fi
                        if [ "\$HTTP_CODE" = "\$2" ]; then
                            echo "  PASS  \$1 → HTTP \$HTTP_CODE"
                        else
                            echo "  FAIL  \$1 → expected \$2, got \$HTTP_CODE"
                            exit 1
                        fi
                    }

                    check "\$BASE/"                      200
                    check "\$BASE/health"                200
                    check "\$BASE/workouts"              200
                    check "\$BASE/workouts/beginner"     200
                    check "\$BASE/workouts/intermediate" 200
                    check "\$BASE/workouts/advanced"     200
                    check "\$BASE/workouts/invalid"      404

                    echo "All smoke tests passed"
                    echo "Application is accessible at: http://localhost:${APP_PORT}"
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
║  Version   : ${env.BUILD_VERSION}                    ║
║  Image     : ${env.IMAGE_VERSIONED}                  ║
║  Container : ${env.CONTAINER_NAME}                   ║
║  URL       : http://localhost:${env.APP_PORT}        ║
║  Commit    : ${env.GIT_COMMIT?.take(7)}              ║
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
║  Version : ${env.BUILD_VERSION}                      ║
╚══════════════════════════════════════════════════════╝
                """
            }
            sh """
                if docker image inspect ${PREV_IMAGE} > /dev/null 2>&1; then
                    echo "Rolling back: ${PREV_IMAGE} → ${IMAGE_LATEST}"
                    docker tag ${PREV_IMAGE} ${IMAGE_LATEST}

                    docker stop ${CONTAINER_NAME} || true
                    docker rm   ${CONTAINER_NAME} || true
                    docker run -d \\
                        --name ${CONTAINER_NAME} \\
                        --network ${NETWORK_NAME} \\
                        --restart unless-stopped \\
                        -p ${APP_PORT}:${APP_PORT} \\
                        ${IMAGE_LATEST}

                    echo "Rollback complete — ${CONTAINER_NAME} running previous version"
                else
                    echo "No rollback image found — this may be the first build"
                fi

                docker rmi ${IMAGE_VERSIONED} || true
            """
        }

        always {
            echo "Build ${BUILD_VERSION} | Result: ${currentBuild.currentResult}"
            sh "docker ps --filter name=${CONTAINER_NAME} --format 'Container: {{.Names}} | Image: {{.Image}} | Status: {{.Status}} | Ports: {{.Ports}}' || true"
        }

    }
}
