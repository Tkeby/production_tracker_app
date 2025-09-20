# Django VPS Deployment Guide

This guide provides step-by-step instructions for deploying the Production Tracker application to a VPS using SQLite with WAL mode for optimal performance.

## Overview

- **Database**: SQLite with WAL (Write-Ahead Logging) mode
- **Web Server**: Nginx (reverse proxy)
- **App Server**: Gunicorn
- **Process Manager**: systemd
- **SSL**: Let's Encrypt (Certbot)

## Prerequisites

- VPS with Ubuntu 20.04+ or similar Linux distribution
- Domain name pointing to your VPS IP (optional but recommended)
- SSH access to your VPS

## Phase 1: VPS Setup & Server Preparation

### 1.1 Initial Server Setup

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv nginx supervisor sqlite3 git curl wget

# Create a dedicated deploy user
sudo adduser deploy
sudo usermod -aG sudo deploy

# Switch to deploy user for the rest of the setup
su - deploy
```

### 1.2 Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### 1.3 Node.js Installation

```bash
# Install Node.js for Tailwind CSS compilation
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify installation
node --version
npm --version
```

## Phase 2: Application Deployment

### 2.1 Project Setup

```bash
# Clone your repository (replace with your actual repo URL)
git clone <your-repo-url> /home/deploy/production_tracker
cd /home/deploy/production_tracker

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install production dependencies
pip install -r requirements/base.txt
pip install gunicorn psutil
```

### 2.2 Environment Configuration

Create `/home/deploy/production_tracker/.env`:

```bash
DJANGO_SETTINGS_MODULE=core.settings_prod
DJANGO_SECRET_KEY=your-super-secret-production-key-here

ADMIN_URL=your-secure-admin-url-here/

RESEND_API_KEY=your-super-secret-resend-api-key
DEFAULT_FROM_EMAIL=email@yourdomain.com
```

**Important**: Generate a new secret key for production:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 2.3 Production Settings

The project already includes `core/settings_prod.py` with:
- SQLite WAL mode configuration
- Production security settings
- Static/media file configuration
- Comprehensive logging

Update the `ALLOWED_HOSTS` in `core/settings_prod.py`:
```python
ALLOWED_HOSTS = ['your-domain.com', 'your-server-ip', 'localhost']
```

### 2.4 Database & Static Files Setup

```bash
# Set environment variable
export DJANGO_SETTINGS_MODULE=core.settings_prod

# Run database migrations
python manage.py migrate

# Create superuser account
python manage.py createsuperuser

# Build Tailwind CSS
cd theme/static_src
npm install
npm run build
cd ../..

# Collect static files
python manage.py collectstatic --noinput

# Set proper database permissions
chmod 664 db.sqlite3
chmod 755 /home/deploy/production_tracker
```

### 2.5 Verify WAL Mode

```bash
# Verify SQLite is using WAL mode
sqlite3 db.sqlite3 "PRAGMA journal_mode;"
# Should return: wal

sqlite3 db.sqlite3 "PRAGMA wal_autocheckpoint;"
# Should return: 1000
```

## Phase 3: Gunicorn Configuration

The project includes `gunicorn_config.py` with optimal settings. Update the paths if needed:

```python
# In gunicorn_config.py, ensure paths are correct:
accesslog = "/home/deploy/production_tracker/gunicorn_access.log"
errorlog = "/home/deploy/production_tracker/gunicorn_error.log"
```

Test Gunicorn locally:
```bash
cd /home/deploy/production_tracker
source venv/bin/activate
gunicorn --config gunicorn_config.py core.wsgi:application
```

## Phase 4: Systemd Service Configuration

Create `/etc/systemd/system/production_tracker.service`:

```ini
[Unit]
Description=Django Starter Gunicorn daemon
After=network.target

[Service]
User=deploy
Group=deploy
WorkingDirectory=/home/deploy/production_tracker
Environment="DJANGO_SETTINGS_MODULE=core.settings_prod"
Environment="DJANGO_SECRET_KEY=your-secret-key-here"
ExecStart=/home/deploy/production_tracker/venv/bin/gunicorn \
    --config /home/deploy/production_tracker/gunicorn_config.py \
    core.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable production_tracker
sudo systemctl start production_tracker

# Check service status
sudo systemctl status production_tracker
```

## Phase 5: Nginx Configuration

Create `/etc/nginx/sites-available/production_tracker`:

```nginx
upstream production_tracker {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com www.your-domain.com your-server-ip;
    
    client_max_body_size 100M;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    # Static files
    location /static/ {
        alias /home/deploy/production_tracker/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable, no-transform";
        add_header Vary "Accept-Encoding";
        
        # Gzip compression
        gzip on;
        gzip_types text/css application/javascript text/javascript application/json;
    }
    
    # Media files
    location /media/ {
        alias /home/deploy/production_tracker/media/;
        expires 30d;
        add_header Cache-Control "public, immutable, no-transform";
    }
    
    # Main application
    location / {
        proxy_pass http://production_tracker;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_buffering off;
        
        # Timeouts
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
    
    # Health check endpoint
    location /health/ {
        access_log off;
        proxy_pass http://production_tracker;
        proxy_set_header Host $http_host;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/production_tracker /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

### 5.1 Optional - block admin url requests by ip
```bash 
# In /etc/nginx/sites-available/production_tracker
location /your-custom-secure-admin-url/ {
    allow 203.0.113.1;  # Replace with your IP address
    allow 192.168.1.0/24;  # Example Your office network
    deny all;
    
    proxy_pass http://production_tracker;
    proxy_set_header Host $http_host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```


## Phase 6: SSL/HTTPS Setup

### 6.1 Install Certbot

```bash
sudo apt install certbot python3-certbot-nginx
```

### 6.2 Obtain SSL Certificate

```bash
# Replace with your actual domain
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

### 6.3 Auto-renewal

Certbot automatically sets up auto-renewal. Test it:
```bash
sudo certbot renew --dry-run
```

## Phase 7: Backup Strategy

### 7.1 Database Backup Script

Create `/home/deploy/scripts/backup_db.sh`:
```bash
sudo mkdir -p /home/deploy/scripts
```
```bash
#!/bin/bash
DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/home/deploy/backups"
PROJECT_DIR="/home/deploy/production_tracker"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup SQLite database with WAL mode compatibility
cd $PROJECT_DIR
sqlite3 db.sqlite3 "PRAGMA wal_checkpoint(FULL); .backup $BACKUP_DIR/db_$DATE.sqlite3"

# Compress the backup
gzip $BACKUP_DIR/db_$DATE.sqlite3

# Keep only last 30 days of backups
find $BACKUP_DIR -name "db_*.sqlite3.gz" -mtime +30 -delete

# Log the backup
echo "$(date): Database backup completed - db_$DATE.sqlite3.gz" >> $BACKUP_DIR/backup.log
```

Make it executable:
```bash
chmod +x /home/deploy/scripts/backup_db.sh
```

### 7.2 Automated Backups

Add to crontab:
```bash
crontab -e

# Add daily backup at 2 AM
0 2 * * * /home/deploy/scripts/backup_db.sh
```

## Phase 8: Monitoring & Logging

### 8.1 Log Rotation

Create `/etc/logrotate.d/production_tracker`:

```
/home/deploy/production_tracker/django.log
/home/deploy/production_tracker/gunicorn_*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 644 deploy deploy
    postrotate
        systemctl reload production_tracker
    endscript
}
```

### 8.2 Health Monitoring Script

Create `/home/deploy/scripts/health_check.sh`:

```bash
#!/bin/bash
LOGFILE="/home/deploy/logs/health_check.log"
mkdir -p /home/deploy/logs

# Check if application responds
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost)

if [ $response != "200" ]; then
    echo "$(date): Application health check failed! Response code: $response" >> $LOGFILE
    # Restart the service
    sudo systemctl restart production_tracker
    echo "$(date): production_tracker service restarted" >> $LOGFILE
else
    echo "$(date): Application health check passed" >> $LOGFILE
fi

# Check disk space (warn if usage > 80%)
disk_usage=$(df -h /home/deploy/ | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $disk_usage -gt 80 ]; then
    echo "$(date): WARNING: Disk usage is ${disk_usage}%" >> $LOGFILE
fi
```

Make it executable:
```bash
chmod +x /home/deploy/scripts/health_check.sh
```

Add to crontab for every 5 minutes:
```bash
*/5 * * * * /home/deploy/scripts/health_check.sh
```

## Phase 9: Deployment Automation

### 9.1 Deployment Script

Create `/home/deploy/scripts/deploy.sh`:

```bash
#!/bin/bash
PROJECT_DIR="/home/deploy/production_tracker"
VENV_DIR="$PROJECT_DIR/venv"

echo "Starting deployment..."

cd $PROJECT_DIR

# Pull latest changes
git pull origin main

# Activate virtual environment
source $VENV_DIR/bin/activate

# Install/update dependencies
pip install -r requirements/base.txt

# Build Tailwind CSS
echo "Building Tailwind CSS..."
cd theme/static_src
npm install
npm run build
cd ../..

# Run migrations
export DJANGO_SETTINGS_MODULE=core.settings_prod
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput --clear

# Restart services
sudo systemctl restart production_tracker
sudo systemctl reload nginx

# Check if deployment was successful
sleep 5
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost)
if [ $response = "200" ]; then
    echo "Deployment successful! Application is responding."
else
    echo "Deployment may have issues. Response code: $response"
    exit 1
fi

echo "Deployment completed successfully!"
```

Make it executable:
```bash
chmod +x /home/deploy/scripts/deploy.sh
```

## Phase 10: Security Hardening

### 10.1 Additional Security Measures

```bash
# Disable password authentication (use SSH keys only)
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
sudo systemctl restart ssh

# Install fail2ban
sudo apt install fail2ban

# Configure basic fail2ban for SSH and Nginx
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 10.2 Database Security

```bash
# Set restrictive permissions on database
chmod 640 /home/deploy/production_tracker/db.sqlite3
chown deploy:deploy /home/deploy/production_tracker/db.sqlite3
```

## Common Operations

### Service Management

```bash
# Check service status
sudo systemctl status production_tracker
sudo systemctl status nginx

# View logs
sudo journalctl -u production_tracker -f
tail -f /home/deploy/production_tracker/gunicorn_error.log
tail -f /home/deploy/production_tracker/gunicorn_access.log
tail -f /home/deploy/production_tracker/django.log

# Restart services
sudo systemctl daemon-reload
sudo systemctl restart production_tracker
sudo systemctl restart nginx

curl -I http://localhost
```

### Database Operations

```bash
# Check WAL mode
sqlite3 /home/deploy/production_tracker/db.sqlite3 "PRAGMA journal_mode;"

# Manual checkpoint (force WAL to database)
sqlite3 /home/deploy/production_tracker/db.sqlite3 "PRAGMA wal_checkpoint(FULL);"

# Database size information
sqlite3 /home/deploy/production_tracker/db.sqlite3 ".dbinfo"
```

### Troubleshooting

```bash
# Check if Gunicorn is running
ps aux | grep gunicorn

# Check port availability
sudo netstat -tlnp | grep :8000

# Test Gunicorn directly
cd /home/deploy/production_tracker
source venv/bin/activate
gunicorn --bind 0.0.0.0:8000 core.wsgi:application

# Check Nginx configuration
sudo nginx -t

# Check disk space
df -h

# Check memory usage
free -h
```

## Performance Optimization

### SQLite Optimizations (Already Configured)

The `settings_prod.py` already includes optimal SQLite settings:
- WAL mode for better concurrency
- Increased cache size
- Memory temp store
- Optimized timeout settings

### Additional Nginx Optimizations

Add to the Nginx server block:
```nginx
# Enable gzip compression
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

# Set client timeouts
client_body_timeout 12;
client_header_timeout 12;
 devkeepalive_timeout 15;
send_timeout 10;
```

## Deployment Checklist

- [ ] VPS set up with proper user and firewall
- [ ] Node.js and npm installed for Tailwind CSS compilation
- [ ] Project cloned and dependencies installed
- [ ] Environment variables configured
- [ ] Tailwind CSS built and compiled
- [ ] Database migrated and WAL mode verified
- [ ] Static files collected
- [ ] Gunicorn service running
- [ ] Nginx configured and running
- [ ] SSL certificate installed
- [ ] Backup system configured
- [ ] Monitoring scripts set up
- [ ] Health checks working
- [ ] Security hardening applied

## Support & Maintenance

### Regular Maintenance Tasks

1. **Weekly**: Check logs for errors, monitor disk space
2. **Monthly**: Update system packages, review backup integrity
3. **Quarterly**: Review security settings, update dependencies

### Emergency Procedures

If the site goes down:
1. Check service status: `sudo systemctl status production_tracker nginx`
2. Check logs: `sudo journalctl -u production_tracker -n 50`
3. Restart services: `sudo systemctl restart production_tracker nginx`
4. Check database integrity if issues persist

For urgent support, maintain access to:
- Server SSH keys
- Database backups
- DNS configuration
- SSL certificate renewal logs

---

**Note**: Always test deployment procedures in a staging environment before applying to production. Keep your secret keys secure and never commit them to version control.
