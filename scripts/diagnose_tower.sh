#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
#  scripts/diagnose_tower.sh — NEXO Tower Diagnostic
#  Run from Termux phone to check torre + domain health
#  Usage: bash diagnose_tower.sh [TOWER_IP]
# ============================================================

TOWER_IP="${1:-192.168.100.22}"
TOWER_PORT="${2:-8000}"
BASE_URL="http://${TOWER_IP}:${TOWER_PORT}"
API_KEY="${NEXO_API_KEY:-nexo_dev_key_2025}"
DOMAIN="elanarcocapital.com"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

ok()   { echo -e "${GREEN}  ✓${NC} $*"; }
fail() { echo -e "${RED}  ✗${NC} $*"; }
warn() { echo -e "${YELLOW}  !${NC} $*"; }
info() { echo -e "${CYAN}  ·${NC} $*"; }

echo -e "\n${BOLD}══════════════════════════════════════════${NC}"
echo -e "${BOLD}   NEXO TORRE DIAGNOSTIC — $(date '+%H:%M:%S')${NC}"
echo -e "${BOLD}══════════════════════════════════════════${NC}\n"

# ─── 1. Network reachability ─────────────────────────────────
echo -e "${BOLD}[ 1/5 ] Network${NC}"
if ping -c 1 -W 2 "${TOWER_IP}" >/dev/null 2>&1; then
    ok "Torre IP ${TOWER_IP} is reachable (LAN)"
else
    fail "Torre IP ${TOWER_IP} NOT reachable — are you on the same WiFi?"
    warn "Hint: Check WiFi SSID on phone vs torre network"
fi

# ─── 2. Backend health ───────────────────────────────────────
echo -e "\n${BOLD}[ 2/5 ] Backend (LAN)${NC}"
HTTP_CODE=$(curl -s -o /tmp/nexo_health.json -w "%{http_code}" --connect-timeout 5 "${BASE_URL}/health" 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
    ok "Backend responding at ${BASE_URL}/health"
    if command -v jq >/dev/null 2>&1; then
        cat /tmp/nexo_health.json | jq -r '"    Status: \(.status // "ok")"' 2>/dev/null
    fi
elif [ "$HTTP_CODE" = "000" ]; then
    fail "Backend NOT responding (connection refused or timeout)"
    warn "Backend process may be down. From torre run:"
    warn "  .venv\\Scripts\\python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"
else
    warn "Backend returned HTTP $HTTP_CODE"
fi

# ─── 3. Tower control endpoint ───────────────────────────────
echo -e "\n${BOLD}[ 3/5 ] Tower Status API${NC}"
TOWER_STATUS=$(curl -s --connect-timeout 5 "${BASE_URL}/api/tower/status" 2>/dev/null)
if echo "$TOWER_STATUS" | grep -q '"ok":true'; then
    ok "Tower control API responding"
    TUNNEL_ALIVE=$(echo "$TOWER_STATUS" | grep -o '"alive":[a-z]*' | head -2 | tail -1)
    DIAG=$(echo "$TOWER_STATUS" | grep -o '"diagnosis":"[^"]*"' | cut -d'"' -f4)
    info "Tunnel: $TUNNEL_ALIVE"
    info "Diagnosis: $DIAG"
else
    warn "Tower control API not available (may need update — run: git pull && restart)"
fi

# ─── 4. Domain / Cloudflare ──────────────────────────────────
echo -e "\n${BOLD}[ 4/5 ] Domain (${DOMAIN})${NC}"
DOMAIN_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 8 "https://${DOMAIN}/health" 2>/dev/null)
if [ "$DOMAIN_CODE" = "200" ]; then
    ok "Domain ${DOMAIN} is UP and responding"
elif [ "$DOMAIN_CODE" = "000" ]; then
    fail "Domain ${DOMAIN} is DOWN (no response)"
    info "This means cloudflared tunnel is not running on the torre."
    echo ""
    echo -e "  ${BOLD}→ FIX from this phone (if backend is alive):${NC}"
    echo "    curl -s -X POST ${BASE_URL}/api/tower/restart-tunnel \\"
    echo "      -H 'X-API-Key: ${API_KEY}' | jq ."
else
    warn "Domain returned HTTP $DOMAIN_CODE"
fi

# ─── 5. Restart if needed ────────────────────────────────────
echo -e "\n${BOLD}[ 5/5 ] Auto-fix options${NC}"
if [ "$HTTP_CODE" = "200" ] && [ "$DOMAIN_CODE" != "200" ]; then
    echo -e "${YELLOW}  Backend is alive but domain is down.${NC}"
    echo -e "  Attempting tunnel restart...\n"
    RESTART_RESULT=$(curl -s -X POST "${BASE_URL}/api/tower/restart-tunnel" \
        -H "X-API-Key: ${API_KEY}" \
        --connect-timeout 10 2>/dev/null)
    if echo "$RESTART_RESULT" | grep -q '"ok":true'; then
        ok "Tunnel restart command sent successfully!"
        info "Wait 15 seconds then re-run this script to verify."
    else
        fail "Could not restart tunnel via API"
        warn "Log into torre manually and run:"
        warn "  AUTOSTART_TORRE.bat"
    fi
elif [ "$HTTP_CODE" = "200" ] && [ "$DOMAIN_CODE" = "200" ]; then
    ok "Everything is working correctly!"
else
    fail "Backend is down — cannot auto-fix remotely"
    warn "Connect to torre via RDP or physically restart:"
    warn "  Double-click AUTOSTART_TORRE.bat"
    warn "  Or run: schtasks /run /tn NEXO_Torre_Autostart"
fi

echo -e "\n${BOLD}══════════════════════════════════════════${NC}"
echo -e "  LAN Backend:  ${BASE_URL}"
echo -e "  Domain:       https://${DOMAIN}"
echo -e "  OmniGlobe:    https://${DOMAIN}/omniglobe"
echo -e "${BOLD}══════════════════════════════════════════${NC}\n"

# ─── Quick reference commands ────────────────────────────────
echo -e "${BOLD}Quick commands:${NC}"
echo "  # Restart tunnel only:"
echo "  curl -X POST ${BASE_URL}/api/tower/restart-tunnel -H 'X-API-Key: ${API_KEY}'"
echo ""
echo "  # Check stream status:"
echo "  curl ${BASE_URL}/api/tower/stream/status"
echo ""
echo "  # Start OBS stream:"
echo "  curl -X POST ${BASE_URL}/api/tower/stream -H 'X-API-Key: ${API_KEY}' -H 'Content-Type: application/json' -d '{\"action\":\"start\"}'"
echo ""
echo "  # Send mobile heartbeat:"
echo "  curl -X POST ${BASE_URL}/api/mobile/heartbeat -H 'Content-Type: application/json' -d '{\"agent_id\":\"telefono\"}'"
echo ""
