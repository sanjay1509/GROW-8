# Run Grow8's 62 frontend Playwright tests without changing React or FastAPI.
# Build from the GROW-8 project root:
#   docker build -f qa/Dockerfile -t grow8-qa:62 .
FROM mcr.microsoft.com/playwright:v1.56.1-noble

WORKDIR /workspace

# Install frontend and QA dependencies using the versions pinned in their manifests.
COPY grow8-/package.json grow8-/package-lock.json ./grow8-/
RUN npm ci --prefix grow8- --no-audit --no-fund
COPY qa/package.json ./qa/package.json
RUN npm install --prefix qa --no-audit --no-fund

# Keep the application code unchanged; Vite runs inside this QA container.
COPY grow8-/ ./grow8-/
COPY qa/ ./qa/

WORKDIR /workspace/qa
CMD ["npm", "run", "test:frontend:smoke"]
