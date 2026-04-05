#!/bin/bash
# Migration script to run pending Alembic migrations

set -e

echo "Starting database migrations..."
cd "$(dirname "$0")"

# Run Alembic migrations
alembic upgrade head

echo "Migrations completed successfully!"
