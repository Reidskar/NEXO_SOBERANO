#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# NEXO — Phone Screen → OBS via RTMP (Termux)
# ============================================================
# Streams phone camera to OBS on the Torre via Tailscale RTMP.
# OBS adds it as a Media Source: rtmp://TOWER_IP/live/phone
#
# Usage:
#   bash phone_obs_stream.sh [camera_id] [quality]
#
#   camera_id: 0=back, 1=front (default: 0)
#   quality:   low|mid|high (default: mid)
#             low=360p/500k, mid=720p/1000k, high=1080p/2000k
#
# Requirements:
#   pkg install ffmpeg termux-api
# ============================================================
set -e

CAMERA_ID="${1:-0}"
QUALITY="${2:-mid}"

# ── Tower RTMP endpoint (via Tailscale) ───────────────────────
TOWER_IP="${NEXO_TOWER_IP:-${TAILSCALE_TOWER_IP:-192.168.100.22}}"
RTMP_URL="rtmp://${TOWER_IP}/live/phone"
STREAM_KEY="${NEXO_STREAM_KEY:-nexo_phone}"

# ── Quality presets ───────────────────────────────────────────
case "$QUALITY" in
  low)  WIDTH=640;  HEIGHT=360;  BITRATE=500k;  FPS=15 ;;
  mid)  WIDTH=1280; HEIGHT=720;  BITRATE=1000k; FPS=24 ;;
  high) WIDTH=1920; HEIGHT=1080; BITRATE=2000k; FPS=30 ;;
  *)    WIDTH=1280; HEIGHT=720;  BITRATE=1000k; FPS=24 ;;
esac

echo "════════════════════════════════════════"
echo "  NEXO Phone → OBS Stream"
echo "  Camera: ${CAMERA_ID} | Quality: ${QUALITY}"
echo "  Target: ${RTMP_URL}/${STREAM_KEY}"
echo "  Resolution: ${WIDTH}x${HEIGHT} @ ${FPS}fps / ${BITRATE}"
echo "════════════════════════════════════════"

# ── Check dependencies ────────────────────────────────────────
if ! command -v ffmpeg &>/dev/null; then
  echo "[NEXO] Installing ffmpeg..."
  pkg install -y ffmpeg
fi
if ! command -v termux-camera-photo &>/dev/null; then
  echo "[NEXO] Installing termux-api..."
  pkg install -y termux-api
fi

# ── Stream using v4l2 if available (Android 12+), else mjpeg ─
# Try direct camera streaming via ffmpeg
echo "[NEXO] Starting stream... (Ctrl+C to stop)"
echo "[NEXO] Add to OBS: Media Source → ${RTMP_URL}/${STREAM_KEY}"

# Method 1: Android camera via scrcpy export (USB/WiFi)
# Method 2: IP Webcam HTTP → ffmpeg relay (recommended for Termux)
# Method 3: Camera2 API via termux-camera (still frames, not video)

# Use termux-camera + ffmpeg for MJPEG → RTMP relay
TEMP_FIFO="$HOME/.nexo_cam_fifo"
[ -p "$TEMP_FIFO" ] || mkfifo "$TEMP_FIFO"

echo "[NEXO] Using MJPEG → RTMP relay approach"
echo "[NEXO] Note: For smoother video, install 'IP Webcam' app and:"
echo "[NEXO]   1. Start IP Webcam on phone (port 8080)"
echo "[NEXO]   2. Set IP_WEBCAM_URL below and re-run with --ipcam flag"

if [[ "$*" == *"--ipcam"* ]]; then
  # IP Webcam relay: pull from phone HTTP server → push to OBS
  IP_WEBCAM_PORT="${NEXO_IP_WEBCAM_PORT:-8080}"
  IP_WEBCAM_URL="http://127.0.0.1:${IP_WEBCAM_PORT}/videofeed"

  echo "[NEXO] Relaying from IP Webcam: ${IP_WEBCAM_URL}"
  ffmpeg -y \
    -re \
    -i "$IP_WEBCAM_URL" \
    -vf "scale=${WIDTH}:${HEIGHT},fps=${FPS}" \
    -c:v libx264 -preset ultrafast -tune zerolatency \
    -b:v "$BITRATE" -maxrate "$BITRATE" -bufsize "$((${BITRATE%k} * 2))k" \
    -pix_fmt yuv420p \
    -f flv \
    "${RTMP_URL}/${STREAM_KEY}" \
    2>&1 | grep -v "^frame="
else
  # Fallback: capture still frames in a loop and encode as video stream
  echo "[NEXO] Using frame capture loop (low fps, use --ipcam for smooth video)"

  FRAME_DIR="$HOME/.nexo_frames"
  mkdir -p "$FRAME_DIR"

  # Frame capture loop
  (
    N=0
    while true; do
      FRAME="${FRAME_DIR}/frame_$(printf '%04d' $((N % 10))).jpg"
      termux-camera-photo -c "$CAMERA_ID" "$FRAME" 2>/dev/null
      N=$((N + 1))
      sleep 0.1
    done
  ) &
  CAPTURE_PID=$!

  # Give capture loop time to fill frames
  sleep 2

  # Stream frames as MJPEG → RTMP
  ffmpeg -y \
    -framerate "$FPS" \
    -pattern_type glob \
    -i "${FRAME_DIR}/frame_*.jpg" \
    -stream_loop -1 \
    -vf "scale=${WIDTH}:${HEIGHT}" \
    -c:v libx264 -preset ultrafast -tune zerolatency \
    -b:v "$BITRATE" -pix_fmt yuv420p \
    -f flv \
    "${RTMP_URL}/${STREAM_KEY}" \
    2>&1 | grep -v "^frame=" &
  FFMPEG_PID=$!

  cleanup() {
    kill "$CAPTURE_PID" "$FFMPEG_PID" 2>/dev/null
    rm -rf "$FRAME_DIR"
    echo "[NEXO] Stream stopped."
  }
  trap cleanup EXIT INT TERM

  wait "$FFMPEG_PID"
fi
