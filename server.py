#!/usr/bin/env python3
"""Compatibility entrypoint for DOBEDUB STUDIO.

The monolith stdlib HTTP server has been replaced by the FastAPI app. This
file remains so older local commands such as `python3 server.py` continue to
start the current local server.
"""

from __future__ import annotations

from scripts.run_local import main


if __name__ == "__main__":
    main()
