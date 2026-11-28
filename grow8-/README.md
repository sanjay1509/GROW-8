# GROW8 Frontend

React 19, TypeScript and Vite frontend for the GROW8 contributor, creator and admin workflows.

## Run locally

Start the backend stack first by following [`../docs.md`](../docs.md). Then:

```bash
npm ci
npm run dev
```

Vite prints the local URL (normally <http://localhost:5173>). The frontend uses `http://localhost:8000/api/v1` by default. Set `VITE_API_BASE_URL` in a local `.env` file if the API runs elsewhere.

## Checks

```bash
npm run lint
npm run build
```

The end-to-end API collection is maintained in [`../grow8-backend/tests/postman/grow8.postman_collection.json`](../grow8-backend/tests/postman/grow8.postman_collection.json) and runs with `make postman` from `grow8-backend/`.
