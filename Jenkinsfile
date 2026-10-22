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
                    sh '''
                        set -eu
                        env -u AWS_ACCESS_KEY_ID \
                            -u AWS_SECRET_ACCESS_KEY \
                            -u AWS_SESSION_TOKEN \
                            -u AWS_PROFILE \
                            terraform init
                    '''
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
                    set -e
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

                        echo 'SonarQube analysis completed.'
                    } catch (Exception e) {
                        echo "SonarQube analysis failed: ${e.getMessage()}"
                        echo 'Continuing without blocking deployment.'
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
                    set -e

                    docker build -t girijos/mini-amazon-user-service:${IMAGE_TAG} ./services/user-service
                    docker build -t girijos/mini-amazon-product-service:${IMAGE_TAG} ./services/product-service
                    docker build -t girijos/mini-amazon-cart-service:${IMAGE_TAG} ./services/cart-service
                    docker build -t girijos/mini-amazon-order-service:${IMAGE_TAG} ./services/order-service
                    docker build -t girijos/mini-amazon-payment-service:${IMAGE_TAG} ./services/payment-service
                    docker build -t girijos/mini-amazon-notification-service:${IMAGE_TAG} ./services/notification-service
                    docker build -t girijos/mini-amazon-frontend:${IMAGE_TAG} ./frontend

                    echo "Built Docker images with tag ${IMAGE_TAG}."
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
                        set -eu

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
                    set +e

                    echo "Starting Trivy security scans..."

                    if ! command -v trivy >/dev/null 2>&1; then
                        echo "WARNING: Trivy is not installed. Scan skipped."
                    else
                        for image in \
                            girijos/mini-amazon-user-service:${IMAGE_TAG} \
                            girijos/mini-amazon-product-service:${IMAGE_TAG} \
                            girijos/mini-amazon-cart-service:${IMAGE_TAG} \
                            girijos/mini-amazon-order-service:${IMAGE_TAG} \
                            girijos/mini-amazon-payment-service:${IMAGE_TAG} \
                            girijos/mini-amazon-notification-service:${IMAGE_TAG} \
                            girijos/mini-amazon-frontend:${IMAGE_TAG}
                        do
                            echo "Scanning: $image"
                            trivy image \
                                --scanners vuln \
                                --severity HIGH,CRITICAL \
                                "$image" || true
                        done
                    fi

                    echo "Trivy stage completed."
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
                withCredentials([
                    usernamePassword(
                        credentialsId: 'github-credentials',
                        usernameVariable: 'GIT_USERNAME',
                        passwordVariable: 'GIT_PASSWORD'
                    )
                ]) {
                    sh '''
                        set -eu
ROLLBACK_BUILD="${ROLLBACK_BUILD:-}"
VALUES_FILE=helm/mini-amazon/values.yaml

                        if [ -n "${ROLLBACK_BUILD}" ]; then
                            DEPLOY_TAG="${ROLLBACK_BUILD}"
                            echo "Preparing rollback to image tag ${DEPLOY_TAG}"
                        else
                            DEPLOY_TAG="${IMAGE_TAG}"
                            echo "Preparing deployment of image tag ${DEPLOY_TAG}"
                        fi

                        python3 - "$VALUES_FILE" "$DEPLOY_TAG" <<'PY'
import sys

values_file = sys.argv[1]
deploy_tag = sys.argv[2]

services = {
    "user",
    "product",
    "cart",
    "order",
    "payment",
    "notification",
    "frontend",
}

with open(values_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

current_service = None
updated = []
updated_services = set()

for line in lines:
    stripped = line.strip()

    if stripped.endswith(":") and not stripped.startswith("tag:"):
        name = stripped[:-1]
        if name in services:
            current_service = name

    if current_service and stripped.startswith("tag:"):
        indent = line[:len(line) - len(line.lstrip())]
        line = indent + 'tag: "' + deploy_tag + '"\\n'
        updated_services.add(current_service)
        current_service = None

    updated.append(line)

missing = services - updated_services
if missing:
    sys.exit("ERROR: Could not update tags for: " + ", ".join(sorted(missing)))

with open(values_file, "w", encoding="utf-8") as f:
    f.writelines(updated)

print("Updated image tags to:", deploy_tag)
print("Updated services:", ", ".join(sorted(updated_services)))
PY

                        git diff -- "$VALUES_FILE"
                        git config user.name "Jenkins"
                        git config user.email "jenkins@local"
                        git add "$VALUES_FILE"

                        if git diff --cached --quiet; then
                            echo "No GitOps changes to commit."
                            exit 0
                        fi

                        git commit -m "chore: update image tags to ${DEPLOY_TAG} [skip ci]"

                        # Push through the existing GitHub credential.
                        # Do not print the authenticated URL.
                        git push \
                            "https://${GIT_USERNAME}:${GIT_PASSWORD}@github.com/Giri0135792468/mini-amazon-devops.git" \
                            HEAD:main

                        echo "GitOps values updated successfully."
                        echo "Deployment tag: ${DEPLOY_TAG}"
                    '''
                }
            }
        }

        // ============================================================
        // TERRAFORM AWS DIAGNOSTIC
        // ============================================================

        stage('Terraform AWS Diagnostic') {
            when {
                expression {
                    !params.DESTROY_INFRA
                }
            }
            steps {
                dir('terraform') {
                    sh '''
                        set -eu

                        echo "========================================"
                        echo "AWS identity from Jenkins"
                        echo "========================================"

                        aws sts get-caller-identity

                        echo "========================================"
                        echo "AWS credential source"
                        echo "========================================"

                        aws configure list

                        echo "========================================"
                        echo "AWS environment variable names"
                        echo "========================================"

                        env | cut -d= -f1 | grep '^AWS_' || true

                        echo "========================================"
                        echo "Terraform version and providers"
                        echo "========================================"

                        terraform version
                        terraform providers
                    '''
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
                            set -eu

                            echo "Bootstrapping VPC, EKS and IAM."

                            env -u AWS_ACCESS_KEY_ID \
                                -u AWS_SECRET_ACCESS_KEY \
                                -u AWS_SESSION_TOKEN \
                                -u AWS_PROFILE \
                                terraform apply \
                                -target=module.vpc \
                                -target=module.eks \
                                -target=module.iam \
                                -auto-approve

                            echo "Checking Argo CD Helm release."

                            if helm status argocd -n argocd >/dev/null 2>&1; then
                                echo "Argo CD Helm release already exists."

                                if env -u AWS_ACCESS_KEY_ID \
                                    -u AWS_SECRET_ACCESS_KEY \
                                    -u AWS_SESSION_TOKEN \
                                    -u AWS_PROFILE \
                                    terraform state show helm_release.argocd >/dev/null 2>&1; then

                                    echo "Argo CD is already managed by Terraform."
                                else
                                    echo "Argo CD exists but is missing from Terraform state."
                                    echo "Importing existing Argo CD release."

                                    env -u AWS_ACCESS_KEY_ID \
                                        -u AWS_SECRET_ACCESS_KEY \
                                        -u AWS_SESSION_TOKEN \
                                        -u AWS_PROFILE \
                                        terraform import \
                                        helm_release.argocd \
                                        argocd/argocd

                                    echo "Argo CD import completed."
                                fi
                            else
                                echo "Argo CD release does not exist."
                                echo "Terraform must create it during the full apply."
                            fi
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
                        sh '''
                            set -eu

                            env -u AWS_ACCESS_KEY_ID \
                                -u AWS_SECRET_ACCESS_KEY \
                                -u AWS_SESSION_TOKEN \
                                -u AWS_PROFILE \
                                terraform plan
                        '''
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
                        sh '''
                            set -eu

                            env -u AWS_ACCESS_KEY_ID \
                                -u AWS_SECRET_ACCESS_KEY \
                                -u AWS_SESSION_TOKEN \
                                -u AWS_PROFILE \
                                terraform apply -auto-approve
                        '''
                    }
                }
            }
        }

        // ============================================================
        // CONFIGURE EKS ACCESS
        // ============================================================

        stage('Configure EKS Access') {
            when {
                expression {
                    !params.DESTROY_INFRA
                }
            }
            steps {
                sh '''
                    set -eu

                    aws eks update-kubeconfig \
                        --region ap-south-2 \
                        --name mini-amazon-eks

                    kubectl get nodes
                '''
            }
        }

        // ============================================================
        // CREATE ARGO CD APPLICATION
        // ============================================================

        stage('Create Argo CD Application') {
            when {
                expression {
                    !params.DESTROY_INFRA
                }
            }
            steps {
                sh '''
                    set -eu

                    cat <<'EOF' | kubectl apply -f -
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: mini-amazon
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/Giri0135792468/mini-amazon-devops.git
    targetRevision: main
    path: helm/mini-amazon
    helm:
      valueFiles:
        - values.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: mini
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
EOF

                    kubectl get application mini-amazon -n argocd
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
                sh 'helm lint ./helm/mini-amazon'
            }
        }

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
            set -eu

            echo "Waiting for Argo CD Application to sync."

            SYNC=""
            for i in $(seq 1 60); do
                SYNC=$(kubectl get application mini-amazon \
                    -n argocd \
                    -o jsonpath='{.status.sync.status}' \
                    2>/dev/null || true)

                HEALTH=$(kubectl get application mini-amazon \
                    -n argocd \
                    -o jsonpath='{.status.health.status}' \
                    2>/dev/null || true)

                echo "Attempt $i: Sync=$SYNC, Health=$HEALTH"

                if [ "$SYNC" = "Synced" ]; then
                    break
                fi

                sleep 10
            done

            if [ "$SYNC" != "Synced" ]; then
                echo "ERROR: Argo CD did not reach Synced status."
                kubectl describe application mini-amazon -n argocd
                exit 1
            fi

            echo "Waiting for deployments in namespace mini."

            COUNT=0
            for i in $(seq 1 60); do
                COUNT=$(kubectl get deployments -n mini \
                    -o name 2>/dev/null | wc -l)

                if [ "$COUNT" -gt 0 ]; then
                    break
                fi

                echo "No Deployments found yet. Attempt $i."
                sleep 10
            done

            if [ "$COUNT" -eq 0 ]; then
                echo "ERROR: No Deployments found in namespace mini."
                kubectl get all -n mini
                exit 1
            fi

            echo "Waiting for all Deployments to become available."

            kubectl wait \
                --for=condition=Available \
                deployment \
                --all \
                -n mini \
                --timeout=10m

            echo "Pods:"
            kubectl get pods -n mini

            echo "Services:"
            kubectl get services -n mini

            echo "Ingress:"
            kubectl get ingress -n mini

            echo "Helm releases:"
            helm list -n mini

            echo "Deployment verification completed."
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
                        set -eu

                        echo "Preparing infrastructure for destruction."

                        # Configure EKS access if the cluster still exists.
                        aws eks update-kubeconfig \
                            --region ap-south-2 \
                            --name mini-amazon-eks || true

                        # Remove the Argo CD Application first.
                        kubectl delete application mini-amazon \
                            -n argocd \
                            --ignore-not-found=true || true

                        sleep 30

                        # Remove the Helm release if present.
                        helm uninstall mini-amazon \
                            --namespace mini || true

                        # Remove ingress and LoadBalancer services.
                        kubectl delete ingress \
                            --all \
                            -n mini \
                            --ignore-not-found=true || true

                        kubectl get svc \
                            -n mini \
                            --field-selector spec.type=LoadBalancer \
                            -o name 2>/dev/null |
                            xargs -r kubectl delete -n mini || true

                        echo "Waiting for load balancers to be removed."
                        sleep 60

                        # Remove application namespace.
                        kubectl delete namespace mini \
                            --ignore-not-found=true || true

                        for i in $(seq 1 30); do
                            if ! kubectl get namespace mini >/dev/null 2>&1; then
                                echo "Namespace mini has been deleted."
                                break
                            fi

                            echo "Namespace still exists; waiting."
                            sleep 10
                        done

                        # Inspect available Kubernetes-related ENIs.
                        ENI_DATA=$(aws ec2 describe-network-interfaces \
                            --region ap-south-2 \
                            --filters Name=status,Values=available \
                            --query "NetworkInterfaces[?starts_with(Description, 'aws-K8S-')].[NetworkInterfaceId,Description,RequesterManaged]" \
                            --output text)

                        if [ -n "$ENI_DATA" ]; then
                            printf '%s\\n' "$ENI_DATA" |
                            while read -r ENI_ID ENI_DESCRIPTION REQUESTER_MANAGED; do
                                [ -n "$ENI_ID" ] || continue

                                echo "Checking ENI: $ENI_ID"
                                echo "Description: $ENI_DESCRIPTION"

                                # Do not delete requester-managed ENIs.
                                if [ "$REQUESTER_MANAGED" != "False" ]; then
                                    echo "Skipping requester-managed ENI."
                                    continue
                                fi

                                INSTANCE_ID=$(printf '%s' "$ENI_DESCRIPTION" |
                                    grep -o 'i-[a-zA-Z0-9]*' | head -1 || true)

                                if [ -z "$INSTANCE_ID" ]; then
                                    echo "No instance ID found; skipping ENI."
                                    continue
                                fi

                                INSTANCE_STATE=$(aws ec2 describe-instances \
                                    --instance-ids "$INSTANCE_ID" \
                                    --region ap-south-2 \
                                    --query 'Reservations[0].Instances[0].State.Name' \
                                    --output text 2>/dev/null || echo "not-found")

                                if [ "$INSTANCE_STATE" = "terminated" ] ||
                                   [ "$INSTANCE_STATE" = "not-found" ]; then
                                    echo "Deleting orphaned ENI: $ENI_ID"

                                    aws ec2 delete-network-interface \
                                        --network-interface-id "$ENI_ID" \
                                        --region ap-south-2
                                else
                                    echo "Instance is active; skipping ENI."
                                fi
                            done
                        else
                            echo "No available Kubernetes-related ENIs found."
                        fi

                        # Empty all object versions and delete markers from
                        # the project image bucket before Terraform destroy.
                        BUCKET="mini-amazon-product-images-189761005134-ap2"

                        if aws s3api head-bucket \
                            --bucket "$BUCKET" \
                            --region ap-south-2 2>/dev/null; then

                            while true; do
                                VERSIONS=$(aws s3api list-object-versions \
                                    --bucket "$BUCKET" \
                                    --region ap-south-2 \
                                    --output json)

                                DELETE_JSON=$(printf '%s' "$VERSIONS" |
                                    python3 -c '
import json
import sys

data = json.load(sys.stdin)
objects = []

for item in data.get("Versions", []):
    objects.append({
        "Key": item["Key"],
        "VersionId": item["VersionId"]
    })

for item in data.get("DeleteMarkers", []):
    objects.append({
        "Key": item["Key"],
        "VersionId": item["VersionId"]
    })

print(json.dumps({"Objects": objects, "Quiet": True}))
')

                                COUNT=$(printf '%s' "$DELETE_JSON" |
                                    python3 -c '
import json
import sys
print(len(json.load(sys.stdin).get("Objects", [])))
')

                                if [ "$COUNT" -eq 0 ]; then
                                    break
                                fi

                                echo "Deleting $COUNT S3 object versions/delete markers."

                                printf '%s' "$DELETE_JSON" > /tmp/s3-delete.json

                                aws s3api delete-objects \
                                    --bucket "$BUCKET" \
                                    --region ap-south-2 \
                                    --delete file:///tmp/s3-delete.json
                            done

                            echo "S3 bucket emptied."
                        else
                            echo "S3 bucket does not exist; skipping."
                        fi

                        # Destroy infrastructure only after cleanup.
                        cd terraform

                        env -u AWS_ACCESS_KEY_ID \
                            -u AWS_SECRET_ACCESS_KEY \
                            -u AWS_SESSION_TOKEN \
                            -u AWS_PROFILE \
                            terraform destroy -auto-approve

                        echo "Terraform destroy completed."
                    '''
                }
            }
        }
    }
}



