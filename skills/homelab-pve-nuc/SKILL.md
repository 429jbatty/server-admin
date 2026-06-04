---
name: homelab-pve-nuc
description: Interact safely with the active Intel NUC Proxmox host through `ssh pve-nuc`. Use when inspecting, configuring, restoring guests on, or troubleshooting the primary homelab host.
---

# Homelab PVE NUC

Use this skill for work on the active Intel NUC Proxmox host rather than the retired Lenovo migration source.

## Command Approval Rule

- Run expected NUC commands that directly implement or verify the documented Lenovo-to-NUC migration without requesting per-batch approval.
- Keep the user informed before meaningful migration changes and clearly label work that targets `pve-nuc`.
- Ask before a NUC command that the user would not normally expect as part of the documented migration.
- Always ask before formatting, repartitioning, erasing data, changing the NUC's production network identity, or taking an unexpected destructive or materially out-of-scope action.
- Never let a local Lenovo command look like a NUC command.

## Access And Last-Known State

- SSH alias: `pve-nuc`
- Last-known hostname and Proxmox node: `pve-nuc`
- Last-known production LAN address: `192.168.1.184/24`
- Last-known bridge: `vmbr0`, with bridge port `nic0`
- Last verified: Proxmox VE `9.2.3`, Debian 13, kernel `7.0.6-2-pve`
- Last verified storage: active `local`, `local-lvm`, and guarded `usb-backup`
- Last verified guests: VM `100` and CTs `101` through `108`; CTs `101` and `103` stopped, all others running
- Last verified devices: USB backup HDD, SONOFF coordinator, `/dev/dri/card0`, `/dev/dri/renderD128`, and `/dev/net/tun`

These are orientation facts, not current truth. Reverify before acting.

## Start Protocol

1. Read `/root/server-admin/notes/migrations/lenovo-to-nuc/README.md` and the relevant phase doc on the Lenovo/repo side.
2. Ask what the user changed manually since the last session.
3. Run expected read-only NUC checks through `ssh pve-nuc`.
4. Summarize the results and any mismatches.
5. Compare live state with docs and summarize mismatches before changes.
6. Run expected documented migration changes; ask before unexpected or high-impact actions.
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
- Avoid nested `ssh pve-nuc bash -lc "..."` quoting when a simple SSH command or stdin pipe can perform the operation. Nested quoting was reparsed unexpectedly during the HDD fstab setup even though the append portion still succeeded.
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

- The NUC is the production host at `pve-nuc` / `192.168.1.184`.
- The retired Lenovo remains `proxmox` / `192.168.1.186`; never move it back to `.184` without a separately planned cutover.
- Do not format, repartition, initialize, or erase the USB HDD.
- Before adding `usb-backup`, verify the HDD by filesystem UUID and mount it at `/mnt/proxmox-usb-backup`.
- Configure `usb-backup` with `is_mountpoint 1`; never point it at an unmounted directory.
- Reverify NUC device paths instead of copying Lenovo paths. In particular, the NUC iGPU was observed as `card0`, while Lenovo-era docs may mention `card1`.
- Verify the SONOFF Zigbee coordinator by USB ID `10c4:ea60` before starting Home Assistant.
- Verify `/dev/net/tun` before starting CT `106` or CT `107`.
- Restore and validate guests in the order documented in `phase-5-guest-restore.md`.

## Change And Verification Pattern

For each requested NUC change:

1. Confirm it is an expected part of the documented migration.
2. Tell the user what meaningful change is being made.
3. Run it through `ssh pve-nuc`.
4. Run read-only verification.
5. Report actual state and mismatches.
6. Ask before any unexpected, destructive, identity-changing, or materially out-of-scope action.
7. Update `/root/server-admin/notes/migrations/lenovo-to-nuc/cutover-log.md`.

Never store secrets from restored guests or host configuration in Git or chat.
