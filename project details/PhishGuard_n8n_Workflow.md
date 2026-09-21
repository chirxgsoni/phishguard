# PhishGuard — n8n Workflow Integration

## Where n8n fits in the architecture

n8n is not the detection engine — your FastAPI backend (Layers 0–4) stays the brain. n8n sits alongside it as the **ingestion + SOAR automation layer**:

- **Ingestion:** watches Gmail (or other apps later) and hands new messages to your backend, instead of you hand-writing a custom polling/OAuth connector.
- **SOAR automation:** once your backend returns a risk score, n8n branches on severity and fans out the "autonomous response" actions from your blueprint — alerts, reports, logging.

What n8n should **not** be used for: the live, per-scan progress bar in your UI (Layer 0→4 streaming). That needs a real-time WebSocket from your own backend — n8n polls or reacts to webhooks, it isn't built for sub-second UI streaming.

---

## Step-by-step process

### 1. Set up n8n
Use n8n Cloud (fastest for a hackathon, nothing to manage) or self-host with one Docker command. Either way you get a visual canvas where each box is a step in the workflow.

### 2. Add a Gmail Trigger node
n8n has a built-in Gmail node with OAuth already handled — connect the same Google account you're scanning. Set it to trigger on "new message" (optionally filtered to a label). This replaces the custom Gmail-polling code that would otherwise need to be written in the backend.

### 3. Add an HTTP Request node → your FastAPI backend
Wire the Gmail node's output into an HTTP Request node that `POST`s to your own `/api/scans` endpoint with the email body and sender. n8n is just the courier here — all actual detection logic (Layers 0–4) stays in your backend.

### 4. Poll or wait for the result
Add a Wait node (a few seconds) followed by another HTTP Request node that `GET`s `/api/scans/{scan_id}`. For something closer to instant, add a webhook callback in your backend that pings an n8n Webhook node when the scan finishes, instead of polling.

### 5. Branch on risk severity
Add an IF node checking the returned `severity` field. LOW/MEDIUM can just log quietly; HIGH triggers the interesting branch — this is your blueprint's "Score ≥ 70 triggers automated workflow" logic, now visible as a diagram.

### 6. Fan out the HIGH-risk actions
From the HIGH branch, add parallel nodes:
- **Slack or Discord node** — alert your "security team"
- **Email/SMTP node** — send the auto-generated CERT-style report
- **Google Sheets or Supabase node** — log the incident for your dashboard's history table

### 7. Test with your three demo scenarios
Run your blueprint's Scenario A (safe notice), B (bank alert), and C (quishing QR) through the workflow and confirm the canvas branches correctly. This is a strong live-demo moment: show the n8n canvas mid-run right after showing the Evidence Cards in your UI.

---

## Tradeoff to keep in mind

Adding n8n means one moving part that lives outside your own codebase — fine for a demo, but it's not something Gemini or Claude can build for you. You wire it up manually in the n8n canvas once your backend's `/api/scans` endpoint exists and is reachable (publicly, or via a tunnel like ngrok during development).

If you want your backend built with this integration in mind from the start (e.g. a webhook-callback field so n8n doesn't have to poll), add a short note to that effect in the backend prompt before handing it to Gemini.
