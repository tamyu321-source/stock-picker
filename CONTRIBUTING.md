# Contributing

Thanks for helping improve Open Stock Picker. This project is a research workflow tool, so contributions should preserve explainability, avoid broker-order execution, and keep external data failures understandable to users.

## Local Setup

```powershell
npm install
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the backend:

```powershell
python -m backend.app
```

Run the frontend:

```powershell
npm run dev
```

## Validation

Before opening a pull request, run:

```powershell
python -m unittest discover backend/tests
npm run build
```

Backend tests use fake providers where possible, so they should not require live market-data access.

## Contribution Scope

Good first areas:

- Improve provider reliability, fallback behavior, and error messages.
- Add focused tests for scoring, universe discovery, and streaming behavior.
- Improve documentation, screenshots, deployment notes, and examples.
- Refactor large files into clearer components without changing behavior.
- Improve accessibility, responsive layout, and multilingual UI coverage.

Please avoid:

- Broker login, credential storage, or order placement.
- Hard-coding unverifiable stock recommendations.
- Adding API keys or secrets to the repository.
- Treating research output as financial advice.

## Pull Request Notes

- Keep changes focused and describe the behavior impact.
- Mention which markets or providers are affected.
- Add or update tests when changing scoring, discovery, streaming, or error handling.
- Include screenshots for visible UI changes when practical.
