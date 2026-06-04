# Lenovo To NUC Cutover Log

This file is agent-maintained by default. The user does not need to keep it current by hand.

Use it for concise notes after verified work or discovered mismatches. Do not store secrets, raw dumps, private keys, app databases, or backup archive contents here.

## Entry Format

```text
Date:
Actor:
Phase:
What was checked or changed:
Evidence:
Next safe action:
```

## Entries

Date: 2026-06-01
Actor: Agent
Phase: Phase 3 / Phase 4 preflight
What was checked or changed: Ran approved read-only SSH preflight against `pve-nuc`.
Evidence: NUC is reachable as hostname `pve-nuc` at `192.168.1.185/24`, running Proxmox VE `9.2.3` on Debian 13 with kernel `7.0.6-2-pve`. Storage currently has `local` and `local-lvm`; `usb-backup` is not configured. No VMs or LXCs are present. `/dev/dri/card0`, `/dev/dri/renderD128`, and `/dev/net/tun` exist. `/mnt/proxmox-usb-backup` is not mounted. `lsusb` shows a Logitech receiver and Intel Bluetooth, but not the Seagate USB HDD or SONOFF Zigbee coordinator.
Next safe action: Verify and create fresh Lenovo-side backups before moving the USB HDD or restoring guests.

Date: 2026-06-01
Actor: Agent
Phase: Phase 2 backup readiness
What was checked or changed: Ran approved read-only Lenovo-side backup readiness checks.
Evidence: `usb-backup` is active in Proxmox and the daily backup job `homelab-usb-daily` is enabled for all guests at `02:30`. VM `100` is running; CTs `102`, `104`, `105`, `106`, `107`, and `108` are running; CTs `101` and `103` are stopped. Latest visible guest backups, host-config backup, media-stack file snapshot, and Albumary SQLite backup are from 2026-05-31. The USB HDD is mounted at `/mnt/proxmox-usb-backup` but currently shows read-only mount options.
Next safe action: Diagnose why `/mnt/proxmox-usb-backup` is mounted read-only before running fresh migration backups.

Date: 2026-06-01
Actor: Agent
Phase: Phase 2 backup readiness
What was checked or changed: Ran approved read-only diagnostics for the read-only USB backup mount.
Evidence: `/etc/fstab` mounts UUID `9218d3f8-9449-4221-9dd8-36b5b7884152` at `/mnt/proxmox-usb-backup` with `defaults,noatime,nofail,x-systemd.device-timeout=10`, not an explicit read-only option. `/etc/pve/storage.cfg` defines `usb-backup` with `is_mountpoint 1`. `findmnt` still reports `/dev/sda1 ext4 ro,nosuid,nodev,noatime`, but `lsblk -f /dev/sda` reports `/dev/sda` is not a block device and `blkid /dev/sda1` returns no device data. Backup services last completed successfully on 2026-05-31. Recent kernel log output reviewed did not show an obvious ext4 remount error in the captured tail.
Next safe action: Confirm whether the USB HDD is physically connected to the Lenovo, inspect current block devices, and decide whether to remount/reconnect before running fresh backups.

Date: 2026-06-01
Actor: Agent
Phase: Phase 2 backup readiness
What was checked or changed: Rechecked physical USB HDD visibility after user confirmed it is plugged into the Lenovo.
Evidence: `lsblk -f` now shows `/dev/sda1` as ext4 label `HOMELAB_BACKUP`, UUID `9218d3f8-9449-4221-9dd8-36b5b7884152`, mounted at `/mnt/proxmox-usb-backup` with about 3.4T available. `lsusb` shows Seagate RSS LLC Portable device `0bc2:2344`. `findmnt` still shows the mount as read-only. `/dev/disk/by-uuid/` was not present in this shell environment.
Next safe action: Diagnose why the present ext4 filesystem is mounted read-only before running fresh migration backups.

Date: 2026-06-03
Actor: Agent
Phase: Phase 2 backup recovery and verification
What was checked or changed: Recovered from the failed CT `108` backup, removed its incomplete temporary backup directory, retried the CT-only snapshot backup, and verified Phase 2 backup readiness.
Evidence: Host-namespace checks confirmed `/dev/sda1` is mounted at `/mnt/proxmox-usb-backup` as `rw,noatime`; earlier read-only observations came from the restricted agent shell rather than the host mount namespace. The stale `vzdump` snapshot had already been removed and no backup process was active. The retry created `/mnt/proxmox-usb-backup/dump/vzdump-lxc-108-2026_06_03-22_52_11.tar.zst`, completed successfully, and passed `zstd -t`. `pct listsnapshot 108` shows only `current`. Proxmox lists fresh 2026-06-03 guest backups for VM `100` and CTs `101` through `108`; supporting host-config, media-stack file, and Albumary SQLite backups also exist from 2026-06-03.
Next safe action: Complete the reviewed Phase 3 NUC staging checks, confirm the planned cutover identity, and make the repo and host-level service sources available on the NUC before moving the USB HDD or restoring guests.

Date: 2026-06-03
Actor: Agent
Phase: Phase 3 NUC base install
What was checked or changed: Reverified the NUC staging host, installed required utilities, copied the clean server-admin repo from the Lenovo, and installed repo-backed host scripts and systemd units without enabling or starting them.
Evidence: `pve-nuc` remains reachable at staging address `192.168.1.185/24` with `vmbr0` bridged to `nic0`, Proxmox VE `9.2.3`, active `local` and `local-lvm` storage, and no guests. Installed `git`; `rsync` and `sqlite3` were already present. `/root/server-admin` is clean on branch `master` at commit `1574c88`. Backup scripts are installed under `/usr/local/sbin`; backup timers and the metrics exporter unit are installed under `/etc/systemd/system`. `systemd-analyze verify` passed, all newly installed units remain disabled and inactive, and `pveproxy` remains active. The USB HDD is not connected and `usb-backup` is intentionally not configured yet.
Next safe action: Complete final read-only Phase 3 reachability and host-capacity checks, keep the NUC on its staging identity while the Lenovo is live, then begin the reviewed Phase 4 physical storage and device move.

Date: 2026-06-03
Actor: Agent
Phase: Phase 3 NUC base install completion
What was checked or changed: Synced the latest migration checkpoint to the NUC and completed final read-only Phase 3 reachability, capacity, service-health, and repo checks.
Evidence: The Proxmox API at `https://192.168.1.185:8006` returned expected unauthenticated HTTP `401`, confirming reachability. The NUC resolves as `pve-nuc.home` at `192.168.1.185`; `pveproxy`, `pvedaemon`, and `pvestatd` are active. It has an Intel i7-10710U with 12 logical CPUs, 15 GiB RAM, about 84 GiB free on the root filesystem, and an empty approximately 349 GiB `local-lvm` thin pool. `/root/server-admin` is clean at commit `9d9d0ce`. Phase 3 is complete with the NUC intentionally retaining its staging identity and with `usb-backup` deferred until the HDD is mounted during Phase 4.
Next safe action: Prepare for Phase 4 by safely stopping Lenovo services and guests that use the USB HDD, unmounting the HDD, physically moving the HDD and required USB devices to the NUC, and then running reviewed NUC device checks before configuring storage or restoring guests.

Date: 2026-06-03
Actor: Agent
Phase: Phase 4 Lenovo storage and device cutover
What was checked or changed: Quiesced Lenovo workloads and schedules that use the USB HDD or cutover devices, then safely unmounted the HDD.
Evidence: Disabled Proxmox backup job `homelab-usb-daily`; disabled and stopped the host backup timers and Lenovo metrics exporter. VM `100`, CT `104`, and CT `106` shut down cleanly. No `vzdump`, `tar`, `zstd`, or `rsync` backup process was active. After `sync` and `umount /mnt/proxmox-usb-backup`, `findmnt` returned no mount, `lsblk -f` showed filesystem UUID `9218d3f8-9449-4221-9dd8-36b5b7884152` with no mountpoint, and Proxmox marked `usb-backup` inactive because its guarded mountpoint is absent.
Next safe action: Physically move the Seagate USB HDD and SONOFF Zigbee coordinator from the Lenovo to the NUC, then run the reviewed NUC read-only device discovery checks before mounting or configuring anything.

Date: 2026-06-03
Actor: Agent
Phase: Phase 4 NUC storage and device setup
What was checked or changed: Discovered the moved devices, mounted the existing USB HDD by UUID, and registered it as guarded Proxmox storage `usb-backup`.
Evidence: The NUC sees the Seagate HDD as `/dev/sda1`, ext4 label `HOMELAB_BACKUP`, UUID `9218d3f8-9449-4221-9dd8-36b5b7884152`. It is mounted at `/mnt/proxmox-usb-backup` as `rw,noatime` with about 3.4 TiB free; all expected backup and media directories exist. `/etc/fstab` contains exactly one proven UUID-based mount entry. Proxmox reports `usb-backup` active with `is_mountpoint 1` and can enumerate existing backups for VM `100` and CTs `101` through `108`. The SONOFF coordinator is visible as USB ID `10c4:ea60` and stable path `/dev/serial/by-id/usb-SONOFF_SONOFF_Dongle_Lite_MG21_2c1766ef5fa2ef11baaf8a6661ce3355-if00-port0`. NUC device paths are `/dev/dri/card0`, `/dev/dri/renderD128`, and `/dev/net/tun`; `vmbr0` remains bridged to `nic0`.
Next safe action: Complete final read-only Phase 4 checks, sync the latest repo checkpoint to the NUC, then begin Phase 5 restores without starting a restored guest until its Lenovo counterpart is stopped.

Date: 2026-06-03
Actor: Agent
Phase: Phase 4 completion
What was checked or changed: Completed final NUC storage, device, media-path, guest-inventory, and repo verification.
Evidence: `usb-backup` remains active and guarded by `is_mountpoint 1`; the HDD remains mounted `rw,noatime`. The latest media-stack file snapshot resolves to `/mnt/proxmox-usb-backup/file-backups/srv-media-stack/snapshots/20260603-015205`, and the live `library`, `downloads`, and `config` directories exist. The Seagate HDD, SONOFF coordinator, NUC iGPU, TUN device, and `vmbr0` bridge remain visible. The NUC has no VMs or LXCs yet and its repo is clean at commit `86b1261`. Phase 4 is complete.
Next safe action: Begin Phase 5 by restoring guests in dependency order while stopped, then stop each still-running Lenovo counterpart before starting and validating it on the NUC.

Date: 2026-06-03
Actor: Agent
Phase: Phase 5 guest restore - CT 102 AdGuard
What was checked or changed: Restored CT `102` to the NUC while stopped, then handed AdGuard service ownership from Lenovo to NUC.
Evidence: The selected archive `/mnt/proxmox-usb-backup/dump/vzdump-lxc-102-2026_06_03-02_32_06.tar.zst` passed `zstd -t`. Restored CT `102` preserved the original MAC and DHCP configuration. Lenovo CT `102` was shut down and set to `onboot=0` before the NUC copy started. NUC CT `102` is running at `192.168.1.189`; `AdGuardHome` is active and HTTP returned expected status `302`.
Next safe action: Restore VM `100` Home Assistant to the NUC while stopped, verify its configuration includes the moved SONOFF USB device, then start and validate it without restarting the stopped Lenovo copy.

Date: 2026-06-03
Actor: Agent
Phase: Phase 5 guest restore - VM 100 Home Assistant
What was checked or changed: Restored VM `100` Home Assistant to the NUC while stopped, verified its configuration, then started and validated it.
Evidence: The selected archive `/mnt/proxmox-usb-backup/dump/vzdump-qemu-100-2026_06_03-02_30_09.vma.zst` passed `zstd -t`. Restored VM `100` preserved its original MAC and `usb0: host=10c4:ea60` SONOFF passthrough. The Lenovo VM was already stopped. NUC VM `100` is running; the guest agent responds, reports IPv4 `192.168.1.187`, and Home Assistant returned HTTP `200` at port `8123`.
Next safe action: Confirm Zigbee functionality in the Home Assistant UI when convenient, then restore CT `107` Tailscale while stopped and hand off service ownership from the still-running Lenovo copy.

Date: 2026-06-03
Actor: Agent
Phase: Phase 5 guest restore - CT 107 Tailscale
What was checked or changed: Restored CT `107` to the NUC while stopped, then handed Tailscale subnet-router ownership from Lenovo to NUC.
Evidence: The selected archive `/mnt/proxmox-usb-backup/dump/vzdump-lxc-107-2026_06_03-02_36_21.tar.zst` passed `zstd -t`. Restored CT `107` preserved its original MAC, DHCP configuration, and `/dev/net/tun` passthrough. Lenovo CT `107` was shut down and set to `onboot=0` before the NUC copy started. NUC CT `107` is running at `192.168.1.198`, has `net.ipv4.ip_forward = 1`, and retained Tailscale identity `100.103.90.53`.
Next safe action: Restore CT `104` Jellyfin while stopped, change its restored Lenovo-era `/dev/dri/card1` passthrough to the NUC `/dev/dri/card0` path, then start and validate Jellyfin and media mounts.

Date: 2026-06-03
Actor: User
Phase: Migration workflow
What was checked or changed: Changed the NUC command-approval rule for the remainder of the migration.
Evidence: Expected NUC commands that directly implement or verify the documented migration may run without per-batch approval. Agents must still ask before unexpected, destructive, identity-changing, formatting, repartitioning, erasing, or materially out-of-scope NUC actions.
Next safe action: Continue Phase 5 guest restores using the updated command-approval rule.

Date: 2026-06-04
Actor: Agent
Phase: Phase 5 guest restore - CT 104 Jellyfin
What was checked or changed: Restored CT `104` Jellyfin to the NUC while stopped, replaced its Lenovo-era iGPU card path, then started and validated it.
Evidence: The selected archive `/mnt/proxmox-usb-backup/dump/vzdump-lxc-104-2026_06_03-02_32_31.tar.zst` passed `zstd -t`. Before adjustment, the restored config used `/dev/dri/card1`; a config backup was saved on the NUC and `dev1` was changed to NUC path `/dev/dri/card0` with GID `44`. `renderD128` remains GID `993`. NUC CT `104` is running at `192.168.1.191`; `jellyfin` is active, media movie/TV paths resolve, both iGPU devices are visible inside the container, and HTTP returned expected status `302`.
Next safe action: Restore CT `106` media stack while stopped, verify and refresh its HDD bind mounts and TUN device, then start and validate Docker services.

Date: 2026-06-04
Actor: Agent
Phase: Phase 5 guest restore - CT 106 media stack
What was checked or changed: Restored CT `106` to the NUC while stopped, refreshed its read-only media snapshot browse mount, then started and validated the media stack.
Evidence: The selected archive `/mnt/proxmox-usb-backup/dump/vzdump-lxc-106-2026_06_03-02_34_17.tar.zst` passed `zstd -t`. A restored-config backup was saved on the NUC, then `mp2` was refreshed from the historical May 12 snapshot to `/mnt/proxmox-usb-backup/file-backups/srv-media-stack/snapshots/20260603-015205/library`. NUC CT `106` is running at `192.168.1.197`; live media, downloads, guest backup, latest media snapshot, and TUN paths resolve. All nine Docker Compose services are running, and expected LAN endpoints returned successful or expected redirect responses.
Next safe action: Restore CT `105` Albumary while stopped, hand off ownership from the still-running Lenovo copy, then validate its database and service.

Date: 2026-06-04
Actor: Agent
Phase: Phase 5 guest restore - CT 105 Albumary
What was checked or changed: Restored CT `105` to the NUC while stopped, then handed Albumary ownership from Lenovo to NUC.
Evidence: The selected archive `/mnt/proxmox-usb-backup/dump/vzdump-lxc-105-2026_06_03-02_33_04.tar.zst` passed `zstd -t`. The restored config preserved static address `192.168.1.100/24` and its original MAC. Lenovo CT `105` was stopped before the NUC copy started. NUC CT `105` is running at `192.168.1.100`; `/opt/spotify_tracker/data/spotify_tracker.sqlite` is readable and `spotify-tracker-api.service` is active.
Next safe action: Restore CT `108` monitoring while stopped using the recovered fresh manual backup, hand off ownership from the still-running Lenovo copy, then validate Grafana, Prometheus, and Uptime Kuma.

Date: 2026-06-04
Actor: Agent
Phase: Phase 5 guest restore - CT 108 monitoring
What was checked or changed: Restored CT `108` to the NUC while stopped, then handed monitoring-stack ownership from Lenovo to NUC.
Evidence: The recovered archive `/mnt/proxmox-usb-backup/dump/vzdump-lxc-108-2026_06_03-22_52_11.tar.zst` passed `zstd -t`. The restored NUC config matched the Lenovo source config and remained stopped until Lenovo CT `108` was shut down and set to `onboot=0`. NUC CT `108` is running at `192.168.1.200`; Grafana, Prometheus, the PVE exporter, and Uptime Kuma containers are running; Grafana health, Prometheus readiness, and Uptime Kuma returned expected responses. Prometheus reports its configured `prometheus`, `node-exporter`, and `pve` targets as up, but the host targets still point to the Lenovo production identity `192.168.1.184` until the separately approved host-identity cutover.
Next safe action: Restore stopped reference CT `101`, then restore stale CT `103` as stopped reference state without relying on it for Jellyfin.

Date: 2026-06-04
Actor: Agent
Phase: Phase 5 guest restore completion
What was checked or changed: Restored CT `101` and stale CT `103` to the NUC as stopped reference containers, completing the planned guest restore scope.
Evidence: The selected June 3 archives for CT `101` and CT `103` passed `zstd -t`; both Lenovo sources were already stopped; both restored NUC configurations match their sources; and both NUC containers remain stopped. The NUC now contains VM `100` and CTs `101` through `108`. VM `100` and CTs `102`, `104`, `105`, `106`, `107`, and `108` are running; CTs `101` and `103` are stopped. `local`, `local-lvm`, and `usb-backup` are active, with `local-lvm` about 9.4% used.
Next safe action: Begin Phase 6 read-only service validation while the NUC remains on staging identity `pve-nuc` / `192.168.1.185`, then request explicit approval before the production host-identity cutover.

Date: 2026-06-04
Actor: Agent
Phase: Phase 6 staging validation and host protection
What was checked or changed: Validated restored services and devices, restored automatic backups and host metrics on the NUC, synced the current operational repo to the NUC, and smoke-tested the repo-backed backup services.
Evidence: Every HTTP endpoint in `homelab-services.yml` returned its expected success or redirect response. Home Assistant's core configuration check passed; `qm config 100` retains `usb0: host=10c4:ea60`; `lsusb` sees the SONOFF coordinator; Jellyfin, media-stack Compose, monitoring Compose, and Tailscale checks passed. Installed and enabled `prometheus-node-exporter`; enabled `homelab-metrics-exporter.service`; both respond on NUC staging address `192.168.1.185`. Recreated enabled Proxmox job `homelab-usb-daily` for `02:30`; enabled the host-config, media-stack file, and Albumary SQLite backup timers; and manually verified all three backup services completed successfully. Fresh NUC-side host-config, media-stack file, and Albumary SQLite backup artifacts were created on June 4. The NUC repo is clean at commit `f64c312`.
Next safe action: Choose the final host identity approach before changing networking. The safer recommendation is to keep Proxmox node name `pve-nuc` and move only the production IP `192.168.1.184`; an in-place rename to `proxmox` is now higher risk because the NUC node is no longer empty. Recreate the NUC-local monitoring API token at the production-IP cutover, then verify host metrics and remaining application-level checks.

Date: 2026-06-04
Actor: Agent
Phase: Phase 6 production identity cutover
What was checked or changed: Completed the approved host-IP handoff, kept the safer NUC Proxmox node name, recreated NUC-local monitoring authorization, and reconciled canonical operational docs.
Evidence: Rollback copies of both hosts' network and hosts files were created. Lenovo node `proxmox` moved from `192.168.1.184` to retirement address `192.168.1.186`; all Lenovo guests remain stopped and its guest backup job remains disabled. NUC node `pve-nuc` moved from staging address `192.168.1.185` to production address `192.168.1.184`; its guests retained their intended running/stopped states, all storage remains active, and its guest backup job remains enabled. The local `pve-nuc` SSH alias now targets `.184` with a distinct host-key alias. Recreated privilege-separated NUC token `prometheus@pve!monitoring` with `PVEAuditor` ACLs and rotated the secret only inside CT `108`. Prometheus now reports node `pve-nuc`, all expected guests, and active storage at instance `192.168.1.184`; both host exporters report the NUC.
Next safe action: Run final service/catalog validation, sync and back up the completed docs on the NUC, then treat the migration as complete while retaining the Lenovo only as an explicitly managed rollback source.

Date: 2026-06-04
Actor: Agent
Phase: Phase 6 completion
What was checked or changed: Completed final automated validation, synced the final operational repo to the NUC, created a final host-config backup, and created a fresh CT `108` backup after monitoring-token rotation.
Evidence: NUC node `pve-nuc` is active at `192.168.1.184`; `local`, `local-lvm`, and `usb-backup` are active; the HDD is mounted `rw,noatime`; all backup timers, host exporters, and core Proxmox services are active. Home Assistant's core check passed; Tailscale is authenticated; media and monitoring Compose stacks are healthy; and every HTTP endpoint in `homelab-services.yml` returned its expected success or redirect response. Final host-config archive `proxmox-host-config.20260604-102529.tar.zst` exists. Fresh archive `vzdump-lxc-108-2026_06_04-10_25_39.tar.zst` completed successfully, passed `zstd -t`, and left no stale snapshot. Canonical docs and active-host skills were updated at commit `bf51187`.
Next safe action: Treat the migration as complete. Perform the optional human confidence checks in `TODO.md`, then decide how long to retain the powered Lenovo rollback source before repurposing it.
