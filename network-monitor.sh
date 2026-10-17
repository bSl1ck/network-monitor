#!/usr/bin/env bash

# Network Monitor v1.2
# Nmap scanning, change detection, cleanup and Telegram alerts

set -euo pipefail

# Display usage information
show_help() {
    cat <<'EOF'
Network Monitor v1.2

USAGE:
  ./network-monitor.sh [TARGET_IP]
  ./network-monitor.sh --help

DESCRIPTION:
  Scans a network device using Nmap and compares results
  with the previous scan.

  Sends Telegram alerts when network changes are detected.

ARGUMENTS:
  TARGET_IP    IPv4 address of the device to monitor.
               Default: 192.168.1.1

OPTIONS:
  -h, --help   Display this help message.

EXAMPLES:
  ./network-monitor.sh 192.168.0.1
  ./network-monitor.sh 192.168.1.254
  ./network-monitor.sh --help

REQUIREMENTS:
  Bash, Python 3, Nmap, curl, flock

Only scan devices you own or are authorized to assess.
EOF
}

# Process command-line options
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    -*)
        echo "ERROR: Unknown option: $1" >&2
        echo "Use --help for usage information." >&2
        exit 2
        ;;
esac

# Accept at most one target argument
if (( $# > 1 )); then
    echo "ERROR: Too many arguments." >&2
    echo "Use --help for usage information." >&2
    exit 2
fi


TARGET="${1:-192.168.1.1}"

# Validate the target IPv4 address
validate_ipv4() {
    local ip="$1"
    local octet
    local -a octets

    if [[ ! "$ip" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
        return 1
    fi

    IFS='.' read -r -a octets <<< "$ip"

    for octet in "${octets[@]}"; do
        if (( 10#$octet > 255 )); then
            return 1
        fi
    done

    return 0
}

if ! validate_ipv4 "$TARGET"; then
    echo "ERROR: Invalid IPv4 address: $TARGET" >&2
    exit 2
fi


SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPORT_DIR="$SCRIPT_DIR/reports/$TARGET"
PARSER="$SCRIPT_DIR/parse_nmap.py"
TELEGRAM="$SCRIPT_DIR/telegram_notify.sh"

DATE=$(date +%Y-%m-%d_%H-%M-%S)

CURRENT="$REPORT_DIR/scan-$DATE.xml"
PREVIOUS="$REPORT_DIR/latest.xml"
DIFF="$REPORT_DIR/diff-$DATE.txt"

mkdir -p "$REPORT_DIR"

# Remove archived reports older than 30 days
cleanup_reports() {
    echo "[Cleanup] Removing reports older than 30 days..."

    find "$REPORT_DIR" -maxdepth 1 -type f \
        \( -name 'scan-*.xml' -o -name 'diff-*.txt' \) \
        -mtime +29 -print -delete

    echo "[Cleanup] Finished."
}

# Send Telegram alert without interrupting the monitor
send_telegram_alert() {
    local message="$1"

    echo "[Telegram] Sending network change alert..."

    if bash "$TELEGRAM" "$message"; then
        echo "[Telegram] Alert delivered."
    else
        echo "WARNING: Telegram notification failed." >&2
    fi
}

# Prevent multiple instances from running simultaneously
exec 9>"$SCRIPT_DIR/network-monitor.lock"

if ! flock -n 9; then
    echo "ERROR: Network Monitor is already running."
    exit 3
fi

echo "================================"
echo "       NETWORK MONITOR v1.2"
echo "================================"
echo "Target: $TARGET"
echo "Date: $DATE"
echo

echo "[1/3] Starting Nmap scan..."

nmap -sT -sV -oX "$CURRENT" "$TARGET"

echo
echo "[2/3] Comparing scan results..."

if [[ -f "$PREVIOUS" ]]; then

    if python3 "$PARSER" "$PREVIOUS" "$CURRENT" > "$DIFF"; then
        echo "STATUS: No changes detected."
    else
        status=$?

        if [[ "$status" -eq 1 ]]; then
            echo "WARNING: Network changes detected!"

            MESSAGE="NETWORK CHANGE DETECTED
Target: $TARGET
Date: $DATE

$(cat "$DIFF")"

            send_telegram_alert "$MESSAGE"

        else
            echo "ERROR: Comparison failed (code: $status)." >&2
            exit "$status"
        fi
    fi

    cat "$DIFF"

else
    # First run: validate scan before creating baseline
    if python3 "$PARSER" "$CURRENT" "$CURRENT" > "$DIFF"; then
        echo "Initial scan validated. Creating baseline."
    else
        echo "ERROR: Initial scan validation failed." >&2
        exit 2
    fi
fi

echo
echo "[3/3] Updating baseline..."

cp "$CURRENT" "$PREVIOUS"

echo
echo "Scan completed!"
echo "Report: $CURRENT"
echo "Comparison: $DIFF"

echo
cleanup_reports
