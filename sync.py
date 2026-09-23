#!/usr/bin/env python3
"""Report each agent's position in the sidebar panel as the $aidx token.

focus_agent targets panel positions, and agent rows have no built-in number
token, so the position has to be pushed back as pane metadata.

herdr turns done into idle once an agent has been looked at, and that emits
no event: the panel re-sorts on its own while the numbers stay put. So the
plugin also owns the panel order, through an agent view sorted by the same
numbers. The order can lag until the next event, but rows and numbers never
disagree.
"""

import fcntl
import json
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

import tomllib

HERDR = os.environ.get("HERDR_BIN_PATH") or "herdr"
CONFIG = Path(
    os.environ.get("HERDR_CONFIG_PATH") or Path.home() / ".config/herdr/config.toml"
)
SOCKET = os.environ.get("HERDR_SOCKET_PATH") or str(
    Path.home() / ".config/herdr/herdr.sock"
)
# herdr's panel order while ui.agent_panel_sort = "priority": attention first,
# and within one status the most recent state change wins.
PRIORITY = {"blocked": 4, "done": 3, "working": 2, "idle": 1}


def herdr(*args):
    done = subprocess.run(
        [HERDR, *args], capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        sys.exit(f"agent-index: herdr {' '.join(args)}: {done.stderr.strip()}")
    return done.stdout


def api(method, params):
    # The CLI has no command for agent views, only the socket API does.
    request = {"id": "agent-index", "method": method, "params": params}
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.connect(SOCKET)
        conn.sendall(json.dumps(request).encode() + b"\n")
        reply = json.loads(conn.makefile().readline())
    if "error" in reply:
        sys.exit(f"agent-index: {method}: {reply['error']}")


def sorts_by_priority():
    try:
        with open(CONFIG, "rb") as handle:
            ui = tomllib.load(handle).get("ui", {})
    except (OSError, ValueError):
        return False
    return str(ui.get("agent_panel_sort", "")).strip().lower() == "priority"


def main():
    state_dir = os.environ.get("HERDR_PLUGIN_STATE_DIR") or tempfile.gettempdir()
    # Status events arrive in bursts; without the lock a slow run can report a
    # stale order on top of a fresher one.
    with open(Path(state_dir) / "agent-index.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        agents = json.loads(herdr("agent", "list"))["result"]["agents"]
        by_priority = sorts_by_priority()
        if by_priority:
            agents.sort(
                key=lambda agent: (
                    -PRIORITY.get(str(agent.get("agent_status") or "").lower(), 0),
                    -int(agent.get("state_change_seq") or 0),
                )
            )
        for number, agent in enumerate(agents, start=1):
            herdr(
                "pane",
                "report-metadata",
                agent["pane_id"],
                "--source",
                "agent-index",
                "--token",
                f"aidx={number}",
                # Views compare tokens as strings, so "10" would sort before "2".
                "--token",
                f"aord={number:03d}",
            )
        api(
            "agent.view.set",
            {
                "source": f"plugin:{os.environ['HERDR_PLUGIN_ID']}",
                # While a view is active herdr disables the header sort toggle
                # and paints the label in the accent colour. A blank braille
                # cell survives herdr's label trim and hides the label.
                "label": chr(0x2800),
                "sort": [
                    {"field": {"token": "aord"}, "order": "asc"},
                    # Agents detected after this run have no number yet.
                    {"field": "attention", "order": "desc"},
                    {"field": "state_change_seq", "order": "desc"},
                ],
            },
        )


main()
