"""VM-side automation entry point -- run from the VM's own crontab every 15
minutes, not GitHub Actions (same proven pattern as the other 6 trackers in
this portfolio; GitHub's schedule trigger was repeatedly measured at ~15-21%
real delivery for sub-hourly cadences).
"""

import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_DIR / "src"
DATA_FILES = ["data/history.csv", "docs/data.json"]

sys.path.insert(0, str(SRC_DIR))


def run(*args, check=True):
    return subprocess.run(list(args), cwd=str(REPO_DIR), check=check)


def sync_with_remote():
    # --hard, not --soft, and BEFORE the pipeline runs -- reset --soft only
    # moves HEAD, leaving stale index entries for any file this script
    # doesn't explicitly `git add`, which then get silently recommitted on
    # the next force-push. Learned this the hard way on hormuz-strait-monitor.
    run("git", "fetch", "origin", "main")
    run("git", "reset", "--hard", "origin/main")


def build_commit_message(payload):
    parts = [
        f"{payload['aircraft_tracked_total']} aircraft tracked",
        f"{payload['co2_kg_this_snapshot'] / 1000:.1f}t CO2 this snapshot",
    ]
    leaderboard = payload.get("airline_leaderboard") or []
    if leaderboard:
        top = leaderboard[0]
        parts.append(f"top: {top['airline']} ({top['co2_kg_per_hour'] / 1000:.1f}t/hr)")
    if payload.get("dark_aircraft_flags"):
        parts.append(f"{len(payload['dark_aircraft_flags'])} dark-aircraft flag(s)")
    return "data: flight emissions update — " + " | ".join(parts)


def git_commit_and_push(payload):
    # freddynyanda@proton.me is Fred's real, verified GitHub email -- same
    # standardization as every other tracker in this portfolio.
    run("git", "config", "user.name", "nyandajr")
    run("git", "config", "user.email", "freddynyanda@proton.me")
    run("git", "add", *DATA_FILES, check=False)

    diff = run("git", "diff", "--cached", "--quiet", check=False)
    if diff.returncode == 0:
        print("[run_and_push] no changes to commit")
        return

    run("git", "commit", "-m", build_commit_message(payload))
    run("git", "push", "--force", "origin", "HEAD:main")


def main():
    sync_with_remote()

    import pipeline
    payload = pipeline.run()

    git_commit_and_push(payload)
    print("[run_and_push] done")


if __name__ == "__main__":
    main()
