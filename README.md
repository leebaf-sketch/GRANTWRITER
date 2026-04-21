# Email Response Assistant

A small Flask app where you can:

1. Save email response templates.
2. Paste an incoming email.
3. Get the best matching template and improvement suggestions.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000

## How matching works

- Keyword overlap between incoming email and template text.
- Fuzzy string similarity using `difflib.SequenceMatcher`.
- Combined weighted score is used to rank templates.

## Improvement suggestions

The app checks for:
- Whether questions are answered directly.
- Whether tone includes appreciation.
- Whether response includes next steps/timeline.
- If the response is too short.
