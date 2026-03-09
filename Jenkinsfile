pipeline {
    agent any

    environment {
        IMAGE_NAME    = "aceest-fitness"
        APP_PORT      = "5000"
        // Semantic version tag: e.g. v1.0.42
        BUILD_VERSION = "v1.0.${BUILD_NUMBER}"
        // Full image references
        IMAGE_VERSIONED = "${IMAGE_NAME}:${BUILD_VERSION}"
        IMAGE_LATEST    = "${IMAGE_NAME}:latest"
        // Snapshot of the previous latest — used for rollback
        PREV_IMAGE    = "${IMAGE_NAME}:previous"
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
                sh 'python3 -m py_compile app.py && echo "✅ Lint PASSED"'
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
                // If a "latest" image already exists, snapshot it as "previous"
                // so we can roll back to it if this build breaks production.
                sh """
                    if docker image inspect ${IMAGE_LATEST} > /dev/null 2>&1; then
                        docker tag ${IMAGE_LATEST} ${PREV_IMAGE}
                        echo "✅ Saved ${IMAGE_LATEST} → ${PREV_IMAGE}"
                    else
                        echo "ℹNo existing latest image — skipping snapshot"
                    fi
                """
            }
        }

        stage('Docker Build') {
            steps {
                echo "Building image ${IMAGE_VERSIONED}..."
                // Build with both a versioned tag and latest
                sh """
                    docker build \\
                        --label "build.version=${BUILD_VERSION}" \\
                        --label "build.number=${BUILD_NUMBER}" \\
                        --label "git.commit=${GIT_COMMIT}" \\
                        -t ${IMAGE_VERSIONED} \\
                        -t ${IMAGE_LATEST} \\
                        .
                """
                echo "✅ Tagged as ${IMAGE_VERSIONED} and ${IMAGE_LATEST}"
            }
        }

        stage('Verify Image') {
            steps {
                echo '🔬 Verifying built image...'
                sh """
                    docker image inspect ${IMAGE_VERSIONED} > /dev/null 2>&1 && \\
                        echo "✅ Image ${IMAGE_VERSIONED} verified" || \\
                        (echo "❌ Image verification failed" && exit 1)
                """
                // Print image size and labels for audit trail
                sh "docker image ls ${IMAGE_NAME} --format 'Tag: {{.Tag}} | Size: {{.Size}} | Created: {{.CreatedAt}}'"
            }
        }

    }

    post {

        success {
            script {
                echo """
╔══════════════════════════════════════════════╗
║   ✅  BUILD SUCCESSFUL                       ║
╠══════════════════════════════════════════════╣
║  Version : ${env.BUILD_VERSION}              ║
║  Image   : ${env.IMAGE_VERSIONED}            ║
║  Commit  : ${env.GIT_COMMIT?.take(7)}        ║
╚══════════════════════════════════════════════╝
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
╔══════════════════════════════════════════════╗
║   ❌  BUILD FAILED — Initiating Rollback     ║
╠══════════════════════════════════════════════╣
║  Version : ${env.BUILD_VERSION}              ║
╚══════════════════════════════════════════════╝
                """
            }
            // ── ROLLBACK STRATEGY ────────────────────────────────────────
            // Restore the "previous" snapshot back to "latest" so the
            // last known-good image stays active.
            sh """
                echo "Checking for rollback image: ${IMAGE_PREV}"

                if docker image inspect ${PREV_IMAGE} > /dev/null 2>&1; then
                    echo "Rolling back: ${PREV_IMAGE} → ${IMAGE_LATEST}"
                    docker tag ${PREV_IMAGE} ${IMAGE_LATEST}
                    echo "✅ Rollback complete — ${IMAGE_LATEST} restored"
                else
                    echo "⚠️  No rollback image found — this may be the first build"
                fi

                if docker image inspect ${IMAGE_VERSIONED} > /dev/null 2>&1; then
                    docker rmi ${IMAGE_VERSIONED} || true
                    echo "Removed failed image ${IMAGE_VERSIONED}"
                fi
            """
        }

        always {
            echo "Build ${BUILD_VERSION} | Result: ${currentBuild.currentResult}"
        }

    }
}
