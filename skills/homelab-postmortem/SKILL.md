---
name: homelab-postmortem
description: Conduct safe, read-only post-mortems for Proxmox homelab outages, Healthchecks.io alerts, watchdog failures, network incidents, guest/service downtime, backup failures, or unexplained reboots on the active NUC host. Use when the user asks to investigate what happened, build an incident timeline, identify root cause, explain why monitoring or watchdogs did or did not work, or recommend follow-up fixes without immediately changing production.
---

# Homelab Postmortem

Use this skill to investigate homelab incidents from evidence before proposing fixes.
Default to read-only commands until the user explicitly asks for remediation.

## Safety Rules

- Do not reboot, restart services, edit configs, clear logs, install packages, or change networking during the post-mortem.
- Do not print secret values, Healthchecks.io UUID URLs, API tokens, VPN credentials, or app passwords.
- Prefer `ssh pve-nuc` for active-host evidence. If sandboxed SSH fails, rerun with approval and treat the first failure as an environment restriction.
- Preserve user changes and repo state. Run `git status --short` before any repo edits if the post-mortem later becomes documentation work.
- Separate facts, inferences, and recommendations. Mark uncertain conclusions clearly.

## Core Workflow

1. Anchor the incident:
   - Record the user's reported symptom, first alert time, timezone, and manual recovery time if known.
   - Check host time with `ssh pve-nuc date --iso-8601=seconds`.
   - Check boot boundaries with `uptime -s`, `last -x reboot shutdown | head -20`, and `journalctl --list-boots --no-pager`.
2. Verify current state:
   - Check `systemctl --failed --no-pager`, `pveversion -v`, `pvesm status`, `qm list`, and `pct list`.
   - For Healthchecks incidents, check `systemctl status cron --no-pager` and the cron entry without revealing the ping URL.
   - For local watchdog incidents, check `systemctl status homelab-health-watchdog.timer homelab-health-watchdog.service --no-pager`, the failure counter, and `/var/log/homelab-health-watchdog/`.
3. Build the timeline from logs:
   - Use the boot index covering the incident, usually `-b -1` after a manual reboot.
   - Query narrow windows first, then expand: `journalctl -b <idx> --since=YYYY-MM-DDTHH:MM:SS --until=YYYY-MM-DDTHH:MM:SS --no-pager`.
   - Pull focused logs for `cron`, `homelab-health-watchdog`, kernel (`-k`), Proxmox services, storage, and relevant guests.
4. Classify the failure mode:
   - Host down: no local logs until reboot, journal ends unexpectedly, watchdog/hardware reset evidence.
   - Network path down: local cron/watchdog continue, but outbound checks time out or NIC/link/kernel errors appear.
   - Service down: host and network are healthy, but a guest, Docker service, or Proxmox service fails.
   - Monitor-only issue: host/service evidence is healthy while the external checker or heartbeat config failed.
5. Explain monitor and watchdog behavior:
   - Compare what each monitor checks against what actually failed.
   - For Healthchecks, remember cron may hide curl output with `>/dev/null 2>&1`; session duration can still reveal retries/timeouts.
   - For `homelab-health-watchdog`, inspect the installed script and `/etc/default/homelab-health-watchdog`; default checks are local-only unless gateway/external checks are enabled.

## Evidence Checklist

Use the relevant subset; avoid giant unfocused log dumps unless needed.

```bash
ssh pve-nuc date --iso-8601=seconds
ssh pve-nuc uptime -s
ssh pve-nuc last -x reboot shutdown | head -20
ssh pve-nuc journalctl --list-boots --no-pager
ssh pve-nuc systemctl --failed --no-pager
ssh pve-nuc systemctl status cron --no-pager
ssh pve-nuc systemctl status homelab-health-watchdog.timer homelab-health-watchdog.service --no-pager
ssh pve-nuc cat /var/lib/homelab-health-watchdog/consecutive-failures
ssh pve-nuc ls -la /var/log/homelab-health-watchdog
ssh pve-nuc journalctl -b -1 -u cron --since=YYYY-MM-DDTHH:MM:SS --until=YYYY-MM-DDTHH:MM:SS --no-pager
ssh pve-nuc journalctl -b -1 -u homelab-health-watchdog.service --since=YYYY-MM-DDTHH:MM:SS --until=YYYY-MM-DDTHH:MM:SS --no-pager
ssh pve-nuc journalctl -b -1 -k --since=YYYY-MM-DDTHH:MM:SS --until=YYYY-MM-DDTHH:MM:SS --no-pager
```

For NIC or network incidents, add:

```bash
ssh pve-nuc lspci -nn -s 00:1f.6
ssh pve-nuc ethtool -i nic0
ssh pve-nuc ethtool nic0
ssh pve-nuc journalctl -b -1 -k --grep=e1000e --no-pager
ssh pve-nuc journalctl -b 0 -k --grep=e1000e --no-pager
```

For backup or storage incidents, add read-only checks from `notes/homelab-backup-runbook.md`.
For media/Jellyfin incidents, use `skills/homelab-media-stack/SKILL.md` after this skill.

## Report Format

Lead with the answer, then show enough evidence to make it trustworthy:

- Summary: one or two sentences with the likely root cause and impact.
- Timeline: exact local timestamps with source evidence.
- Root cause: distinguish confirmed facts from likely interpretation.
- Why detection/recovery behaved as it did: Healthchecks, cron, watchdog, HA, or service restart behavior.
- Current state: whether the host/service is recovered and any residual errors.
- Recommendations: prioritized, concrete next steps; do not implement them unless asked.

Keep the report secret-safe. Redact URLs and tokens, and avoid pasting full diagnostic bundles unless the user asks.
