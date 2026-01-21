pipeline {
    agent any

    environment {
        ARTIFACTS_DIR = "artifacts/${BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install -e .
                    ansible-galaxy collection install community.docker
                '''
            }
        }

        stage('E2E Tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    autoe2e run -f demo/spec.yml --suite all --artifacts-dir ${ARTIFACTS_DIR}
                '''
            }
        }
    }

    post {
        always {
            // Archive artifacts
            archiveArtifacts artifacts: "${ARTIFACTS_DIR}/**/*", allowEmptyArchive: true

            // Publish JUnit results
            junit testResults: "${ARTIFACTS_DIR}/reports/junit.xml", allowEmptyResults: true

            // Cleanup
            sh '''
                . venv/bin/activate
                autoe2e down -f demo/spec.yml || true
            '''
        }

        failure {
            echo 'E2E tests failed! Check artifacts for logs.'
        }

        success {
            echo 'E2E tests passed!'
        }
    }
}
