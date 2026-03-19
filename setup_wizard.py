#!/usr/bin/env python3
"""
APOD Wallpaper Setup Wizard
Runs after installation to guide users through first-time setup
"""

import sys
import os
import subprocess
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.prompt import Prompt, Confirm
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None


def get_console():
    """Get console instance (rich if available)."""
    if RICH_AVAILABLE and Console:
        return Console()
    return None


def print_banner(console=None):
    """Print setup wizard banner."""
    if console and RICH_AVAILABLE:
        title = Text("APOD Wallpaper Setup Wizard", style="bold magenta")
        subtitle = Text("First-Time Configuration", style="dim orange")
        panel = Panel(
            f"{title}\n{subtitle}",
            border_style="magenta",
            padding=(1, 2),
        )
        console.print(panel)
    else:
        print("\n" + "=" * 50)
        print("APOD Wallpaper Setup Wizard")
        print("First-Time Configuration")
        print("=" * 50 + "\n")


def print_section(title: str, console=None):
    """Print a section header."""
    if console and RICH_AVAILABLE:
        console.rule(title, style="magenta")
    else:
        print(f"\n{title}")
        print("-" * 40)


def main():
    console = get_console()
    print_banner(console)

    # Step 1: Welcome
    print_section("Welcome", console)
    if console and RICH_AVAILABLE:
        console.print("Thank you for installing APOD Wallpaper!")
        console.print("This wizard will help you configure the application.\n")
    else:
        print("Thank you for installing APOD Wallpaper!")
        print("This wizard will help you configure the application.\n")

    # Step 2: API Key
    print_section("NASA API Key", console)
    if console and RICH_AVAILABLE:
        console.print("APOD uses the NASA API to fetch images.")
        console.print("You're using the [bold]DEMO_KEY[/bold] by default (limited requests).")
        console.print("For unlimited access, get a free API key at:")
        console.print("[link]https://api.nasa.gov[/link]\n")
    else:
        print("APOD uses the NASA API to fetch images.")
        print("You're using the DEMO_KEY by default (limited requests).")
        print("For unlimited access, get a free API key at:")
        print("https://api.nasa.gov\n")

    use_custom_key = Confirm.ask(
        "Do you want to set a NASA API key now?",
        default=False,
        console=console if RICH_AVAILABLE else None
    )

    api_key = None
    if use_custom_key:
        api_key = Prompt.ask(
            "Paste your NASA API key",
            default="DEMO_KEY",
            password=False,
            console=console if RICH_AVAILABLE else None
        )
        if api_key and api_key != "DEMO_KEY":
            # Try to set environment variable
            try:
                os.environ["NASA_API_KEY"] = api_key
                if console and RICH_AVAILABLE:
                    console.print("[green]✓[/green] API key will be used for this session")
                else:
                    print("[OK] API key set")
            except Exception as e:
                if console and RICH_AVAILABLE:
                    console.print(f"[yellow]⚠[/yellow] Could not set API key: {e}")
                else:
                    print(f"Warning: Could not set API key: {e}")

    # Step 3: Test Run
    print_section("Test Run", console)
    if console and RICH_AVAILABLE:
        console.print("Would you like to test the wallpaper setter now?")
        console.print("This will fetch today's APOD and set it as your wallpaper.\n")
    else:
        print("Would you like to test the wallpaper setter now?")
        print("This will fetch today's APOD and set it as your wallpaper.\n")

    run_test = Confirm.ask(
        "Run a test now?",
        default=True,
        console=console if RICH_AVAILABLE else None
    )

    if run_test:
        if console and RICH_AVAILABLE:
            console.print("\n[cyan]→[/cyan] Running test...\n")
        else:
            print("\nRunning test...\n")

        # Find the APODWallpaper executable
        possible_paths = [
            Path.cwd() / "APODWallpaper.exe",
            Path.cwd().parent / "APODWallpaper.exe",
            Path.home() / "AppData" / "Local" / "Programs" / "APODWallpaper" / "APODWallpaper.exe",
        ]

        exe_path = None
        for path in possible_paths:
            if path.exists():
                exe_path = path
                break

        if exe_path:
            try:
                cmd = [str(exe_path), "--dry-run", "--random"]
                if api_key and api_key != "DEMO_KEY":
                    cmd.extend(["--api-key", api_key])

                result = subprocess.run(cmd, capture_output=False)
                if result.returncode == 0:
                    if console and RICH_AVAILABLE:
                        console.print("[green]✓[/green] Test completed successfully!")
                    else:
                        print("Test completed successfully!")
                else:
                    if console and RICH_AVAILABLE:
                        console.print("[yellow]⚠[/yellow] Test had issues (exit code: {})".format(result.returncode))
                    else:
                        print(f"Test had issues (exit code: {result.returncode})")
            except Exception as e:
                if console and RICH_AVAILABLE:
                    console.print(f"[red]✗[/red] Error running test: {e}")
                else:
                    print(f"Error running test: {e}")
        else:
            if console and RICH_AVAILABLE:
                console.print("[red]✗[/red] Could not find APODWallpaper.exe")
            else:
                print("Could not find APODWallpaper.exe")

    # Step 4: Completion
    print_section("Setup Complete", console)
    if console and RICH_AVAILABLE:
        console.print("[green]✓[/green] Setup is complete!")
        console.print("\n[bold]Next steps:[/bold]")
        console.print("• The app will run automatically on Windows logon")
        console.print("• You can manually run it anytime from the Start Menu")
        console.print("• Edit [yellow]apodwp_launcher.bat[/yellow] to customize options")
        console.print("\n[link]https://apod.nasa.gov[/link]")
    else:
        print("Setup is complete!")
        print("\nNext steps:")
        print("• The app will run automatically on Windows logon")
        print("• You can manually run it anytime from the Start Menu")
        print("• Edit apodwp_launcher.bat to customize options")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSetup cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
