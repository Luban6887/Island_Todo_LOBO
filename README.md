# LOBO 🐺

A Dynamic-Island style productivity widget that lives at the top-center edge of your screen.

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows-0078D6)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- **Hover to reveal** — move your cursor to the top-center edge and the island slides in
- **Pill view** — a compact pill shows your remaining task count
- **Click to expand** — opens a Tasks / Notes panel
- **Click outside / `Esc`** — collapses back to the pill
- **Right-click the pill** — quit
- **Animated wolf mascot** — a bouncing, blinking wolf face with particles, sparkles, hearts and stars
- **Tasks & Notes** — add, complete, delete and clear-done items
- **Auto-save** — everything is stored next to the script as `LOBO_data.json`
- **Native transparency** — uses the Windows layered-window transparent colour so only the island is visible

## Screenshots

> _Add your own screenshots here._

## Getting Started

### Run from source

Requires Python 3.8+ with `tkinter` (bundled with the standard Windows installer).

```bash
python lobo.pyw
```

### Build a standalone executable

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name LOBO --icon lobo.ico lobo.pyw
```

The finished binary is written to `dist\LOBO.exe`. It is fully standalone — no Python installation required on the target machine.

## Usage

| Action | Result |
| --- | --- |
| Move cursor to top-center edge | Reveal the island |
| Click the pill | Expand the Tasks / Notes panel |
| Click a task / its checkbox | Toggle done |
| `+` or `Enter` | Add the typed item |
| `×` | Delete a row |
| `clear done` | Remove all completed tasks |
| Click outside / `Esc` | Collapse to pill |
| Right-click the pill | Quit LOBO |

## How it works

- The window is `overrideredirect` + `-topmost`, pinned to the top edge of the screen.
- A transparent key colour (`#010203`) is set with `-transparentcolor` so the window background disappears and only the drawn island remains clickable.
- A spring physics loop animates width/height between the pill and expanded states.
- All artwork (the wolf face, rounded rectangles, stars, hearts, sparkles) is drawn directly on a `tkinter.Canvas` — there are no external image assets.

## Data

LOBO stores its state in `LOBO_data.json` beside the executable/script:

```json
{
  "tasks": [{ "t": "Buy milk", "d": false }],
  "notes": ["Remember to stretch"]
}
```

Delete the file to reset LOBO.

## Project layout

```
Lobo/
├─ lobo.pyw          # the application
├─ lobo.ico          # yellow round app icon
├─ lobo.png          # icon source (PNG)
├─ LOBO_data.json    # saved tasks & notes (auto-created)
├─ README.md
└─ dist/
   └─ LOBO.exe       # standalone build output
```

## License

MIT — see `LICENSE` (add one before publishing if you don't already have it).
