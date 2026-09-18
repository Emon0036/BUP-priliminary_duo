from __future__ import annotations

import json
import urllib.request


def main() -> None:
    with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=5) as response:
        assert json.load(response) == {"status": "ok"}
    print("health: PASS")


if __name__ == "__main__":
    main()
