pipeline {
    agent any

    parameters {
        choice(
            name: 'DEPLOY_STRATEGY',
            choices: ['rolling-update', 'blue-green', 'canary', 'shadow', 'ab-testing'],
            description: 'Kubernetes deployment strategy'
        )
        // string(
        //     name: 'DOCKER_TAG',
        //     defaultValue: '',
        //     description: 'Docker tag — leave blank to auto-generate v2.BUILD_NUMBER'
        // )
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
        IMAGE_NAME = "aceest-fitness"
        BUILD_TAG  = "v1.${BUILD_NUMBER}"
        KUBE_NS    = "aceest"
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
                echo '=== Setting up Python virtual environment ==='
                sh '''
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

        // SonarQube scans the source code for bugs, vulnerabilities, and code quality issues
        stage('SonarQube Static Analysis') {
            environment {
                // This pulls the scanner using the Name field from your screenshot
                SCANNER_HOME = tool 'sonarqube-scanner-int' 
            }
            steps {
                echo '=== Running SonarQube static analysis ==='
                withSonarQubeEnv('sonarqube-scanner-int') {
                    sh '''
                        . venv/bin/activate
                        
                        $SCANNER_HOME/bin/sonar-scanner \
                          -Dsonar.projectKey=aceest-fitness \
                          -Dsonar.sources=. \
                          -Dsonar.python.version=3 \
                          -Dsonar.sourceEncoding=UTF-8
                    '''
                }
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

        stage('Kubernetes Deployment') {
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
                                    aceest-app=${IMAGE_NAME}:${BUILD_TAG} \
                                    -n ${KUBE_NS} --record
                                kubectl rollout status deployment/aceest-rolling \
                                    -n ${KUBE_NS} --timeout=120s
                            """
                            break

                        case 'blue-green':
                            echo "Deploying: Blue-Green"
                            sh """
                                sed -i 's|aceest-fitness:green|${IMAGE_NAME}:${BUILD_TAG}|g' \
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

                                sed -i 's|aceest-fitness:canary|${IMAGE_NAME}:${BUILD_TAG}|g' \
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
                                sed -i 's|aceest-fitness:shadow|${IMAGE_NAME}:${BUILD_TAG}|g' \
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
                                sed -i 's|aceest-fitness:variant-b|${IMAGE_NAME}:${BUILD_TAG}|g' \
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

        // stage('Deploy Latest Image') {
        //     steps {
        //         echo '=== Stopping old container and deploying latest ==='
        //         sh '''
        //             docker stop aceest-app 2>/dev/null || true
        //             docker rm aceest-app 2>/dev/null || true

        //             # Kill ANY other container holding port 5000
        //             CONFLICT=$(docker ps --filter "publish=5000" --format "{{.ID}}")
        //             if [ -n "$CONFLICT" ]; then
        //                 echo "Found container occupying port 5000 — stopping it..."
        //                 echo "$CONFLICT" | xargs docker stop
        //                 echo "$CONFLICT" | xargs docker rm 2>/dev/null || true
        //             fi

        //             docker run -d \
        //                 --name aceest-app \
        //                 -p 5000:5000 \
        //                 --restart unless-stopped \
        //                 ${IMAGE_NAME}:latest

        //             echo "=== App deployed at http://localhost:5000 ==="
        //             docker ps | grep aceest-app
        //         '''
        //     }
        // }

        // stage('Rollback Check') {
        //     steps {
        //         echo '=== Verifying deployment health ==='
        //         sh '''
        //             sleep 5
        //             if docker ps | grep -q aceest-app; then
        //                 echo "Deployment SUCCESS - container is healthy"
        //                 docker ps | grep aceest-app
        //             else
        //                 echo "Container crashed - triggering rollback..."

        //                 PREV_TAG=$(docker images ${IMAGE_NAME} \
        //                     --format "{{.Tag}}" \
        //                     | grep "^v1\\." \
        //                     | grep -v "^${BUILD_TAG}$" \
        //                     | sort -t. -k2 -rn \
        //                     | head -1)

        //                 if [ -n "$PREV_TAG" ]; then
        //                     echo "Rolling back to ${IMAGE_NAME}:${PREV_TAG}"
        //                     docker stop aceest-app 2>/dev/null || true
        //                     docker rm aceest-app 2>/dev/null || true
        //                     docker run -d \
        //                         --name aceest-app \
        //                         -p 5000:5000 \
        //                         --restart unless-stopped \
        //                         ${IMAGE_NAME}:${PREV_TAG}
        //                     echo "Rollback complete - running ${PREV_TAG}"
        //                 else
        //                     echo "No previous image found for rollback"
        //                     exit 1
        //                 fi
        //             fi
        //         '''
        //     }
        // }
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
