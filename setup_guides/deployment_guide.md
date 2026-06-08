# Deployment Guide

## Option 1: Docker Compose (Recommended)

### Prerequisites
- Docker and Docker Compose installed
- `.env` file configured with all credentials

### Deploy
```bash
# Build and start all services
docker-compose up -d

# Check logs
docker-compose logs -f scanner
docker-compose logs -f dashboard

# Stop
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

### Services
| Service | Port | Description |
|---------|------|-------------|
| postgres | 5432 | PostgreSQL database |
| scanner | — | Main scanning service |
| dashboard | 8501 | Streamlit web dashboard |

Access dashboard: http://localhost:8501

## Option 2: Local Development

### Prerequisites
- Python 3.11+
- PostgreSQL 14+

### Setup
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your credentials

# Create database
psql -U postgres -c "CREATE DATABASE intraday_scanner;"
psql -U postgres -c "CREATE USER scanner WITH PASSWORD 'scanner_password';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE intraday_scanner TO scanner;"

# Run scanner
python main.py

# Run dashboard (separate terminal)
streamlit run dashboard/app.py
```

## Option 3: VPS Deployment

### Recommended VPS
- **DigitalOcean Droplet:** 2 vCPU, 4GB RAM, $24/month
- **AWS EC2:** t3.medium
- **Azure VM:** Standard_B2s

### Setup on Ubuntu VPS
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Clone or upload project
cd /opt
# Upload your project files here

# Configure
cp .env.example .env
nano .env  # Edit credentials

# Deploy
docker compose up -d

# Set up auto-restart on boot
sudo systemctl enable docker

# View logs
docker compose logs -f
```

### Auto-Start on System Boot
The `docker-compose.yml` uses `restart: unless-stopped`, so all services
will automatically restart when the VPS reboots.

## Monitoring

### Check Service Status
```bash
docker-compose ps
```

### View Logs
```bash
# All services
docker-compose logs -f

# Scanner only
docker-compose logs -f scanner

# Last 100 lines
docker-compose logs --tail=100 scanner
```

### Database Access
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U scanner -d intraday_scanner

# Backup database
docker-compose exec postgres pg_dump -U scanner intraday_scanner > backup.sql

# Restore database
docker-compose exec -T postgres psql -U scanner intraday_scanner < backup.sql
```

## Security Notes

1. **Never commit `.env`** to version control
2. Use a firewall to restrict PostgreSQL port (5432) to localhost only
3. If exposing the dashboard publicly, add authentication via Streamlit config
4. Rotate Dhan API tokens regularly
5. Use HTTPS reverse proxy (nginx) for production dashboard access
