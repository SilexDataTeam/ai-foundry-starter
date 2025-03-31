FROM registry.access.redhat.com/ubi9/nodejs-22:9.5-1742955796 AS base

# Copy the api server code with owner and permissions
COPY --chown=1001:0 . /workspace/chat-app

WORKDIR /workspace/chat-app

# Install dependencies
RUN npm install

# Prisma
RUN npx prisma generate

# Build the frontend
RUN npm run build

# Expose the port
EXPOSE 8080

# Entrypoint
ENTRYPOINT ["npm", "start", "--prefix", "/workspace/chat-app"]