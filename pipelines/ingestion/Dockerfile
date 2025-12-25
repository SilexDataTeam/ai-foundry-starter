FROM registry.access.redhat.com/ubi9/ubi:9.7 AS base

# Install python, pip, and libpq
RUN yum install -y python3.11 python3.11-pip libpq \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/pip pip /usr/bin/pip3.11 1 \
    && update-alternatives --set python /usr/bin/python3.11 \
    && update-alternatives --set pip /usr/bin/pip3.11 \
    && yum clean all \
    && rm -rf /var/cache/yum \
    && pip install wheel

# Install dependencies
COPY requirements.txt /ingestion/
RUN pip install --no-cache-dir -r /ingestion/requirements.txt

# Copy the the ingestion code
COPY . /ingestion/

# Entrypoint
WORKDIR /ingestion/