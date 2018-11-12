# Use an official Python runtime as a parent image
FROM python:3.6-slim

# runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
		build-essential \
		libgmp-dev \
        pkg-config \
        dh-autoreconf \
        wget \
	&& rm -rf /var/lib/apt/lists/*
RUN wget https://github.com/eficode/wait-for/raw/master/wait-for
RUN chmod +x wait-for
RUN mv wait-for /usr/bin/

# Set the working directory to /app
WORKDIR /app

# Cache dependencies if possible
COPY setup.py /app
COPY setup.cfg /app
RUN python -c 'from setup import *; print_install_requires()' \
        > /tmp/requirements.txt && \
    pip install -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variable
ARG _COMMIT_HASH
ENV PORT 8080
ENV _COMMIT_HASH ${_COMMIT_HASH}

# Run app.py when the container launches
ENTRYPOINT ["bash", "-c"]
CMD ["nekoyume init && honcho start"]
