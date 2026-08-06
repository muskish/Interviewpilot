# InterviewPilot — Adaptive Multi-Agent AI Mock Interview Coach

> Work in progress. Full README (architecture, setup, design decisions, example
> transcripts) lands in the final phase. This is a placeholder so the repo
> isn't empty.

## Status
Phase 1 complete: project scaffold, config, and shared data models.

## Quick setup (so far)
```bash
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env   # then fill in your API key
python test_api_connection.py   # sanity-check your LLM provider before anything else
```
