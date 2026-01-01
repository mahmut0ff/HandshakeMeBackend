# HandshakeMe Backend

A comprehensive Django REST API backend for the HandshakeMe contractor-client platform with advanced features including payments, escrow, real-time chat, content moderation, and modern admin panel.

## 🚀 Features

### Core Features
- **User Authentication & Authorization** - JWT-based auth with role-based permissions
- **Project Management** - Complete CRUD for projects with categories and skills
- **Real-time Chat** - WebSocket-based messaging with file attachments
- **Review System** - Ratings and reviews for contractors and clients
- **Notification System** - Real-time notifications via WebSocket and email
- **Content Moderation** - AI-powered content filtering and manual moderation
- **Modern Admin Panel** - Custom admin interface with analytics and metrics

### Advanced Features
- **Multi-language Support** - English, Russian, Uzbek, Kyrgyz
- **File Upload & Management** - Support for images, videos, and documents
- **Search & Filtering** - Advanced search with location-based filtering
- **Rate Limiting** - API rate limiting for security
- **Comprehensive Testing** - Unit tests with 90%+ coverage
- **CI/CD Pipeline** - GitHub Actions for automated testing and deployment

## 🛠️ Tech Stack

- **Framework**: Django 4.2.7 + Django REST Framework
- **Database**: PostgreSQL 13+
- **Cache**: Redis 6+
- **Task Queue**: Celery with Redis broker
- **WebSockets**: Django Channels
- **File Storage**: Local/AWS S3 (configurable)
- **Documentation**: drf-spectacular (OpenAPI 3.0)

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL 13+
- Redis 6+
- Node.js 18+ (for frontend)

## 🚀 Quick Start

### 1. Clone and Setup Environment

```bash
git clone <repository-url>
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Database Setup

```bash
# Create PostgreSQL database
createdb contractor_connect

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Setup system (optional)
python manage.py setup_system --create-admin --setup-moderation --create-test-data
```

### 4. Start Services

```bash
# Start Redis (in separate terminal)
redis-server

# Start Celery worker (in separate terminal)
celery -A contractor_connect worker -l info

# Start Django development server
python manage.py runserver
```

### 5. Verify Installation

```bash
# Test API endpoints
python test_api.py --base-url http://localhost:8000

# Access admin panel
# http://localhost:8000/admin-panel/

# Access API documentation
# http://localhost:8000/api/docs/
```

## 📚 API Documentation

### Authentication Endpoints
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout
- `POST /api/auth/refresh/` - Refresh JWT token
- `GET /api/auth/profile/` - Get user profile
- `PUT /api/auth/profile/` - Update user profile

### Project Endpoints
- `GET /api/projects/` - List projects
- `POST /api/projects/` - Create project
- `GET /api/projects/{id}/` - Get project details
- `PUT /api/projects/{id}/` - Update project
- `DELETE /api/projects/{id}/` - Delete project
- `POST /api/projects/{id}/apply/` - Apply to project

### Review Endpoints
- `GET /api/reviews/` - List reviews
- `POST /api/reviews/` - Create review
- `GET /api/reviews/{id}/` - Get review details
- `PUT /api/reviews/{id}/` - Update review
- `DELETE /api/reviews/{id}/` - Delete review

### Chat Endpoints
- `GET /api/chat/conversations/` - List conversations
- `POST /api/chat/conversations/` - Create conversation
- `GET /api/chat/messages/` - List messages
- `POST /api/chat/messages/` - Send message

### Admin Panel
- `GET /admin-panel/` - Admin dashboard
- `GET /admin-panel/users/` - User management
- `GET /admin-panel/projects/` - Project management
- `GET /admin-panel/reviews/` - Review management
- `GET /admin-panel/analytics/` - Analytics dashboard

## 🔧 Configuration

### Environment Variables

```bash
# Django Settings
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=contractor_connect
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

## 🧪 Testing

### Run Tests

```bash
# Run all tests
python manage.py test

# Run with coverage
coverage run --source='.' manage.py test
coverage report
coverage html

# Run specific app tests
python manage.py test apps.projects
python manage.py test apps.reviews
python manage.py test apps.moderation
```

### API Testing

```bash
# Test all endpoints
python test_api.py

# Test specific base URL
python test_api.py --base-url https://api.handshakeme.com
```

## 🚀 Deployment

### Production Setup

1. **Environment Configuration**
```bash
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
SECRET_KEY=your-production-secret-key
```

2. **Database Migration**
```bash
python manage.py migrate --settings=contractor_connect.settings.production
```

3. **Static Files**
```bash
python manage.py collectstatic --noinput
```

4. **Process Management**
```bash
# Use gunicorn for Django
gunicorn contractor_connect.wsgi:application

# Use daphne for WebSockets
daphne contractor_connect.asgi:application

# Use supervisor for Celery
celery -A contractor_connect worker -l info
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser
```

## 📊 Monitoring & Analytics

### Admin Panel Features
- **User Analytics** - Registration trends, active users, user types
- **Project Analytics** - Project completion rates, categories, success metrics
- **Review Analytics** - Rating distributions, review trends, quality metrics
- **Content Moderation** - Flagged content, moderation queue, user warnings
- **System Health** - API response times, error rates, database performance

### Logging Configuration

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 🔒 Security Features

- **JWT Authentication** with automatic token refresh
- **Rate Limiting** on all API endpoints
- **Content Moderation** with AI-powered filtering
- **Input Validation** and sanitization
- **CORS Configuration** for frontend integration
- **SQL Injection Protection** via Django ORM
- **XSS Protection** with proper escaping
- **CSRF Protection** for state-changing operations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Write comprehensive tests for new features
- Update documentation for API changes
- Use meaningful commit messages
- Ensure all tests pass before submitting PR

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the [API documentation](http://localhost:8000/api/docs/)
- Review the [admin panel](http://localhost:8000/admin-panel/)

## 🗺️ Roadmap

- [ ] **Advanced Search** - Elasticsearch integration
- [ ] **Mobile API** - Optimized endpoints for mobile apps
- [ ] **Multi-tenancy** - Support for multiple organizations
- [ ] **Advanced Analytics** - Machine learning insights
- [ ] **API Versioning** - Backward compatibility support
- [ ] **Microservices** - Split into smaller services
- [ ] **GraphQL API** - Alternative to REST API
- [ ] **Blockchain Integration** - Smart contracts for payments