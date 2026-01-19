# Initialize Project

Set up and start the SuperInsight AI platform locally.

## 1. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

Installs all Python packages including FastAPI, SQLAlchemy, Celery, pytest, and other dependencies.

## 2. Initialize System

```bash
python main.py
```

Initializes the system, creates necessary directories, and sets up the database.

## 3. Install Frontend Dependencies

```bash
cd frontend && npm install
```

Installs React 19, Vite, Ant Design, TanStack Query, and other frontend packages.

## 4. Start Backend Server

```bash
uvicorn src.app:app --reload --port 8000
```

Starts FastAPI server with hot-reload on port 8000. PostgreSQL database connection is configured via .env file.

## 5. Start Frontend Server (new terminal)

```bash
cd frontend && npm run dev
```

Starts Vite dev server on port 5173.

## 6. Validate Setup

Check that everything is working:

```bash
# Test API health
curl -s http://localhost:8000/health

# Check system status
curl -s http://localhost:8000/system/status

# Check Swagger docs load
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8000/docs
```

## Access Points

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **Label Studio**: http://localhost:8080 (if using Docker)

## Docker Setup (Alternative)

For full stack with all services:

```bash
docker-compose up -d
# or
./start-fullstack.sh
```

This starts:
- PostgreSQL
- Redis
- Neo4j
- Label Studio
- SuperInsight API
- Frontend (optional)

## Cleanup

To stop services:
- Backend: Ctrl+C in terminal
- Frontend: Ctrl+C in terminal
- Docker: `docker-compose down`

## Notes

- Environment file (.env) required - copy from .env.example
- Database migrations: `alembic upgrade head`
- Backend must start before frontend for API calls to work
- Check .kiro/steering/tech.md for detailed setup instructions
