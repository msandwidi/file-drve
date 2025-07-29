# Use official Python image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

RUN mkdir -p /app/static

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install pipenv
RUN pip install --upgrade pip && pip install pipenv

# Copy Pipenv files
COPY Pipfile Pipfile.lock /app/

# Install Python dependencies
RUN pipenv install --deploy --ignore-pipfile

# Copy the rest of the app
COPY . /app/

# Collect static files (optional, if needed)
RUN pipenv run python manage.py collectstatic --noinput

# Expose port (if you're using Gunicorn or similar)
EXPOSE 8000

# Start the server with gunicorn (change 'myproject.wsgi' to your actual WSGI path)
CMD ["pipenv", "run", "gunicorn", "file_drive.wsgi:application", "--bind", "0.0.0.0:8000"]
