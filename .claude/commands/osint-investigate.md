---
name: osint-investigate
description: Run full OSINT investigation on a target using BigBrother + Gemma 4.
allowed_tools: ["Bash", "Read"]
---

# /osint-investigate <target> [type]

Runs full OSINT profile via BigBrother → Gemma 4 analysis → OmniGlobe injection.

## Types
- `username` — social media footprint
- `email` — breach lookup
- `ip` — network scan + geolocation + Shodan
- `phone` — carrier + location lookup

## Usage
```bash
curl -X POST http://localhost:8000/api/osint/globe/inject \
  -H "x-api-key: $NEXO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"target": "TARGET", "target_type": "TYPE"}'
```

## Check services first
```bash
curl http://localhost:8000/api/osint/status
python scripts/supervisor_osint.py --once
```
