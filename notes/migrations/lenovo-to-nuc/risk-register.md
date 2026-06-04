# Lenovo To NUC Migration Risk Register

This file tracks known migration risks and the required mitigation. It is not a detailed status ledger; agents should verify live state before acting.

## Risks

| Risk | Why It Matters | Mitigation |
| --- | --- | --- |
| USB HDD mount failure | The same disk contains guest backups, host backups, live media-stack data, and media-stack config. | Mount by UUID `9218d3f8-9449-4221-9dd8-36b5b7884152`; keep `usb-backup` guarded by `is_mountpoint 1`; verify before restores. |
| Live media and backup data share one disk | File-backup snapshots are useful rollback points but not a separate hardware backup. | Treat USB HDD as critical; do not format it; keep Home Assistant off-box backup enabled; consider later separate backup storage. |
| Host IP takeover | The NUC and Lenovo cannot both safely own `192.168.1.184` at the same time. | Use a staging IP until cutover or shut down/disconnect the Lenovo before the NUC takes over the final identity. |
| NUC NIC name differs | Lenovo bridge used a USB Ethernet interface name that will not match the NUC. | Verify `ip link` and update `vmbr0` bridge port for the NUC interface. |
| Zigbee USB passthrough | Home Assistant depends on SONOFF `10c4:ea60` if ZHA is in use. | Verify `lsusb` and `qm config 100`; confirm `/dev/ttyUSB0` inside Home Assistant after restore. |
| Intel iGPU path changes | Jellyfin CT `104` used Lenovo-era `/dev/dri/renderD128` and `/dev/dri/card1`. | Verify `/dev/dri` on the NUC before reapplying CT device passthrough. |
| `/dev/net/tun` unavailable | CT `106` Gluetun and CT `107` Tailscale need TUN. | Verify host TUN and LXC config before starting those containers. |
| DHCP/static lease mismatch | Several services are documented by stable LAN IPs even when guest configs use DHCP. | Verify actual IPs after restore before changing service catalog or dashboard files. |
| Secrets are not in Git | VPN, Tailscale, API keys, app credentials, and monitoring tokens may need manual re-entry or restored guest state. | Document secret locations only; use existing guest backups where possible; do not commit values. |
| CT `103` is stale | It has the same hostname role as Jellyfin but is not the active service. | Restore only as reference if desired; do not rely on it for active Jellyfin. |
| FileBrowser backup mount uses resolved snapshot | Proxmox does not hotplug bind mounts through the `current` symlink. | Re-resolve the latest snapshot path before restoring CT `106` backup browse mount. |
| Monitoring token restoration | CT `108` Proxmox exporter uses a token stored only inside the CT. | Prefer restoring CT `108`; if recreated, rotate/recreate a read-only PVE token and store it only in CT secrets. |

## Do Not Touch Without Asking

- Do not format or repartition the USB HDD.
- Do not delete CT `103`.
- Do not expose LAN services publicly.
- Do not commit raw inventory dumps, backup archives, app databases, private keys, provider credentials, Tailscale auth keys, or `/etc/pve/priv/*`.
- Do not change service IPs, ports, or dashboard catalog entries without verifying live state and confirming intent.
