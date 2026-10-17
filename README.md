
# Network Monitor v1.2

A lightweight Linux network monitoring tool built with **Bash, Python, Nmap and Telegram Bot API**.

Network Monitor periodically scans an authorized network device, compares the results with a previous scan and sends Telegram alerts when changes are detected.

## Features

- TCP port scanning and service version detection using Nmap
- XML report validation and comparison using Python
- Detection of port state and service changes
- Telegram notifications when network changes are detected
- Separate scan history for each target IPv4 address
- Scheduled monitoring with cron
- Automatic removal of archived reports older than 30 days
- Log rotation using logrotate
- Protection against concurrent executions using flock
- Command-line help and IPv4 address validation
- No third-party Python packages required

## Requirements

- Linux (developed and tested on Kali Linux)
- Bash
- Python 3
- Nmap
- curl
- flock (util-linux)
- Telegram bot and Chat ID for notifications

Optional:

- cron for automatic monitoring
- logrotate for log management

## Project Structure

```text
network-monitor/
├── .gitignore
├── README.md
├── LICENSE                  # MIT open-source license
├── network-monitor.sh
├── parse_nmap.py
├── telegram_notify.sh
├── logrotate.conf.example
│
├── logrotate.conf           # Optional local configuration
├── logrotate.state          # Created by logrotate
├── cron.log                 # Scheduled execution output
├── network-monitor.lock     # Runtime lock file
│
└── reports/
    └── TARGET_IP/
        ├── latest.xml       # Current comparison baseline
        ├── scan-*.xml       # Historical scan reports
        └── diff-*.txt       # Comparison results
```

Runtime files and local configuration are excluded from Git.

Telegram credentials are stored separately:

```text
~/.config/network-monitor/telegram.env
```

Never commit Telegram credentials to a public repository.

## Installation

### 1. Install dependencies

On Kali Linux, Debian or Ubuntu:

```bash
sudo apt update
sudo apt install nmap python3 curl util-linux git
```

For scheduled monitoring and log rotation:

```bash
sudo apt install cron logrotate
```

### 2. Clone the repository

```bash
git clone https://github.com/bSl1ck/network-monitor.git
cd network-monitor
```

### 3. Set executable permissions

```bash
chmod +x network-monitor.sh
```

### 4. Display help

```bash
./network-monitor.sh --help
```

### 5. Run your first scan

```bash
./network-monitor.sh 192.168.1.1
```

Replace the example address with a device you are authorized to scan.

The first successful scan creates a baseline. Subsequent scans are compared against that baseline.

## Usage

### Scan a network device

```bash
./network-monitor.sh 192.168.1.1
```

### Use the default target

```bash
./network-monitor.sh
```

Default target: `192.168.1.1`

### Show help

```bash
./network-monitor.sh --help
```

### Check Bash syntax

```bash
bash -n network-monitor.sh
```

### Check Python syntax

```bash
python3 -m py_compile parse_nmap.py
```

### View saved reports

```bash
ls -lh reports/192.168.1.1/
```

### Compare two XML reports manually

```bash
python3 parse_nmap.py old.xml new.xml
```

Exit codes:

| Code | Meaning |
|------|---------|
| 0 | No changes detected |
| 1 | Network changes detected |
| 2 | Validation or comparison error |

The main script additionally returns exit code 3 when another instance holds the monitoring lock.

## How It Works

1. The main Bash script validates the target IPv4 address.
2. An exclusive flock lock prevents overlapping executions.
3. Nmap scans the selected target using `-sT -sV`.
4. Nmap saves the results in XML format.
5. Python validates the XML and compares it with the previous baseline.
6. If network changes are detected, a Telegram notification is attempted.
7. After a successful comparison, the new scan replaces the previous baseline.
8. Archived reports older than 30 days are removed.

Reports are organized by target:

```text
reports/
├── 192.168.1.1/
│   └── latest.xml
└── 192.168.1.254/
    └── latest.xml
```

Each target maintains an independent baseline.

## Telegram Configuration

### 1. Create a Telegram bot

Open the official Telegram BotFather:

https://t.me/BotFather

Send `/newbot` and follow the instructions.

Save the Bot Token securely.

Start a private conversation with your new bot and send it a message.

Use the Telegram Bot API `getUpdates` method to identify your private Chat ID.

Telegram Bot API documentation:

https://core.telegram.org/bots/api

### 2. Create the configuration directory

```bash
mkdir -p ~/.config/network-monitor
chmod 700 ~/.config/network-monitor
```

### 3. Create the credentials file

```bash
nano ~/.config/network-monitor/telegram.env
```

Add:

```ini
BOT_TOKEN=YOUR_BOT_TOKEN
CHAT_ID=YOUR_CHAT_ID
```

Replace both placeholders with your actual credentials.

Do not add spaces around `=`.

### 4. Protect the credentials

```bash
chmod 600 ~/.config/network-monitor/telegram.env
```

### 5. Test Telegram notifications

From the project directory:

```bash
bash telegram_notify.sh 'Hello from Network Monitor!'
```

Expected terminal output:

```text
Telegram message sent successfully.
```

The corresponding message should arrive in your Telegram chat.

The notification script reads credentials from the configuration file automatically.

Telegram failures are logged but do not prevent the main script from completing an otherwise successful scan.

## Automatic Scheduling

Network Monitor can run automatically using the user's crontab.

First, determine the absolute installation path:

```bash
pwd
```

Use the result to construct the cron commands.

Open the cron editor:

```bash
crontab -e
```

Example daily scan at 20:00:

```cron
0 20 * * * /usr/bin/bash /home/USERNAME/network-monitor/network-monitor.sh 192.168.1.1 >> /home/USERNAME/network-monitor/cron.log 2>&1
```

Replace `/home/USERNAME/network-monitor` with the actual absolute installation directory and change the target IP if necessary.

The target argument is optional. If omitted, the script uses its default target.

Verify the saved schedule:

```bash
crontab -l
```

Check the cron service:

```bash
systemctl status cron
```

View recent scheduled execution output:

```bash
tail -n 30 cron.log
```

Cron jobs run according to the Linux system's local time.

The system must be running at the scheduled time.

## Log Rotation

A configuration template is included:

```text
logrotate.conf.example
```

Copy it:

```bash
cp logrotate.conf.example logrotate.conf
```

Edit the local configuration:

```bash
nano logrotate.conf
```

Replace the example log path with the absolute path to your project's `cron.log`.

The default rotation policy is:

- Rotate when the log reaches 1 MiB
- Retain four previous log archives
- Compress rotated logs using gzip
- Skip missing or empty logs

Test the configuration without modifying files:

```bash
logrotate -d -s ./logrotate.state ./logrotate.conf
```

Initialize the local rotation state:

```bash
logrotate -v -s ./logrotate.state ./logrotate.conf
```

For automatic rotation, schedule logrotate in your crontab.

Example daily check at 19:00:

```cron
0 19 * * * /usr/sbin/logrotate -s /home/USERNAME/network-monitor/logrotate.state /home/USERNAME/network-monitor/logrotate.conf
```

Adjust both paths to your installation.

Schedule log rotation outside normal monitoring runs to reduce conflicts with active log writes.

## Troubleshooting

### Monitor does not start

Check script syntax:

```bash
bash -n network-monitor.sh
```

Verify required tools:

```bash
command -v nmap
command -v python3
command -v curl
command -v flock
```

Try running the program manually:

```bash
bash network-monitor.sh 192.168.1.1
```

### Invalid IPv4 address

The program requires an IPv4 address with four valid octets.

Invalid example:

```text
192.168.1.999
```

Valid example:

```text
192.168.1.1
```

### Another instance is running

If you see:

```text
ERROR: Network Monitor is already running.
```

Another process may hold the exclusive lock.

Check running processes:

```bash
pgrep -af network-monitor.sh
```

Do not delete `network-monitor.lock` while monitoring processes may still be running.

### Telegram notifications are missing

Test the sender manually:

```bash
bash telegram_notify.sh 'Telegram test'
```

Check configuration file permissions:

```bash
ls -l ~/.config/network-monitor/telegram.env
```

Expected permissions: `600`.

Verify that the Bot Token and Chat ID are correct and that the bot has an active private conversation with you.

Never share the credentials file.

### Cron does not run

Check scheduled tasks:

```bash
crontab -l
```

Inspect cron service activity:

```bash
sudo journalctl -u cron --since '1 hour ago' --no-pager
```

Check the monitoring log:

```bash
tail -n 50 cron.log
```

### XML comparison errors

Check the report paths and run:

```bash
python3 parse_nmap.py old.xml new.xml
```

The parser checks scan scope, host availability, host identity, port counts and duplicate or unexpected port entries.

Comparison errors return exit code 2.

The baseline is not updated after a comparison validation error.

## Backup and Recovery

Back up the project regularly, especially before modifying the scripts.

Create an archive from the parent directory of the project:

```bash
cd ..
tar -czf network-monitor-backup.tar.gz \
  --exclude='network-monitor/.git' \
  --exclude='network-monitor/network-monitor.lock' \
  --exclude='network-monitor/logrotate.state' \
  --exclude='network-monitor/__pycache__' \
  network-monitor
```

This command backs up the project code and any existing reports and logs.

Telegram credentials are stored outside the project directory and are not included.

To verify the archive:

```bash
gzip -t network-monitor-backup.tar.gz
```

To list the contents:

```bash
tar -tzf network-monitor-backup.tar.gz
```

To restore the project, extract the archive into the desired parent directory:

```bash
tar -xzf network-monitor-backup.tar.gz -C /path/to/parent-directory
```

After restoration:

1. Install the required dependencies.
2. Restore Telegram credentials separately.
3. Check and update local logrotate paths.
4. Restore or recreate the required cron jobs.
5. Verify file permissions.
6. Test Telegram notifications.
7. Run a manual scan and check its output.

Do not overwrite an existing installation without reviewing its data first.

## Security and Limitations

- Scan only networks and devices you own or are authorized to assess.
- Keep Telegram Bot Tokens private.
- Do not commit `.env` files or sensitive runtime data.
- Avoid running the monitoring scripts as root unless specifically required.
- Protect backups containing internal network information.
- Nmap's default TCP scan does not cover every TCP or UDP port.
- Local network scan results do not establish Internet-facing exposure.
- This tool is intended for change detection, not comprehensive vulnerability assessment.
- Network or Telegram failures may require manual investigation.
- Scheduled monitoring requires a running Linux system and cron service.


## License

This project is licensed under the MIT License.

See the [LICENSE](LICENSE) file for the full license text.

Copyright (c) 2026 bSl1ck.
