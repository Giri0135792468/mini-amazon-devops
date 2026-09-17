pipeline {
    agent any

    parameters {
        booleanParam(
            name: 'DESTROY_INFRA',
            defaultValue: false,
            description: 'Destroy all Terraform infrastructure'
        )
    }

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

        stage('Terraform AWS Bootstrap') {
            steps {
                withCredentials([
                    string(
                        credentialsId: 'db-password',
                        variable: 'TF_VAR_db_password'
                    ),
                    string(
                        credentialsId: 'jwt-secret',
                        variable: 'TF_VAR_jwt_secret'
                    ),
                    string(
                        credentialsId: 'flask-secret-key',
                        variable: 'TF_VAR_flask_secret_key'
                    )
                ]) {
                    dir('terraform') {
                        sh '''
                            terraform apply \
                                -target=module.vpc \
                                -target=module.eks \
                                -target=module.iam \
                                -auto-approve
                        '''
                    }
                }
            }
        }
stage('Terraform Plan') {
    steps {
        withCredentials([
            string(
                credentialsId: 'db-password',
                variable: 'TF_VAR_db_password'
            ),
            string(
                credentialsId: 'jwt-secret',
                variable: 'TF_VAR_jwt_secret'
            ),
            string(
                credentialsId: 'flask-secret-key',
                variable: 'TF_VAR_flask_secret_key'
            )
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
                    string(
                        credentialsId: 'db-password',
                        variable: 'TF_VAR_db_password'
                    ),
                    string(
                        credentialsId: 'jwt-secret',
                        variable: 'TF_VAR_jwt_secret'
                    ),
                    string(
                        credentialsId: 'flask-secret-key',
                        variable: 'TF_VAR_flask_secret_key'
                    )
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
                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub-credentials',
                        usernameVariable: 'DOCKER_USERNAME',
                        passwordVariable: 'DOCKER_PASSWORD'
                    )
                ]) {
                    sh '''
                        echo "$DOCKER_PASSWORD" | docker login \
                            -u "$DOCKER_USERNAME" \
                            --password-stdin

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
                    rm -rf /tmp/mini-amazon-k8s

                    cp -R k8s /tmp/mini-amazon-k8s

                    find /tmp/mini-amazon-k8s \
                        -type f \
                        -name "*.yaml" \
                        -exec sed -i "s/:1.0/:${IMAGE_TAG}/g" {} +

                    kubectl apply \
                        -f /tmp/mini-amazon-k8s/ \
                        -n mini \
                        --recursive
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

        stage('Destroy Infrastructure') {

            when {
                expression {
                    params.DESTROY_INFRA
                }
            }

            steps {

                withCredentials([
                    string(
                        credentialsId: 'db-password',
                        variable: 'TF_VAR_db_password'
                    ),
                    string(
                        credentialsId: 'jwt-secret',
                        variable: 'TF_VAR_jwt_secret'
                    ),
                    string(
                        credentialsId: 'flask-secret-key',
                        variable: 'TF_VAR_flask_secret_key'
                    )
                ]) {

                    sh '''
                        set -e

                        echo "========================================"
                        echo "Preparing infrastructure for destruction"
                        echo "========================================"

                        # ----------------------------------------
                        # 1. Configure EKS access
                        # ----------------------------------------
                        echo "Configuring EKS access..."

                        aws eks update-kubeconfig \
                            --region ap-south-2 \
                            --name mini-amazon-eks || true

                        # ----------------------------------------
                        # 2. Remove Kubernetes Ingress
                        # ----------------------------------------
                        echo "Removing Kubernetes ingress..."

                        kubectl delete ingress \
                            --all \
                            -n mini \
                            --ignore-not-found=true || true

                        # ----------------------------------------
                        # 3. Remove LoadBalancer Services
                        # ----------------------------------------
                        echo "Removing Kubernetes LoadBalancer services..."

                        kubectl get svc \
                            -n mini \
                            --field-selector spec.type=LoadBalancer \
                            -o name 2>/dev/null | \
                            xargs -r kubectl delete -n mini || true

                        # ----------------------------------------
                        # 4. Wait for AWS Load Balancers
                        # ----------------------------------------
                        echo "Waiting for AWS Load Balancers to disappear..."

                        sleep 60

                        # ----------------------------------------
                        # 5. Delete Kubernetes namespace
                        # ----------------------------------------
                        echo "Deleting Kubernetes namespace..."

                        kubectl delete namespace mini \
                            --ignore-not-found=true || true

                        # ----------------------------------------
                        # 6. Empty versioned S3 bucket
                        # ----------------------------------------
                        echo "========================================"
                        echo "Emptying S3 bucket"
                        echo "========================================"

                        BUCKET="mini-amazon-product-images"

                        if aws s3api head-bucket \
                            --bucket "$BUCKET" \
                            --region ap-south-2 2>/dev/null
                        then

                            while true
                            do

                                VERSIONS=$(aws s3api list-object-versions \
                                    --bucket "$BUCKET" \
                                    --region ap-south-2 \
                                    --output json)

                                DELETE_JSON=$(echo "$VERSIONS" | python3 -c '
import sys
import json

d = json.load(sys.stdin)

objects = []

for x in d.get("Versions", []):
    objects.append({
        "Key": x["Key"],
        "VersionId": x["VersionId"]
    })

for x in d.get("DeleteMarkers", []):
    objects.append({
        "Key": x["Key"],
        "VersionId": x["VersionId"]
    })

print(json.dumps({
    "Objects": objects,
    "Quiet": True
}))
')

                                COUNT=$(echo "$DELETE_JSON" | python3 -c '
import sys
import json

d = json.load(sys.stdin)

print(len(d.get("Objects", [])))
')

                                if [ "$COUNT" -eq 0 ]; then
                                    break
                                fi

                                echo "Deleting $COUNT S3 object versions/delete markers..."

                                echo "$DELETE_JSON" > /tmp/s3-delete.json

                                aws s3api delete-objects \
                                    --bucket "$BUCKET" \
                                    --region ap-south-2 \
                                    --delete file:///tmp/s3-delete.json

                            done

                            echo "S3 bucket is empty."

                        else

                            echo "S3 bucket does not exist. Skipping."

                        fi

                        # ----------------------------------------
                        # 7. Terraform Destroy
                        # ----------------------------------------
                        echo "========================================"
                        echo "Destroying Terraform infrastructure"
                        echo "========================================"

                        cd terraform

                        terraform destroy -auto-approve

                        echo "========================================"
                        echo "Terraform destroy completed"
                        echo "========================================"
                    '''
                }
            }
        }
    }
}