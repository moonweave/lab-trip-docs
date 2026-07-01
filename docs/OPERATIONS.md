# Operations

## Recommended Setup

Use a lab desktop, mini PC, NAS with Python support, or Linux server that can stay on during collection periods.

Recommended minimum:

- CPU: recent 4-core CPU
- RAM: 8 GB minimum, 16 GB preferred
- Storage: SSD 512 GB or more
- OS: Ubuntu/Linux preferred, Windows acceptable

## Start

```bash
cd lab-trip-docs
export TRIPDOC_ADMIN_PASSWORD='replace-with-a-strong-password'
python -m tripdoc
```

## Access

On the central PC:

```text
http://localhost:8501
```

From another lab computer on the same network:

```text
http://CENTRAL_PC_IP:8501
```

## Backup

Back up the `data/` directory. It contains the SQLite database and uploaded originals.

Good enough for an MVP:

```bash
zip -r lab-trip-docs-backup.zip data
```

For real operation, schedule a daily encrypted backup to a lab NAS or institution-approved storage.

## Off-Campus Access

Avoid public port forwarding. Prefer:

- school VPN
- Tailscale or ZeroTier
- SSH tunnel for trusted admins

