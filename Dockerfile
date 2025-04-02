FROM python:3.9-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port for API
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Define volume for persistent data
VOLUME ["/app/data"]

# Run the application
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8000", "--db", "/app/data/universal_api.db", "--instance-file", "/app/data/api_instances.json"] 