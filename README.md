# virtualcord

A simple Discord Rich Presence client that reports running VirtualBox VMs (Linux).

![pypresence](https://img.shields.io/badge/using-pypresence-00bb88.svg?style=for-the-badge&logo=discord&logoWidth=20)

## What this is

`virtualcord` watches VirtualBox (via `VBoxManage`) for running virtual machines and updates Discord Rich Presence with the active VM's name and OS. It's a lightweight, single-file program (`main.py`) intended to run on Linux where `VBoxManage` from VirtualBox is available.

Key behaviors implemented in `main.py`:

- Requires `assets.json` (in repo) for mapping OS types to presence images.
- Requires `config.ini` with a `Rich Presence` section and a `client_id` (Discord Application RPC client ID).
- Connects to Discord RPC via `pypresence` and updates presence when VMs start/stop.

## Requirements

- Python 3.13+ (see `pyproject.toml` and `.python-version`) — adjust this if you target a different runtime.
- VirtualBox (so `VBoxManage` is available in PATH).
- Dependencies listed in `requirements.txt`:

  - pypresence
  - pyutil
  - virtualbox

Install dependencies (recommended in a venv):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Installation / Setup

1. Clone this repository.
2. Copy `config.example.ini` to `config.ini` and edit it.

- At minimum set `client_id` under the `[Rich Presence]` section to your Discord application's RPC client ID.

3. Ensure `assets.json` exists in the project root (it is required by `main.py`). The `assets/` folder contains OS/architecture icon mappings used by the presence.

## Configuration

- `config.example.ini` contains the configuration options. Create `config.ini` from it.

Important values:

- `[Rich Presence]` -> `client_id` (required): your Discord RPC app client ID.

If `config.ini` or `client_id` is missing, `main.py` will exit with a message explaining the missing item.

### Available Values

- `{machine name}`: Name of the machine in VirtualBox (e.g. "My Windows Machine")
- `{os name}`: Name of OS. (e.g. "Microsoft Windows")
- `{os version name}`: Name of OS version. (e.g. "Windows 8")
- `{os version image}`: Image key of OS version. (e.g. "windows_8")
- `{architecture}`: OS architecture (e.g. "64")
- `{architecture image}`: Image key of OS architecture (e.g. "64")
- `{icon}`: Image key of VirtualBox Icon.

## Usage

Run the program from the project root:

```bash
python main.py
```

Behavior notes:

- The script polls `VBoxManage list runningvms` every ~3 seconds and updates Discord when the first running VM changes.
- If no VMs are running the presence is cleared.

## Troubleshooting

- "VBoxManage not found": install VirtualBox or ensure `VBoxManage` is in your PATH.
- "Missing assets.json": make sure `assets.json` exists in the project root.
- "Missing config.ini" or "Missing client_id": copy `config.example.ini` to `config.ini` and set `client_id`.
- Discord RPC connection failures: ensure Discord is running on the same machine and the `client_id` is correct.

## Assets

The repository includes an `assets/` directory and `assets.json` for mapping OS types and architectures to image keys. `main.py` reads `assets.json` to choose the `large_image` key used in presence updates.

## Contributing

Small fixes, improvements, and asset additions are welcome. Open issues or PRs on the repository.

## License

This project is licensed under the MIT License — see the `LICENSE` file for details.

## Acknowledgements

- [DiscordBox](https://github.com/bukanspot/DiscordBox) for creating the original concept and inspiration for this project.
- [pypresence](https://github.com/qwertyquerty/pypresence) for providing the Discord RPC integration used in this project.
- [VirtualBox](https://www.virtualbox.org/) for the virtualization platform that this project interacts with.
