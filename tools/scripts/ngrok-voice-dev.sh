#!/usr/bin/env bash
# ngrok-voice-dev.sh - Print ngrok setup for local AI receptionist (voice) testing.
# Use ONE ngrok process with TWO tunnels to avoid ERR_NGROK_334 (endpoint already online).
# WebSocket (wss://) is supported automatically on ngrok http tunnels.
# See docs/voice-local-testing.md for full steps.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOC="$REPO_ROOT/docs/voice-local-testing.md"
NGROK_CONFIG="$REPO_ROOT/tools/ngrok-voice.yml"

echo "=============================================="
echo "  LexiqAI – Local voice (AI receptionist)"
echo "  ngrok setup for Twilio webhook + stream"
echo "=============================================="
echo ""

# Check ngrok
if ! command -v ngrok &>/dev/null; then
  echo "ngrok is not installed or not in PATH."
  echo "Install: https://ngrok.com/download"
  echo "Then: ngrok config add-authtoken YOUR_TOKEN"
  echo ""
  exit 1
fi

echo "1) Start your stack (if not already running):"
echo "   cd $REPO_ROOT && docker compose up -d"
echo ""
echo "2) Start BOTH tunnels in ONE ngrok process (avoids ERR_NGROK_334):"
echo ""
if [ ! -f "$NGROK_CONFIG" ]; then
  echo "   Copy the example config first:"
  echo "   cp $REPO_ROOT/tools/ngrok-voice.yml.example $NGROK_CONFIG"
  echo ""
fi
echo "   ngrok start api-core voice-gateway --config=$NGROK_CONFIG"
echo ""
echo "   You'll get two https URLs (api-core and voice-gateway)."
echo "   WebSocket (wss://) works on the same URLs; no extra config."
echo ""
echo "3) Copy the two https URLs from the ngrok UI and set:"
echo ""
echo "   export API_BASE_URL=https://YOUR_API_NGROK_URL"
echo "   export VOICE_GATEWAY_URL=wss://YOUR_VOICE_NGROK_HOST/streams/twilio"
echo ""
echo "   Then restart api-core:"
echo "   docker compose up -d api-core --force-recreate"
echo ""
echo "4) In Twilio Console, set your number's Voice webhook to:"
echo "   https://YOUR_API_NGROK_URL/api/v1/twilio/webhook  (POST)"
echo ""
echo "5) Call your Twilio number to test."
echo ""
echo "Full guide: $DOC"
echo ""
