pipeline {
    agent any

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
                    apt-get update -y
                    apt-get install -y python3 python3-pip python3-venv
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

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

        stage('Unit Tests') {
            steps {
                echo '=== Running Pytest unit tests ==='
                sh '''
                    . venv/bin/activate
                    pytest tests/ -v --tb=short
                '''
            }
        }

        stage('Docker Build') {
            steps {
                echo '=== Building Docker image ==='
                sh 'docker build -t aceest-fitness:latest .'
            }
        }
    }

    post {
        success {
            echo '✅ BUILD SUCCESSFUL – All stages successfully passed!'
        }
        failure {
            echo '❌ BUILD FAILED – Check the logs above for errors.'
        }
        always {
            echo '=== Pipeline finished ==='
        }
    }
}
