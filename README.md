# 🌤️ Weather Data API

REST API for weather data management and analysis with temperature and precipitation statistics.

**Author**: Anthony Zakhaur

## 🛠️ Technologies

- **FastAPI** - Web framework
- **PostgreSQL** - Main database
- **Redis** - Cache and task management
- **Celery** - Background task processing
- **Poetry** - Dependency management
- **Docker & Docker Compose** - Containerization

## 🚀 How to run the project

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ and Poetry (for local development)

### Setup steps

```bash
# 1. Clone the repository
git clone <repository-url>
cd weather-data-api

# 2. Copy and configure environment variables
cp .env.example .env
# Edit the .env file with your configurations if needed

# 3. Start the server
make up
```

### 📍 Available URLs

- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **Flower (Celery Monitor)**: http://localhost:5555

## 📋 Available commands

```bash
make help              # Show all available commands
make up                # Start development environment
make down              # Stop services
make test              # Run tests
make migrate           # Run database migrations
make migrate-generate  # Generate new migration
make lint              # Run linters
make format            # Format code
make pre-commit        # Run pre-commit hooks
```

## 🗄️ Database

```bash
# Run migrations
make migrate

# Generate new migration (after model changes)
make migrate-generate
```

## 📥 Import weather data

### Using CLI commands

```bash
# Load historical data for a city
docker compose run --rm api python manage.py load-weather-data "Madrid" \
    --start-date 2025-01-01 \
    --end-date 2025-01-31 \
    --country "Spain"

# List cities in the database
docker compose run --rm api python manage.py list-cities

# Add new city with recent data automatically
docker compose run --rm api python manage.py add-new-city "Barcelona"
```

### Advanced options

```bash
# Load data with specific provider
docker compose run --rm api python manage.py load-weather-data "Valencia" \
    --start-date 2025-06-01 \
    --end-date 2025-06-30 \
    --provider openmeteo

# View command help
docker compose run --rm api python manage.py --help
```

## 🧪 Run tests

```bash
# Run all tests
make test
```

## 🔧 Development

### Linting and formatting

```bash
# Format code
make format

# Run linters
make lint

# Run pre-commit hooks
make pre-commit
```

## 📖 API Usage

### Main endpoints

#### 1. Temperature statistics

```bash
# Get temperature statistics for a city
curl "http://localhost:8000/api/v1/temperature/stats?city=Madrid&start_date=2025-07-01&end_date=2025-07-31"

# With custom thresholds
curl "http://localhost:8000/api/v1/temperature/stats?city=Madrid&start_date=2025-07-01&end_date=2025-07-31&threshold_high=35.0&threshold_low=5.0"
```

#### 2. Precipitation statistics

```bash
# Get precipitation statistics
curl "http://localhost:8000/api/v1/precipitation/stats?city=Madrid&start_date=2025-07-01&end_date=2025-07-31"
```

#### 3. General statistics

```bash
# Get general statistics for all cities
curl "http://localhost:8000/api/v1/statistics/all"
```

#### 4. Health checks

```bash
# Basic health check
curl "http://localhost:8000/api/v1/health"

# Detailed health check
curl "http://localhost:8000/api/v1/health/detailed"
```

### Example response - Temperature statistics

```json
{
  "temperature": {
    "average": 28.5,
    "average_by_day": {
      "2025-07-01": 29.2,
      "2025-07-02": 27.8,
      "2025-07-03": 28.5
    },
    "max": {
      "value": 35.4,
      "date_time": "2025-07-01T15:00"
    },
    "min": {
      "value": 18.2,
      "date_time": "2025-07-03T06:00"
    },
    "hours_above_threshold": 45,
    "hours_below_threshold": 0
  }
}
```

### Example response - Precipitation statistics

```json
{
  "precipitation": {
    "total": 15.6,
    "total_by_day": {
      "2025-07-01": 5.2,
      "2025-07-02": 0.0,
      "2025-07-03": 10.4
    },
    "days_with_precipitation": 2,
    "max": {
      "value": 10.4,
      "date": "2025-07-03"
    },
    "average": 5.2
  }
}
```

## 📄 License

MIT License
