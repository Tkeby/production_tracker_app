#!/bin/bash

# Production PDF Setup Script
# Run this on your VPS to install all required dependencies

echo "🚀 Setting up PDF generation for production..."

# Update system
sudo apt update

echo "📦 Installing system dependencies for Playwright..."

# Install Chromium dependencies
sudo apt install -y \
    libnss3-dev \
    libatk-bridge2.0-dev \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libgtk-3-0 \
    libxss1 \
    libasound2 \
    fonts-liberation \
    libappindicator3-1 \
    libxss1 \
    libgconf-2-4 \
    xdg-utils \
    wget \
    ca-certificates \
    chromium-browser

echo "🎨 Installing fonts for better PDF rendering..."
sudo apt install -y fonts-dejavu-core fonts-freefont-ttf fonts-noto

echo "📋 Installing WeasyPrint system dependencies..."
sudo apt install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-cffi \
    python3-brotli \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0

echo "✅ System dependencies installed successfully!"

echo "🔧 Now run the following commands in your project directory:"
echo "  source venv/bin/activate"
echo "  pip install -r requirements/base.txt"
echo "  python -m playwright install chromium"
echo "  sudo systemctl restart your-django-app"

echo "🎯 PDF generation should now work in production!"
