// ═══════════════════════════════════════════════════════════════════
// ACEest Fitness & Gym — Phase 2 CI/CD Pipeline
//
// Stages:
//   1. Checkout
//   2. Python Environment Setup
//   3. Lint Check (flake8)
//   4. Unit Tests (pytest + coverage)
//   5. SonarQube Analysis + Quality Gate
//   6. Docker Build & Tag
//   7. Push to Docker Hub
//   8. Deploy to Kubernetes (strategy selected via DEPLOY_STRATEGY param)
//      ├── rolling-update (default)
//      ├── blue-green
//      ├── canary
//      ├── shadow
//      └── ab-testing
//   9. Post-Deployment Health Check + Auto-Rollback
// ═══════════════════════════════════════════════════════════════════

pipeline {
    agent any

    parameters {
        choice(
            name: 'DEPLOY_STRATEGY',
            choices: ['rolling-update', 'blue-green', 'canary', 'shadow', 'ab-testing'],
            description: 'Kubernetes deployment strategy'
        )
        string(
            name: 'DOCKER_TAG',
            defaultValue: '',
            description: 'Docker tag — leave blank to auto-generate v2.BUILD_NUMBER'
        )
        booleanParam(
            name: 'ROLLBACK_ON_FAIL',
            defaultValue: true,
            description: 'Auto-rollback Kubernetes deployment on health check failure'
        )
        string(
            name: 'CANARY_WEIGHT',
            defaultValue: '10',
            description: 'Canary traffic % (canary strategy only)'
        )
    }

    environment {
        IMAGE_NAME      = "aceest-fitness"
        DOCKER_HUB_USER = credentials('dockerhub-username')
        FULL_IMAGE      = "${DOCKER_HUB_USER}/${IMAGE_NAME}"
        BUILD_TAG       = "${params.DOCKER_TAG ?: "v2.${BUILD_NUMBER}"}"
        KUBE_NS         = "aceest"
        SONAR_HOST      = "http://localhost:9000"
    }

    stages {

        stage('Checkout') {
            steps {
                echo '=== Stage 1: Checkout ==='
                checkout scm
                sh 'git log --oneline -5'
            }
        }

        stage('Setup Python Environment') {
            steps {
                echo '=== Stage 2: Setup Python Virtual Environment ==='
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip -q
                    pip install -r requirements.txt -q
                    python --version
                '''
            }
        }

        stage('Lint Check') {
            steps {
                echo '=== Stage 3: Lint Check (flake8) ==='
                sh '''
                    . venv/bin/activate
                    flake8 app.py --select=E9,F63,F7,F82 --show-source --statistics
                    echo "Lint passed."
                '''
            }
        }

        stage('Unit Tests') {
            steps {
                echo '=== Stage 4: Unit Tests (pytest + coverage) ==='
                sh '''
                    . venv/bin/activate
                    pytest tests/ -v --tb=short \
                        --junit-xml=test-results.xml \
                        --cov=app \
                        --cov-report=xml:coverage.xml \
                        --cov-report=term-missing
                '''
            }
            post {
                always {
                    junit 'test-results.xml'
                }
            }
        }

        stage('SonarQube Analysis') {
            steps {
                echo '=== Stage 5a: SonarQube Static Analysis ==='
                withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
                    withSonarQubeEnv('SonarQube') {
                        sh '''
                            sonar-scanner \
                              -Dsonar.projectKey=aceest-fitness \
                              -Dsonar.projectName="ACEest Fitness" \
                              -Dsonar.projectVersion=${BUILD_TAG} \
                              -Dsonar.sources=app.py \
                              -Dsonar.tests=tests \
                              -Dsonar.python.coverage.reportPaths=coverage.xml \
                              -Dsonar.python.xunit.reportPath=test-results.xml \
                              -Dsonar.host.url=${SONAR_HOST} \
                              -Dsonar.login=${SONAR_TOKEN}
                        '''
                    }
                }
            }
        }

        stage('SonarQube Quality Gate') {
            steps {
                echo '=== Stage 5b: SonarQube Quality Gate ==='
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Docker Build & Tag') {
            steps {
                echo "=== Stage 6: Docker Build — ${IMAGE_NAME}:${BUILD_TAG} ==="
                sh '''
                    docker build \
                        -t ${FULL_IMAGE}:${BUILD_TAG} \
                        -t ${FULL_IMAGE}:latest \
                        --label "build.number=${BUILD_NUMBER}" \
                        --label "git.commit=$(git rev-parse --short HEAD)" \
                        .
                    docker images | grep ${IMAGE_NAME}
                '''
            }
        }

        stage('Push to Docker Hub') {
            steps {
                echo '=== Stage 7: Push to Docker Hub ==='
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-credentials',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                        docker push ${FULL_IMAGE}:${BUILD_TAG}
                        docker push ${FULL_IMAGE}:latest
                        docker logout
                        echo "Push complete: ${FULL_IMAGE}:${BUILD_TAG}"
                    '''
                }
            }
        }

        stage('Kubernetes Deploy') {
            steps {
                echo "=== Stage 8: Kubernetes Deploy — Strategy: ${params.DEPLOY_STRATEGY} ==="
                script {
                    sh "kubectl apply -f k8s/namespace.yaml"
                    sh "kubectl apply -f k8s/configmap.yaml"

                    switch (params.DEPLOY_STRATEGY) {

                        case 'rolling-update':
                            echo "Deploying: Rolling Update"
                            sh """
                                kubectl apply -f k8s/rolling-update/rolling-update.yaml -n ${KUBE_NS}
                                kubectl set image deployment/aceest-rolling \
                                    aceest-app=${FULL_IMAGE}:${BUILD_TAG} \
                                    -n ${KUBE_NS} --record
                                kubectl rollout status deployment/aceest-rolling \
                                    -n ${KUBE_NS} --timeout=120s
                            """
                            break

                        case 'blue-green':
                            echo "Deploying: Blue-Green"
                            sh """
                                sed -i 's|aceest-fitness:green|${FULL_IMAGE}:${BUILD_TAG}|g' \
                                    k8s/blue-green/green-deployment.yaml
                                kubectl apply -f k8s/blue-green/green-deployment.yaml -n ${KUBE_NS}
                                kubectl rollout status deployment/aceest-green \
                                    -n ${KUBE_NS} --timeout=120s

                                GREEN_IP=\$(kubectl get svc aceest-green-staging \
                                    -n ${KUBE_NS} -o jsonpath='{.spec.clusterIP}')
                                if curl -sf http://\${GREEN_IP}:5000/api/health | grep -q '"ok"'; then
                                    sed -i 's/version: blue/version: green/' \
                                        k8s/blue-green/service-switch.yaml
                                    kubectl apply -f k8s/blue-green/service-switch.yaml -n ${KUBE_NS}
                                    echo "Traffic switched to GREEN."
                                else
                                    echo "Green health check FAILED — keeping BLUE live."
                                    exit 1
                                fi
                            """
                            break

                        case 'canary':
                            echo "Deploying: Canary (${params.CANARY_WEIGHT}% traffic)"
                            sh """
                                TOTAL=10
                                CANARY_REPLICAS=\$(( ${params.CANARY_WEIGHT} * TOTAL / 100 ))
                                [ "\$CANARY_REPLICAS" -lt 1 ] && CANARY_REPLICAS=1
                                STABLE_REPLICAS=\$(( TOTAL - CANARY_REPLICAS ))

                                sed -i 's|aceest-fitness:canary|${FULL_IMAGE}:${BUILD_TAG}|g' \
                                    k8s/canary/canary-deployment.yaml
                                kubectl apply -f k8s/canary/canary-deployment.yaml -n ${KUBE_NS}
                                kubectl scale deployment aceest-stable \
                                    --replicas=\$STABLE_REPLICAS -n ${KUBE_NS}
                                kubectl scale deployment aceest-canary \
                                    --replicas=\$CANARY_REPLICAS -n ${KUBE_NS}
                                kubectl rollout status deployment/aceest-canary \
                                    -n ${KUBE_NS} --timeout=120s
                                echo "Canary live: \$CANARY_REPLICAS/10 replicas = ~${params.CANARY_WEIGHT}% traffic"
                            """
                            break

                        case 'shadow':
                            echo "Deploying: Shadow"
                            sh """
                                sed -i 's|aceest-fitness:shadow|${FULL_IMAGE}:${BUILD_TAG}|g' \
                                    k8s/shadow/shadow-deployment.yaml
                                kubectl apply -f k8s/shadow/shadow-deployment.yaml -n ${KUBE_NS}
                                kubectl rollout status deployment/aceest-shadow \
                                    -n ${KUBE_NS} --timeout=120s
                                echo "Shadow deployment active — mirroring production traffic."
                            """
                            break

                        case 'ab-testing':
                            echo "Deploying: A/B Testing"
                            sh """
                                sed -i 's|aceest-fitness:variant-b|${FULL_IMAGE}:${BUILD_TAG}|g' \
                                    k8s/ab-testing/ab-deployment.yaml
                                kubectl apply -f k8s/ab-testing/ab-deployment.yaml -n ${KUBE_NS}
                                kubectl rollout status deployment/aceest-variant-b \
                                    -n ${KUBE_NS} --timeout=120s
                                echo "A/B Testing live — Variant B = ${BUILD_TAG}"
                            """
                            break

                        default:
                            error "Unknown DEPLOY_STRATEGY: ${params.DEPLOY_STRATEGY}"
                    }
                }
            }
        }

        stage('Post-Deploy Health Check') {
            steps {
                echo '=== Stage 9: Health Check & Auto-Rollback ==='
                script {
                    sh 'sleep 10'
                    def healthy = sh(
                        script: """
                            kubectl get pods -n ${KUBE_NS} -l app=aceest-fitness \
                                --field-selector=status.phase=Running --no-headers | wc -l
                        """,
                        returnStdout: true
                    ).trim().toInteger()

                    echo "Running pods found: ${healthy}"

                    if (healthy < 1) {
                        if (params.ROLLBACK_ON_FAIL) {
                            echo "ROLLING BACK — no healthy pods detected."
                            sh """
                                kubectl rollout undo deployment/aceest-rolling  -n ${KUBE_NS} || true
                                kubectl rollout undo deployment/aceest-canary   -n ${KUBE_NS} || true
                                kubectl rollout undo deployment/aceest-green    -n ${KUBE_NS} || true
                                kubectl rollout undo deployment/aceest-variant-b -n ${KUBE_NS} || true
                                echo "Rollback complete."
                            """
                        }
                        error "Health check FAILED — 0 running pods after deploy."
                    }

                    echo "Health check PASSED — ${healthy} pod(s) running."
                    sh "kubectl get pods -n ${KUBE_NS} -l app=aceest-fitness"
                }
            }
        }

    } // end stages

    post {
        success {
            echo "BUILD SUCCESSFUL — ${FULL_IMAGE}:${BUILD_TAG} | Strategy: ${params.DEPLOY_STRATEGY}"
        }
        failure {
            echo "BUILD FAILED — Check logs. Rollback on fail: ${params.ROLLBACK_ON_FAIL}"
        }
        always {
            echo '=== Pipeline complete ==='
            sh '''
                docker images | grep aceest-fitness || true
                kubectl get pods -n aceest 2>/dev/null || true
            '''
            cleanWs()
        }
    }
}
