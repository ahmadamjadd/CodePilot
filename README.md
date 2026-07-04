# CodePilot Review

Local development scaffold for a multi-agent AI code review system.

## Prerequisites

- Python 3.11 or newer
- `pip`

## Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configure environment variables

```bash
cp .env.example .env
```

Populate the `.env` file with your local API settings before running any later steps.

## Project layout

```text
src/codepilot_review/
  agents/
  graph/
  llm/
  models/
  reporting/
```

Step 1 only sets up the project structure and local development files. The graph and agent implementation will be added in later steps.