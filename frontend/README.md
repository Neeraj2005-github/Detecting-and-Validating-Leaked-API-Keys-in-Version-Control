# Detecting Secrets in Version Control Frontend

This frontend is built for a single-user, local deployment and intentionally has no authentication layer.

> No authentication — single-user local deployment. RBAC/multi-user auth is scoped as future work (see project report §11).

## Scope

- Local demo and review workflows only
- No login, no session management, no RBAC/multi-user access control
- Backend is expected to be trusted and local-only for the current review
- Future authentication work is explicitly out of scope for this frontend

## Run locally

```bash
npm install
npm run dev
```

The app expects the backend API at the local default URL or via the `VITE_API_URL` environment variable.

## Notes

- No `Authorization` headers are used in the API client
- The app is designed to be easy to adapt if auth is added later by changing only the central API client
- This is a deliberate product scope decision, not an oversight
