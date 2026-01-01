#!/bin/bash

# Contractor Connect Backend Quick Start Script

echo "🚀 Quick Start - Contractor Connect Backend"
echo "==========================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup.sh first."
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please copy .env.example to .env and configure it."
    exit 1
fi

# Run migrations
echo "📊 Running database migrations..."
python manage.py migrate

# Load initial data
echo "📚 Loading initial data..."
python manage.py setup_initial_data

# Create superuser if it doesn't exist
echo "👤 Checking for superuser..."
python manage.py shell -c "
from apps.accounts.models import User
if not User.objects.filter(is_superuser=True).exists():
    print('No superuser found. Please create one:')
    exit(1)
else:
    print('✅ Superuser already exists')
" 2>/dev/null || {
    echo "Creating superuser..."
    python manage.py createsuperuser
}

echo ""
echo "✅ Quick start completed!"
echo ""
echo "🌐 Available endpoints:"
echo "   API Documentation: http://localhost:8000/api/docs/"
echo "   Admin Panel: http://localhost:8000/admin/"
echo "   API Root: http://localhost:8000/api/"
echo ""
echo "🚀 Starting development server..."
echo "   Press Ctrl+C to stop the server"
echo ""

# Start the development server
python manage.py runserver