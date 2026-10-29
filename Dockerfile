# Render (or any Docker host): builds the web app, then serves it with the API on $PORT.
FROM node:22-slim AS web
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt
COPY backend/ backend/
COPY data/boundaries/ data/boundaries/
COPY seed/ seed/
COPY --from=web /app/frontend/dist frontend/dist
WORKDIR /app/backend
CMD uvicorn pikdrishti.api:app --host 0.0.0.0 --port ${PORT:-10000}
