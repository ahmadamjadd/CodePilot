# CodePilot Review

CodePilot is an automated, multi-agent AI pull request reviewer. It hooks into GitHub webhooks to analyze code changes (git diffs), runs specialized AI agents to review code quality and security issues, and posts a consolidated review report back as a comment on the PR.

## 🏗️ Architecture Flow

```text
[GitHub Webhook Event]
          │
          ▼
[AWS API Gateway (HTTP API)]
          │ (Direct SQS Integration)
          ▼
   [AWS SQS Queue]
          │ (Event Source Mapping Trigger)
          ▼
[AWS Lambda (Python 3.12)]
     │
     ├─► [LangGraph Orchestrator]
     │         │
     │         ├─► [Security Agent] (Checks secrets, SQLi, LLM-based security)
     │         ├─► [Clean Code Agent] (Checks styling, complexity, naming rules)
     │         └─► [Lead Reviewer Agent] (Aggregates and formats the final report)
     │
     ▼
[Post PR Comment back to GitHub]
```

---

## 🤖 AI Agents Workflow & Orchestration

The core review logic is built around a stateful multi-agent system orchestrated using **LangGraph**. A state object containing the `git_diff` is passed sequentially through three specialized agents:

1. **Security Agent:**
   * **Role:** Analyzes the added code changes for security flaws.
   * **Checks:** Scans for hardcoded secrets/API keys, SQL injection patterns (direct string concatenation in queries), and other vulnerabilities.
   * **Mechanism:** Combines local heuristics with zero-shot LLM prompts to detect patterns that standard static checkers might miss.

2. **Clean Code Agent:**
   * **Role:** Assesses code readability, maintainability, and design quality.
   * **Checks:** Validates naming conventions (e.g., catching temporary/unclear variable names), identifies overly complex boolean expressions, flags long lines, and evaluates adherence to SOLID and DRY principles.
   * **Mechanism:** Merges deterministic syntax analysis with contextual LLM feedback.

3. **Lead Reviewer Agent (Aggregator):**
   * **Role:** Acts as the lead reviewer that compiles the final report and issues the decision.
   * **Action:** Consolidates findings from the Security and Clean Code agents, formats them into a polished markdown report, and issues a final **Merge Decision** (`Changes Requested` vs. `Approved`).

---

## 🛠️ Technology Stack

*   **Orchestration:** [LangGraph](https://github.com/langchain-ai/langgraph) (Python) to coordinate specialized review agents.
*   **LLM Provider:** [Groq API](https://groq.com/) using the high-performance `llama-3.3-70b-versatile` model.
*   **Infrastructure:** AWS Lambda (runtime Python 3.12), AWS SQS, and AWS API Gateway (HTTP API).
*   **IaC (Infrastructure as Code):** Terraform.

---

## Getting Started

### Prerequisites

*   Python 3.11 or newer
*   Terraform 1.4+
*   A Groq API Key
*   A GitHub Personal Access Token (PAT) with repository read/write access (to read PR diffs and write comments).

### Local Setup

1. **Clone the repository and create a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Open the `.env` file and populate it with your keys:
   *   `GROQ_API_KEY`: Your Groq API key (starts with `gsk_`).
   *   `GITHUB_TOKEN`: Your GitHub token.

---

## 🧪 Testing Locally

You can test the system locally before deploying it to AWS:

### 1. Test LLM Connection
Run the Groq client test script:
```bash
PYTHONPATH=src .venv/bin/python scripts/test_groq_client.py
```

### 2. Test End-to-End Review Graph
You can run the full multi-agent review graph against `sample.diff`:
```python
# Create a test script (e.g. test_run.py)
from codepilot_review import run_review

with open("sample.diff", "r") as f:
    diff_content = f.read()

report = run_review(diff_content)
print(report)
```

---

## ☁️ Deployment (Terraform)

The infrastructure is fully automated using Terraform.

### 1. Configure TF Variables
Create a `terraform.tfvars` inside the `terraform` directory:
```hcl
aws_region           = "ap-south-1"
groq_api_key         = "your-groq-api-key"
github_token         = "your-github-token"
sqs_queue_name       = "codepilot-sqs-queue"
lambda_function_name = "codepilot-review-lambda"
```

### 2. Deploy
Run the following commands inside the `terraform` directory:
```bash
terraform init
terraform plan
terraform apply
```

### 3. Output
Once deployment is complete, Terraform will output:
*   `api_id`: The ID of your API Gateway.
*   `webhook_url`: The HTTP POST URL to configure as your GitHub Webhook endpoint.

---

## ⚠️ Important Considerations

### 🔑 Security
*   **AWS Provider:** Ensure you configure your AWS credentials via local environment variables (`AWS_ACCESS_KEY_ID` & `AWS_SECRET_ACCESS_KEY`) or your AWS profile. **Never hardcode AWS keys inside the Terraform code.**

### 📦 Cross-Platform Builds
*   The `build.tf` script installs requirements locally via `pip install -t build` to package them for AWS Lambda. 
*   If you are building from macOS or Windows, Python packages containing compiled C-extensions (like `pydantic_core` or `orjson`) will fail to run inside the Lambda Linux environment.
*   **Recommendation:** If deploying from a non-Linux machine, build your dependencies inside a Linux Docker container, or use the `--platform manylinux2014_x86_64 --only-binary=:all:` flag with pip.