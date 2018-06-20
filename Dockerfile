# Use an official Python runtime as a parent image
FROM python:3.6-slim

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
ADD . /app

# runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
		build-essential \
		libgmp-dev \
	&& rm -rf /var/lib/apt/lists/*

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt
RUN nekoyume init

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variable
ENV PORT 80

# Run app.py when the container launches
CMD ["honcho", "start"]
