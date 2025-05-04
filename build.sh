#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

# Enable debugging
set -x

echo "🚀 Starting BMTC College LMS Deployment Script..."

# Function to handle errors
handle_error() {
    echo "❌ Error occurred on line $1"
    exit 1
}

trap 'handle_error $LINENO' ERR

# Install Python dependencies
echo "📦 Installing dependencies..."
pip install -r requirements/production.txt || {
    echo "❌ Failed to install dependencies"
    exit 1
}

# Create necessary directories
echo "📁 Creating required directories..."
mkdir -p mediafiles || {
    echo "❌ Failed to create mediafiles directory"
    exit 1
}
mkdir -p staticfiles || {
    echo "❌ Failed to create staticfiles directory"
    exit 1
}

# Set proper permissions
echo "🔒 Setting directory permissions..."
chmod -R 755 mediafiles || {
    echo "❌ Failed to set permissions for mediafiles"
    exit 1
}
chmod -R 755 staticfiles || {
    echo "❌ Failed to set permissions for staticfiles"
    exit 1
}

# Collect static files for production
echo "🎨 Collecting static assets..."
python manage.py collectstatic --no-input || {
    echo "❌ Failed to collect static files"
    exit 1
}

# Run database migrations
echo "🔄 Running database migrations..."
python manage.py migrate || {
    echo "❌ Failed to run migrations"
    exit 1
}

# Create superuser with specific credentials
echo "👤 Creating superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
try:
    if not User.objects.filter(username='bmtc-super-admin').exists():
        User.objects.create_superuser(
            username='bmtc-super-admin',
            email='superadmin@bmtc.ac.ke',
            password='ithima-valley@2025'
        )
        print('✅ Superuser created successfully')
    else:
        print('✅ Superuser already exists')
except Exception as e:
    print(f'❌ Error creating superuser: {str(e)}')
    raise
" || {
    echo "❌ Failed to create superuser"
    exit 1
}

# Optional: Reset migrations if needed
if [[ "${RESET_MIGRATIONS:-}" == "true" ]]; then
  echo "🗑️ Deleting old migration files..."
  find . -path "*/migrations/*.py" -not -name "__init__.py" -delete || {
    echo "❌ Failed to delete migration files"
    exit 1
  }
  find . -path "*/migrations/*.pyc" -delete || {
    echo "❌ Failed to delete compiled migration files"
    exit 1
  }
  echo "🔄 Creating fresh migrations..."
  python manage.py makemigrations || {
    echo "❌ Failed to create migrations"
    exit 1
  }
  python manage.py migrate || {
    echo "❌ Failed to apply migrations"
    exit 1
  }
fi

echo "✅ BMTC College LMS deployment completed successfully." 