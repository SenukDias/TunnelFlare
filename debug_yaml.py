import yaml
from pathlib import Path

config_content = {
    "tunnel": "8b0268ab-...",
    "credentials-file": str(Path.home() / ".cloudflared" / "8b0268ab-....json"),
    "ingress": [
        {
            "hostname": "app.example.com",
            "service": "http://localhost:8000"
        },
        {
            "service": "http_status:404"
        }
    ]
}

print(yaml.dump(config_content, sort_keys=False))
