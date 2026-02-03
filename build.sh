#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

echo "Starting BMTC College LMS 2026 Deployment Script..."

# Install Python dependencies
echo " Installing dependencies..."
pip install -r requirements/production.txt

# Create necessary directories
echo " Creating required directories..."
mkdir -p mediafiles
mkdir -p staticfiles

# Set proper permissions
echo " Setting directory permissions..."
chmod -R 755 mediafiles
chmod -R 755 staticfiles

# Collect static files for production
echo " Collecting static assets..."
python manage.py collectstatic --no-input

# Run database migrations
echo "Running database migrations..."
python manage.py migrate

# Create superuser with specific credentials
echo "Creating superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(username='bmtc-super-admin').exists():
    User.objects.create_superuser(
        username='bmtc-super-admin',
        email='superadmin@bmtc.ac.ke',
        password='ithima-valley@2025'
    )
    print('Superuser created successfully')
else:
    print('Superuser already exists')
"

# Optional: Reset migrations if needed
if [[ "${RESET_MIGRATIONS:-}" == "true" ]]; then
  echo " Deleting old migration files..."
  find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
  find . -path "*/migrations/*.pyc" -delete
  echo " Creating fresh migrations..."
  python manage.py makemigrations
  python manage.py migrate
fi

echo "BMTC College LMS deployment completed successfully." 