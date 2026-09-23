
pipeline {
    agent any

    parameters {
        booleanParam(
            name: 'DESTROY_INFRA',
            defaultValue: false,
            description: 'Destroy all Terraform infrastructure'
        )

        string(
            name: 'ROLLBACK_BUILD',
            defaultValue: '',
            description: 'Jenkins build number to rollback to'
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

        // ============================================================
        // TERRAFORM
        // ============================================================

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

        // ============================================================
        // APPLICATION TEST
        // ============================================================

        stage('Test') {
            when {
                expression {
                    !params.DESTROY_INFRA
                }
            }

            steps {
                sh '''
                    python3 -m compileall frontend services
                '''
            }
        }

        // ============================================================
        // DOCKER BUILD
        // ============================================================

        stage('Build Docker Images') {
            when {
                expression {
                    !params.DESTROY_INFRA &&
                    !params.ROLLBACK_BUILD?.trim()
                }
            }

            steps {
                sh '''
                    docker build \
                        -t girijos/mini-amazon-user-service:${IMAGE_TAG} \
                        ./services/user-service

                    docker build \
                        -t girijos/mini-amazon-product-service:${IMAGE_TAG} \
                        ./services/product-service

                    docker build \
                        -t girijos/mini-amazon-cart-service:${IMAGE_TAG} \
                        ./services/cart-service

                    docker build \
                        -t girijos/mini-amazon-order-service:${IMAGE_TAG} \
                        ./services/order-service

                    docker build \
                        -t girijos/mini-amazon-payment-service:${IMAGE_TAG} \
                        ./services/payment-service

                    docker build \
                        -t girijos/mini-amazon-notification-service:${IMAGE_TAG} \
                        ./services/notification-service

                    docker build \
                        -t girijos/mini-amazon-frontend:${IMAGE_TAG} \
                        ./frontend

                    echo "========================================"
                    echo "Docker Images Built"
                    echo "========================================"

                    echo "girijos/mini-amazon-user-service:${IMAGE_TAG}"
                    echo "girijos/mini-amazon-product-service:${IMAGE_TAG}"
                    echo "girijos/mini-amazon-cart-service:${IMAGE_TAG}"
                    echo "girijos/mini-amazon-order-service:${IMAGE_TAG}"
                    echo "girijos/mini-amazon-payment-service:${IMAGE_TAG}"
                    echo "girijos/mini-amazon-notification-service:${IMAGE_TAG}"
                    echo "girijos/mini-amazon-frontend:${IMAGE_TAG}"

                    echo "========================================"
                '''
            }
        }

        // ============================================================
        // DOCKER PUSH
        // ============================================================

        stage('Push Docker Images') {
            when {
                expression {
                    !params.DESTROY_INFRA &&
                    !params.ROLLBACK_BUILD?.trim()
                }
            }

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

                        docker push \
                            girijos/mini-amazon-user-service:${IMAGE_TAG}

                        docker push \
                            girijos/mini-amazon-product-service:${IMAGE_TAG}

                        docker push \
                            girijos/mini-amazon-cart-service:${IMAGE_TAG}

                        docker push \
                            girijos/mini-amazon-order-service:${IMAGE_TAG}

                        docker push \
                            girijos/mini-amazon-payment-service:${IMAGE_TAG}

                        docker push \
                            girijos/mini-amazon-notification-service:${IMAGE_TAG}

                        docker push \
                            girijos/mini-amazon-frontend:${IMAGE_TAG}

                        docker logout
                    '''
                }
            }
        }

        // ============================================================
        // TRIVY SECURITY SCAN
        // ============================================================

        stage('Trivy Security Scan') {
            when {
                expression {
                    !params.DESTROY_INFRA &&
                    !params.ROLLBACK_BUILD?.trim()
                }
            }

            steps {
                sh '''
                    echo "========================================"
                    echo "Trivy Security Scan"
                    echo "========================================"

                    for image in \
                        girijos/mini-amazon-user-service:${IMAGE_TAG} \
                        girijos/mini-amazon-product-service:${IMAGE_TAG} \
                        girijos/mini-amazon-cart-service:${IMAGE_TAG} \
                        girijos/mini-amazon-order-service:${IMAGE_TAG} \
                        girijos/mini-amazon-payment-service:${IMAGE_TAG} \
                        girijos/mini-amazon-notification-service:${IMAGE_TAG} \
                        girijos/mini-amazon-frontend:${IMAGE_TAG}
                    do
                        echo "========================================"
                        echo "Scanning: $image"
                        echo "========================================"

                        trivy image \
                            --scanners vuln \
                            --severity HIGH,CRITICAL \
                            "$image" || true
                    done

                    echo "========================================"
                    echo "Trivy scan completed"
                    echo "Security findings are currently informational."
                    echo "Pipeline will continue regardless of vulnerabilities."
                    echo "========================================"
                '''
            }
        }

        // ============================================================
        // EKS ACCESS
        // ============================================================

        stage('Configure EKS Access') {
            when {
                expression {
                    !params.DESTROY_INFRA
                }
            }

            steps {
                sh '''
                    aws eks update-kubeconfig \
                        --region ap-south-2 \
                        --name mini-amazon-eks

                    kubectl get nodes
                '''
            }
        }

        // ============================================================
        // HELM VALIDATION
        // ============================================================

        stage('Helm Lint') {
            when {
                expression {
                    !params.DESTROY_INFRA
                }
            }

            steps {
                sh '''
                    helm lint ./helm/mini-amazon
                '''
            }
        }

        // ============================================================
        // HELM DEPLOYMENT
        // ============================================================

        stage('Deploy to EKS') {
            when {
                expression {
                    !params.DESTROY_INFRA
                }
            }

            steps {
                sh '''
                    if [ -n "${ROLLBACK_BUILD}" ]; then
                        DEPLOY_TAG="${ROLLBACK_BUILD}"

                        echo "========================================"
                        echo "ROLLBACK DEPLOYMENT"
                        echo "Deploying build: ${DEPLOY_TAG}"
                        echo "========================================"
                    else
                        DEPLOY_TAG="${IMAGE_TAG}"

                        echo "========================================"
                        echo "NORMAL DEPLOYMENT"
                        echo "Deploying build: ${DEPLOY_TAG}"
                        echo "========================================"
                    fi

                    helm upgrade --install mini-amazon ./helm/mini-amazon \
                        --namespace mini \
                        --create-namespace \
                        --set images.user.tag=${DEPLOY_TAG} \
                        --set images.product.tag=${DEPLOY_TAG} \
                        --set images.cart.tag=${DEPLOY_TAG} \
                        --set images.order.tag=${DEPLOY_TAG} \
                        --set images.payment.tag=${DEPLOY_TAG} \
                        --set images.notification.tag=${DEPLOY_TAG} \
                        --set images.frontend.tag=${DEPLOY_TAG}
                '''
            }
        }

        // ============================================================
        // VERIFY
        // ============================================================

        stage('Verify Deployment') {
            when {
                expression {
                    !params.DESTROY_INFRA
                }
            }

            steps {
                sh '''
                    echo "========================================"
                    echo "Pods"
                    echo "========================================"

                    kubectl get pods -n mini

                    echo "========================================"
                    echo "Services"
                    echo "========================================"

                    kubectl get services -n mini

                    echo "========================================"
                    echo "Ingress"
                    echo "========================================"

                    kubectl get ingress -n mini

                    echo "========================================"
                    echo "Helm Release"
                    echo "========================================"

                    helm list -n mini
                '''
            }
        }

        // ============================================================
        // DESTROY INFRASTRUCTURE
        // ============================================================

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
                        # 2. Remove Helm release
                        # ----------------------------------------

                        echo "Removing Helm release..."

                        helm uninstall mini-amazon \
                            --namespace mini || true

                        # ----------------------------------------
                        # 3. Remove Kubernetes Ingress
                        # ----------------------------------------

                        echo "Removing Kubernetes ingress..."

                        kubectl delete ingress \
                            --all \
                            -n mini \
                            --ignore-not-found=true || true

                        # ----------------------------------------
                        # 4. Remove LoadBalancer Services
                        # ----------------------------------------

                        echo "Removing Kubernetes LoadBalancer services..."

                        kubectl get svc \
                            -n mini \
                            --field-selector spec.type=LoadBalancer \
                            -o name 2>/dev/null | \
                            xargs -r kubectl delete -n mini || true

                        # ----------------------------------------
                        # 5. Wait for AWS Load Balancers
                        # ----------------------------------------

                        echo "Waiting for AWS Load Balancers to disappear..."

                        sleep 60

                        # ----------------------------------------
                        # 6. Delete Kubernetes namespace
                        # ----------------------------------------

                        echo "Deleting Kubernetes namespace..."

                        kubectl delete namespace mini \
                            --ignore-not-found=true || true

                        # ----------------------------------------
                        # 7. Empty versioned S3 bucket
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
                        # 8. Terraform Destroy
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

