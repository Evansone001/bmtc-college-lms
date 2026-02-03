# Use Python 3.9 slim image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings.production

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/production.txt /app/requirements/production.txt
RUN pip install --upgrade pip \
    && pip install -r requirements/production.txt

# Copy project
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/mediafiles /app/staticfiles

# Collect static files
RUN python manage.py collectstatic --no-input

# Add and run the build script
COPY build.sh /app/build.sh
RUN chmod +x /app/build.sh

# Expose port
EXPOSE 8000

# Run build script and start the application
CMD ["./build.sh", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
