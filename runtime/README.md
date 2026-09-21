# Runtime data

This directory contains local development databases and other runtime output. SQLite files are ignored by Git:

- `*.sqlite3`
- `*.sqlite`
- `*.db`

Use an explicit `DATABASE_URL` when starting the API, for example `sqlite:///./runtime/shd-local.sqlite3`. Do not place production credentials or shared persistent data here.
