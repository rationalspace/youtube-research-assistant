#!/usr/bin/env bash
# rotate-logs.sh — rotate cron.log weekly, keeping the last 4 archived logs
# Called by cron every Sunday at 7:55 AM (before the 8 AM finance run)

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$DIR/cron.log"

if [ ! -f "$LOG" ] || [ ! -s "$LOG" ]; then
    exit 0  # nothing to rotate
fi

STAMP="$(date +%Y%m%d)"
cp "$LOG" "$DIR/cron.log.$STAMP"
: > "$LOG"
echo "$(date): Log rotated to cron.log.$STAMP" >> "$LOG"

# Keep only the 4 most recent archives
ls -t "$DIR"/cron.log.2* 2>/dev/null | tail -n +5 | xargs rm -f

echo "Log rotation complete — archived as cron.log.$STAMP"
