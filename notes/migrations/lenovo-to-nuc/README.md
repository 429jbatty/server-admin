# Lenovo To NUC Migration

This directory is the permanent runbook for moving the homelab from the Lenovo Proxmox host to the Intel NUC. It is designed for piecemeal work across human and agent sessions.

The docs are the safety contract and checklist. They are not the live status source of truth. Before acting, verify the live state with read-only checks.

## Agent Start Protocol

Every agent session must begin here:

1. Read this file and the phase document for the requested work.
2. Ask the user what they already did manually, if anything.
3. Run read-only checks against the current machine before changing anything.
4. Compare expected state with actual state.
5. If chat, docs, and live state disagree, summarize the mismatch before acting.
6. Act only on the next safe chunk the user requested.

Live state wins only after read-only verification. Do not rely on memory from earlier sessions.

## Migration Order

1. [Phase 1: Inventory](phase-1-inventory.md)
2. [Phase 2: Backups](phase-2-backups.md)
3. [Phase 3: NUC Base Install](phase-3-nuc-base-install.md)
4. [Phase 4: Storage And Devices](phase-4-storage-devices.md)
5. [Phase 5: Guest Restore](phase-5-guest-restore.md)
6. [Phase 6: Validation](phase-6-validation.md)

Supporting docs:

- [Risk Register](risk-register.md)
- [Cutover Log](cutover-log.md)
- Inventory task source: `../../../lenovo_proxmox_migration_inventory_task.md`

## Ground Rules

- Do not perform migration changes until the relevant phase doc has been read.
- Do not assume a step is complete because a previous chat said so; verify it.
- Do not commit raw inventory dumps, secrets, app databases, private keys, provider credentials, Tailscale auth keys, or `/etc/pve/priv/*`.
- Keep services LAN-only unless a separate exposure plan exists.
- Keep CT `104` focused on Jellyfin.
- Keep media automation services in CT `106`.
- Preserve the no-secrets boundary by documenting secret locations, not values.

## Default Migration Assumptions

- The NUC will take over the existing Proxmox LAN identity unless the user changes the plan:
  - Hostname: `proxmox`
  - Host IP: `192.168.1.184/24`
  - Gateway: `192.168.1.254`
  - Bridge: `vmbr0`
- The first migration pass keeps the existing USB HDD as the live media and backup disk.
- The USB HDD mountpoint remains `/mnt/proxmox-usb-backup`.
- The Proxmox storage ID remains `usb-backup`.
- Restore scope defaults to VM `100` and CTs `101` through `108`, including stopped CT `101` and stale CT `103`, unless the user explicitly drops them.

## Canonical Repo References

- Repo overview: `../../../README.md`
- Documentation contract: `../../documentation-maintenance.md`
- Architecture overview: `../../homelab-overview.md`
- Proxmox inventory: `../../proxmox-media-inventory.md`
- Backup runbook: `../../homelab-backup-runbook.md`
- Media stack runbook: `../../media-stack-runbook.md`
- Monitoring runbook: `../../monitoring-runbook.md`
- Service catalog: `../../../homelab-services.yml`

## When To Update Other Docs

Do not update the main operational docs just because a plan exists. Update them after migration execution changes ground truth.

Update `homelab-services.yml`, Home Assistant dashboard/package files, and relevant runbooks if service IPs, ports, owners, health checks, host paths, backup schedules, mount points, or monitoring targets change.
