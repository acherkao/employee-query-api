# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# --no-cache-dir makes the image smaller
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container at /app
COPY . .

# Make port 8000 available to the world outside this container
# Code Engine will map this to the public port 443 (HTTPS)
EXPOSE 8000

# Define environment variables needed by the app
# You will set the actual secret values in the Code Engine UI, not here.
ENV SUPABASE_URL ""
ENV SUPABASE_KEY ""
ENV OPENAI_API_KEY ""
ENV MY_API_KEY ""

# Run uvicorn server when the container launches
# The host 0.0.0.0 is crucial for it to be accessible from outside the container.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
