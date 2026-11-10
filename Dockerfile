FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

WORKDIR /app

# Create a non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and prompt templates
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser prompts/ ./prompts/

USER appuser

# Healthcheck checking /api/v1/health using Python's built-in urllib
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/v1/health').getcode() == 200 else 1)"

# Expose FastAPI default port
EXPOSE 8000

# Start FastAPI server
CMD ["uvicorn", "alma_lessons.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
