# Project Activity Logs

This folder stores a chronological project history so any AI model (or developer) can continue work with context.

## Structure

- `INDEX.md`: quick directory by date.
- `YYYY-MM-DD.md`: one file per day with timeline, scope, and technical findings.

## Update Rule

For each work day:

1. Create or update `logs/YYYY-MM-DD.md`.
2. Add commit timeline in chronological order.
3. Record what changed (feature/fix/security/deploy).
4. Record open risks with exact file and line reference.
5. Update `logs/INDEX.md`.

## Quick Commands

```bash
# commits from today
git log --since='today 00:00' --date=iso --pretty=format:'%h|%ad|%an|%s'

# unique files touched today
git log --since='today 00:00' --name-only --pretty=format: | sed '/^$/d' | sort -u
```

## Notes

- Keep logs factual and short.
- Never store secrets or passwords in these files.
