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
            steps {
                echo 'Installing Python packages...'
                sh 'pip install -r requirements.txt'
            }
        }

        stage('Lint') {
            steps {
                echo 'Checking for syntax errors...'
                sh 'python -m py_compile app.py && echo "Lint PASSED"'
            }
        }

        stage('Test') {
            steps {
                echo 'Running unit tests...'
                sh 'pytest tests/test_app.py -v'
            }
        }

        stage('Docker Build') {
            steps {
                echo 'Building Docker image...'
                sh 'docker build -t aceest-fitness:latest .'
            }
        }

    }

    post {
        success {
            echo 'BUILD SUCCESSFUL — All stages passed!'
        }
        failure {
            echo 'BUILD FAILED — Check the logs above'
        }
    }
}
