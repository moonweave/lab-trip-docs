# Environment Requirements

This document describes the runtime environment for running Lab Trip Docs on one central lab PC or internal server.

`requirements.txt` is only for Python package dependencies. This file is for the broader operating conditions: Python version, hardware, network, storage, security, and the recommended `uv` setup.

## Recommended runtime

| Item | Recommendation |
|---|---|
| Python | 3.12 recommended, 3.10+ supported by project metadata |
| Package manager | `uv` preferred, `pip` fallback supported |
| OS | Ubuntu/Linux preferred for always-on operation; Windows 10/11 also works |
| CPU | 4-core CPU or better |
| RAM | 8 GB minimum, 16 GB preferred |
| Storage | SSD recommended; start with at least 100 GB free for real document collection |
| GPU | Not required |
| Browser | Chrome, Edge, Firefox, or Safari |
| Network | Same lab LAN/Wi-Fi, school VPN, or private VPN such as Tailscale |
| Port | TCP 8501 inbound to the central PC |

## Python dependencies

Runtime Python packages are listed in `requirements.txt`.

```text
pypdf>=5.0
openpyxl>=3.1
reportlab>=4.0
```

These cover PDF text extraction, Excel export, and PDF summary generation. OCR is not required for the current MVP. Scanned PDFs and image receipts are intentionally kept in the review queue until OCR is added.

## uv-first setup

The repository includes `.python-version` with `3.12`, so `uv` users can keep the central PC environment consistent.

### macOS / Linux

```bash
git clone https://github.com/moonweave/lab-trip-docs.git
cd lab-trip-docs

uv python install 3.12
uv venv --python 3.12
source .venv/bin/activate
uv pip sync requirements.txt

export TRIPDOC_HOST=0.0.0.0
export TRIPDOC_PORT=8501
export TRIPDOC_DATA_DIR=data
export TRIPDOC_ADMIN_USER=admin
export TRIPDOC_ADMIN_PASSWORD='replace-with-a-strong-password'
python -m tripdoc
```

### Windows PowerShell

```powershell
git clone https://github.com/moonweave/lab-trip-docs.git
cd lab-trip-docs

uv python install 3.12
uv venv --python 3.12
.\.venv\Scripts\Activate.ps1
uv pip sync requirements.txt

$env:TRIPDOC_HOST="0.0.0.0"
$env:TRIPDOC_PORT="8501"
$env:TRIPDOC_DATA_DIR="data"
$env:TRIPDOC_ADMIN_USER="admin"
$env:TRIPDOC_ADMIN_PASSWORD="replace-with-a-strong-password"
python -m tripdoc
```

After startup, open the service on the central PC:

```text
http://localhost:8501
```

Other lab members on the same network should connect to:

```text
http://CENTRAL_PC_IP:8501
```

## pip fallback

`uv` is preferred, but standard Python virtual environments also work.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m tripdoc
```

On Windows, activate with:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Data directory

By default, runtime data is stored under `data/`.

```text
data/
  app.db        # SQLite database
  uploads/      # uploaded original documents
  exports/      # generated Excel and ZIP outputs
```

Back up the whole `data/` directory. It contains the uploaded originals and the document matching database.

## Security baseline

Use this as an internal lab tool, not a public internet service.

- Set a strong `TRIPDOC_ADMIN_PASSWORD` before real use.
- Do not expose port `8501` directly to the public internet.
- Prefer school VPN, lab VPN, or a private overlay network for off-campus access.
- Keep the GitHub repository private before uploading real documents or examples.
- Back up `data/` to an institution-approved or encrypted location.

## Firewall checklist

If the central PC can open `http://localhost:8501` but other lab computers cannot connect, allow inbound TCP `8501` on the central PC firewall.

## Operational checklist

Before using it for a real trip:

1. Create a test trip.
2. Upload a small traveler roster.
3. Upload 10 to 20 past documents.
4. Check name matching accuracy.
5. Check document category accuracy.
6. Download Excel and ZIP output.
7. Confirm `data/` backup works.

## Optional Docker runtime

Docker is optional. It is useful when the central PC is a Linux server or mini PC.

```bash
docker compose up --build -d
```

Before Docker-based real operation, change the default password in `compose.yml` or pass a stronger password through your deployment environment.
