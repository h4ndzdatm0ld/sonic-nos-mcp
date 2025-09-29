# Techsupport Scenario Index

This directory holds the collected troubleshooting bundles for the latest SONiC lab runs. Each archive name reflects the fault that was induced before `show techsupport` was executed. The table below spells out what to look for in each tarball once you unpack it (or browse it with `tar`/`python -m tarfile`). The listed evidence paths use the archive-internal layout that `show techsupport` generates.

| Archive | Scenario recap | Where to look | What to confirm | Expected root-cause statement |
|---------|----------------|---------------|-----------------|------------------------------|
| `techsupport_bgp_md5.tar.gz` | BGP peering on `sonic1` was forced into an MD5 password mismatch against neighbor `10.255.0.2` before the capture. | • `dump/bgp_summary` – neighbor stuck in `Active`/`Connect`<br>• `dump/CONFIG_DB.json` – `BGP_NEIGHBOR|10.255.0.2` carries `auth_type: md5` with the bogus secret<br>• `log/syslog*.gz` – `Neighbor ... Inactive` and password mismatch syslog lines | Confirms the session never established due to MD5 auth failures and shows the misconfigured secret that triggered the symptoms. | “BGP session down because `sonic1` has the wrong MD5 password configured for neighbor 10.255.0.2.” |
| `techsupport_syncd_crash.tar.gz` | `docker kill syncd` triggered the ASIC pipeline container crash loop. Techsupport was taken while `syncd` was recovering. | • `dump/docker.ps` – `syncd` uptime just a few seconds when captured<br>• `dump/syslog` and `log/syslog*.gz` – `syncd` exit/crash traces<br>• `dump/saidump` – empty or truncated because `syncd` was restarting | Verifies `syncd` had been terminated and restarted, with supporting crash logs and short container uptime. | “Forwarding dataplane unstable due to `syncd` container crash/restart cycle on sonic1.” |
| `techsupport_oom.tar.gz` | Aggressive memory ballooning inside `swss` triggered host-level panic-on-OOM, leading to rapid container restarts and multiple reboots immediately prior to the dump. | • `dump/reboot.cause.history` – run of back-to-back `Unknown` reboots at `15:52–16:01` after the stress test<br>• `dump/docker.ps` / `dump/docker.stats` – infrastructure services recently restarted (uptime only a few minutes)<br>• `etc/sysctl.conf` – `vm.panic_on_oom = 2` explains why the kernel reboots instead of logging the kill<br>• `log/syslog.1.gz` – warm-start/port init spam right after the enforced reboot | Shows the memory exhaustion side effects: repeated host reboots, freshly restarted containers, and configuration that converts OOM into a system panic (hiding classic `oom-killer` lines). | “Host rebooted repeatedly because OOM panic (vm.panic_on_oom=2) was hit during swss memory exhaustion.” |

## How to inspect without unpacking everything

```bash
python3 - <<'PY'
import tarfile, gzip
with tarfile.open('techsupport/techsupport_oom.tar.gz', 'r:gz') as tar:
    data = tar.extractfile('sonic_dump_sonic1_20250928_160443/dump/reboot.cause.history').read()
    print(data.decode())
PY
```

## Example LLM discovery prompt

> You have access to `techsupport/techsupport_oom.tar.gz`, collected right after a lab-induced memory exhaustion on SONiC node `sonic1`. Please extract only the evidence needed to explain why the box rebooted repeatedly around 15:52–16:01 UTC. Look for:
> * configuration or sysctl settings that change OOM handling
> * logs that indicate memory pressure or kernel panic
> * container/service uptimes that corroborate a recent restart
> Summarise the root cause and list the supporting file paths inside the archive (keep the output under 250 words).

Feel free to tweak the prompt to target the other bundles—replace the archive name and adjust the bullet list to the scenario under investigation.

## Example evaluation prompt

> Field engineers reported intermittent packet drops on `sonic1`, so they grabbed `techsupport/techsupport_oom.tar.gz` during the incident window. Review the bundle and explain what was happening on the box around the capture time, including any contributing configuration or platform conditions. Keep the response concise and cite the internal file paths you rely on.

## Scenario prompts

- `techsupport_bgp_md5.tar.gz`: “A routing peer at `10.255.0.2` keeps flapping against `sonic1`. Inspect this tech-support archive and tell me why the session won’t stay established, pointing to the evidence you use.”
- `techsupport_syncd_crash.tar.gz`: “ASIC programming keeps failing on `sonic1`. Use this tech-support bundle to determine what was happening to the forwarding pipeline when the snapshot was taken, and cite relevant files.”
- `techsupport_oom.tar.gz`: “Control-plane services on `sonic1` restarted unexpectedly. Review this tech-support archive and describe the platform conditions around the capture, including any configuration that influenced the behavior. Reference the file paths you rely on.”
