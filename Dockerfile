FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy source code
COPY ./app /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
