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

        // ============================================================
        // CHECKOUT
        // ============================================================

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        // ============================================================
        // TERRAFORM INIT
        // ============================================================

        stage('Terraform Init') {
            steps {
                dir('terraform') {
                    sh 'terraform init'
                }
            }
        }

        // ============================================================
        // APPLICATION TEST
        // ============================================================

        stage('Test') {
            when {
                expression {
                    !params.DESTROY_INFRA &&
                    !params.ROLLBACK_BUILD?.trim()
                }
            }

            steps {
                sh '''
                    python3 -m compileall frontend services
                '''
            }
        }

        // ============================================================
        // SONARQUBE CODE ANALYSIS
        // ============================================================

        stage('SonarQube Analysis') {
            when {
                expression {
                    !params.DESTROY_INFRA &&
                    !params.ROLLBACK_BUILD?.trim()
                }
            }

            steps {
                script {
                    try {
                        def scannerHome = tool 'SonarScanner'

                        withSonarQubeEnv('SonarQube') {
                            sh "${scannerHome}/bin/sonar-scanner"
                        }

                        echo "========================================"
                        echo "SonarQube analysis completed"
                        echo "Pipeline will continue regardless of SonarQube findings."
                        echo "========================================"

                    } catch (Exception e) {

                        echo "========================================"
                        echo "SonarQube analysis failed"
                        echo "Reason: ${e.getMessage()}"
                        echo "Continuing pipeline without blocking deployment."
                        echo "========================================"
                    }
                }
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
        // UPDATE GITOPS VALUES
        // ============================================================

        stage('Update GitOps Values') {
            when {
                expression {
                    !params.DESTROY_INFRA
                }
            }

            steps {
                script {
                    withCredentials([
                        usernamePassword(
                            credentialsId: 'github-credentials',
                            usernameVariable: 'GIT_USERNAME',
                            passwordVariable: 'GIT_PASSWORD'
                        )
                    ]) {
                        sh '''
                            set -e

                            VALUES_FILE="helm/mini-amazon/values.yaml"

                            if [ -n "${ROLLBACK_BUILD}" ]; then
                                DEPLOY_TAG="${ROLLBACK_BUILD}"

                                echo "========================================"
                                echo "GITOPS ROLLBACK"
                                echo "Updating Git desired state to build: ${DEPLOY_TAG}"
                                echo "========================================"
                            else
                                DEPLOY_TAG="${IMAGE_TAG}"

                                echo "========================================"
                                echo "GITOPS DEPLOYMENT"
                                echo "Updating Git desired state to build: ${DEPLOY_TAG}"
                                echo "========================================"
                            fi

                            python3 - "$VALUES_FILE" "$DEPLOY_TAG" <<'PY'
import sys

values_file = sys.argv[1]
deploy_tag = sys.argv[2]

services = [
    "user",
    "product",
    "cart",
    "order",
    "payment",
    "notification",
    "frontend"
]

with open(values_file, "r") as f:
    lines = f.readlines()

current_service = None
updated = []

for line in lines:

    stripped = line.strip()

    if stripped.endswith(":") and not stripped.startswith("tag:"):
        service_name = stripped[:-1]

        if service_name in services:
            current_service = service_name

    if current_service and stripped.startswith("tag:"):
        indent = line[:len(line) - len(line.lstrip())]

        line = '{}tag: "{}"\n'.format(indent, deploy_tag)

        current_service = None

    updated.append(line)

with open(values_file, "w") as f:
    f.writelines(updated)
PY

                            echo "========================================"
                            echo "Git diff"
                            echo "========================================"

                            git diff -- "$VALUES_FILE"

                            git config user.name "Jenkins"
                            git config user.email "jenkins@local"

                            git add "$VALUES_FILE"

                            if git diff --cached --quiet; then
                                echo "No GitOps changes to commit."
                                exit 0
                            fi

                            git commit \
                                -m "chore: update image tags to ${DEPLOY_TAG} [skip ci]"

                            ORIGIN_URL=$(git remote get-url origin)

                            if echo "$ORIGIN_URL" | grep -q '^git@github.com:'; then
                                REPO_PATH=$(echo "$ORIGIN_URL" \
                                    | sed 's#^git@github.com:##')
                            else
                                REPO_PATH=$(echo "$ORIGIN_URL" \
                                    | sed -E 's#https?://[^/]+/##; s#\\.git$##')
                            fi

                            git push \
                                "https://${GIT_USERNAME}:${GIT_PASSWORD}@github.com/${REPO_PATH}.git" \
                                HEAD:main

                            echo "========================================"
                            echo "GitOps update pushed successfully"
                            echo "Deployment tag: ${DEPLOY_TAG}"
                            echo "========================================"
                        '''
                    }
                }
            }
        }

        // ============================================================
        // TERRAFORM AWS BOOTSTRAP
        // ============================================================

        stage('Terraform AWS Bootstrap') {
            when {
                expression {
                    !params.DESTROY_INFRA
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

        // ============================================================
        // TERRAFORM PLAN
        // ============================================================

        stage('Terraform Plan') {
            when {
                expression {
                    !params.DESTROY_INFRA
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
                    dir('terraform') {
                        sh 'terraform plan'
                    }
                }
            }
        }

        // ============================================================
        // TERRAFORM APPLY
        // ============================================================

        stage('Terraform Apply') {
            when {
                expression {
                    !params.DESTROY_INFRA
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
                    dir('terraform') {
                        sh 'terraform apply -auto-approve'
                    }
                }
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
        // VERIFY
        // ============================================================

// ============================================================
// VERIFY ARGO CD DEPLOYMENT
// ============================================================

stage('Verify Deployment') {
    when {
        expression {
            !params.DESTROY_INFRA
        }
    }

    steps {
        sh '''
            set -e

            echo "========================================"
            echo "Waiting for Argo CD Application"
            echo "========================================"

            for i in $(seq 1 30)
            do
                if kubectl get application mini-amazon \
                    -n argocd >/dev/null 2>&1
                then
                    echo "Argo CD Application found."
                    break
                fi

                echo "Waiting for Argo CD Application..."
                sleep 10
            done

            echo "========================================"
            echo "Argo CD Application"
            echo "========================================"

            kubectl get application mini-amazon -n argocd

            echo "========================================"
            echo "Waiting for Mini Amazon Pods"
            echo "========================================"

            kubectl wait \
                --for=condition=Available \
                deployment \
                --all \
                -n mini \
                --timeout=10m

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

            echo "========================================"
            echo "Deployment verification completed"
            echo "========================================"
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
                        # 2. Remove Argo CD Application
                        # ----------------------------------------

                        echo "Removing Argo CD Application..."

                        kubectl delete application mini-amazon \
                            -n argocd \
                            --ignore-not-found=true || true

                        sleep 30


                        # ----------------------------------------
                        # 3. Remove Helm release
                        # ----------------------------------------

                        echo "Removing Helm release..."

                        helm uninstall mini-amazon \
                            --namespace mini || true


                        # ----------------------------------------
                        # 4. Remove Kubernetes Ingress
                        # ----------------------------------------

                        echo "Removing Kubernetes ingress..."

                        kubectl delete ingress \
                            --all \
                            -n mini \
                            --ignore-not-found=true || true


                        # ----------------------------------------
                        # 5. Remove LoadBalancer Services
                        # ----------------------------------------

                        echo "Removing Kubernetes LoadBalancer services..."

                        kubectl get svc \
                            -n mini \
                            --field-selector spec.type=LoadBalancer \
                            -o name 2>/dev/null | \
                            xargs -r kubectl delete -n mini || true


                        # ----------------------------------------
                        # 6. Wait for AWS Load Balancers
                        # ----------------------------------------

                        echo "Waiting for AWS Load Balancers to disappear..."

                        sleep 60


                        # ----------------------------------------
                        # 7. Delete Kubernetes namespace
                        # ----------------------------------------

                        echo "Deleting Kubernetes namespace..."

                        kubectl delete namespace mini \
                            --ignore-not-found=true || true


                        # ----------------------------------------
                        # 8. Wait for Kubernetes namespace
                        # ----------------------------------------

                        echo "Waiting for Kubernetes namespace to terminate..."

                        for i in $(seq 1 30)
                        do
                            if ! kubectl get namespace mini >/dev/null 2>&1; then
                                echo "Namespace mini has been deleted."
                                break
                            fi

                            echo "Namespace still exists. Waiting..."
                            sleep 10
                        done


                        # ----------------------------------------
                        # 9. Clean up orphaned Kubernetes ENIs
                        # ----------------------------------------

                        echo "========================================"
                        echo "Checking for orphaned Kubernetes ENIs"
                        echo "========================================"

                        ENI_DATA=$(aws ec2 describe-network-interfaces \
                            --region ap-south-2 \
                            --filters \
                                Name=status,Values=available \
                            --query 'NetworkInterfaces[?starts_with(Description, `aws-K8S-`)].[NetworkInterfaceId,Description,RequesterManaged]' \
                            --output text)

                        if [ -n "$ENI_DATA" ]; then

                            echo "$ENI_DATA" | while read -r ENI_ID ENI_DESCRIPTION REQUESTER_MANAGED
                            do

                                echo "----------------------------------------"
                                echo "Checking ENI: $ENI_ID"
                                echo "Description: $ENI_DESCRIPTION"
                                echo "RequesterManaged: $REQUESTER_MANAGED"
                                echo "----------------------------------------"

                                if [ "$REQUESTER_MANAGED" = "False" ]; then

                                    INSTANCE_ID=$(echo "$ENI_DESCRIPTION" | grep -o 'i-[a-zA-Z0-9]*' | head -1)

                                    if [ -n "$INSTANCE_ID" ]; then

                                        INSTANCE_STATE=$(aws ec2 describe-instances \
                                            --instance-ids "$INSTANCE_ID" \
                                            --region ap-south-2 \
                                            --query 'Reservations[0].Instances[0].State.Name' \
                                            --output text 2>/dev/null || echo "not-found")

                                        echo "Associated instance: $INSTANCE_ID"
                                        echo "Instance state: $INSTANCE_STATE"

                                        if [ "$INSTANCE_STATE" = "terminated" ] || [ "$INSTANCE_STATE" = "not-found" ]; then

                                            echo "Deleting orphaned Kubernetes ENI: $ENI_ID"

                                            aws ec2 delete-network-interface \
                                                --network-interface-id "$ENI_ID" \
                                                --region ap-south-2

                                            echo "Deleted ENI: $ENI_ID"

                                        else

                                            echo "Instance is still active. Skipping ENI: $ENI_ID"

                                        fi

                                    else

                                        echo "Could not determine EC2 instance from ENI description."
                                        echo "Skipping ENI: $ENI_ID"

                                    fi

                                else

                                    echo "ENI is requester-managed. Skipping: $ENI_ID"

                                fi

                            done

                        else

                            echo "No orphaned Kubernetes ENIs found."

                        fi


                        # ----------------------------------------
                        # 10. Verify orphaned Kubernetes ENIs
                        # ----------------------------------------

                        echo "========================================"
                        echo "Verifying Kubernetes ENI cleanup"
                        echo "========================================"

                        REMAINING_ENIS=$(aws ec2 describe-network-interfaces \
                            --region ap-south-2 \
                            --filters \
                                Name=status,Values=available \
                            --query 'NetworkInterfaces[?starts_with(Description, `aws-K8S-`)].NetworkInterfaceId' \
                            --output text)

                        if [ -n "$REMAINING_ENIS" ]; then
                            echo "Remaining available Kubernetes ENIs:"
                            echo "$REMAINING_ENIS"
                        else
                            echo "No available Kubernetes ENIs remain."
                        fi


                        # ----------------------------------------
                        # 11. Empty versioned S3 bucket
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
                        # 12. Terraform Destroy
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