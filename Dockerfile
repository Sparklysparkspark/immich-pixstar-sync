# Immich → Pix-Star Favorites Sync
# Runtime image: Python 3.11 on slim Debian
FROM python:3.11-slim

# Work in /app
WORKDIR /app

# Install OS basics (kept minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code into image
COPY . .

# Ensure entrypoint is executable
RUN chmod +x docker-entrypoint.sh

# Unbuffered logs for nicer 'docker logs'
ENV PYTHONUNBUFFERED=1

# First run our entrypoint (handles config), then run the app
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "main.py"]
