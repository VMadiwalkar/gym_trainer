#!/bin/bash

# Kubernetes Deployment Script for Gym Trainer Bot
# Usage: bash deploy.sh

set -e

echo "🚀 Starting Kubernetes deployment for Gym Trainer Bot..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 0: Create namespace
echo -e "${BLUE}Step 0: Creating 'trainer' namespace...${NC}"
kubectl create namespace trainer --dry-run=client -o yaml | kubectl apply -f -
echo -e "${GREEN}✓ Namespace 'trainer' created${NC}"
read -p "Enter your GEMINI_API_KEY (or press Enter to skip): " GEMINI_KEY
if [ ! -z "$GEMINI_KEY" ]; then
    kubectl create secret generic gemini-secret \
        --from-literal=GEMINI_API_KEY="$GEMINI_KEY" \
        -n trainer \
        --dry-run=client -o yaml | kubectl apply -f -
    echo -e "${GREEN}✓ Gemini secret created${NC}"
else
    echo -e "${YELLOW}⚠ Skipping Gemini secret (update k8s-gemini-secret.yaml manually)${NC}"
fi

kubectl apply -f k8s-postgres-secret.yaml
echo -e "${GREEN}✓ PostgreSQL secret created${NC}"

# Step 2: Deploy PostgreSQL
echo -e "${BLUE}Step 2: Deploying PostgreSQL...${NC}"
kubectl apply -f k8s-postgres-configmap.yaml
echo -e "${GREEN}✓ ConfigMap created${NC}"

kubectl apply -f k8s-postgres-pvc.yaml
echo -e "${GREEN}✓ PersistentVolumeClaim created${NC}"

kubectl apply -f k8s-postgres-statefulset.yaml
echo -e "${GREEN}✓ StatefulSet created${NC}"

kubectl apply -f k8s-postgres-service.yaml
echo -e "${GREEN}✓ Services created${NC}"

# Wait for PostgreSQL to be ready
echo -e "${BLUE}Waiting for PostgreSQL to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s -n trainer
echo -e "${GREEN}✓ PostgreSQL is ready${NC}"

# Step 3: Deploy Flask Application
echo -e "${BLUE}Step 3: Deploying Flask Application...${NC}"
kubectl apply -f k8s-flask-deployment.yaml
echo -e "${GREEN}✓ Flask deployment created${NC}"

# Step 4: Verify deployment
echo -e "${BLUE}Step 4: Verifying deployment...${NC}"
echo ""
echo -e "${GREEN}Checking Pod Status:${NC}"
kubectl get pods -n trainer

echo ""
echo -e "${GREEN}Checking Services:${NC}"
kubectl get svc -n trainer

echo ""
echo -e "${GREEN}Checking StatefulSets:${NC}"
kubectl get statefulset -n trainer

# Step 5: Display access information
echo ""
echo -e "${YELLOW}================================${NC}"
echo -e "${YELLOW}Deployment Complete! 🎉${NC}"
echo -e "${YELLOW}================================${NC}"
echo ""
echo -e "${GREEN}Flask Application Access:${NC}"
echo "kubectl port-forward svc/gym-trainer-service 5000:80 -n trainer"
echo "Then visit: http://localhost:5000"
echo ""
echo -e "${GREEN}PostgreSQL Access (from inside cluster):${NC}"
echo "kubectl port-forward svc/postgres-service 5432:5432 -n trainer"
echo "psql -h localhost -U postgres -d gym_trainer_db"
echo ""
echo -e "${GREEN}Monitor Logs:${NC}"
echo "kubectl logs -f deployment/gym-trainer-flask -n trainer"
echo "kubectl logs -f statefulset/postgres -n trainer"
echo ""
