---
name: homelab-grafana
description: Operate, troubleshoot, create, split, and deploy Grafana dashboards for this Proxmox homelab monitoring stack in CT 108. Use for Grafana panel or PromQL changes, dashboard JSON and layout work, Home Assistant versus server-infrastructure organization, provisioning failures, missing metrics, dashboard deployment, and monitoring documentation updates.
---

# Homelab Grafana

Work from `/root/server-admin`. Treat repo dashboard JSON as desired state and
CT `108` runtime files as deployed state.

## Ground Truth

- Active Proxmox host: `pve-nuc` (`192.168.1.184`). Use `ssh pve-nuc` from
  the retired Lenovo workspace.
- Monitoring CT: `108` (`192.168.1.200`), runtime root `/opt/monitoring`.
- Grafana: `http://192.168.1.200:3000`; Prometheus:
  `http://192.168.1.200:9090`.
- Repo dashboards: `monitoring/grafana/dashboards/`.
- Runtime dashboards: `/opt/monitoring/grafana/dashboards/` inside CT `108`.
- Provisioner: `monitoring/grafana/provisioning/dashboards/dashboards.yml`;
  folder `Homelab`, file refresh `60s`, UI edits disabled.
- Current dashboard UIDs:
  - `home-overview`: Home Assistant comfort, battery, presence, security,
    chores, and availability.
  - `server-infrastructure`: host, storage, guests, and scrape pipeline.
  - `albumary-website`: public site and Cloudflare metrics.
- Grafana credentials and Home Assistant/Proxmox tokens exist only under
  `/opt/monitoring/secrets/` in CT `108`. Never print or copy them into Git.
- CT `108` does not have `jq`; validate JSON in the repo workspace.

## Start Every Task

1. Read `AGENTS.md`, `notes/monitoring-runbook.md`, and the dashboard JSON being
   changed. Read `notes/documentation-maintenance.md` before edits.
2. Run `git status --short`; preserve unrelated work and never inspect `.env`.
3. Compare repo and runtime checksums before changing a live dashboard:

```bash
sha256sum monitoring/grafana/dashboards/*.json
ssh pve-nuc "pct exec 108 -- sha256sum /opt/monitoring/grafana/dashboards/*.json"
```

4. Confirm the stack before mutations:

```bash
ssh pve-nuc "pct exec 108 -- bash -lc 'cd /opt/monitoring && docker compose ps'"
curl -fsS http://192.168.1.200:3000/api/health
curl -fsS http://192.168.1.200:9090/-/ready
```

If repo and runtime differ, identify whether the runtime file is an intentional
hotfix before replacing it. Preserve it with a suffix that does not end in
`.json`, such as `.pre-change-YYYYMMDD`; Grafana would provision a backup that
still ends in `.json`.

## Edit Efficiently

- Preserve a dashboard UID unless the user intends a new dashboard. Grafana
  uses the UID in URLs and cross-dashboard links.
- Use unique numeric panel IDs and keep every panel inside Grafana's 24-column
  grid. Reflow panels deliberately after splitting or deleting panels.
- Keep Home Assistant panels in `home-overview` and Proxmox/server panels in
  `server-infrastructure`. Keep Albumary website analytics separate.
- Keep dashboard variables only when a remaining panel references them.
- Use `/d/<uid>` for cross-dashboard links and `keepTime: true` when comparison
  across dashboards benefits from the same time range.
- Copy existing panel JSON when possible so datasource UIDs, field options,
  units, thresholds, and legend conventions remain consistent.
- Use datasource UID `prometheus`. Prefer explicit PromQL job/entity filters;
  avoid unbounded high-cardinality queries.
- Inspect metric names quickly with repo search and Prometheus:

```bash
grep -Rni 'metric_or_panel_text' monitoring home-assistant scripts
curl -fsSG http://192.168.1.200:9090/api/v1/query \
  --data-urlencode 'query=up'
```

Use `scripts/check-dashboards.py` before deployment. Pass specific files while
iterating or omit arguments to validate every repo dashboard:

```bash
python3 skills/homelab-grafana/scripts/check-dashboards.py \
  monitoring/grafana/dashboards/home-overview.json
python3 skills/homelab-grafana/scripts/check-dashboards.py
```

## Deploy

Use the bundled helper for normal dashboard-only changes. It validates locally,
copies files through `pve-nuc`, keeps a runtime backup, restarts only Grafana,
checks provisioning logs, and verifies each UID through Grafana's API without
printing credentials:

```bash
skills/homelab-grafana/scripts/deploy-dashboards.sh \
  monitoring/grafana/dashboards/home-overview.json
```

To retire a provisioned dashboard while deploying replacements, provide its
runtime filename. The helper moves it to a dated non-JSON backup rather than
deleting it:

```bash
skills/homelab-grafana/scripts/deploy-dashboards.sh \
  --retire homelab-overview.json \
  monitoring/grafana/dashboards/home-overview.json \
  monitoring/grafana/dashboards/server-infrastructure.json
```

Do not use this helper when Compose, provisioning, datasources, Prometheus, or
secrets also change; follow the monitoring runbook and validate that broader
change explicitly.

## Diagnose

- Missing dashboard: compare repo/runtime files, inspect the provisioning YAML,
  then search recent Grafana logs for `provision`, `error`, or `failed`.
- Empty panel: query the exact PromQL in Prometheus, check the relevant target
  under `/api/v1/targets`, then verify labels rather than weakening filters
  blindly.
- Missing Home Assistant data: check job `home-assistant` and the focused export
  in `home-assistant/prometheus_package.yaml`.
- Missing host or guest data: check jobs `node-exporter` and `pve` respectively.
- Grafana unhealthy after a dashboard-only change: restore the dated runtime
  backup, remove or move aside the new file, restart Grafana, and inspect logs.

## Finish

1. Verify the dashboard appears in Grafana's `Homelab` folder and its key panels
   return data for the intended time range.
2. Update `README.md`, `notes/monitoring-runbook.md`, and
   `notes/proxmox-media-inventory.md` when dashboard names, roles, UIDs, runtime
   paths, exporters, or monitoring architecture change.
3. Run the validator, `git diff --check`, and a secret-oriented diff review.
4. Commit only task files with a focused message. Do not stage `.env` or
   unrelated work.
