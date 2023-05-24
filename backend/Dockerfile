# Use the official Python image
FROM python:3.10
WORKDIR /app

# Install dependencies
COPY requirements.txt /app
RUN pip install -r requirements.txt

# Copy the rest
COPY . /app

# Set environment variables
ENV PYTHONBUFFERED=1
ENV PYTHONEXECUTABLE=python3
# Expose to any IP address
ENV HOST=0.0.0.0
# Expost the port
EXPOSE 5000
ENV PORT=5000
# Don't forget to pass your own MONGO_URI in .env.local (at project's root)
# (this one runs in `mongo` container)
ENV MONGO_URI=mongodb://mongo:27017
ENV PYTHON_ENV=production

# Run the app
CMD ["python3", "-m", "scripts.app"]
