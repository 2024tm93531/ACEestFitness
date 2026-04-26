pipeline {
    agent any

    parameters {
        choice(
            name: 'DEPLOY_STRATEGY',
            choices: ['rolling-update', 'blue-green', 'canary', 'shadow', 'ab-testing'],
            description: 'Kubernetes deployment strategy'
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
        IMAGE_NAME = "2024tm93531/aceest-fitness"
        BUILD_TAG  = "v1.${BUILD_NUMBER}"
        //#DOCKER_HUB_USER = credentials('dockerhub-username')
        KUBE_NS    = "aceest"
        // Explicit kubeconfig path
        KUBECONFIG = "/var/jenkins_home/.kube/config"
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

        stage('SonarQube Static Analysis') {
            environment {
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

        stage('Push to Docker Hub') {
            steps {
                echo '=== Stage 7: Push to Docker Hub ==='

                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-credentials',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {

                    sh """
                        echo "\$DOCKER_PASS" | docker login -u "\$DOCKER_USER" --password-stdin
                        docker push ${IMAGE_NAME}:${BUILD_TAG}
                        docker push ${IMAGE_NAME}:latest
                        echo "Push complete: ${IMAGE_NAME}:${BUILD_TAG}"
                    """

                    script {
                        if (params.DEPLOY_STRATEGY == 'blue-green') {
                            sh """
                                docker tag ${IMAGE_NAME}:latest       ${IMAGE_NAME}:blue
                                docker push ${IMAGE_NAME}:blue

                                docker tag ${IMAGE_NAME}:${BUILD_TAG} ${IMAGE_NAME}:green
                                docker push ${IMAGE_NAME}:green

                                echo "Blue-Green tags pushed"
                            """
                        } else if (params.DEPLOY_STRATEGY == 'ab-testing') {
                            sh """
                                docker tag ${IMAGE_NAME}:latest       ${IMAGE_NAME}:variant-a
                                docker push ${IMAGE_NAME}:variant-a

                                docker tag ${IMAGE_NAME}:${BUILD_TAG} ${IMAGE_NAME}:variant-b
                                docker push ${IMAGE_NAME}:variant-b

                                echo "A/B tags pushed"
                            """
                        } else if (params.DEPLOY_STRATEGY == 'shadow') {
                            sh """
                                docker tag ${IMAGE_NAME}:${BUILD_TAG} ${IMAGE_NAME}:shadow
                                docker push ${IMAGE_NAME}:shadow

                                echo "Shadow tag pushed"
                            """
                        }

                        sh 'docker logout'
                    }
                }
            }
        }

        // NEW STAGE: Validate Kubernetes Access
        stage('Validate Kubernetes Access') {
            steps {
                echo '=== Validating Kubernetes cluster connectivity ==='
                script {
                    try {
                        sh '''
                            echo "--- Checking kubeconfig file ---"
                            if [ ! -f "$KUBECONFIG" ]; then
                                echo "ERROR: kubeconfig not found at $KUBECONFIG"
                                echo "Available directories in /var/jenkins_home:"
                                ls -la /var/jenkins_home/ || true
                                exit 1
                            fi
                            
                            echo "kubeconfig found at: $KUBECONFIG"
                            ls -la "$KUBECONFIG"
                            
                            echo ""
                            echo "--- Testing kubectl version ---"
                            kubectl version --client
                            
                            echo ""
                            echo "--- Testing cluster connection ---"
                            kubectl cluster-info
                            
                            echo ""
                            echo "--- Listing available nodes ---"
                            kubectl get nodes -o wide
                            
                            echo ""
                            echo "--- Checking authentication ---"
                            kubectl auth can-i create deployments --all-namespaces
                            
                            echo ""
                            echo "--- Current context ---"
                            kubectl config current-context
                            
                            echo "✓ Kubernetes access validated successfully"
                        '''
                    } catch (Exception e) {
                        echo "❌ ERROR: Cannot access Kubernetes cluster"
                        echo "Exception: ${e.message}"
                        echo ""
                        echo "TROUBLESHOOTING STEPS:"
                        echo "1. Verify kubeconfig is mounted into Jenkins container"
                        echo "2. Check kubeconfig file permissions: chmod 600 ~/.kube/config"
                        echo "3. Verify Kubernetes cluster is running and accessible"
                        echo "4. Check network connectivity to Kubernetes API server"
                        error("Kubernetes validation failed - see logs above for details")
                    }
                }
            }
        }

        stage('Kubernetes Deployment') {
            steps {
                echo "=== Stage: Kubernetes Deploy — Strategy: ${params.DEPLOY_STRATEGY} ==="
                script {
                    try {
                        sh '''
                            echo "--- Creating/verifying namespace ---"
                            kubectl create namespace ${KUBE_NS} --dry-run=client -o yaml | kubectl apply -f -
                            kubectl get namespace ${KUBE_NS}
                            
                            echo ""
                            echo "--- Applying configmap ---"
                            kubectl apply -f k8s/configmap.yaml -n ${KUBE_NS}

                            echo ""
                            echo "--- Applying PVC ---"
                            kubectl apply -f k8s/sqlite-pvc.yaml -n ${KUBE_NS}
                        '''

                        switch (params.DEPLOY_STRATEGY) {

                            case 'rolling-update':
                                echo "Deploying: Rolling Update"
                                sh """
                                    set -e
                                    kubectl apply -f k8s/rolling-update/rolling-update.yaml -n ${KUBE_NS}
                                    kubectl set image deployment/aceest-rolling \\
                                        aceest-app=${IMAGE_NAME}:${BUILD_TAG} \\
                                        -n ${KUBE_NS}
                                    kubectl rollout status deployment/aceest-rolling \\
                                        -n ${KUBE_NS} --timeout=120s
                                """
                                break

                            case 'blue-green':
                                echo "Deploying: Blue-Green"
                                sh """
                                    set -e
                                    kubectl apply -f k8s/blue-green/blue-deployment.yaml -n ${KUBE_NS}
                                    kubectl rollout status deployment/aceest-blue \\
                                        -n ${KUBE_NS} --timeout=120s

                                    kubectl apply -f k8s/blue-green/service-switch.yaml -n ${KUBE_NS}

                                    kubectl apply -f k8s/blue-green/green-deployment.yaml -n ${KUBE_NS}
                                    kubectl rollout status deployment/aceest-green \\
                                        -n ${KUBE_NS} --timeout=120s

                                    GREEN_IP=\$(kubectl get svc aceest-green-staging \\
                                        -n ${KUBE_NS} -o jsonpath='{.spec.clusterIP}')
                                    
                                    echo "Testing Green deployment health at: \${GREEN_IP}:5000"
                                    if curl -sf http://\${GREEN_IP}:5000/api/health | grep -q '"ok"'; then
                                        echo "✓ Green health check PASSED"
                                        sed -i 's/version: blue/version: green/' \\
                                            k8s/blue-green/service-switch.yaml
                                        kubectl apply -f k8s/blue-green/service-switch.yaml -n ${KUBE_NS}
                                        echo "Traffic switched to GREEN."
                                    else
                                        echo "❌ Green health check FAILED"
                                        exit 1
                                    fi
                                """
                                break

                            case 'canary':
                                echo "Deploying: Canary (${params.CANARY_WEIGHT}% traffic)"
                                sh """
                                    set -e
                                    TOTAL=10
                                    CANARY_REPLICAS=\$(( ${params.CANARY_WEIGHT} * TOTAL / 100 ))
                                    [ "\$CANARY_REPLICAS" -lt 1 ] && CANARY_REPLICAS=1
                                    STABLE_REPLICAS=\$(( TOTAL - CANARY_REPLICAS ))

                                    echo "Canary replicas: \$CANARY_REPLICAS/\$TOTAL"
                                    echo "Stable replicas: \$STABLE_REPLICAS/\$TOTAL"

                                    sed -i 's|aceest-fitness:canary|aceest-fitness:${BUILD_TAG}|g' \\
                                        k8s/canary/canary-deployment.yaml
                                    kubectl apply -f k8s/canary/canary-deployment.yaml -n ${KUBE_NS}
                                    kubectl scale deployment aceest-stable \\
                                        --replicas=\$STABLE_REPLICAS -n ${KUBE_NS}
                                    kubectl scale deployment aceest-canary \\
                                        --replicas=\$CANARY_REPLICAS -n ${KUBE_NS}
                                    kubectl rollout status deployment/aceest-canary \\
                                        -n ${KUBE_NS} --timeout=120s
                                    echo "✓ Canary live: \$CANARY_REPLICAS/10 replicas = ~${params.CANARY_WEIGHT}% traffic"
                                """
                                break

                            case 'shadow':
                                echo "Deploying: Shadow"
                                sh """
                                    set -e
                                    kubectl apply -f k8s/shadow/shadow-deployment.yaml -n ${KUBE_NS}
                                    kubectl rollout status deployment/aceest-shadow \\
                                        -n ${KUBE_NS} --timeout=120s
                                    echo "✓ Shadow deployment active — mirroring production traffic."
                                """
                                break

                            case 'ab-testing':
                                echo "Deploying: A/B Testing"
                                sh """
                                    set -e
                                    kubectl apply -f k8s/ab-testing/ab-deployment.yaml -n ${KUBE_NS}
                                    kubectl rollout status deployment/aceest-variant-b \\
                                        -n ${KUBE_NS} --timeout=120s
                                    echo "✓ A/B Testing live — Variant A = :variant-a | Variant B = :variant-b"
                                """
                                break

                            default:
                                error "Unknown DEPLOY_STRATEGY: ${params.DEPLOY_STRATEGY}"
                        }
                    } catch (Exception e) {
                        echo "❌ Deployment failed: ${e.message}"
                        error("Kubernetes deployment failed")
                    }
                }
            }
        }

        stage('Post-Deploy Health Check') {
            steps {
                echo '=== Post-Deploy Health Check & Auto-Rollback ==='
                script {
                    try {
                        sh 'sleep 10'
                        def healthy = sh(
                            script: """
                                kubectl get pods -n ${KUBE_NS} -l app=aceest-fitness \\
                                    --field-selector=status.phase=Running --no-headers | wc -l
                            """,
                            returnStdout: true
                        ).trim().toInteger()

                        echo "Running pods found: ${healthy}"

                        if (healthy < 1) {
                            if (params.ROLLBACK_ON_FAIL) {
                                echo "⚠️ ROLLING BACK — no healthy pods detected."
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

                        echo "✓ Health check PASSED — ${healthy} pod(s) running."
                        sh "kubectl get pods -n ${KUBE_NS} -l app=aceest-fitness"
                    } catch (Exception e) {
                        echo "❌ Health check error: ${e.message}"
                        error("Post-deploy health check failed")
                    }
                }
            }
        }

        stage('Access Info') {
            steps {
                echo '=== Application Access — Port Forward Commands ==='
                script {
                    switch (params.DEPLOY_STRATEGY) {

                        case 'rolling-update':
                            sh """
                                echo ""
                                echo "Strategy: Rolling Update"
                                echo "Service:  aceest-rolling-service (NodePort 30084)"
                                echo ""
                                echo "Run to access the app:"
                                echo "  kubectl port-forward svc/aceest-rolling-service 5000:5000 -n ${KUBE_NS}"
                                echo ""
                                echo "Then open: http://localhost:5000"
                                echo ""
                                kubectl get svc aceest-rolling-service -n ${KUBE_NS} || true
                            """
                            break

                        case 'blue-green':
                            sh """
                                echo ""
                                echo "Strategy: Blue-Green"
                                echo "Live service:         aceest-service       (NodePort 30080)"
                                echo "Blue staging service: aceest-blue-staging  (NodePort 30085)"
                                echo "Green staging service:aceest-green-staging (NodePort 30081)"
                                echo ""
                                echo "Run to access live traffic (whichever version is active):"
                                echo "  kubectl port-forward svc/aceest-service 8080:5000 -n ${KUBE_NS}"
                                echo ""
                                echo "Run to access blue staging directly:"
                                echo "  kubectl port-forward svc/aceest-blue-staging 8085:5000 -n ${KUBE_NS}"
                                echo ""
                                echo "Run to access green staging directly:"
                                echo "  kubectl port-forward svc/aceest-green-staging 8081:5000 -n ${KUBE_NS}"
                                echo ""
                                echo "Then open:"
                                echo "  http://localhost:8080  (live)"
                                echo "  http://localhost:8085  (blue staging)"
                                echo "  http://localhost:8081  (green staging)"
                                echo ""
                                kubectl get svc aceest-service aceest-blue-staging aceest-green-staging -n ${KUBE_NS} || true
                            """
                            break

                        case 'canary':
                            sh """
                                echo ""
                                echo "Strategy: Canary"
                                echo "Service: aceest-canary-service (NodePort 30082)"
                                echo "         Routes to both stable (~90%) and canary (~10%) pods"
                                echo ""
                                echo "Run to access the app:"
                                echo "  kubectl port-forward svc/aceest-canary-service 5000:5000 -n ${KUBE_NS}"
                                echo ""
                                echo "Then open: http://localhost:5000"
                                echo ""
                                kubectl get svc aceest-canary-service -n ${KUBE_NS} || true
                            """
                            break

                        case 'shadow':
                            sh """
                                echo ""
                                echo "Strategy: Shadow"
                                echo "Production service: aceest-production-service (NodePort 30083)"
                                echo "Shadow service:     aceest-shadow-service     (ClusterIP — internal only)"
                                echo ""
                                echo "Run to access production traffic:"
                                echo "  kubectl port-forward svc/aceest-production-service 5000:5000 -n ${KUBE_NS}"
                                echo ""
                                echo "Run to inspect shadow (internal) traffic:"
                                echo "  kubectl port-forward svc/aceest-shadow-service 5001:5000 -n ${KUBE_NS}"
                                echo ""
                                echo "Then open: http://localhost:5000 (production)"
                                echo ""
                                kubectl get svc aceest-production-service aceest-shadow-service -n ${KUBE_NS} || true
                            """
                            break

                        case 'ab-testing':
                            sh """
                                echo ""
                                echo "Strategy: A/B Testing"
                                echo "Variant A (control): aceest-variant-a-svc (ClusterIP)"
                                echo "Variant B (test):    aceest-variant-b-svc (ClusterIP)"
                                echo ""
                                echo "Run to access Variant A:"
                                echo "  kubectl port-forward svc/aceest-variant-a-svc 5000:5000 -n ${KUBE_NS}"
                                echo ""
                                echo "Run to access Variant B:"
                                echo "  kubectl port-forward svc/aceest-variant-b-svc 5001:5000 -n ${KUBE_NS}"
                                echo ""
                                echo "Then open: http://localhost:5000 (Variant A)  |  http://localhost:5001 (Variant B)"
                                echo ""
                                kubectl get svc aceest-variant-a-svc aceest-variant-b-svc -n ${KUBE_NS} || true
                            """
                            break
                    }
                }
            }
        }
    }

    post {
        success {
            echo "✓ BUILD SUCCESSFUL - Deployed ${IMAGE_NAME}:${BUILD_TAG}"
            sh '''
                kubectl get pods -n ${KUBE_NS} -l app=aceest-fitness || true
            '''
        }
        failure {
            echo "❌ BUILD FAILED - Check the logs above for errors."
            sh '''
                echo "--- Deployment status ---"
                kubectl get all -n ${KUBE_NS} || true
                echo ""
                echo "--- Recent pod events ---"
                kubectl describe pods -n ${KUBE_NS} -l app=aceest-fitness | tail -50 || true
            '''
        }
        always {
            echo '=== Pipeline finished ==='
            sh '''
                docker images | grep aceest-fitness || true
            '''
        }
    }
}
