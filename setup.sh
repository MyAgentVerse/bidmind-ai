#!/bin/bash

# BidMind AI Backend Setup Script
# This script sets up the development environment

set -e

echo "🚀 BidMind AI Backend Setup"
echo "================================"

# Check Python version
echo "✓ Checking Python version..."
python_version=$(python --version 2>&1 | cut -d' ' -f2)
echo "  Python $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "✓ Creating virtual environment..."
    python -m venv venv
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "✓ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "✓ Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "✓ Creating .env file from template..."
    cp .env.example .env
    echo "  ⚠️  Please edit .env with your configuration (especially OPENAI_API_KEY and DATABASE_URL)"
else
    echo "✓ .env file already exists"
fi

# Create uploads directory
echo "✓ Creating uploads directory..."
mkdir -p uploads

# Print next steps
echo ""
echo "================================"
echo "✅ Setup Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Configure your .env file:"
echo "   - Set OPENAI_API_KEY"
echo "   - Set DATABASE_URL (PostgreSQL connection string)"
echo "   - Adjust other settings as needed"
echo ""
echo "2. Set up the database:"
echo "   - Ensure PostgreSQL is running"
echo "   - Run: alembic upgrade head"
echo ""
echo "3. Start the development server:"
echo "   - Run: uvicorn app.main:app --reload"
echo "   - Visit: http://localhost:8000/api/docs"
echo ""
echo "For more information, see README.md"
