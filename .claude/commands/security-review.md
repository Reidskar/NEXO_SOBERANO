---
name: security-review
description: Run security audit on changed Python files — checks secrets, input validation, auth guards.
allowed_tools: ["Bash", "Read", "Grep", "Glob"]
---

# /security-review

Audits NEXO SOBERANO backend for security issues.

## Steps

1. **Scan for hardcoded secrets**
   ```bash
   grep -rn "sk-\|api_key\s*=\s*['\"]" backend/ NEXO_CORE/ --include="*.py" | grep -v ".env\|os.getenv\|os.environ"
   ```

2. **Check auth guards on new endpoints**
   - Every `POST/DELETE/PATCH` route must call `_require_key()` or use a Depends guard
   - Public `GET` endpoints are acceptable only for `/status`, `/health`, `/poll`

3. **Run bandit static analysis**
   ```bash
   .venv/Scripts/python.exe -m bandit -r backend/ NEXO_CORE/ -ll -q
   ```

4. **Verify no staged secrets**
   ```bash
   git diff --cached --name-only | grep -E "\.env$|auth/.*\.json|\.zip$"
   ```

5. **Check BigBrother/OSINT routes** — confirm all protected with API key

## Pass Criteria
- bandit reports 0 HIGH severity issues
- No hardcoded credentials in diff
- All mutation endpoints gated
