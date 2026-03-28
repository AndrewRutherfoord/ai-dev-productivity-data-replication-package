
import unidiff

# ! Don't think we need this. It's just not worth the compute effort

def parse_diff(filename, raw_diff):
    """Wrap a raw hunk in proper unified diff headers so unidiff can parse it."""
    full_diff = f"--- a/{filename}\n+++ b/{filename}\n{raw_diff}"
    return unidiff.PatchSet(full_diff)

def line_churn(filename, raw_diff):
    # This can parse the git diff, but it outputs the same info as the added_lines and deleted_lines from the query, so not sure if it's worth it. Would be useful if we go for line level, but that would be a lot of work.
    patch = parse_diff(filename, raw_diff)

    stats = {"added": 0, "removed": 0, "modified": 0}
    for f in patch:
        for hunk in f:
            added = [l for l in hunk if l.is_added]
            removed = [l for l in hunk if l.is_removed]
            # Paired add/remove lines within a hunk ≈ modifications
            modified = min(len(added), len(removed))
            stats["modified"] += modified
            stats["added"] += len(added) - modified
            stats["removed"] += len(removed) - modified
    return stats
