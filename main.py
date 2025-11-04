#!/usr/bin/env python3

# A simple Discord Rich Presence for VirtualBox VMs on Linux
# Made by ChatGPT and modified by @wh0crypt
# Based on the original work by @bukanspot

from __future__ import annotations

import configparser
import json
import subprocess
import sys
import time
from pathlib import Path

from pypresence import Presence


def list_running_vms() -> tuple[list[str] | None, str | None]:
    """
    Return running VirtualBox VM names and an optional error message.

    Runs the command ``VBoxManage list runningvms`` and parses its output.

    Returns:
        A tuple (names, error) where:
        - names is a list[str] of VM names when the command succeeds and VMs
            are found;
        - names is an empty list when the command succeeds but no VMs are
            currently running;
        - names is ``None`` and error is a short string when ``VBoxManage`` is
            not available (FileNotFoundError) or another execution-level error
            prevents running the command.

    The function deliberately does not raise on missing ``VBoxManage`` so the
    caller can handle the condition gracefully.
    """

    try:
        p = subprocess.run(
            ["VBoxManage", "list", "runningvms"], capture_output=True, text=True
        )
    except FileNotFoundError:
        return None, "VBoxManage not found"

    out = p.stdout.strip()
    if not out:
        return [], None

    lines = [line.strip() for line in out.splitlines() if line.strip()]
    names = []
    for L in lines:
        if L.startswith('"'):
            parts = L.split('"')
            if len(parts) >= 3:
                names.append(parts[1])
            else:
                names.append(L)
        else:
            names.append(L)

    return names, None


def get_vm_info_by_name(name: str) -> dict[str, str]:
    """
    Retrieve machine-readable VM information for a VM by name.

    Executes ``VBoxManage showvminfo <name> --machinereadable`` and parses the
    output into a dict of string keys to string values.

    Returns:
        A dict mapping info keys to their values (both as strings). If the
        command fails for any reason (including when ``VBoxManage`` is not
        available), an empty dict is returned. Values are stripped of any
        surrounding double quotes by the parser.

    The function intentionally swallows execution errors and returns an empty
    dict so callers can treat absence-of-info uniformly.
    """

    try:
        p = subprocess.run(
            ["VBoxManage", "showvminfo", name, "--machinereadable"],
            capture_output=True,
            text=True,
        )
    except Exception:
        return {}

    out = p.stdout
    info = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            info[k.strip()] = v.strip().strip('"')

    return info


def get_image_for_os(ostype: str, osmap: dict) -> str:
    """
    Return an image key for a given VirtualBox OS type using `osmap`.

    The function performs a case-insensitive, partial match of the provided
    ``ostype`` against the entries in ``osmap["operating_systems"]``.

    Expected ``osmap`` shape (simplified):

        {
            "operating_systems": {
                "Family": {
                    "versions": {
                        "version-key": {"name": "Display Name", "image": "image_key"},
                        ...
                    }
                },
                ...
            }
        }

    Matching strategy:
      - For each family and version, check if the version key or the
        configured display name appears (case-insensitive) in ``ostype``.
      - Return the first matched ``vdata['image']``.

    Returns:
      - The image key (str) when a match is found.
      - "unknown" if no match is found or if the structure doesn't contain
        expected keys.
    """

    ostype_lower = ostype.lower()
    for family, data in osmap["operating_systems"].items():
        for version, vdata in data["versions"].items():
            if version.lower() in ostype_lower or vdata["name"].lower() in ostype_lower:
                return vdata["image"]

    return "unknown"


def main() -> None:
    """
    Main entry point for the virtualcord process.

    Behavior summary
    - Validates required files: `assets.json` is required for icon mapping and
      `config.ini` must exist with a `[Rich Presence]` section containing
      `client_id` (Discord RPC application client ID).
    - Loads `assets.json` (used by `get_image_for_os`) and the configuration.
    - Connects to Discord RPC via `pypresence.Presence(client_id)`.
    - Enters a polling loop that calls `list_running_vms()` roughly every 3
      seconds. When a running VM is detected (the first name returned by
      `list_running_vms`), the program gathers VM info, chooses an image via
      `get_image_for_os`, and updates the Discord presence. When no VMs are
      running the presence is cleared.

    Exit / error behavior
    - If `assets.json` or `config.ini` is missing, the function prints a
      short message and calls ``sys.exit(1)``.
    - If `client_id` is missing from the config the program will print an
      explanatory message and exit with code 1.
    - If the Discord RPC connection fails the program exits with code 1 and
      prints the exception.
    - `list_running_vms()` returns `(None, error_msg)` when `VBoxManage` is
      not available; in this case the loop prints the error and breaks.

    Runtime notes
    - The function intentionally keeps exception handling minimal and prints
      errors to stdout; this keeps the script suitable for simple usage or
      supervisors (systemd) where logs can be inspected.
    - A KeyboardInterrupt (Ctrl-C) will clear the RPC presence (if possible)
      and exit cleanly.
    """

    base = Path(__file__).parent
    client_id = None
    cfg = base / "config.ini"
    osmap_path = base / "assets.json"

    if not osmap_path.exists():
        print("Missing assets.json — please create it.")
        sys.exit(1)

    osmap = json.loads(osmap_path.read_text())

    if not cfg.exists():
        print("Missing config.ini")
        sys.exit(1)

    cp = configparser.ConfigParser()
    cp.read(cfg)
    client_id = cp.get("Rich Presence", "client_id", fallback=None)

    if not client_id:
        print("Missing client_id in config.ini (Rich Presence section). Exiting.")
        sys.exit(1)

    try:
        rpc = Presence(client_id)
        rpc.connect()
        print("Connected to Discord RPC")
    except Exception as e:
        print("Could not connect to Discord RPC:", e)
        sys.exit(1)

    prev = None
    start = None

    try:
        while True:
            names, err = list_running_vms()
            if err:
                print("VBoxManage error:", err)
                break

            if not names:
                if prev is not None:
                    print("No VMs running -> clearing presence")
                    try:
                        rpc.clear()
                    except Exception as e:
                        print("rpc.clear error:", e)

                    prev = None

                start = None
            else:
                vm_name = names[0]
                if vm_name != prev:
                    print("Detected VM start/change:", vm_name)
                    info = get_vm_info_by_name(vm_name)
                    ostype = info.get("ostype", info.get("ostype", "unknown"))
                    image = get_image_for_os(ostype, osmap)
                    details = f"{ostype}"
                    state = f"VM: {vm_name}"
                    start = time.time()
                    presence = {
                        "details": details,
                        "state": state,
                        "start": start,
                        "large_image": image,
                        "large_text": vm_name,
                        "buttons": [
                            {
                                "label": "View Repo",
                                "url": "https://github.com/wh0crypt/virtualcord",
                            }
                        ],
                    }

                    try:
                        rpc.update(**presence)
                    except Exception as e:
                        print("rpc.update error:", e)

                    prev = vm_name
            time.sleep(3)
    except KeyboardInterrupt:
        print("Exiting")
        try:
            rpc.clear()
        except Exception as e:
            print("rpc.clear error:", e)


if __name__ == "__main__":
    main()
