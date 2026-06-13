# Cloud Run Demo Deployment

Fastest demo path: deploy the existing combined Dockerfile as one Cloud Run
service. The container starts both services:

- Next.js on `$PORT` (public web app)
- FastAPI/LangGraph agent on `AGENT_PORT=8123` (internal to the same container)

This keeps the public demo to one URL and avoids cross-service CORS/env wiring
during the hackathon.

## Prerequisites

Install and authenticate the Google Cloud CLI locally:

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

Enable required APIs:

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com
```

## Secrets

Create secrets once:

```bash
printf '%s' 'YOUR_GEMINI_API_KEY' | gcloud secrets create gemini-api-key --data-file=-
printf '%s' 'YOUR_LINKUP_API_KEY' | gcloud secrets create linkup-api-key --data-file=-
printf '%s' 'YOUR_REDIS_URL' | gcloud secrets create redis-url --data-file=-
```

`LINKUP_API_KEY` and `REDIS_URL` are optional for a public demo. The app degrades
gracefully if LinkUp is unavailable, and the deal store falls back to in-memory
state if Redis is absent.

## Build And Deploy

From the repo root:

```bash
gcloud run deploy rfp-intake-cockpit \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars NODE_ENV=production,AGENT_PORT=8123,RFP_AGENT_URL=http://localhost:8123/rfp,FIXED_AGENT_URL=http://localhost:8123/fixed,DYNAMIC_AGENT_URL=http://localhost:8123/dynamic,LEGAL_AGENT_URL=http://localhost:8123/legal \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest,LINKUP_API_KEY=linkup-api-key:latest,REDIS_URL=redis-url:latest
```

If you skip LinkUp or Redis secrets, remove those names from `--set-secrets`.

## Demo URL

Cloud Run prints a service URL after deployment. The app redirects `/` to
`/rfp-intake`, so judges can use the root URL directly.

## Resetting The Demo

The nav has a `Reset demo` button that clears browser-side Copilot/A2UI state and
starts a fresh RFP intake session.
