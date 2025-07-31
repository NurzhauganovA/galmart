# README.md
# Galmart - Advanced Reservation System

![Django](https://img.shields.io/badge/Django-4.2-green)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)
![Redis](https://img.shields.io/badge/Redis-7-red)
![Docker](https://img.shields.io/badge/Docker-ready-blue)

A professional-grade Django-based reservation system with microservices architecture, featuring real-time analytics, event-driven processing, and comprehensive monitoring.

## 🚀 Features

- **Advanced Reservation System** with time-based expiration
- **Dual Database Architecture** (Main + Analytics)
- **Event-Driven Architecture** with Kafka
- **Asynchronous Processing** with Celery
- **Real-time Monitoring** with Prometheus & Grafana
- **Comprehensive Testing** (Unit, Integration, Performance)
- **Production-Ready** Docker configuration
- **API Documentation** with OpenAPI/Swagger

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │────│  Django API     │────│  PostgreSQL     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │
                       ┌───────┴───────┐
                       │               │
               ┌───────▼────┐  ┌───────▼────┐
               │   Redis    │  │   Kafka    │
               │  (Cache)   │  │ (Events)   │
               └────────────┘  └────────────┘
                       │
               ┌───────▼────┐
               │   Celery   │
               │ (Workers)  │
               └────────────┘
```

## 🛠️ Tech Stack

- **Backend**: Django 4.2, Django REST Framework
- **Databases**: PostgreSQL (Main + Analytics)
- **Cache**: Redis
- **Message Broker**: Apache Kafka
- **Task Queue**: Celery
- **Monitoring**: Prometheus, Grafana, Jaeger
- **Containerization**: Docker, Docker Compose
- **Web Server**: Nginx (Production)

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- Make (optional, for convenience commands)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/NurzhauganovA/galmart.git
   cd galmart
   ```

2. **Setup environment**
   ```bash
   cp docker/envs/.env.example .env
   # Edit .env with your configuration
   ```

3. **Quick start with Make**
   ```bash
   make init  # Build, start, migrate, and load data
   ```

   Or manual setup:
   ```bash
   docker-compose build
   docker-compose up -d
   docker-compose exec web python manage.py migrate
   docker-compose exec web python manage.py migrate --database=analytics
   docker-compose exec web python manage.py loaddata fixtures/test_data.json
   ```

4. **Access the application**
   - API: http://localhost/api/
   - Admin: http://localhost/admin/
   - API Docs: http://localhost/api/schema/swagger-ui/
   - Grafana: http://localhost:3000 (admin/admin123)
   - Prometheus: http://localhost:9090

## 📚 API Documentation

The API is fully documented with OpenAPI/Swagger. Visit `/api/schema/swagger-ui/` for interactive documentation.

### Key Endpoints

- `POST /api/reservations/` - Create reservation
- `POST /api/reservations/{id}/confirm/` - Confirm reservation
- `POST /api/reservations/{id}/cancel/` - Cancel reservation
- `GET /api/products/` - List products
- `GET /api/products/search/` - Search products
- `GET /api/analytics/dashboard/` - Analytics dashboard

## 🧪 Testing

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test types
make test-unit
make test-integration

# Performance testing
make test-performance
```

## 🔧 Development

### Setup Development Environment

```bash
# Setup local development
make dev-setup

# Run in development mode
make dev-run

# Code quality checks
make lint
make format
```

### Available Commands

```bash
make help  # Show all available commands
```

Key commands:
- `make up` - Start all services
- `make down` - Stop all services
- `make logs` - View logs
- `make shell` - Django shell
- `make migrate` - Run migrations
- `make test` - Run tests

## 📊 Monitoring

### Grafana Dashboards
- Application metrics
- Database performance
- Celery task monitoring
- Business metrics (reservations, revenue)

### Prometheus Metrics
- HTTP request metrics
- Database connection pools
- Cache hit rates
- Custom business metrics

### Health Checks
- `/health/` - Basic health check
- `/api/status/` - Detailed system status

## 🔐 Security

- JWT authentication
- Rate limiting
- CORS configuration
- SQL injection protection
- XSS protection
- Security headers

## 📈 Performance

### Optimization Features
- Database query optimization
- Redis caching
- Connection pooling
- Async task processing
- Database indexing
- Static file optimization

### Scaling
- Horizontal scaling support
- Load balancer ready
- Database sharding ready
- Microservices architecture

## 🐳 Deployment

### Production Deployment

```bash
# Deploy to production
make deploy

# Or with staging
make deploy-staging
```