# Smart News/Research Analyst Agent — ADK on Cloud Run

An AI research assistant that combines **web lookup + summarization + classification**
in a single agent pipeline. Built with Google ADK and Gemini 2.5 Flash.

Ask it about any topic — a news event, a country, a technology, a person —
and it returns a clean structured brief in seconds.

---

## Agent Architecture

```
root_agent  (greeter / entry point)
    └── analysis_workflow  (SequentialAgent)
            ├── 1. researcher_agent      ← fetches Wikipedia content
            ├── 2. summarizer_agent      ← produces TL;DR + bullet points
            ├── 3. classifier_agent      ← assigns topic categories
            └── 4. presenter_agent       ← formats the final output
```

Each agent writes its output to a shared state key that the next agent reads.
No external paid APIs — only Wikipedia (free, no key needed).

---

## Example Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Topic: Quantum Computing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUMMARY
Quantum computing uses quantum mechanical phenomena like superposition and
entanglement to process information in fundamentally different ways than
classical computers...

• Qubits can represent 0 and 1 simultaneously (superposition)
• Entanglement links qubits so the state of one instantly affects another
• Major players include IBM, Google, and various startups
• Current machines are "noisy" and error-prone — still pre-commercial
• Expected to revolutionise cryptography, drug discovery, and logistics

CLASSIFICATION
• Science & Technology — The topic is fundamentally about a new computing paradigm
• Business & Economy — Major corporations and startups are investing heavily

Source: Wikipedia
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Project Files

```
news_analyst_agent/
├── __init__.py        ← marks directory as Python package
├── agent.py           ← all agent logic
├── requirements.txt   ← dependencies
└── README.md
```

---

## Full Deployment Guide

### Prerequisites
- A Google account (personal, not work/school)
- A Google Cloud project with billing enabled

---

### PART A — Google Cloud Project Setup

#### 1. Create a Google Cloud Project

1. Go to https://console.cloud.google.com/projectcreate
2. Enter a project name (e.g. `news-analyst-lab`)
3. Click **Create**
4. Note your **Project ID** — you'll need it shortly

#### 2. Enable Billing

1. Go to https://console.cloud.google.com/billing
2. Link your project to a billing account
3. New accounts get **$300 free credits** — this project costs < $1

#### 3. Open Cloud Shell

Click the `>_` icon in the top-right of the Cloud Console, or go to:
https://shell.cloud.google.com

Click **Authorize** if prompted.

#### 4. Set your project

```bash
gcloud config set project YOUR_PROJECT_ID
```

#### 5. Enable required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  compute.googleapis.com
```

This takes ~1 minute. You'll see: `Operation finished successfully.`

---

### PART B — Project Setup in Cloud Shell

#### 6. Create the project directory

```bash
cd && mkdir news_analyst_agent && cd news_analyst_agent
cloudshell open-workspace ~/news_analyst_agent
```

#### 7. Create each file

Run this for each file to open the editor, then paste the contents:

```bash
cloudshell edit __init__.py
cloudshell edit agent.py
cloudshell edit requirements.txt
```

Paste the contents of each file from this repository into the editor and save.

#### 8. Create your `.env` file

Run this entire block in the terminal — it auto-fills your project values:

```bash
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
SA_NAME=news-analyst-sa

cat <<EOF > .env
PROJECT_ID=$PROJECT_ID
PROJECT_NUMBER=$PROJECT_NUMBER
SA_NAME=$SA_NAME
SERVICE_ACCOUNT=${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com
MODEL=gemini-2.5-flash
EOF

# Verify it looks correct
cat .env
```

Expected output — make sure PROJECT_ID is not empty:
```
PROJECT_ID=your-project-id
PROJECT_NUMBER=123456789
SA_NAME=news-analyst-sa
SERVICE_ACCOUNT=news-analyst-sa@your-project-id.iam.gserviceaccount.com
MODEL=gemini-2.5-flash
```

#### 9. Install Python dependencies

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

---

### PART C — IAM Setup

#### 10. Load environment variables

```bash
source .env
```

#### 11. Create a dedicated service account

```bash
gcloud iam service-accounts create ${SA_NAME} \
    --display-name="Service Account for News Analyst Agent"
```

#### 12. Grant Vertex AI permissions

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/aiplatform.user"
```

---

### PART D — (Optional) Test Locally

Before deploying, you can run the agent locally to verify it works:

```bash
source .env
adk web
```

Open http://localhost:8000 in your browser.
Type `hello`, then ask about any topic (e.g. "Tell me about SpaceX").
If it returns a formatted brief → everything is working. Press Ctrl+C to stop.

---

### PART E — Deploy to Cloud Run

#### 13. Run the deployment command

Make sure you're inside the `news_analyst_agent/` directory, then run:

```bash
source .env

uvx --from google-adk==1.14.0 \
adk deploy cloud_run \
  --project=$PROJECT_ID \
  --region=us-central1 \
  --service_name=news-analyst-agent \
  --with_ui \
  . \
  -- \
  --labels=project=news-analyst-agent \
  --service-account=$SERVICE_ACCOUNT
```

**When prompted:**
- `Do you want to continue (Y/n)?` → type **Y** and press Enter
- `Allow unauthenticated invocations?` → type **y** and press Enter

This takes **3–5 minutes**. Don't close the terminal.

#### 14. Copy your Cloud Run URL

When it finishes, you'll see something like:
```
Service URL: https://news-analyst-agent-abc123xyz.us-central1.run.app
```

**This is your submission URL. Copy it.**

---

### PART F — Test the Deployed Agent

1. Open the Cloud Run URL in your browser
2. Toggle **Token Streaming** ON (top right)
3. Type: `hello`
4. When prompted, type a topic like: `climate change` or `artificial intelligence`
5. You should receive a formatted summary + classification

---

## Cleanup (After Submission)

To avoid any future charges once you're done:

```bash
gcloud run services delete news-analyst-agent --region=us-central1 --quiet
gcloud artifacts repositories delete cloud-run-source-deploy --location=us-central1 --quiet
```

---

## Cost Estimate

| Resource | Estimated Cost |
|----------|---------------|
| Cloud Run (a few test calls) | < $0.01 |
| Cloud Build (one-time deploy) | ~$0.03 |
| Artifact Registry | ~$0.01 |
| Vertex AI / Gemini 2.5 Flash | < $0.05 |
| **Total** | **< $0.10** |

Well within the $300 free trial. Scale-to-zero means zero cost when idle.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Agent Framework | Google ADK 1.14.0 |
| LLM | Gemini 2.5 Flash (via Vertex AI) |
| Web Lookup | Wikipedia API (free, no key) |
| Hosting | Google Cloud Run |
| Container Build | Cloud Build + Artifact Registry |
| Auth | IAM Service Account |
