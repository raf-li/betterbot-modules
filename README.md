# BetterBot Module Store

This is the official module repository for [BetterBot](https://github.com/YOUR_USERNAME/betterbot).

## Structure

```
betterbot-modules/          ← root of THIS repo
├── registry.json           ← index of all available modules
├── example_module/
│   ├── __init__.py
│   ├── module.ini
│   ├── utils.py
│   └── locales/
│       └── en.json
└── tickets/
    ├── __init__.py
    └── module.ini
```

## Adding Your Module

1. Create a folder with your module files.
2. Make sure `module.ini` has a **`min_core_version`** field under `[dependencies]`.
3. Add an entry to `registry.json` with these required fields:

```json
{
  "folder": "your_module_folder",
  "name": "Your Module Name",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "What your module does.",
  "category": "admin-tools",
  "min_core_version": "1.0.0",
  "files": ["__init__.py", "module.ini"]
}
```

### Available Categories
- `admin-tools`
- `community`
- `entertainment`
- `developer-tools`
- `utilities`

## Configuring BetterBot to use this Store

In your `config.json`, add:

```json
"module_store": {
  "registry_url": "https://raw.githubusercontent.com/YOUR_USERNAME/betterbot-modules/main/registry.json",
  "raw_base_url":  "https://raw.githubusercontent.com/YOUR_USERNAME/betterbot-modules/main"
}
```
