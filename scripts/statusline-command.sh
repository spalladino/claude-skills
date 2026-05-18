#!/bin/bash

# Single jq pass: extract every field we need, one per line, into an array.
mapfile -t F < <(jq -r '
    .model.display_name // .model.id // "unknown",
    (.effort.level // "normal"),
    (.context_window.context_window_size // 200000),
    (.context_window.current_usage.input_tokens // 0),
    (.context_window.current_usage.cache_creation_input_tokens // 0),
    (.context_window.current_usage.cache_read_input_tokens // 0),
    ([.todos[]? | select(.status != "deleted")] | length),
    ([.todos[]? | select(.status == "completed")] | length),
    (.rate_limits.five_hour.used_percentage // ""),
    (.rate_limits.five_hour.resets_at // ""),
    (.cost.total_cost_usd // ""),
    (.cwd // "")
')
model=${F[0]}      effort_raw=${F[1]}
model=${model/(1M context)/1M}
ctx_max=${F[2]}    ctx_in=${F[3]}    ctx_cc=${F[4]}    ctx_cr=${F[5]}
total_tasks=${F[6]} completed=${F[7]}
rate_pct=${F[8]}   rate_reset=${F[9]}
cost_usd=${F[10]}  cwd=${F[11]}

case "$effort_raw" in
    xhigh)  effort="xHigh" ;;
    high)   effort="High"  ;;
    medium) effort="Med"   ;;
    low)    effort="Low"   ;;
    normal) effort="Med"   ;;
    *)      effort="${effort_raw^}" ;;
esac

# Context: % free
context_used=$(( ctx_in + ctx_cc + ctx_cr ))
if [ "$ctx_max" -gt 0 ]; then
    percent_free=$(( 100 - (context_used * 100 / ctx_max) ))
else
    percent_free=100
fi

# Tasks
if [ "${total_tasks:-0}" -gt 0 ] 2>/dev/null; then
    tasks=" | tasks:${completed}/${total_tasks}"
else
    tasks=""
fi

# 5-hour rate limit window
if [ -n "$rate_pct" ] && [ -n "$rate_reset" ]; then
    rate_left=$(awk -v p="$rate_pct" 'BEGIN { printf "%d", 100 - p }')
    reset_at=$(date -d "@${rate_reset}" +%H:%M 2>/dev/null \
               || date -r "${rate_reset}" +%H:%M 2>/dev/null)
    rate=" | 5h:${rate_left}% (resets ${reset_at})"
else
    rate=""
fi

# Cost (only if non-trivial)
# if [ -n "$cost_usd" ] && awk -v c="$cost_usd" 'BEGIN { exit !(c >= 0.01) }'; then
#     cost=$(awk -v c="$cost_usd" 'BEGIN { printf " | $%.2f", c }')
# else
#     cost=""
# fi
cost=""

# Folder: strip ~/Projects/ or ~/ prefix
folder=${cwd/#$HOME\/Projects\//}
folder=${folder/#$HOME\//\~/}

# Git branch (cheap, no fork to rev-parse if not in a repo)
git_branch=$(git symbolic-ref --quiet --short HEAD 2>/dev/null \
             || git rev-parse --short HEAD 2>/dev/null \
             || echo "no repo")

echo "${model} ${effort} | ${percent_free}% free${tasks}${rate}${cost} | ${folder} | ${git_branch}"
