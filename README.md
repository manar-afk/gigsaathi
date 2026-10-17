# GigSaathi – GenAI assistant for gig and informal workers (India)

Multilingual (English, Hindi in Devanagari, Roman Hindi) help with earnings tracking, safety, rights and
welfare schemes, document help, and complaint drafting. Voice input and read-aloud are built in.

## How it works
1. **Understand** (1 LLM call): Gemini classifies the message, detects the language, and extracts earnings fields as validated JSON.
2. **Earnings (R1)**: totals, net and income per hour are computed by code (`Decimal`), never by the LLM. Replies use fixed
   localized templates, so earnings requests cost one LLM call.
3. **Guidance (R2-R5)**: entries are retrieved from `data/knowledge_base.json`. The LLM may only use retrieved entries and must
   cite their IDs. Citations are checked in code; uncited or invented IDs produce a "no verified information" reply.
   If nothing is retrieved, the LLM is not called for the answer at all.

## Requirement traceability
| Requirement | Files |
|---|---|
| R1 Earnings tracking | `app/services/earnings.py`, `app/storage/`, `app/services/assistant.py` (`_log`, `summary`) |
| R2 Safety practices | `data/knowledge_base.json` (topic `safety`), `app/services/assistant.py` (`_answer`) |
| R3 Rights and schemes | `data/knowledge_base.json` (topics `scheme`, `rights`), `app/retrieval/kb.py` |
| R4 Document help | `data/knowledge_base.json` (topic `document`) |
| R5 Grievance drafting | `app/services/prompts.py` (`GRIEVANCE_TASK`), `app/services/messages.py` (disclaimer) |
| Multilingual, voice | `app/services/messages.py`, `app/static/app.js` |

## Knowledge base and state coverage
- `data/knowledge_base.json`: 21 entries. National entries have `states: []`; state entries list their state and are only
  used when the user selects a city (or names a city/state) in that state. Add a state by adding an entry with `"states": ["<State>"]`.
- `data/cities.json`: 52 large cities (Census 2011 / MoHUA million-plus lists) mapped to their current states, with common aliases.
- `source_type`: `official` or `secondary`. Secondary entries (news, law-firm or legal-summary pages) are labelled in the UI with
  "please confirm with your state Labour Department". Upgrade them to `official` once you replace the URL with the state
  government or gazette page.
- Entries added on 2026-10-17 carry `last_verified: "2026-10-17"` (checked against the cited page that day). The first 12 national
  entries still have `last_verified: null`.

### Before you submit
Open each `source_url`, confirm the text, then set `last_verified`. State gig laws change fast: confirm for each state whether the
law is in force, the board is working, and registration is open. The Karnataka law is reported as contested, the Telangana law
was reported as passed by the Assembly (check for notification), and the Maharashtra item is only a bill.

## Run locally
```bash
pip install -r requirements-dev.txt
python -m pytest                      # 27 tests, LLM and storage mocked
gcloud auth application-default login
export PROJECT_ID=your-project VERTEX_LOCATION=us-central1 MODEL_NAME=gemini-2.5-flash
uvicorn app.main:app --reload --port 8080
```

## Deploy on Google Cloud Run (no API keys)
```bash
gcloud config set project YOUR_PROJECT
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  aiplatform.googleapis.com firestore.googleapis.com
gcloud firestore databases create --location=asia-south1 --type=firestore-native

gcloud iam service-accounts create gigsaathi-sa
SA=gigsaathi-sa@YOUR_PROJECT.iam.gserviceaccount.com
gcloud projects add-iam-policy-binding YOUR_PROJECT --member=serviceAccount:$SA --role=roles/aiplatform.user
gcloud projects add-iam-policy-binding YOUR_PROJECT --member=serviceAccount:$SA --role=roles/datastore.user

gcloud run deploy gigsaathi --source . --region asia-south1 --service-account $SA \
  --min-instances 1 --max-instances 3 --allow-unauthenticated \
  --set-env-vars PROJECT_ID=YOUR_PROJECT,VERTEX_LOCATION=us-central1,MODEL_NAME=gemini-2.5-flash
```
Check that your chosen `MODEL_NAME` is available in `VERTEX_LOCATION` (Vertex AI model availability varies by region).
Health check: `GET /health`.

## Config (environment variables)
`PROJECT_ID`, `VERTEX_LOCATION`, `MODEL_NAME`, `RATE_LIMIT_PER_MINUTE` (default 20), `MAX_MESSAGE_CHARS` (default 1000), `KB_PATH`.

## Security notes
No secrets in code or repo; ADC only. Input length/control-character limits; user text is delimited as data and the
delimiter cannot be closed by the user; LLM output is schema-validated; per-user and per-IP rate limits; CSP and other
headers; frontend writes with `textContent` (no HTML injection); logs hold intent, language and latency only.

## Known limits (be upfront with judges)
- No login: data is keyed by a random per-browser ID. Clearing browser storage loses access to old entries.
- Rate limiter is per instance.
- Retrieval is keyword-based; the LLM translates the query to English keywords first.
- Knowledge base coverage is limited to the entries in `data/knowledge_base.json`.
