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
        IMAGE_NAME = "aceest-fitness"
        BUILD_TAG  = "v1.${BUILD_NUMBER}"
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
                        '''

                        switch (params.DEPLOY_STRATEGY) {

                            case 'rolling-update':
                                echo "Deploying: Rolling Update"
                                sh """
                                    set -e
                                    kubectl apply -f k8s/rolling-update/rolling-update.yaml -n ${KUBE_NS}
                                    kubectl set image deployment/aceest-rolling \\
                                        aceest-app=${IMAGE_NAME}:${BUILD_TAG} \\
                                        -n ${KUBE_NS} --record
                                    kubectl rollout status deployment/aceest-rolling \\
                                        -n ${KUBE_NS} --timeout=120s
                                """
                                break

                            case 'blue-green':
                                echo "Deploying: Blue-Green"
                                sh """
                                    set -e
                                    sed -i 's|aceest-fitness:green|${IMAGE_NAME}:${BUILD_TAG}|g' \\
                                        k8s/blue-green/green-deployment.yaml
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

                                    sed -i 's|aceest-fitness:canary|${IMAGE_NAME}:${BUILD_TAG}|g' \\
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
                                    sed -i 's|aceest-fitness:shadow|${IMAGE_NAME}:${BUILD_TAG}|g' \\
                                        k8s/shadow/shadow-deployment.yaml
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
                                    sed -i 's|aceest-fitness:variant-b|${IMAGE_NAME}:${BUILD_TAG}|g' \\
                                        k8s/ab-testing/ab-deployment.yaml
                                    kubectl apply -f k8s/ab-testing/ab-deployment.yaml -n ${KUBE_NS}
                                    kubectl rollout status deployment/aceest-variant-b \\
                                        -n ${KUBE_NS} --timeout=120s
                                    echo "✓ A/B Testing live — Variant B = ${BUILD_TAG}"
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
    }

    post {
        success {
            echo "✓ BUILD SUCCESSFUL - Deployed ${IMAGE_NAME}:${BUILD_TAG}"
            sh 'kubectl get pods -n ${KUBE_NS} -l app=aceest-fitness' || true
        }
        failure {
            echo "❌ BUILD FAILED - Check the logs above for errors."
            sh '''
                echo "--- Deployment status ---"
                kubectl get all -n ${KUBE_NS} || true
                echo ""
                echo "--- Recent pod events ---"
                kubectl describe pods -n ${KUBE_NS} -l app=aceest-fitness | tail -50 || true
            ''' || true
        }
        always {
            echo '=== Pipeline finished ==='
            sh 'docker images | grep aceest-fitness || true'
        }
    }
}
