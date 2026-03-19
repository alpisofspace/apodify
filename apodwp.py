import argparse
import ctypes
import datetime as dt
import html
import json
import random
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import winreg  # type: ignore
except Exception:
    winreg = None  # type: ignore

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None  # type: ignore


NASA_APOD_API = "https://api.nasa.gov/planetary/apod"
APOD_ARCHIVE_BASE = "https://apod.nasa.gov/apod/"
APOD_START_DATE = dt.date(1995, 6, 16)
DEFAULT_DIR_NAME = "APOD"


# UI Helper Functions
def _get_console():
    """Get console instance (rich if available, standard otherwise)."""
    if RICH_AVAILABLE and Console:
        return Console()
    return None


def _print_banner(console=None):
    """Print startup banner."""
    if console and RICH_AVAILABLE:
        banner_text = Text()
        banner_text.append("APODify v1", style="bold magenta")
        banner_text.append("\nmade by alpis", style="dim orange")
        panel = Panel(
            banner_text,
            border_style="magenta",
            padding=(1, 2),
            expand=False
        )
        console.print(panel)
    else:
        print("\n" + "=" * 50)
        print("APODify v1")
        print("made by alpis")
        print("=" * 50 + "\n")


def _print_status(message: str, status: str = "info", console=None):
    """Print a status message. status: info, success, warning, error"""
    if console and RICH_AVAILABLE:
        icons = {"info": "→", "success": "✓", "warning": "⚠", "error": "✗"}
        colors = {"info": "magenta", "success": "orange", "warning": "yellow", "error": "red"}
        icon = icons.get(status, "•")
        color = colors.get(status, "white")
        text = Text(f"[{icon}] {message}", style=f"bold {color}")
        console.print(text)
    else:
        prefix = {"info": "[→]", "success": "[✓]", "warning": "[⚠]", "error": "[✗]"}
        print(f"{prefix.get(status, '[•]')} {message}")


def _print_result(title: str, value: str, console=None):
    """Print a result line."""
    if console and RICH_AVAILABLE:
        text = Text()
        text.append(f"{title}: ", style="bold magenta")
        text.append(value, style="white")
        console.print(text)
    else:
        print(f"{title}: {value}")


def _print_divider(console=None):
    """Print a visual divider."""
    if console and RICH_AVAILABLE:
        console.rule(style="magenta")
    else:
        print("-" * 50)


def _show_preview(image_path: Path, console=None) -> None:
    """Open image in default viewer for preview."""
    try:
        if os.name == "nt":
            os.startfile(image_path)
        else:
            import subprocess
            subprocess.Popen(["xdg-open", str(image_path)])
    except Exception as e:
        _print_status(f"Could not open preview: {e}", "warning", console)


def _ask_user_confirmation(console=None) -> bool:
    """Ask user Y/N confirmation in terminal."""
    if console and RICH_AVAILABLE:
        from rich.prompt import Confirm
        try:
            return Confirm.ask(
                "Set this as your wallpaper?",
                default=True,
                console=console
            )
        except Exception:
            return True
    else:
        while True:
            resp = input("\nSet this as your wallpaper? (y/n): ").strip().lower()
            if resp in ("y", "yes"):
                return True
            elif resp in ("n", "no"):
                return False
            print("Please enter 'y' or 'n'")


def _http_get_json(url: str, headers: dict | None = None, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec - NASA API URL
        data = resp.read()
    return json.loads(data.decode("utf-8"))


def _http_download(url: str, dest_path: Path, headers: dict | None = None, timeout: int = 60) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec - NASA image URL
        with open(dest_path, "wb") as f:
            # Stream to file in chunks
            while True:
                chunk = resp.read(1024 * 64)
                if not chunk:
                    break
                f.write(chunk)


def _user_agent() -> str:
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    return f"apodwp/1.0 Python/{py_ver} (+https://api.nasa.gov/)"


def fetch_apod_metadata(api_key: str, date: str | None = None) -> dict:
    params = {
        "api_key": api_key,
        "thumbs": "true",
    }
    if date:
        params["date"] = date
    url = f"{NASA_APOD_API}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": _user_agent(), "Accept": "application/json"}
    return _http_get_json(url, headers=headers)


def _apod_archive_url_for_date(date: dt.date) -> str:
    page_name = date.strftime("ap%y%m%d.html")
    return urllib.parse.urljoin(APOD_ARCHIVE_BASE, page_name)


def _parse_apod_date_from_html(html_body: str) -> dt.date | None:
    # Typical format: <b>2025 October 21</b>
    match = re.search(r"<b>\s*(\d{4})\s+([A-Za-z]+)\s+(\d{1,2})\s*</b>", html_body, re.IGNORECASE)
    if not match:
        return None
    year = int(match.group(1))
    month_name = match.group(2)
    day = int(match.group(3))

    month: int | None = None
    for fmt in ("%B", "%b"):
        try:
            month = dt.datetime.strptime(month_name, fmt).month
            break
        except ValueError:
            continue
    if not month:
        return None

    try:
        return dt.date(year, month, day)
    except ValueError:
        return None


def fetch_apod_html(date: dt.date | None, timeout: int = 30) -> dict:
    """Scrape APOD site for given date (or today if None) and return metadata."""

    if date is not None:
        target_url = _apod_archive_url_for_date(date)
        expected_date = date
    else:
        target_url = urllib.parse.urljoin(APOD_ARCHIVE_BASE, "astropix.html")
        expected_date = None

    headers = {"User-Agent": _user_agent(), "Accept": "text/html"}
    req = urllib.request.Request(target_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec - NASA APOD site
            html_body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"APOD HTML fetch failed (HTTP {exc.code})") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"APOD HTML fetch failed: {exc.reason}") from exc

    title_match = re.search(r"<title>.*?-\s*(.*?)</title>", html_body, re.IGNORECASE | re.DOTALL)
    title = html.unescape(title_match.group(1).strip()) if title_match else "Astronomy Picture of the Day"

    image_match = re.search(r"<a[^>]+href\s*=\s*\"(image/[^\"]+)\"", html_body, re.IGNORECASE)
    if not image_match:
        image_match = re.search(r"<img[^>]+src\s*=\s*\"(image/[^\"]+)\"", html_body, re.IGNORECASE)
    if not image_match:
        raise RuntimeError("Could not locate image link in APOD HTML page")

    rel_url = image_match.group(1)
    image_url = urllib.parse.urljoin(APOD_ARCHIVE_BASE, rel_url)

    # Explanation paragraph often wrapped in <b>Explanation:</b>
    expl_match = re.search(r"<b>Explanation:</b>(.*?)<p>", html_body, re.IGNORECASE | re.DOTALL)
    explanation = (
        html.unescape(re.sub(r"<[^>]+>", " ", expl_match.group(1))).strip()
        if expl_match
        else ""
    )

    resolved_date = expected_date or _parse_apod_date_from_html(html_body) or dt.date.today()

    return {
        "media_type": "image",
        "url": image_url,
        "hdurl": image_url,
        "title": title,
        "date": resolved_date.isoformat(),
        "explanation": explanation,
        "source": "apod_html",
        "fallback": True,
        "page_url": target_url,
    }


def random_apod_date(start: dt.date = APOD_START_DATE, end: dt.date | None = None) -> dt.date:
    if end is None:
        end = dt.date.today()
    if end < start:
        raise ValueError("End date is before start date for random selection")
    span = (end - start).days
    if span <= 0:
        return start
    offset = random.randint(0, span)
    return start + dt.timedelta(days=offset)


def _safe_filename(text: str, max_len: int = 80) -> str:
    # Replace non-filename-safe chars with underscore
    text = re.sub(r"[\\/:*?\"<>|]", "_", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[:max_len].rstrip()
    return text


def choose_apod_image(meta: dict) -> tuple[str, str]:
    """Return (image_url, suggested_ext). Raises ValueError if not available.

    Prefers HD when available. For videos, uses thumbnail_url if present.
    """
    media_type = meta.get("media_type")
    if media_type == "image":
        url = meta.get("hdurl") or meta.get("url")
        if not url:
            raise ValueError("APOD image URL missing")
    elif media_type == "video":
        url = meta.get("thumbnail_url") or meta.get("url")
        if not url:
            raise ValueError("APOD is a video without thumbnail; cannot set wallpaper")
    else:
        raise ValueError(f"Unsupported media_type: {media_type}")

    parsed = urllib.parse.urlparse(url)
    ext = os.path.splitext(parsed.path)[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".bmp"}:
        # Default to .jpg if unknown
        ext = ".jpg"
    return url, ext


def build_output_path(base_dir: Path, meta: dict, ext: str) -> Path:
    date = meta.get("date") or dt.date.today().isoformat()
    title = meta.get("title") or "apod"
    name = f"{date} - {_safe_filename(title)}{ext}"
    return base_dir / name


def set_wallpaper_windows(image_path: Path, style: str = "fill") -> None:
    if os.name != "nt":
        raise RuntimeError("Wallpaper setting is implemented for Windows only")

    # Map logical styles to registry values
    styles = {
        "fill": (10, 0),
        "fit": (6, 0),
        "stretch": (2, 0),
        "tile": (0, 1),
        "center": (0, 0),
        "span": (22, 0),  # Win8+
    }
    style = style.lower()
    if style not in styles:
        raise ValueError(f"Unknown style '{style}'. Use one of: {', '.join(styles)}")

    wallpaper_style, tile_wallpaper = styles[style]

    if winreg is None:
        raise RuntimeError("winreg not available; cannot set wallpaper style")

    # Update registry for style
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_SET_VALUE) as key:  # type: ignore
        winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, str(wallpaper_style))  # type: ignore
        winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, str(tile_wallpaper))  # type: ignore

    # Apply wallpaper
    SPI_SETDESKWALLPAPER = 20
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDWININICHANGE = 0x02

    res = ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER,
        0,
        str(image_path),
        SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE,
    )
    if not res:
        raise OSError("SystemParametersInfoW failed to set wallpaper")


def resolve_output_dir(dir_arg: str | None) -> Path:
    if dir_arg:
        return Path(dir_arg).expanduser().resolve()
    # Default to Pictures\APOD if exists, else current dir / APOD
    home = Path.home()
    pictures = home / "Pictures"
    base = pictures if pictures.exists() else Path.cwd()
    return (base / DEFAULT_DIR_NAME).resolve()


def ensure_unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for i in range(2, 1000):
        candidate = path.with_name(f"{stem} ({i}){suffix}")
        if not candidate.exists():
            return candidate
    # Fallback to timestamp to avoid loops
    ts = int(time.time())
    return path.with_name(f"{stem}-{ts}{suffix}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Set Windows wallpaper to NASA APOD.")
    parser.add_argument("--api-key", dest="api_key", default=os.environ.get("NASA_API_KEY", "DEMO_KEY"), help="NASA API key (env NASA_API_KEY) ")
    parser.add_argument("--date", dest="date", default=None, help="APOD date YYYY-MM-DD (defaults to today)")
    parser.add_argument("--dir", dest="out_dir", default=None, help="Directory to save images (default: Pictures/APOD)")
    parser.add_argument("--style", dest="style", default="fill", choices=["fill", "fit", "stretch", "tile", "center", "span"], help="Wallpaper style")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and download but do not set wallpaper")
    parser.add_argument("--no-download", action="store_true", help="Do not re-download if a same-named file exists")
    parser.add_argument("--random", action="store_true", help="Choose a random APOD date from the archive")
    parser.add_argument("--preview", action="store_true", default=True, help="Show image preview before setting (default: True)")
    parser.add_argument("--no-preview", dest="preview", action="store_false", help="Skip image preview")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    console = _get_console()
    _print_banner(console)
    
    args = parse_args(argv or sys.argv[1:])

    if args.random and args.date:
        _print_status("--random cannot be combined with --date", "error", console)
        return 1

    target_date: dt.date | None = None
    if args.date:
        try:
            target_date = dt.datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            _print_status("Invalid --date value (expected YYYY-MM-DD)", "error", console)
            return 1

    meta: dict | None = None

    if args.random:
        _print_status("Selecting random APOD date...", "info", console)
        attempts = 0
        errors: list[tuple[dt.date, Exception]] = []
        seen: set[dt.date] = set()
        max_attempts = 10
        while attempts < max_attempts:
            candidate = random_apod_date(APOD_START_DATE, dt.date.today())
            if candidate in seen:
                continue
            seen.add(candidate)
            attempts += 1
            try:
                meta = fetch_apod_html(candidate)
                target_date = candidate
                _print_status(f"Random APOD date: {candidate.isoformat()}", "success", console)
                break
            except Exception as err:
                errors.append((candidate, err))
        if meta is None:
            for candidate, err in errors:
                _print_status(f"Random attempt {candidate.isoformat()} failed: {err}", "warning", console)
            _print_status("Unable to retrieve a random APOD image after multiple attempts", "error", console)
            return 1
    else:
        _print_status("Fetching APOD metadata...", "info", console)
        api_error: Exception | None = None
        date_str = target_date.isoformat() if target_date else None
        try:
            meta = fetch_apod_metadata(api_key=args.api_key, date=date_str)
        except Exception as e:
            api_error = e

        if meta is None:
            try:
                _print_status("NASA API unavailable; using APOD site fallback", "warning", console)
                meta = fetch_apod_html(target_date)
                if api_error:
                    _print_status(f"API error: {api_error}", "warning", console)
            except Exception as fallback_error:
                if api_error:
                    _print_status(f"Error fetching APOD metadata: {api_error}", "error", console)
                _print_status(f"Fallback also failed: {fallback_error}", "error", console)
                return 1

    _print_status("APOD metadata retrieved", "success", console)

    try:
        image_url, ext = choose_apod_image(meta)
    except Exception as e:
        _print_status(f"No usable APOD image: {e}", "error", console)
        return 2

    _print_divider(console)
    _print_result("Title", meta.get('title', 'N/A'), console)
    _print_result("Date", meta.get('date', 'N/A'), console)
    if meta.get("copyright"):
        _print_result("Copyright", meta['copyright'], console)
    _print_divider(console)

    out_dir = resolve_output_dir(args.out_dir)
    out_path = build_output_path(out_dir, meta, ext)
    if args.no_download and out_path.exists():
        final_path = out_path
        _print_status(f"Using cached image (no-download enabled)", "info", console)
    else:
        final_path = ensure_unique_path(out_path)
        _print_status("Downloading image...", "info", console)
        try:
            headers = {"User-Agent": _user_agent(), "Accept": "image/*,application/octet-stream"}
            _http_download(image_url, final_path, headers=headers)
            _print_status("Image downloaded successfully", "success", console)
        except Exception as e:
            _print_status(f"Error downloading APOD image: {e}", "error", console)
            return 3

    _print_result("Saved", str(final_path), console)

    if args.dry_run:
        _print_status("Dry-run mode: not setting wallpaper", "warning", console)
        return 0

    # Show preview and ask user confirmation if enabled
    if args.preview:
        _print_status("Opening image preview...", "info", console)
        _show_preview(final_path, console)
        if not _ask_user_confirmation(console):
            _print_status("Skipped setting wallpaper", "info", console)
            return 0

    _print_status(f"Applying wallpaper (style: {args.style})...", "info", console)
    try:
        set_wallpaper_windows(final_path, style=args.style)
        _print_status("Wallpaper updated successfully", "success", console)
    except Exception as e:
        _print_status(f"Failed to set wallpaper: {e}", "error", console)
        return 4

    _print_divider(console)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
