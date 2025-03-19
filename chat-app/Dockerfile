FROM registry.access.redhat.com/ubi9/nodejs-22:9.5-1741891114 AS base

# Copy the api server code with owner and permissions
COPY --chown=1001:0 . /workspace/chat-app

# Install dependencies
RUN npm install --prefix /workspace/chat-app

# Build the frontend
RUN npm run build --prefix /workspace/chat-app

# Expose the port
EXPOSE 8080

# Entrypoint
WORKDIR /workspace/chat-app
ENTRYPOINT ["npm", "start", "--prefix", "/workspace/chat-app"]