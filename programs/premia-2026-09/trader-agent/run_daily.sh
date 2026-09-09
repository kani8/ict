#!/bin/bash
# Trail B daily runner. Invokes claude -p with the playbook as the prompt.
# Confirmed against installed `claude --help`: --allowedTools and
# --permission-mode both exist with this syntax on this machine's version.
set -uo pipefail
ROOT="/Users/kvatsa/Downloads/GLBX-20260702-TBF7DT8KTH"
cd "$ROOT" || exit 1
mkdir -p trader-agent/logs
LOG="trader-agent/logs/$(date +%F).log"
{
  echo "=== run_daily.sh start: $(date) ==="
  claude -p "$(cat trader-agent/PLAYBOOK.md)

Today is $(date +%F). Execute the playbook now." \
    --model "${TRAIL_B_MODEL:-opus}" \
    --allowedTools "Bash(curl:*),Bash(uv:*),WebFetch,WebSearch,Read,Write,Edit" \
    --permission-mode acceptEdits
  echo "=== run_daily.sh end: $(date) ==="
} >> "$LOG" 2>&1
