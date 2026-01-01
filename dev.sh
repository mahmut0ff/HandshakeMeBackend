#!/bin/bash

# Development script for Contractor Connect Backend

echo "🔧 Starting Contractor Connect Backend Development Environment"

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Virtual environment not activated. Activating..."
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi
fi

# Function to run command in background and track PID
run_bg() {
    echo "🚀 Starting: $1"
    $1 &
    echo $! >> .dev_pids
}

# Clean up function
cleanup() {
    echo ""
    echo "🛑 Shutting down development environment..."
    if [ -f .dev_pids ]; then
        while read pid; do
            if kill -0 $pid 2>/dev/null; then
                kill $pid
                echo "   Stopped process $pid"
            fi
        done < .dev_pids
        rm .dev_pids
    fi
    echo "✅ Development environment stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Create PID tracking file
rm -f .dev_pids

echo "📊 Running migrations..."
python manage.py migrate

echo "📚 Loading initial data..."
python manage.py setup_initial_data

echo ""
echo "🌐 Starting services:"

# Start Django development server
run_bg "python manage.py runserver 0.0.0.0:8000"

# Start Celery worker (if Redis is available)
if command -v redis-cli &> /dev/null && redis-cli ping &> /dev/null; then
    run_bg "celery -A contractor_connect worker --loglevel=info"
    run_bg "celery -A contractor_connect beat --loglevel=info"
    echo "✅ Celery worker and beat started"
else
    echo "⚠️  Redis not available - Celery services not started"
fi

echo ""
echo "🎉 Development environment is ready!"
echo ""
echo "📍 Available endpoints:"
echo "   🌐 API: http://localhost:8000/api/"
echo "   📚 Docs: http://localhost:8000/api/docs/"
echo "   👤 Admin: http://localhost:8000/admin/"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for background processes
wait