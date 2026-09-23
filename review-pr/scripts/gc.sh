#!/usr/bin/env bash
# Garbage-collect cached review-pr worktrees. The markdown in each slug dir is kept;
# only `wt/` (the git worktree) is removed.
#
# Usage: gc.sh [--keep N] [--days D] [--all] [--dry-run]
#   --keep N   keep at most N worktrees, newest first by .stamp (default 6)
#   --days D   remove worktrees not touched in D days (default 7)
#   --all      remove every worktree
#   --dry-run  print what would be removed
#   --grace H  never remove a worktree whose .stamp is younger than H hours (default 6):
#              that is a review in progress, possibly in another session
#
# A worktree is also removed when its PR is merged or closed. State comes from
# meta.json (written by gather on every run) and is refreshed with `gh` when available.
set -euo pipefail

KEEP=6; DAYS=7; ALL=0; DRY=0; GRACE=6
while [ $# -gt 0 ]; do
  case "$1" in
    --keep) KEEP="$2"; shift 2;;
    --days) DAYS="$2"; shift 2;;
    --all) ALL=1; shift;;
    --grace) GRACE="$2"; shift 2;;
    --dry-run) DRY=1; shift;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/review-pr"
[ -d "$ROOT" ] || { echo "gc: nothing to do ($ROOT missing)"; exit 0; }

now=$(date +%s)
removed=0; kept=0
declare -A touched_repos=()

remove_wt() { # slug wt repo reason
  local slug="$1" wt="$2" repo="$3" reason="$4"
  echo "remove $slug/wt ($reason)"
  removed=$((removed+1))
  [ "$DRY" = 1 ] && return 0
  if [ -n "$repo" ] && git -C "$repo" rev-parse --git-dir >/dev/null 2>&1; then
    git -C "$repo" worktree remove --force "$wt" 2>/dev/null || rm -rf "$wt"
    touched_repos["$repo"]=1
  else
    rm -rf "$wt"
  fi
}

# Order slugs newest first by their .stamp (touched by gather on every run).
mapfile -t ordered < <(
  for meta in "$ROOT"/*/meta.json; do
    [ -f "$meta" ] || continue
    dir=$(dirname "$meta")
    stamp=$(stat -c %Y "$dir/.stamp" 2>/dev/null || stat -c %Y "$meta")
    printf '%s\t%s\n' "$stamp" "$dir"
  done | sort -rn | cut -f2-
)

for dir in "${ordered[@]}"; do
  meta="$dir/meta.json"; slug=$(basename "$dir"); wt="$dir/wt"
  [ -d "$wt" ] || continue
  repo=$(jq -r '.repo_root // empty' "$meta")
  owner_repo=$(jq -r '.owner_repo // empty' "$meta")
  pr=$(jq -r '.pr // empty' "$meta")
  state=$(jq -r '.state // "UNKNOWN"' "$meta")
  if [ -n "$owner_repo" ] && [ -n "$pr" ] && command -v gh >/dev/null; then
    fresh=$(gh pr view "$pr" --repo "$owner_repo" --json state --jq .state 2>/dev/null || true)
    if [ -n "$fresh" ] && [ "$fresh" != "$state" ]; then
      state="$fresh"
      if [ "$DRY" = 0 ]; then
        jq --arg s "$state" '.state=$s' "$meta" > "$meta.tmp" && mv "$meta.tmp" "$meta"
      fi
    fi
  fi
  stamp=$(stat -c %Y "$dir/.stamp" 2>/dev/null || stat -c %Y "$meta")
  age_days=$(( (now - stamp) / 86400 ))
  age_hours=$(( (now - stamp) / 3600 ))
  if [ "$ALL" = 0 ] && [ "$age_hours" -lt "$GRACE" ]; then kept=$((kept+1)); echo "keep $slug/wt (in use, ${age_hours}h old)"; continue; fi
  if [ "$ALL" = 1 ]; then remove_wt "$slug" "$wt" "$repo" "--all"
  elif [ "$state" = MERGED ] || [ "$state" = CLOSED ]; then remove_wt "$slug" "$wt" "$repo" "PR $state"
  elif [ "$age_days" -ge "$DAYS" ]; then remove_wt "$slug" "$wt" "$repo" "untouched ${age_days}d"
  elif [ "$kept" -ge "$KEEP" ]; then remove_wt "$slug" "$wt" "$repo" "over --keep $KEEP"
  else kept=$((kept+1)); fi
done

if [ "$DRY" = 0 ]; then
  for repo in "${!touched_repos[@]}"; do
    git -C "$repo" worktree prune 2>/dev/null || true
  done
fi
echo "gc: removed $removed worktree(s), kept $kept"
