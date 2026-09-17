pipeline {
    agent any
environment {
    IMAGE_TAG = "${BUILD_NUMBER}"
}
    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Terraform Init') {
            steps {
                dir('terraform') {
                    sh 'terraform init'
                }
            }
        }

stage('Terraform Plan') {
    steps {
        withCredentials([
            string(credentialsId: 'db-password', variable: 'TF_VAR_db_password'),
            string(credentialsId: 'jwt-secret', variable: 'TF_VAR_jwt_secret'),
            string(credentialsId: 'flask-secret-key', variable: 'TF_VAR_flask_secret_key')
        ]) {
            dir('terraform') {
                sh 'terraform plan'
            }
        }
    }
}

stage('Terraform Apply') {
    steps {
        withCredentials([
            string(credentialsId: 'db-password', variable: 'TF_VAR_db_password'),
            string(credentialsId: 'jwt-secret', variable: 'TF_VAR_jwt_secret'),
            string(credentialsId: 'flask-secret-key', variable: 'TF_VAR_flask_secret_key')
        ]) {
            dir('terraform') {
                sh 'terraform apply -auto-approve'
            }
        }
    }
}
stage('Test') {
    steps {
        sh '''
            python3 -m compileall frontend services
        '''
    }
}
stage('Build Docker Images') {
    steps {
        sh '''
            docker build -t girijos/mini-amazon-user-service:${IMAGE_TAG} ./services/user-service
            docker build -t girijos/mini-amazon-product-service:${IMAGE_TAG} ./services/product-service
            docker build -t girijos/mini-amazon-cart-service:${IMAGE_TAG} ./services/cart-service
            docker build -t girijos/mini-amazon-order-service:${IMAGE_TAG} ./services/order-service
            docker build -t girijos/mini-amazon-payment-service:${IMAGE_TAG} ./services/payment-service
            docker build -t girijos/mini-amazon-notification-service:${IMAGE_TAG} ./services/notification-service
            docker build -t girijos/mini-amazon-frontend:${IMAGE_TAG} ./frontend
        '''
    }
}
stage('Push Docker Images') {
    steps {
        withCredentials([usernamePassword(
            credentialsId: 'dockerhub-credentials',
            usernameVariable: 'DOCKER_USERNAME',
            passwordVariable: 'DOCKER_PASSWORD'
        )]) {
            sh '''
                echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin

                docker push girijos/mini-amazon-user-service:${IMAGE_TAG}
                docker push girijos/mini-amazon-product-service:${IMAGE_TAG}
                docker push girijos/mini-amazon-cart-service:${IMAGE_TAG}
                docker push girijos/mini-amazon-order-service:${IMAGE_TAG}
                docker push girijos/mini-amazon-payment-service:${IMAGE_TAG}
                docker push girijos/mini-amazon-notification-service:${IMAGE_TAG}
                docker push girijos/mini-amazon-frontend:${IMAGE_TAG}

                docker logout
            '''
        }
    }
}
stage('Configure EKS Access') {
    steps {
        sh '''
            aws eks update-kubeconfig \
                --region ap-south-2 \
                --name mini-amazon-eks

            kubectl get nodes
        '''
    }
}



stage('Deploy to EKS') {
    steps {
        sh '''
            cp -R k8s /tmp/mini-amazon-k8s

            find /tmp/mini-amazon-k8s -type f -name "*.yaml" \
                -exec sed -i "s/:1.0/:${IMAGE_TAG}/g" {} +

            kubectl apply -f /tmp/mini-amazon-k8s/ -n mini
        '''
    }
}
stage('Verify Deployment') {
    steps {
        sh '''
            kubectl get pods -n mini
            kubectl get services -n mini
            kubectl get ingress -n mini
        '''
    }
}

    }
}