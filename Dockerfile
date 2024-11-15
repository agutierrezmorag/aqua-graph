# Use Python 3.11 slim base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy only dependency files first
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copy project files
COPY . .

# Expose port
EXPOSE 80

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application with Chainlit
CMD ["poetry", "run", "chainlit", "run", "src/app.py", "--host", "0.0.0.0", "--port", "80", "-h"]