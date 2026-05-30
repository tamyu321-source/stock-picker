# Security Policy

Open Stock Picker is an investment research workflow tool. It does not execute trades and should not store broker credentials.

## Supported Versions

Security fixes target the current `master` branch.

## Reporting a Vulnerability

If GitHub private vulnerability reporting is available for this repository, please use it. If it is not available, open a minimal public issue that describes the affected area without exploit details, secrets, or live credentials.

Please include:

- A short description of the issue.
- Steps to reproduce in a local environment.
- The affected endpoint, provider, or UI surface.
- Any safe proof-of-concept details that do not expose credentials or private data.

## Security Model

- The app is for research support only and does not place broker orders.
- External market-data and news providers are treated as unreliable inputs.
- API keys, paid-data credentials, and `.env` files should stay outside the repository.
- Production deployments should add rate limiting, caching, request timeouts, and reverse-proxy controls.
