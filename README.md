# cronjot

Lightweight cron job logger that stores run history and sends digest summaries via email or Slack.

---

## Installation

```bash
pip install cronjot
```

---

## Usage

Wrap your cron job with `cronjot` to automatically log run history and receive digest summaries.

```python
from cronjot import CronJob

job = CronJob(
    name="daily-report",
    notify="slack",
    webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
)

@job.track
def run():
    # your cron job logic here
    print("Generating daily report...")

run()
```

You can also run it from the command line:

```bash
cronjot run --name "daily-report" --notify email --to alerts@example.com -- python myscript.py
```

Digest summaries include run timestamps, duration, exit status, and any captured output.

### Configuration

Create a `cronjot.yaml` in your project root to set defaults:

```yaml
storage: sqlite          # sqlite or json
db_path: ~/.cronjot.db
notify: slack
webhook_url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
digest_schedule: daily   # daily, weekly, or on-failure
```

---

## Features

- 📋 Stores full run history (status, duration, output)
- 📬 Sends digest summaries via **email** or **Slack**
- 🗄️ Lightweight SQLite or JSON storage — no external dependencies required
- 🖥️ Simple CLI and Python API

---

## License

MIT © [cronjot contributors](LICENSE)