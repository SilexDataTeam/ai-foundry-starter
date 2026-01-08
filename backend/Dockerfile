FROM registry.access.redhat.com/ubi9/ubi:9.7 AS base

# Install python and pip
RUN yum install -y python3.11 python3.11-pip libpq \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/pip pip /usr/bin/pip3.11 1 \
    && update-alternatives --set python /usr/bin/python3.11 \
    && update-alternatives --set pip /usr/bin/pip3.11 \
    && yum clean all \
    && rm -rf /var/cache/yum \
    && pip install wheel

# Install dependencies
COPY requirements.txt /workspace/backend/
RUN pip install --no-cache-dir -r /workspace/backend/requirements.txt

# Copy the api server code
COPY . /workspace/backend/

# Expose the port
EXPOSE 8080

# Entrypoint
WORKDIR /workspace
ENTRYPOINT ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080", "--log-config", "backend/log-config.yaml" ]
