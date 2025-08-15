# Use an official Python runtime as a parent image
FROM python:3.10-slim-buster

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for Redis client (if needed for some Redis versions/libraries)
# apt-get update && apt-get install -y --no-install-recommends \
#     libpq-dev \
#     gcc \
#     && rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app runs on
EXPOSE 8000

# Command to run the FastAPI application
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
# To run both, you'd typically use a process manager like supervisord or separate containers.
# For Docker Compose, we'll define services.