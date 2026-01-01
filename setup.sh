#!/bin/bash

# Contractor Connect Backend Setup Script

echo "🚀 Setting up Contractor Connect Backend..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Copy environment file
echo "⚙️ Setting up environment variables..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env file from .env.example"
    echo "⚠️  Please update the .env file with your actual values"
else
    echo "✅ .env file already exists"
fi

# Create logs directory
echo "📁 Creating logs directory..."
mkdir -p logs

# Create media directory
echo "📁 Creating media directory..."
mkdir -p media/avatars
mkdir -p media/portfolio
mkdir -p media/certifications
mkdir -p media/projects
mkdir -p media/project_documents
mkdir -p media/chat_files
mkdir -p media/chat_images
mkdir -p media/review_images

echo "✅ Backend setup completed!"
echo ""
echo "Next steps:"
echo "1. Update the .env file with your database and Redis credentials"
echo "2. Start PostgreSQL and Redis services"
echo "3. Run: python manage.py migrate"
echo "4. Run: python manage.py createsuperuser"
echo "5. Run: python manage.py runserver"
echo ""
echo "For Docker setup:"
echo "1. Run: docker-compose up --build"