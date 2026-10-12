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

        stage('Terraform Init') {
            steps {
                dir('terraform') {
                    sh 'terraform init'
                }
            }
        }

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

                        echo "SonarQube analysis completed."
                    } catch (Exception e) {
                        echo "SonarQube analysis failed: ${e.getMessage()}"
                        echo "Continuing without blocking deployment."
                    }
                }
            }
        }

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
                '''
            }
        }

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
                        set -e

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

        stage('Trivy Security Scan') {
            when {
                expression {
                    !params.DESTROY_INFRA &&
                    !params.ROLLBACK_BUILD?.trim()
                }
            }
            steps {
                sh '''
                    echo "Starting Trivy security scans"

                    for image in \
                        girijos/mini-amazon-user-service:${IMAGE_TAG} \
                        girijos/mini-amazon-product-service:${IMAGE_TAG} \
                        girijos/mini-amazon-cart-service:${IMAGE_TAG} \
                        girijos/mini-amazon-order-service:${IMAGE_TAG} \
                        girijos/mini-amazon-payment-service:${IMAGE_TAG} \
                        girijos/mini-amazon-notification-service:${IMAGE_TAG} \
                        girijos/mini-amazon-frontend:${IMAGE_TAG}
                    do
                        echo "Scanning $image"

                        if command -v trivy >/dev/null 2>&1; then
                            trivy image \
                                --scanners vuln \
                                --severity HIGH,CRITICAL \
                                "$image" || true
                        else
                            echo "WARNING: Trivy is not installed."
                            break
                        fi
                    done
                '''
            }
        }

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
                                echo "Rolling back to build ${DEPLOY_TAG}"
                            else
                                DEPLOY_TAG="${IMAGE_TAG}"
                                echo "Deploying build ${DEPLOY_TAG}"
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
        service_name = stripped[:-1]

        if service_name in services:
            current_service = service_name

    if current_service and stripped.startswith("tag:"):
        indent = line[:len(line) - len(line.lstrip())]

        # chr(10) safely adds a newline inside the Jenkins heredoc.
        line = indent + 'tag: "' + deploy_tag + '"' + chr(10)

        updated_services.add(current_service)
        current_service = None

    updated.append(line)

missing = services - updated_services

if missing:
    sys.exit(
        "ERROR: Could not update tag fields for: "
        + ", ".join(sorted(missing))
    )

with open(values_file, "w", encoding="utf-8") as f:
    f.writelines(updated)

print("Updated image tags to:", deploy_tag)
print("Updated services:", ", ".join(sorted(updated_services)))
PY

                            echo "Updated Helm values:"
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

                            # Push securely using Jenkins credentials.
                            ORIGIN_URL=$(git remote get-url origin)

                            REPO_PATH=$(echo "$ORIGIN_URL" |
                                sed -E 's#^https?://[^/]+/##; s#\\.git$##')

                            git push \
                                "https://${GIT_USERNAME}:${GIT_PASSWORD}@github.com/${REPO_PATH}.git" \
                                HEAD:main

                            echo "GitOps values updated successfully."
                            echo "Deployment tag: ${DEPLOY_TAG}"
                        '''
                    }
                }
            }
        }
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
                            set -e

                            echo "Checking AWS identity from Jenkins..."
                            aws sts get-caller-identity

                            echo "Bootstrapping VPC, EKS and IAM"
                            terraform apply \
                                -target=module.vpc \
                                -target=module.eks \
                                -target=module.iam \
                                -auto-approve

                            echo "Checking Argo CD Helm release"

                            if helm status argocd -n argocd >/dev/null 2>&1; then
                                echo "Argo CD Helm release exists."

                                if terraform state show helm_release.argocd >/dev/null 2>&1; then
                                    echo "Argo CD is already managed by Terraform."
                                else
                                    echo "Importing existing Argo CD release."
                                    terraform import helm_release.argocd argocd/argocd
                                fi
                            else
                                echo "Argo CD release does not exist yet."
                                echo "Confirm Terraform configuration installs Argo CD."
                            fi
                        '''
                    }
                }
            }
        }

        stage('Terraform AWS Diagnostic') {
            when {
                expression {
                    !params.DESTROY_INFRA
                }
            }
            steps {
                dir('terraform') {
                    sh '''
                        set -e

                        echo "Checking AWS identity from Jenkins pipeline..."
                        aws sts get-caller-identity

                        echo "Checking Terraform provider configuration..."
                        terraform providers
                    '''
                }
            }
        }

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

        stage('Configure EKS Access') {
            when {
                expression {
                    !params.DESTROY_INFRA
                }
            }
            steps {
                sh '''
                    set -e

                    aws eks update-kubeconfig \
                        --region ap-south-2 \
                        --name mini-amazon-eks

                    kubectl get nodes
                '''
            }
        }

        stage('Create Argo CD Application') {
            when {
                expression {
                    !params.DESTROY_INFRA
                }
            }
            steps {
                sh '''
                    set -e

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

        stage('Verify Deployment') {
            when {
                expression {
                    !params.DESTROY_INFRA
                }
            }
            steps {
                sh '''
                    set -e

                    echo "Waiting for Argo CD Application"

                    for i in $(seq 1 30); do
                        if kubectl get application mini-amazon -n argocd >/dev/null 2>&1; then
                            echo "Argo CD Application found."
                            break
                        fi

                        echo "Waiting for Argo CD Application..."
                        sleep 10
                    done

                    kubectl get application mini-amazon -n argocd

                    echo "Waiting for deployments to become available"
                    kubectl wait \
                        --for=condition=Available \
                        deployment \
                        --all \
                        -n mini \
                        --timeout=10m

                    echo "Pods"
                    kubectl get pods -n mini

                    echo "Services"
                    kubectl get services -n mini

                    echo "Ingress"
                    kubectl get ingress -n mini

                    echo "Helm releases"
                    helm list -n mini
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
                    dir('terraform') {
                        sh '''
                            set -e

                            echo "WARNING: Destroying Mini Amazon infrastructure."
                            echo "Ensure you intentionally selected DESTROY_INFRA."

                            aws sts get-caller-identity

                            aws eks update-kubeconfig \
                                --region ap-south-2 \
                                --name mini-amazon-eks || true

                            echo "Removing Argo CD Application"
                            kubectl delete application mini-amazon \
                                -n argocd \
                                --ignore-not-found=true || true

                            sleep 30

                            echo "Removing Mini Amazon Helm release"
                            helm uninstall mini-amazon \
                                --namespace mini || true

                            echo "Removing ingress resources"
                            kubectl delete ingress \
                                --all \
                                -n mini \
                                --ignore-not-found=true || true

                            echo "Removing LoadBalancer services"
                            kubectl get svc \
                                -n mini \
                                --field-selector spec.type=LoadBalancer \
                                -o name 2>/dev/null |
                                xargs -r kubectl delete -n mini || true

                            echo "Waiting for AWS load balancers to be removed"
                            sleep 60

                            echo "Deleting application namespace"
                            kubectl delete namespace mini \
                                --ignore-not-found=true || true

                            echo "Emptying versioned S3 bucket if it exists"
                            BUCKET="mini-amazon-product-images"

                            if aws s3api head-bucket \
                                --bucket "$BUCKET" \
                                --region ap-south-2 2>/dev/null; then

                                while true; do
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

print(json.dumps({"Objects": objects, "Quiet": True}))
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

                                    echo "$DELETE_JSON" > /tmp/s3-delete.json

                                    aws s3api delete-objects \
                                        --bucket "$BUCKET" \
                                        --region ap-south-2 \
                                        --delete file:///tmp/s3-delete.json
                                done

                                echo "S3 object versions and delete markers removed."
                            else
                                echo "S3 bucket does not exist. Skipping."
                            fi

                            echo "Destroying Terraform infrastructure"
                            terraform destroy -auto-approve

                            echo "Terraform destroy completed."
                        '''
                    }
                }
            }
        }
    }
}