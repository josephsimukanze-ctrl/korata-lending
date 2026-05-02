#!/bin/bash
# build.sh - Render build script for Korata Lending System

# Exit on error
set -o errexit

echo "🚀 Starting build process..."

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Run migrations
echo "🗄️ Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "🎨 Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser if needed (optional)
echo "👤 Creating superuser (if not exists)..."
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'Admin123!')" | python manage.py shell || true

echo "✅ Build completed successfully!"
