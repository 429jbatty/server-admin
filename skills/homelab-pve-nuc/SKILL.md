---
name: homelab-pve-nuc
description: Interact safely with the Intel NUC Proxmox staging and target host through `ssh pve-nuc`. Use when inspecting, configuring, migrating to, restoring guests on, or troubleshooting the NUC, especially during the Lenovo-to-NUC migration.
---

# Homelab PVE NUC

Use this skill for any work that targets the Intel NUC rather than the existing Lenovo Proxmox host.

## Non-Negotiable Command Review

- Before running any command on the NUC, show the user the exact NUC command or small command batch and wait for explicit approval.
- Treat approval as applying only to the reviewed commands or clearly stated operation.
- Do not silently add write commands to an approved read-only batch.
- Clearly label commands as running on `pve-nuc`; never let a local Lenovo command look like a NUC command.

This review requirement overrides the normal preference to act autonomously.

## Access And Last-Known State

- SSH alias: `pve-nuc`
- Last-known staging hostname: `pve-nuc`
- Last-known staging LAN address: `192.168.1.185/24`
- Last-known bridge: `vmbr0`, with bridge port `nic0`
- Last verified: Proxmox VE `9.2.3`, Debian 13, kernel `7.0.6-2-pve`
- Last verified storage: `local` and `local-lvm` only
- Last verified guests: none
- Last verified devices: `/dev/dri/card0`, `/dev/dri/renderD128`, and `/dev/net/tun`
- Last verified absent devices: USB backup HDD and SONOFF Zigbee coordinator

These are orientation facts, not current truth. Reverify before acting.

## Start Protocol

1. Read `/root/server-admin/notes/migrations/lenovo-to-nuc/README.md` and the relevant phase doc on the Lenovo/repo side.
2. Ask what the user changed manually since the last session.
3. Present the exact read-only NUC checks for approval.
4. Run approved checks through `ssh pve-nuc`.
5. Compare live state with docs and summarize mismatches before changes.
6. Present each write/change batch for separate approval.
7. Update the migration cutover log after verified work.

## SSH Conventions

- Run NUC commands through the configured alias, for example:

```bash
ssh pve-nuc hostnamectl
ssh pve-nuc pveversion -v
ssh pve-nuc pvesm status
```

- SSH requires host network access from this environment. If a sandboxed attempt fails due network restrictions, rerun with the required escalation; do not reinterpret that failure as a NUC failure.
- Prefer one clear remote command per invocation. Use a remote shell only when the command genuinely requires pipes, expansion, or directory changes.
- Never assume `/root/server-admin` already exists on the NUC; verify it.

## Safe Read-Only Baseline

Offer the relevant subset for review before running:

```bash
ssh pve-nuc hostnamectl
ssh pve-nuc pveversion -v
ssh pve-nuc cat /etc/network/interfaces
ssh pve-nuc ip addr
ssh pve-nuc ip route
ssh pve-nuc pvesm status
ssh pve-nuc cat /etc/pve/storage.cfg
ssh pve-nuc qm list
ssh pve-nuc pct list
ssh pve-nuc lsblk -f
ssh pve-nuc lsusb
ssh pve-nuc ls -la /dev/dri
ssh pve-nuc ls -la /dev/net/tun
```

## NUC-Specific Guardrails

- Keep the NUC staging identity `pve-nuc` / `192.168.1.185` until the user explicitly confirms the cutover identity change.
- Do not assign the Lenovo production identity `proxmox` / `192.168.1.184` while the Lenovo is still using it.
- Do not format, repartition, initialize, or erase the USB HDD.
- Before adding `usb-backup`, verify the HDD by filesystem UUID and mount it at `/mnt/proxmox-usb-backup`.
- Configure `usb-backup` with `is_mountpoint 1`; never point it at an unmounted directory.
- Reverify NUC device paths instead of copying Lenovo paths. In particular, the NUC iGPU was observed as `card0`, while Lenovo-era docs may mention `card1`.
- Verify the SONOFF Zigbee coordinator by USB ID `10c4:ea60` before starting Home Assistant.
- Verify `/dev/net/tun` before starting CT `106` or CT `107`.
- Restore and validate guests in the order documented in `phase-5-guest-restore.md`.

## Change And Verification Pattern

For each requested NUC change:

1. Show the exact command and impact.
2. Wait for approval.
3. Run it through `ssh pve-nuc`.
4. Run approved read-only verification.
5. Report actual state and mismatches.
6. Update `/root/server-admin/notes/migrations/lenovo-to-nuc/cutover-log.md`.

Never store secrets from restored guests or host configuration in Git or chat.
