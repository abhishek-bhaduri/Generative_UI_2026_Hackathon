#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-rfp-intake-cockpit}"
REGION="${REGION:-us-central1}"
PROJECT_ID="${PROJECT_ID:-}"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud is not installed. Install Google Cloud CLI, then rerun this script." >&2
  exit 1
fi

if [[ -z "$PROJECT_ID" ]]; then
  PROJECT_ID="$(gcloud config get-value project 2>/dev/null || true)"
fi

if [[ -z "$PROJECT_ID" || "$PROJECT_ID" == "(unset)" ]]; then
  echo "Set PROJECT_ID or run: gcloud config set project YOUR_PROJECT_ID" >&2
  exit 1
fi

gcloud config set project "$PROJECT_ID" >/dev/null

echo "Enabling required Google Cloud APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com

ensure_secret() {
  local env_name="$1"
  local secret_name="$2"
  local required="${3:-optional}"
  local value="${!env_name:-}"

  if [[ -z "$value" ]]; then
    if [[ "$required" == "required" ]]; then
      echo "Missing required env var: $env_name" >&2
      exit 1
    fi
    echo "Skipping optional secret $secret_name; $env_name is not set."
    return
  fi

  if gcloud secrets describe "$secret_name" >/dev/null 2>&1; then
    printf '%s' "$value" | gcloud secrets versions add "$secret_name" --data-file=-
  else
    printf '%s' "$value" | gcloud secrets create "$secret_name" --data-file=-
  fi
}

ensure_secret GEMINI_API_KEY gemini-api-key required
ensure_secret LINKUP_API_KEY linkup-api-key optional
ensure_secret REDIS_URL redis-url optional

SECRET_ARGS=(--set-secrets GEMINI_API_KEY=gemini-api-key:latest)
if [[ -n "${LINKUP_API_KEY:-}" ]]; then
  SECRET_ARGS+=(--set-secrets LINKUP_API_KEY=linkup-api-key:latest)
fi
if [[ -n "${REDIS_URL:-}" ]]; then
  SECRET_ARGS+=(--set-secrets REDIS_URL=redis-url:latest)
fi

echo "Deploying $SERVICE_NAME to Cloud Run in $REGION..."
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "NODE_ENV=production,AGENT_PORT=8123,RFP_AGENT_URL=http://localhost:8123/rfp,FIXED_AGENT_URL=http://localhost:8123/fixed,DYNAMIC_AGENT_URL=http://localhost:8123/dynamic,LEGAL_AGENT_URL=http://localhost:8123/legal" \
  "${SECRET_ARGS[@]}"

echo "Done. Open the Cloud Run service URL printed above."
