#!/usr/bin/env bash

# Network Monitor v1.2 - Telegram notifications
set -euo pipefail

CONFIG="$HOME/.config/network-monitor/telegram.env"

if [[ ! -f "$CONFIG" ]]; then
    echo "ERROR: Telegram configuration file not found." >&2
    exit 2
fi

# Load Telegram credentials
source "$CONFIG"

if [[ -z "${BOT_TOKEN:-}" || -z "${CHAT_ID:-}" ]]; then
    echo "ERROR: BOT_TOKEN or CHAT_ID is missing." >&2
    exit 2
fi

MESSAGE="${1:-Network Monitor test message}"

curl --fail --silent --show-error \
    --request POST \
    "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${CHAT_ID}" \
    --data-urlencode "text=${MESSAGE}" \
    > /dev/null

echo "Telegram message sent successfully."
