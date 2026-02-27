#!/bin/bash
# Script to recreate the database schema

echo "Stopping any running uvicorn processes..."
pkill -f "uvicorn app.main:app"

echo "Dropping and recreating database..."
docker exec -it law-rag-postgres psql -U lawrag -d postgres -c "DROP DATABASE IF EXISTS law_rag_dev;"
docker exec -it law-rag-postgres psql -U lawrag -d postgres -c "CREATE DATABASE law_rag_dev;"

echo "Database recreated. You can now restart uvicorn."
echo "Run: uvicorn app.main:app --reload"
