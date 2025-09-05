#!/usr/bin/env python3
"""
MkDocs Development Helper Script
Automated local testing with dependency management for Memori SDK documentation
"""

import argparse
import signal
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import List


class Colors:
    """ANSI color codes for terminal output"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    END = "\033[0m"


class MkDocsDevHelper:
    """Automated MkDocs development and testing helper"""

    def __init__(self):
        self.project_root = Path.cwd()
        self.mkdocs_config = self.project_root / "mkdocs.yml"
        self.docs_dir = self.project_root / "docs"
        self.site_dir = self.project_root / "site"
        self.server_process = None
        self.required_packages = [
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.0.0",
            "mkdocs-minify-plugin>=0.7.0",
            "pymdown-extensions>=10.0.0",
            "mkdocs-git-revision-date-localized-plugin>=1.2.0",
            "mkdocstrings[python]>=0.24.0",
            "mkdocs-autorefs>=0.5.0",
        ]

    def print_status(self, message: str, status: str = "INFO"):
        """Print colored status messages"""
        colors = {
            "INFO": Colors.BLUE,
            "SUCCESS": Colors.GREEN,
            "WARNING": Colors.YELLOW,
            "ERROR": Colors.RED,
            "PROCESS": Colors.CYAN,
        }
        color = colors.get(status, Colors.WHITE)
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{color}[{timestamp}] {status}: {message}{Colors.END}")

    def run_command(
        self, cmd: List[str], capture_output: bool = False, check: bool = True
    ) -> subprocess.CompletedProcess:
        """Run a command with proper error handling"""
        try:
            self.print_status(f"Running: {' '.join(cmd)}", "PROCESS")
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                check=check,
                cwd=self.project_root,
            )
            return result
        except subprocess.CalledProcessError as e:
            self.print_status(f"Command failed: {e}", "ERROR")
            if capture_output and e.stdout:
                print(f"STDOUT: {e.stdout}")
            if capture_output and e.stderr:
                print(f"STDERR: {e.stderr}")
            raise

    def check_dependencies(self) -> bool:
        """Check if required dependencies are installed"""
        self.print_status("Checking MkDocs dependencies...", "INFO")

        # Try to build first - if it works, dependencies are fine
        try:
            result = self.run_command(
                ["mkdocs", "build", "--strict", "--clean"],
                capture_output=True,
                check=False,
            )
            if result.returncode == 0:
                self.print_status(
                    "All MkDocs dependencies are working correctly!", "SUCCESS"
                )
                return True
        except FileNotFoundError:
            self.print_status(
                "MkDocs not found (FileNotFoundError). This likely means MkDocs is not installed.",
                "ERROR",
            )

        self.print_status(
            "Some dependencies may be missing. Checking individually...", "WARNING"
        )
        return False

    def install_dependencies(self) -> bool:
        """Install missing MkDocs dependencies"""
        self.print_status("Installing MkDocs dependencies...", "INFO")

        try:
            # Upgrade pip first
            self.run_command(
                [sys.executable, "-m", "pip", "install", "--upgrade", "pip"]
            )

            # Install all required packages
            install_cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
            ] + self.required_packages
            self.run_command(install_cmd)

            self.print_status("Dependencies installed successfully!", "SUCCESS")
            return True

        except subprocess.CalledProcessError as e:
            self.print_status(f"Failed to install dependencies: {e}", "ERROR")
            return False

    def validate_mkdocs_config(self) -> bool:
        """Validate MkDocs configuration file"""
        self.print_status("Validating MkDocs configuration...", "INFO")

        if not self.mkdocs_config.exists():
            self.print_status(f"MkDocs config not found: {self.mkdocs_config}", "ERROR")
            return False

        if not self.docs_dir.exists():
            self.print_status(f"Docs directory not found: {self.docs_dir}", "ERROR")
            return False

        try:
            # Test mkdocs config by doing a dry build
            result = self.run_command(
                ["mkdocs", "build", "--strict", "--clean"],
                capture_output=True,
                check=False,
            )

            if result.returncode == 0:
                self.print_status("MkDocs configuration is valid!", "SUCCESS")
                return True
            else:
                self.print_status("MkDocs configuration has issues:", "ERROR")
                if result.stderr:
                    print(result.stderr)
                return False

        except FileNotFoundError:
            self.print_status("MkDocs command not found. Installing...", "WARNING")
            return False

    def build_docs(self, clean: bool = True, strict: bool = True) -> bool:
        """Build the documentation"""
        self.print_status("Building documentation...", "INFO")

        build_cmd = ["mkdocs", "build"]
        if clean:
            build_cmd.append("--clean")
        if strict:
            build_cmd.append("--strict")

        try:
            self.run_command(build_cmd)
            self.print_status(
                f"Documentation built successfully in {self.site_dir}", "SUCCESS"
            )

            # Show build statistics
            if self.site_dir.exists():
                file_count = sum(1 for _ in self.site_dir.rglob("*") if _.is_file())
                self.print_status(f"Generated {file_count} files", "INFO")

            return True

        except subprocess.CalledProcessError:
            self.print_status("Failed to build documentation", "ERROR")
            return False

    def serve_docs(
        self, host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True
    ) -> None:
        """Serve documentation locally"""
        url = f"http://{host}:{port}"
        self.print_status(f"Starting MkDocs dev server on {url}", "INFO")
        self.print_status("Press Ctrl+C to stop the server", "INFO")

        if open_browser:
            # Open browser after a short delay
            threading.Timer(2.0, lambda: webbrowser.open(url)).start()

        try:
            # Start the server
            serve_cmd = ["mkdocs", "serve", "--dev-addr", f"{host}:{port}"]
            process = subprocess.Popen(serve_cmd, cwd=self.project_root)
            self.server_process = process

            # Wait for the process
            process.wait()

        except KeyboardInterrupt:
            self.print_status("Stopping MkDocs server...", "INFO")
        except subprocess.CalledProcessError as e:
            self.print_status(f"Server failed: {e}", "ERROR")
        finally:
            if self.server_process:
                self.server_process.terminate()

    def cleanup(self) -> None:
        """Clean up build artifacts"""
        self.print_status("Cleaning up build artifacts...", "INFO")

        if self.site_dir.exists():
            import shutil

            shutil.rmtree(self.site_dir)
            self.print_status("Removed site directory", "SUCCESS")

        # Clean up any cache directories
        cache_dirs = [
            self.project_root / ".mkdocs_cache",
            self.project_root / "__pycache__",
        ]

        for cache_dir in cache_dirs:
            if cache_dir.exists():
                import shutil

                shutil.rmtree(cache_dir)
                self.print_status(f"Removed {cache_dir.name}", "SUCCESS")

    def check_for_updates(self) -> None:
        """Check for broken links and missing files"""
        self.print_status("Checking for documentation issues...", "INFO")

        issues = []

        # Check for missing images
        for md_file in self.docs_dir.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            # Simple regex to find image references
            import re

            img_refs = re.findall(r"!\[.*?\]\((.*?)\)", content)
            for img_ref in img_refs:
                if not img_ref.startswith("http"):
                    img_path = (md_file.parent / img_ref).resolve()
                    if not img_path.exists():
                        issues.append(f"Missing image: {img_ref} in {md_file.name}")

        if issues:
            self.print_status(f"Found {len(issues)} documentation issues:", "WARNING")
            for issue in issues[:5]:  # Show first 5 issues
                print(f"  - {issue}")
            if len(issues) > 5:
                print(f"  ... and {len(issues) - 5} more issues")
        else:
            self.print_status("No documentation issues found!", "SUCCESS")

    def show_stats(self) -> None:
        """Show documentation statistics"""
        if not self.docs_dir.exists():
            return

        md_files = list(self.docs_dir.rglob("*.md"))
        total_words = 0
        total_lines = 0

        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8")
                total_lines += len(content.splitlines())
                total_words += len(content.split())
            except Exception:
                continue

        self.print_status("📊 Documentation Statistics:", "INFO")
        print(f"  • Markdown files: {len(md_files)}")
        print(f"  • Total lines: {total_lines:,}")
        print(f"  • Total words: {total_words:,}")
        print(
            f"  • Average words per file: {total_words // len(md_files) if md_files else 0:,}"
        )


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print(f"\n{Colors.YELLOW}Received interrupt signal. Cleaning up...{Colors.END}")
    sys.exit(0)


def main():
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)

    parser = argparse.ArgumentParser(
        description="MkDocs Development Helper for Memori SDK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python docs_dev.py                    # Quick start (install deps + serve)
  python docs_dev.py --install-only     # Just install dependencies
  python docs_dev.py --build            # Build documentation
  python docs_dev.py --serve --port 8080  # Serve on custom port
  python docs_dev.py --check            # Validate and check issues
  python docs_dev.py --clean            # Clean build artifacts
        """,
    )

    parser.add_argument(
        "--install-only", action="store_true", help="Install dependencies only"
    )
    parser.add_argument("--build", action="store_true", help="Build documentation")
    parser.add_argument(
        "--serve", action="store_true", help="Serve documentation locally"
    )
    parser.add_argument(
        "--check", action="store_true", help="Check documentation for issues"
    )
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts")
    parser.add_argument(
        "--stats", action="store_true", help="Show documentation statistics"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port for dev server (default: 8000)"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host for dev server (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="Don't open browser automatically"
    )

    args = parser.parse_args()

    # Initialize helper
    helper = MkDocsDevHelper()

    print(f"{Colors.BOLD}{Colors.CYAN}")
    print("╭─────────────────────────────────────╮")
    print("│     MkDocs Development Helper       │")
    print("│        for Memori SDK              │")
    print("╰─────────────────────────────────────╯")
    print(f"{Colors.END}")

    try:
        # Check and install dependencies if needed
        if not helper.check_dependencies():
            if (
                args.install_only
                or input("\nInstall missing dependencies? [Y/n]: ").lower() != "n"
            ):
                if not helper.install_dependencies():
                    sys.exit(1)
                helper.print_status(
                    "Dependencies installed! Please run the script again.", "SUCCESS"
                )
                if args.install_only:
                    sys.exit(0)

        # Handle specific actions
        if args.clean:
            helper.cleanup()
            return

        if args.stats:
            helper.show_stats()
            return

        # Validate configuration
        if not helper.validate_mkdocs_config():
            helper.print_status(
                "Please fix configuration issues before continuing", "ERROR"
            )
            sys.exit(1)

        if args.check:
            helper.check_for_updates()
            helper.show_stats()
            return

        if args.build:
            if helper.build_docs():
                helper.show_stats()
            return

        if args.serve or (
            not any([args.install_only, args.build, args.check, args.clean, args.stats])
        ):
            # Default action: serve
            helper.print_status("Starting development server...", "INFO")
            helper.serve_docs(
                host=args.host, port=args.port, open_browser=not args.no_browser
            )

    except KeyboardInterrupt:
        helper.print_status("Operation cancelled by user", "WARNING")
    except Exception as e:
        helper.print_status(f"Unexpected error: {e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
