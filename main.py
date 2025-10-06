#!/usr/bin/env python3

# A simple Discord Rich Presence for VirtualBox VMs on Linux
# Made by ChatGPT and modified by @wh0crypt
# Based on the original work by @bukanspot

from __future__ import annotations
import configparser
import json
import subprocess, time, pprint, sys
from pypresence import Presence
from pathlib import Path

def list_running_vms() -> tuple[list[str]|None, str|None]:
  """ Returns (list_of_names, error_string_or_None) """
  
  try:
    p = subprocess.run(["VBoxManage","list","runningvms"], capture_output=True, text=True)
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
  """ Returns a dict of VM info, or empty dict on error """
  
  try:
    p = subprocess.run(["VBoxManage","showvminfo", name, "--machinereadable"],
                        capture_output=True, text=True)
  except Exception:
    return {}

  out = p.stdout
  info = {}
  for line in out.splitlines():
    if "=" in line:
      k,v = line.split("=",1)
      info[k.strip()] = v.strip().strip('"')

  return info

def get_image_for_os(ostype: str, osmap: dict) -> str:
  """Match VBox OS type to image name from osmap.json"""

  ostype_lower = ostype.lower()
  for family, data in osmap["operating_systems"].items():
    for version, vdata in data["versions"].items():
      if version.lower() in ostype_lower or vdata["name"].lower() in ostype_lower:
        return vdata["image"]

  return "unknown"

def main() -> None:
  """ Main entry point """
  
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
  client_id = cp.get("Rich Presence","client_id", fallback=None)

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
          try: rpc.clear()
          except: pass
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
              {"label": "View Repo", "url": "https://github.com/wh0crypt/virtualcord"}
            ]
          }

          try:
            rpc.update(**presence)
          except Exception as e:
            print("rpc.update error:", e)

          prev = vm_name
      time.sleep(3)
  except KeyboardInterrupt:
    print("Exiting")
    try: rpc.clear()
    except: pass

if __name__ == "__main__":
  main()
