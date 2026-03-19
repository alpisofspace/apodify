# Quick Start: Building the APOD Wallpaper Installer

## Prerequisites Checklist

- [ ] Python 3.10+ installed
- [ ] Windows (development machine)
- [ ] Inno Setup 6 installed: https://jrsoftware.org/isinfo.php

## One-Command Install (PowerShell)

From the project root:

```powershell
.\installer\build_installer.ps1
```

The installer will be created at: `dist\APODWallpaperSetup.exe`

## Manual Build (Step-by-Step)

### 1. Prepare environment (first time only)
```powershell
cd apodwallpaper
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install pyinstaller rich
```

### 2. Build executable
```powershell
pyinstaller --clean --noconfirm build\apodwp.spec
```

### 3. Build installer
```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\apodwp_installer.iss
```

### 4. Test the installer
```powershell
dist\APODWallpaperSetup.exe
```

## What You Get

- `dist\APODWallpaperSetup.exe` - The complete installer (ready to distribute)
- `dist\APODWallpaper\` - The portable executable (optional for manual distribution)

## Customization

Before building, you can customize:

**Launcher defaults** (`installer\apodwp_launcher.bat`):
```batch
set "STYLE=fill"        # fill, fit, stretch, tile, center, span
set "USE_RANDOM=yes"    # yes or no
set "API_KEY="          # Leave empty for DEMO_KEY
```

**Installer branding** (`installer\apodwp_installer.iss`):
```iss
#define MyAppPublisher "Your Name"
#define MyAppVersion "1.0.0"
```

## Distribution

**For GitHub:**
1. Run `build_installer.ps1`
2. Upload `APODWallpaperSetup.exe` to releases
3. Include system requirements and download instructions

**For Users:**
- Download `APODWallpaperSetup.exe`
- Run as administrator
- Follow the installer wizard
- ✅ Done! Wallpaper updates automatically on logon

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ISCC.exe` not found | Install Inno Setup 6 or add to PATH |
| `ModuleNotFoundError: rich` | Run `pip install rich` in venv |
| Permission denied | Run PowerShell as administrator |
| Build fails silently | Check `dist\APODWallpaper\` folder for errors |

## Next Steps

1. ✅ Build the installer
2. 📋 Test it on a clean Windows VM
3. 🚀 Publish to GitHub Releases
4. 📖 Create user documentation

---

**Full documentation:** See `BUILD.md` and `README.md` in this folder.
