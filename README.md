# Smart Parking System

A Django REST API for a smart parking system that allows users to register, authenticate, and manage parking sensors.

## Features

- User registration and authentication with JWT tokens
- User profiles with car information (number and model)
- Parking sensor management
- API documentation with Swagger/ReDoc

## Project Structure

The project is organized into the following main components:

- `src/` - Main source code directory
  - `diploma_smart_parking/` - Project settings and main URL configuration
  - `users/` - User authentication and profile management
  - `sensor/` - Parking sensor management
- `tests/` - End-to-end API tests

## API Endpoints

### Authentication

- `POST /api/auth/register/` - Register a new user
- `POST /api/auth/login/` - Obtain JWT tokens (access and refresh)
- `POST /api/auth/refresh/` - Refresh an expired access token
- `GET /api/auth/me/` - Get current user details

### Sensors

- `GET /api/sensor/` - List all sensors
- `POST /api/sensor/lock/<reference>/` - Lock a parking spot
- `POST /api/sensor/unlock/<reference>/` - Unlock a parking spot

## Setup and Installation

### Prerequisites

- Python 3.11+
- Poetry (for dependency management)
- PostgreSQL

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd diploma_smart_parking
```

2. Install dependencies:
```bash
poetry install
```

3. Set up environment variables (create a `.env` file in the `src/` directory):
```
POSTGRES_DB=diploma_smart_parking
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgrespw
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

4. Run migrations:
```bash
cd src
python manage.py migrate
```

5. Start the development server:
```bash
python manage.py runserver
```

### Docker Setup

Alternatively, you can use Docker:

```bash
docker build -t smart-parking .
docker run -p 8000:8000 smart-parking
```

## Testing

The project includes end-to-end tests for the API endpoints. To run the tests:

```bash
python -m pytest
```

For more information about the tests, see the [tests README](tests/README.md).

## API Documentation

API documentation is available at:

- Swagger UI: `/swagger/`
- ReDoc: `/redoc/`

## Development

### Adding New Features

1. Create a new branch for your feature
2. Implement the feature
3. Write tests for the feature
4. Submit a pull request

### Code Style

This project follows PEP 8 style guidelines.