# Slave — PC Check Tool

Developed by **killeremperor** · Windows · Python 3.8+ · UI languages: TR / EN / RU / UK

Slave is a local desktop tool for checking a Windows PC for known cheat/executor software. It has two tools:

- **Browse Tool** – searches file names on your drives with [Everything](https://www.voidtools.com/) for the names in a config list.
- **Data usage check** – lists per-application disk/network I/O totals and connection counts, filtered with its own config list.

A name match is only a lead, not proof. Always check the file or process yourself before drawing conclusions.

## What it does (and does not do)

- Everything runs **locally**. Slave sends nothing anywhere and has no telemetry.
- Browse Tool runs `es.exe` (or talks to Everything's HTTP server on `127.0.0.1:8080`) and only reads file names, paths, sizes and dates.
- Data usage check runs one PowerShell command (`-ExecutionPolicy Bypass` applies to that command only; it does not change your system policy). It reads process names, paths, I/O counters and the number of established TCP connections per process.
- If Everything is installed but not running, Slave starts it in the background.
- Settings are saved in `slave_config.json` next to the script. The loading sound is generated in code and cached as `slave_boot.wav` in your temp folder.
- The only network actions are opening the Discord invite when you click the logo, and `pip install pillow` if you press the install button yourself.
- The passcode screen is a community gate, not security. The source is open; read it.

## Requirements

- Windows 10/11
- Python 3.8+ (tkinter is included with the standard installer)
- [Everything](https://www.voidtools.com/) plus its command-line tool `es.exe`
  (put `es.exe` next to `slave_scanner.py`), **or** Everything → Options → HTTP Server enabled (port 8080)
- Optional: `pip install pillow` for background images and blur

## Install & run

1. Install Everything and download `es.exe` from voidtools.com.
2. Put `es.exe` in the same folder as `slave_scanner.py`.
3. (Optional) `pip install pillow`
4. Run: `python slave_scanner.py`

## Configs

Each tool has its own configs. **Default** is built in and cannot be edited. Use *Create new* to make your own list, *Edit list* to change it, and *Delete* to remove it. The search box only searches what you type and never changes a config.

## Appearance

Brush button in the header: color presets, blurred background image, and interface opacity .
