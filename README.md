# Cloudflare Tunnel CLI

A secure, graphic CLI tool to easily set up Cloudflare Tunnels on your local machine or server.

## Features

- **Automated Setup**: Handles login, tunnel creation, DNS routing, and configuration generation.
- **Graphic Interface**: Beautiful CLI with Cloudflare-themed colors (Orange/Black).
- **Auto-Installation**: Can automatically install `cloudflared` on Linux systems.

## Prerequisites

- A Cloudflare account.
- A domain added to your Cloudflare account.
- Python 3.8+

## Installation

1. Clone this repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Setup Wizard

Run the interactive setup wizard:

```bash
python3 main.py setup
```

Follow the on-screen instructions to:
1. Login to Cloudflare.
2. Create a new tunnel.
3. Route a domain to your tunnel.
4. Configure your local service.
5. Run the tunnel.

### Install cloudflared

If you need to install `cloudflared` manually or separately:

```bash
python3 main.py install
```

## License

MIT
