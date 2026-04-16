# Contributing to BetterBot Module Store

Thank you for your interest in contributing! This repository is the official community module store for the [BetterBot Framework](https://github.com/USERNAME/betterbot).

## How to Submit a New Module

### 1. Fork this Repository
Click the **Fork** button at the top right of this page.

### 2. Create Your Module Folder
Add a new folder with your module's name (use `snake_case`):
```
your_module_name/
├── __init__.py      ← Main module logic (required)
├── module.ini       ← Module metadata (required)
└── locales/
    └── en.json      ← English translations (optional but recommended)
```

### 3. Required: `module.ini` Format
```ini
[metadata]
name        = Your Module Name
version     = 1.0.0
author      = Your Name
description = A short description of what your module does.

[commands]
triggers = .yourcommand, /yourcommand

[dependencies]
min_core_version = 1.0.0
; pip_packages = requests, some-package

[settings]
enabled = true
```

> **`min_core_version`** is required. Check the [BetterBot releases](https://github.com/USERNAME/betterbot/releases) for the latest core version.

### 4. Add Your Module to `registry.json`
Open `registry.json` in the root of this repo and add an entry:
```json
{
  "folder": "your_module_name",
  "name": "Your Module Name",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "A short description of what your module does.",
  "category": "utilities",
  "min_core_version": "1.0.0",
  "files": [
    "__init__.py",
    "module.ini"
  ]
}
```

### 5. Available Categories
| Category | Description |
|---|---|
| `admin-tools` | Server management, moderation |
| `community` | Welcome messages, roles, social |
| `entertainment` | Games, music, fun commands |
| `utilities` | Productivity, automation |
| `developer-tools` | Debugging, logging, testing |

### 6. Open a Pull Request
- Branch name: `add/your-module-name`
- PR title: `[Module] Your Module Name v1.0.0`
- Describe what your module does in the PR description

## Module Quality Guidelines

- ✅ Module must inherit from `BaseModule` in `core/base.py`
- ✅ Must have a `module.ini` with all required fields
- ✅ No hardcoded credentials — use `self.store()` / `self.retrieve()` or `web_schema`
- ✅ No `import *` statements
- ✅ Must not crash on load if optional dependencies are missing
- ❌ No `.env` files — credentials belong in the bot's persistent storage
- ❌ Do not modify any files outside your module's own folder

## Updating an Existing Module

Open a PR that:
1. Updates `__init__.py` and/or other files in your module folder
2. Bumps the `version` in **both** `module.ini` and `registry.json`

---

For questions, open an [Issue](https://github.com/USERNAME/betterbot-modules/issues).
