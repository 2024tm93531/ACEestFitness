pipeline {
    agent any

    stages {

        stage('Checkout') {
            steps {
                echo 'Pulling latest code from GitHub repo...'
                git branch: 'main',
                    url: 'https://github.com/2024tm93531/ACEestFitness.git'
            }
        }

        stage('Install Dependencies') {
            agent {
                docker {
                    image 'python:3.12-slim'
                    args '--user root -v /var/jenkins_home/workspace/aceest-job:/workspace -w /workspace'
                    reuseNode true
                }
            }
            steps {
                echo 'Installing Python packages...'
                sh 'pip install -r requirements.txt'
            }
        }

        stage('Lint') {
            agent {
                docker {
                    image 'python:3.12-slim'
                    args '--user root -v /var/jenkins_home/workspace/aceest-job:/workspace -w /workspace'
                    reuseNode true
                }
            }
            steps {
                echo 'Checking for syntax errors...'
                sh 'python -m py_compile app.py && echo "Lint PASSED ✅"'
            }
        }

        stage('Test') {
            agent {
                docker {
                    image 'python:3.12-slim'
                    args '--user root -v /var/jenkins_home/workspace/aceest-job:/workspace -w /workspace'
                    reuseNode true
                }
            }
            steps {
                echo 'Running unit tests...'
                sh '''
                    pip install -r requirements.txt -q
                    python -m pytest tests/test_app.py -v
                '''
            }
        }

        stage('Docker Build') {
            agent any
            steps {
                echo 'Building Docker image...'
                sh 'docker build -t aceest-fitness:latest .'
                echo 'Docker image built successfully ✅'
            }
        }

    }

    post {
        success {
            echo '✅ BUILD SUCCESSFUL — All stages passed!'
        }
        failure {
            echo '❌ BUILD FAILED — Check the logs above'
        }
    }
}

