# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the working directory
COPY . .

# Set the entrypoint command to start the application. 
# Adapt this based on how your application is structured. For example,
# if you have a 'main.py' file or use a framework like FastAPI or Flask.

# Example for a simple script (replace with your actual entry point):
CMD ["python", "main.py"]  

# Example using uvicorn for a FastAPI app:
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

# Example using gunicorn for a Flask app:
# CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "main:app", "-b", "0.0.0.0:8080"]

# Expose the port that the application will listen on
EXPOSE 8080
