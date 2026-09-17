pipeline {
    agent any

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
                dir('terraform') {
                    sh 'terraform plan'
                }
            }
        }

stage('Terraform Apply') {
    steps {
        dir('terraform') {
            sh 'terraform apply -auto-approve'
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
            docker build -t girijos/mini-amazon-user-service:1.0 ./services/user-service
            docker build -t girijos/mini-amazon-product-service:1.0 ./services/product-service
            docker build -t girijos/mini-amazon-cart-service:1.0 ./services/cart-service
            docker build -t girijos/mini-amazon-order-service:1.0 ./services/order-service
            docker build -t girijos/mini-amazon-payment-service:1.0 ./services/payment-service
            docker build -t girijos/mini-amazon-notification-service:1.0 ./services/notification-service
            docker build -t girijos/mini-amazon-frontend:1.0 ./frontend
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

                docker push girijos/mini-amazon-user-service:1.0
                docker push girijos/mini-amazon-product-service:1.0
                docker push girijos/mini-amazon-cart-service:1.0
                docker push girijos/mini-amazon-order-service:1.0
                docker push girijos/mini-amazon-payment-service:1.0
                docker push girijos/mini-amazon-notification-service:1.0
                docker push girijos/mini-amazon-frontend:1.0

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
            sh 'kubectl apply -f k8s/*.yaml -n mini'
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