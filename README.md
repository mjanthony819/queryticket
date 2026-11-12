# QueryTicket

**Buy the answer, not the database.**

QueryTicket is a synthetic-data demo of paid, privacy-preserving analytics. A data
owner exposes a fixed catalog of allowed analyses. A researcher asks a question in
plain language, an AI-assisted gate maps it to one allowed analysis or refuses it,
the owner approves, and a PayPal (sandbox) payment unlocks the finished report -
never the raw data. Requests for a named customer's records, raw rows, dates or
custom filters are refused before any checkout is created.

Built for the PayPal AI Hackathon. Everything here runs on synthetic fixtures:
no real customers, no real money, no privacy claims.

## What it demonstrates

- Plain-language question -> fixed-catalog mapping (labelled sample rules, or live
  Groq mapping when `GROQ_API_KEY` is set; the deterministic safety gate always
  runs first and can overrule the model).
- Refusal before checkout for personal, record-level, dated, filtered or
  multi-topic requests.
- Owner approval step: a report starts in `review` and must be approved before
  payment.
- Two explicitly labelled payment modes:
  - **Sample simulation** - a local, clearly marked simulated payment so anyone
    can run the full flow with zero credentials.
  - **PayPal sandbox** - a real PayPal Sandbox order create/capture against
    `api-m.sandbox.paypal.com` when `PAYPAL_SANDBOX_CLIENT_ID` and
    `PAYPAL_SANDBOX_SECRET` are set. Test money only; there is intentionally no
    production endpoint in the code.
- Integrity-checked delivery: the report's SHA-256 is stored at creation and
  re-verified at download. The receipt discloses that the hash binds content but
  is not a cryptographic signature.

## Run it (local demo, no dependencies)

Requires Python 3.9+ (standard library only; tested on 3.10).

```bash
python3 app.py
# open http://localhost:8765
```

Walkthrough in the UI:

1. Ask a question, e.g. "How widespread are battery charging problems?"
   Try a refused one too: "Show me John's battery tickets from last week."
2. Approve the mapped report (owner step).
3. Pay: use the labelled sample simulation, or configure the PayPal sandbox
   below and complete a real sandbox checkout.
4. Download the unlocked report with its receipt.

The local app binds to localhost only and guards mutations with a per-launch
token. It is a demo, not multi-user authentication.

## Optional configuration

| Variable | Effect |
|---|---|
| `GROQ_API_KEY` (optional `GROQ_MODEL`, default `openai/gpt-oss-20b`) | Enables live AI question mapping. The deterministic gate still runs first; disagreement or an invalid model answer refuses the request instead of guessing. Without a key the app uses the labelled sample rules. |
| `PAYPAL_SANDBOX_CLIENT_ID` / `PAYPAL_SANDBOX_SECRET` | Enables real PayPal Sandbox create/capture. Without them the app says so plainly and only the labelled simulation is offered. |
| `QUERYTICKET_DB` | Path of the SQLite file (default `queryticket.sqlite` next to `app.py`). |

## Tests

```bash
python3 tests/test_queryticket.py
```

20 acceptance checks: refusal gate, owner approval state machine, simulated
payment unlock, integrity-checked delivery, HTTP token guard, and honest
errors when the sandbox is not configured. Stdlib only, no network, no
credentials.

## Hosted owner-only preview (optional)

`deploy/hosted.py` wraps the same app behind a single-owner password gate for a
private Render deployment. Required environment: `RENDER_EXTERNAL_HOSTNAME`,
`SESSION_SIGNING_KEY` (32+ bytes), `OWNER_PASSWORD_HASH` (`salt_hex:scrypt_hex`).
Set `QUERYTICKET_TEST_SQLITE=1` to run on SQLite; otherwise provide
`DATABASE_URL` (Postgres) and install `psycopg` (`deploy/storage.py` is a
minimal adapter for the fixed statements, not an arbitrary-query gateway).
This preview is owner-only by design - judges should use the local demo above.

## AI evaluation

`docs/ai-evaluation.json` records the one live Groq evaluation that was run:
16/16 correct topic mappings on 16 synthetic, manually labelled paraphrases.
That is a small synthetic sanity check, not independent real-world validation,
and the repository says so wherever the number appears.

## Honesty notes

- All data is synthetic fixtures (`synthetic-camera-support-v1`); ground-truth
  labels are used for counts. No live text classification is claimed.
- The AI was used as a question mapper behind a deterministic gate, never to
  generate analytics, SQL or payment actions.
- This project was built with AI-assisted development.

## License

MIT - see [LICENSE](LICENSE).
