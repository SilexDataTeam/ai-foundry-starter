FROM registry.access.redhat.com/ubi9/nodejs-22:9.7-1766414965 AS base

# Copy the api server code with owner and permissions
COPY --chown=1001:0 . /workspace/chat-app

WORKDIR /workspace/chat-app

# Install dependencies (postinstall runs prisma generate)
RUN npm install

# Build the frontend
RUN npm run build

# Expose the port
EXPOSE 8080

# Entrypoint
ENTRYPOINT ["npm", "start", "--prefix", "/workspace/chat-app"]