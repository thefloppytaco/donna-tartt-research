#!/usr/bin/env bash
# Retry script for the 6 targets that were inconclusive (all 503/timeout) in v3.
# Same logic as v3 but with longer per-attempt backoff and per-target delay.

set -u
WORKDIR="$(cd "$(dirname "$0")/.." && pwd)/assets/sources/archive/wayback"
mkdir -p "$WORKDIR"
LOG="$WORKDIR/_wayback_hunt_retry_log.txt"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
DELAY=30
MIN_SIZE=800
MAX_PER_TARGET=5

TARGETS=(
  "https://www.artforum.com/columns/donna-tartt-on-william-eggleston-181842|Artforum-2001-10-Tartt-EgglestonPortfolio-candidate2.html"
  "https://oxfordamerican.org/magazine/issue-41-fall-2001/spanish-grandeur-in-mississippi|OA-Issue41-2001-Tartt-SpanishGrandeurInMississippi.html"
  "https://oxfordamerican.org/magazine/issue-29-september-october-1999/willie-morris|OA-Issue29-1999-Tartt-WillieMorrisTribute.html"
  "https://oxfordamerican.org/magazine/issue-6-march-april-1995/in-melbourne|OA-Issue6-1995-Tartt-InMelbourne.html"
  "https://www.gq.com/story/donna-tartt-garter-snake|GQ-1995-05-Tartt-AGarterSnake.html"
  "https://www.mauritshuis.nl/en/our-collection/pen-meets-paint|Mauritshuis-PenMeetsPaint-Tartt-contribution.html"
)

echo "Wayback retry — $(date)" > "$LOG"
echo "Workdir: $WORKDIR" >> "$LOG"
echo "---" >> "$LOG"

urlencode() {
  printf '%s' "$1" | python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read(), safe=""))'
}

cdx_query() {
  local url="$1" mode="$2"
  local enc extra api
  enc=$(urlencode "$url")
  extra="&collapse=urlkey"
  [ "$mode" = "prefix" ] && extra="${extra}&matchType=prefix"
  api="https://web.archive.org/cdx/search/cdx?url=${enc}&output=json&limit=20&filter=statuscode:200${extra}"

  local attempt
  for attempt in 1 2 3; do
    local tmpfile code output rc
    tmpfile=$(mktemp)
    code=$(curl -sS --max-time 30 -A "$UA" -o "$tmpfile" -w "%{http_code}" "$api" 2>/dev/null || echo "000")
    if [ "$code" = "200" ]; then
      output=$(python3 - "$tmpfile" <<'PY' 2>/dev/null
import json, sys
path = sys.argv[1]
try:
    data = json.load(open(path))
    if len(data) < 2:
        sys.exit(0)
    hdr = data[0]
    ti = hdr.index('timestamp')
    oi = hdr.index('original')
    for r in data[1:]:
        print(f"{r[ti]}\t{r[oi]}")
except Exception:
    sys.exit(2)
PY
)
      rc=$?
      rm -f "$tmpfile"
      if [ "$rc" = "0" ]; then
        [ -n "$output" ] && printf '%s\n' "$output"
        return 0
      else
        echo "    cdx 200 but JSON parse failed (attempt $attempt)" >&2
      fi
    else
      echo "    cdx HTTP $code (attempt $attempt)" >&2
      rm -f "$tmpfile"
    fi
    sleep $((45 * attempt))
  done
  return 1
}

fetch_snapshot() {
  local ts="$1" url="$2" outpath="$3"
  if ! [[ "$ts" =~ ^[0-9]{14}$ ]]; then
    echo "    ! invalid timestamp '$ts'; skip" >> "$LOG"
    return 1
  fi
  local raw="https://web.archive.org/web/${ts}id_/${url}"
  local code size words
  code=$(curl -sSL --max-time 60 -A "$UA" -w "%{http_code}" -o "$outpath" "$raw" 2>/dev/null || echo "000")
  size=$(wc -c <"$outpath" 2>/dev/null | tr -d ' ')
  words=$(sed 's/<[^>]*>/ /g' "$outpath" 2>/dev/null | tr -s ' \n' ' \n' | wc -w | tr -d ' ')
  echo "    -> $outpath (HTTP $code, ${size}B, ~${words} words)" >> "$LOG"
  if [ "$code" != "200" ] || [ "${size:-0}" -lt "$MIN_SIZE" ]; then
    echo "    ! reject (non-200 or under ${MIN_SIZE}B)" >> "$LOG"
    rm -f "$outpath"
    return 1
  fi
  return 0
}

for entry in "${TARGETS[@]}"; do
  ORIG="${entry%%|*}"
  FILE="${entry##*|}"
  echo "" >> "$LOG"
  echo "=== $ORIG" >> "$LOG"

  hits=0

  echo "  [cdx exact]" >> "$LOG"
  while IFS=$'\t' read -r TS ORIG2; do
    [ -z "${TS:-}" ] && continue
    [ "$hits" -ge "$MAX_PER_TARGET" ] && break
    OUT="$WORKDIR/${FILE%.html}-CDX-WB${TS}.html"
    if fetch_snapshot "$TS" "$ORIG2" "$OUT"; then
      hits=$((hits+1))
    fi
  done < <(cdx_query "$ORIG" exact 2>>"$LOG")

  if [ "$hits" -lt 2 ]; then
    echo "  [cdx prefix]" >> "$LOG"
    while IFS=$'\t' read -r TS ORIG2; do
      [ -z "${TS:-}" ] && continue
      [ "$hits" -ge "$MAX_PER_TARGET" ] && break
      slug=$(printf '%s' "$ORIG2" | sed 's|https\?://||; s|[/?&=]|_|g' | cut -c1-80)
      OUT="$WORKDIR/${FILE%.html}-PREFIX-${slug}-WB${TS}.html"
      if fetch_snapshot "$TS" "$ORIG2" "$OUT"; then
        hits=$((hits+1))
      fi
    done < <(cdx_query "$ORIG" prefix 2>>"$LOG")
  fi

  if [ "$hits" = "0" ]; then
    echo "  *** NO usable capture (after exact + prefix)" >> "$LOG"
  else
    echo "  + captured $hits snapshot(s)" >> "$LOG"
  fi

  sleep "$DELAY"
done

echo "" >> "$LOG"
echo "=== Retry summary ===" >> "$LOG"
ls -la "$WORKDIR"/*.html 2>/dev/null | awk '{printf "%10s  %s\n", $5, $NF}' >> "$LOG"

echo "Retry done. Log: $LOG"
cat "$LOG"
