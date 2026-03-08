pipeline {
    agent any

    environment {
        IMAGE_NAME = "aceest-fitness"
        IMAGE_TAG  = "latest"
        APP_PORT   = "5000"
    }

    stages {

        stage('Checkout') {
            steps {
                echo 'Pulling latest code from GitHub...'
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
                echo '🔍 Checking syntax...'
                sh 'python3 -m py_compile app.py && echo "✅ Lint PASSED"'
            }
        }

        stage('Test') {
            steps {
                echo 'Running unit tests...'
                sh 'python3 -m pytest tests/test_app.py -v --tb=short'
            }
        }

        stage('Docker Build') {
            steps {
                echo 'Building Docker image...'
                sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."
                echo "✅ Image ${IMAGE_NAME}:${IMAGE_TAG} built successfully"
            }
        }

    }

    post {
        success {
            echo '✅ BUILD SUCCESSFUL — All stages passed!'
        }
        failure {
            echo '❌ BUILD FAILED — Check the logs above for details'
        }
        always {
            echo '✅Pipeline complete.'
        }
    }
}
