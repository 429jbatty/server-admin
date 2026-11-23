# Albumary observability

CT `109` (`albumary-observability`, `192.168.1.201`) runs native Loki and nginx. CT `108` provides the central Grafana UI. Production CT `105` runs native Alloy to collect the two Albumary systemd journals.

- Grafana: `http://192.168.1.200:3000`, served by CT `108`, provisions `Albumary Loki` with UID `albumary-loki` and an `Albumary` dashboard folder. Grafana credentials stay only in CT `108`; do not put them in Git.
- Loki: `192.168.1.201:3100`; nginx permits CT `105` (`192.168.1.100`), CT `108` (`192.168.1.200`), and the development machine (`192.168.1.67`). Loki uses loopback port 3101. Update nginx's allowlist if authorized client IPs change; validate with `nginx -t` and reload.
- Native service status: `pct exec 109 -- systemctl status loki nginx` and `pct exec 105 -- systemctl status alloy`. Check the Grafana Docker service in CT `108` and application health and worker timer on CT `105` independently.
- Data: Loki `/var/lib/loki`, production Alloy state `/var/lib/alloy`, persistent journal `/var/log/journal` on CT 105. Loki retention defaults to 30 days, with development streams retained for 3 days. Journal size is capped at 512 MiB subject to free-space limits.
- Resource allocation: 2 cores, 1536 MiB RAM, 512 MiB swap, 20 GiB local-lvm root disk. Check usage and capacity periodically. Guest config backup before enabling nesting is `/root/albumary-observability-backups/109-before-nesting.conf` on the NUC.
- The `albumary-operations` dashboard is provisioned read-only from CT `108`'s `/opt/monitoring/grafana/albumary-dashboards/albumary-operations.json` into the `Albumary` folder. Update it from an Albumary checkout using `deploy/observability/update-dashboard.sh pve-nuc 108`; Grafana polls every 30 seconds. The script lives in the Albumary checkout and requires SSH access to the Proxmox host; it stores no credentials. Verify the dashboard and provisioning status in Grafana.
- Configuration source, installation, updates, log queries, and validation: Albumary repository `deploy/observability/README.md`. Runtime endpoints, credentials, data, and state remain outside that repository.
- No historical log backups are required; normal Proxmox guest backup policy may still include the container. Loki uses local disk and has no disk-full protection.
