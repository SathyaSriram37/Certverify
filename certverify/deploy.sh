#!/bin/bash
set -e

echo "Deploying CertVerify AI to Production..."

# Pull latest code
if [ -d ".git" ]; then
    git pull origin main
fi

# Build containers
docker-compose -f docker-compose.prod.yml build

# Run Alembic migrations against Supabase / PostgreSQL
docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# Start all services
docker-compose -f docker-compose.prod.yml up -d

echo "Waiting for services to become healthy..."
sleep 10

# Verify health endpoint
if curl -f http://localhost/health; then
    echo -e "\n✓ Deployment successful! CertVerify AI is online."
else
    echo -e "\n✗ Health check failed! Inspecting logs..."
    docker-compose -f docker-compose.prod.yml logs --tail 50 backend
    exit 1
fi

