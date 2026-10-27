# Playwright release matches qa/package.json (@playwright/test 1.56.1).
# This image runs the QA tests; Grow8 API and MySQL stay in their existing services.
FROM mcr.microsoft.com/playwright:v1.56.1-noble
WORKDIR /workspace
COPY grow8-/package.json grow8-/package-lock.json ./grow8-/
RUN npm ci --prefix grow8-
COPY qa/package.json ./qa/package.json
RUN npm install --prefix qa --no-audit --no-fund
COPY grow8-/ ./grow8-/
COPY qa/ ./qa/
WORKDIR /workspace/qa
CMD ["npm", "run", "test:frontend:smoke"]
