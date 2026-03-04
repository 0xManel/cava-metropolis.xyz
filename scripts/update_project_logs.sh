#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
LOG_DIR="$REPO_ROOT/logs"
TARGET_DATE="${1:-$(date +%F)}"
LOG_FILE="$LOG_DIR/$TARGET_DATE.md"
INDEX_FILE="$LOG_DIR/INDEX.md"

COMMIT_START_MARKER="<!-- AUTO-COMMITS:START -->"
COMMIT_END_MARKER="<!-- AUTO-COMMITS:END -->"
FILES_START_MARKER="<!-- AUTO-FILES:START -->"
FILES_END_MARKER="<!-- AUTO-FILES:END -->"

mkdir -p "$LOG_DIR"

if [ ! -f "$LOG_FILE" ]; then
  cat > "$LOG_FILE" <<EOF
# Daily Log - $TARGET_DATE

## Manual Notes

Use this section for important context that cannot be inferred from git metadata.

$COMMIT_START_MARKER
$COMMIT_END_MARKER

$FILES_START_MARKER
$FILES_END_MARKER
EOF
fi

COMMITS_TMP="$(mktemp)"
FILES_TMP="$(mktemp)"

{
  echo "## Auto Timeline"
  echo
  echo "_Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")_"
  echo
  COMMIT_ROWS="$(git -C "$REPO_ROOT" log \
    --since="$TARGET_DATE 00:00:00" \
    --until="$TARGET_DATE 23:59:59" \
    --invert-grep \
    --grep='^chore(logs): auto-update daily activity log$' \
    --date=format:'%H:%M:%S' \
    --pretty=format:'%h|%ad|%an|%s')"
  if [ -z "$COMMIT_ROWS" ]; then
    echo "- No commits registered for this day."
  else
    while IFS='|' read -r hash hour author subject; do
      [ -z "$hash" ] && continue
      echo "- \`$hour\` \`$hash\` **$author**: $subject"
    done <<< "$COMMIT_ROWS"
  fi
} > "$COMMITS_TMP"

{
  echo "## Auto Files"
  echo
  echo "_Unique files touched on ${TARGET_DATE}_"
  echo
  FILE_ROWS="$(git -C "$REPO_ROOT" log \
    --since="$TARGET_DATE 00:00:00" \
    --until="$TARGET_DATE 23:59:59" \
    --invert-grep \
    --grep='^chore(logs): auto-update daily activity log$' \
    --name-only \
    --pretty=format: | sed '/^$/d' | sort -u)"
  if [ -z "$FILE_ROWS" ]; then
    echo "- No files changed."
  else
    while IFS= read -r file_path; do
      [ -z "$file_path" ] && continue
      echo "- \`$file_path\`"
    done <<< "$FILE_ROWS"
  fi
} > "$FILES_TMP"

update_block() {
  local file_path="$1"
  local start_marker="$2"
  local end_marker="$3"
  local replacement_file="$4"
  awk -v start="$start_marker" -v end="$end_marker" -v replacement="$replacement_file" '
    BEGIN {
      while ((getline line < replacement) > 0) block = block line "\n";
      close(replacement);
      skip = 0;
      replaced = 0;
    }
    $0 == start {
      print start;
      printf "%s", block;
      skip = 1;
      replaced = 1;
      next;
    }
    $0 == end {
      skip = 0;
      print end;
      next;
    }
    !skip { print; }
    END {
      if (!replaced) {
        print "";
        print start;
        printf "%s", block;
        print end;
      }
    }
  ' "$file_path" > "$file_path.tmp"
  mv "$file_path.tmp" "$file_path"
}

update_block "$LOG_FILE" "$COMMIT_START_MARKER" "$COMMIT_END_MARKER" "$COMMITS_TMP"
update_block "$LOG_FILE" "$FILES_START_MARKER" "$FILES_END_MARKER" "$FILES_TMP"

{
  echo "# Logs Index"
  echo
  entry_count=0
  while IFS= read -r file_name; do
    [ -z "$file_name" ] && continue
    day="${file_name%.md}"
    echo "- \`$day\`: [$file_name](./$file_name)"
    entry_count=$((entry_count + 1))
  done < <(find "$LOG_DIR" -maxdepth 1 -type f -name '20??-??-??.md' -print | sed "s#^$LOG_DIR/##" | sort -r)

  if [ "$entry_count" -eq 0 ]; then
    echo "- No daily logs yet."
  fi
} > "$INDEX_FILE"

rm -f "$COMMITS_TMP" "$FILES_TMP"
