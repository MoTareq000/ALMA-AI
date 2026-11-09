FROM python:3.10-slim

WORKDIR /app

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and prompt templates
COPY src/ ./src/
COPY prompts/ ./prompts/

# Expose FastAPI default port
EXPOSE 8000

# Start FastAPI server
CMD ["uvicorn", "alma_lessons.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]

