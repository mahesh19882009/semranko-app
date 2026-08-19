# Semranko security deployment settings

Local and automated tests may leave Turnstile keys unset; backend verification is bypassed only outside production in that case.

Production requires:

- `ENV=production`
- `TURNSTILE_SECRET_KEY` containing the server secret
- frontend `NEXT_PUBLIC_TURNSTILE_SITE_KEY` containing only the public site key
- the production hostname registered in Cloudflare Turnstile
- `CORS_ORIGINS` containing explicit comma-separated HTTPS frontend origins (never `*`)
- a strong unique `JWT_ACCESS_SECRET`
- Redis reachable by every API instance, with authentication/network isolation
- TLS termination so HSTS and Secure cookie guarantees apply
- `AUTH_COOKIE_SAMESITE=lax` for same-site deployments; use `none` only when frontend and API are genuinely cross-site and HTTPS is enforced

Application authentication uses HttpOnly access/session cookies. Unsafe authenticated requests must include the session-bound `X-CSRF-Token` value sourced from the non-HttpOnly CSRF cookie. Frontend JavaScript must never receive or persist the access/session credentials.
