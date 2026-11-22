# Local mock credential service design

The Semester VIII validity checker will use only a local, owner-controlled mock HTTP or socket service. It must expose:

- `active`: credential should be reported as still valid.
- `inactive`: credential should be reported as revoked.
- `unknown`: checker must fail closed.
- `timeout`: checker must return `unknown` and never retry provider infrastructure.

No real provider credentials, provider SDK calls, or public network endpoints are permitted. Responses must contain synthetic IDs only; secret values remain in memory and are never persisted.
