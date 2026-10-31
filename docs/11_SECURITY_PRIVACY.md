# 11 — Security, Privacy and Responsible Financial AI

## Security posture
Financial data is sensitive even in a prototype. Build with privacy controls, but strictly use synthetic records during the hackathon.

## Synthetic-only policy
All demo profiles, accounts, statements, transactions and notifications must be fictional. Do not connect real banks, open-banking services, SMS/email inboxes or payment systems. Never request bank passwords, UPI PIN, OTP, CVV or full card number. Mark demo records and reports "Synthetic demo data — not real financial records."

## Authentication and authorization
If implemented, use reputable identity/session handling, secure HTTP-only SameSite cookies where appropriate, CSRF protection for cookie mutations, rate limits and ownership checks on every user-scoped resource. Never trust client-supplied user ID. A local demo profile must be labelled as demo authentication, not production security.

## Encryption
Use HTTPS in deployment. Keep Blob Storage private. Use Azure Key Vault and managed identity where possible. Use managed database encryption at rest. Never commit secrets or credentials.

## File upload
Allow only expected formats; validate MIME and file signature, not extension alone. Set file-size/page/row limits. Reject malformed/encrypted files unless safe handling exists. Parse in worker with resource limits. Protect against parser exhaustion and decompression bombs. Store files privately and use short-lived access only when required. Delete temporary files according to retention policy.

## API security
Pydantic validation, payload limits, rate limits, parameterized queries/ORM, CORS allowlist, safe error messages, pagination limits and authorization on every endpoint. Return 404 for inaccessible user-owned records rather than revealing existence.

## AI security
Treat documents, merchant descriptors and notes as untrusted. Prompt injection inside a statement cannot override system instructions. Separate system instructions from retrieved data. Allowlist tools and validate arguments. Never allow arbitrary SQL, shell or external network actions. Minimize context sent to Gemini. Validate structured outputs and numeric claims. Require confirmation for persistent changes.

## Financial boundaries
PaisaFlow provides budgeting education and scenario modelling only. It must not recommend buying/selling named securities, guarantee returns, provide regulated investment advice, make credit decisions, initiate payments or cancel subscriptions. If asked for a specific investment recommendation, explain the boundary and offer general educational information instead.

## Data minimization
Collect only necessary information. No real account numbers. Avoid raw descriptions in logs. Retain uploads only as long as needed. Provide demo reset/delete. Minimize coach history. Do not use user data to train external models. Explain what is sent to Gemini.

## Secrets
Possible secrets: database URL, Redis URL, Gemini key, Azure storage configuration, identity settings and session secret. Use `.env` locally and Key Vault/managed identity in Azure. `.env.example` contains placeholders only.

## Audit events
Record corrections, rule changes, goal/profile edits, scenario save/delete, import confirmation and demo reset. Never store secrets or full statement payloads in audit metadata.

## Incident response
If a key leaks: revoke/rotate, inspect logs, remove from repository history if committed, document and scan. If cross-user exposure is suspected, disable affected endpoint and investigate immediately.

## Security acceptance
No secrets; no real financial fixtures; file validation; ownership tests; prompt injection tests; no raw statement logging; demo reset isolated; HTTPS in deployment; privacy boundary visible.
