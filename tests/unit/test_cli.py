"""
Unit tests for the memori CLI module

Tests for all CLI commands: --version, init, and health
"""

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the CLI module
from memori.cli import cmd_health, cmd_init, cmd_version, get_version, main


class TestGetVersion:
    """Tests for get_version function"""

    def test_get_version_returns_string(self):
        """Test that get_version returns a version string"""
        version = get_version()
        assert isinstance(version, str)
        assert len(version) > 0

    def test_get_version_format(self):
        """Test that version has expected format (x.y.z or 'unknown')"""
        version = get_version()
        # Should be either semver-like or 'unknown'
        assert version == "unknown" or "." in version


class TestVersionCommand:
    """Tests for --version command"""

    def test_cmd_version_output(self, capsys):
        """Test that --version prints version information"""
        args = MagicMock()
        exit_code = cmd_version(args)

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "memori version" in captured.out.lower()

    def test_version_flag_via_main(self, capsys):
        """Test --version flag through main function"""
        with patch.object(sys, "argv", ["memori", "--version"]):
            exit_code = main()

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "version" in captured.out.lower()


class TestInitCommand:
    """Tests for init command"""

    def test_init_creates_config_file(self, tmp_path, monkeypatch):
        """Test that init creates memori.json"""
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "memori.json"

        args = MagicMock()
        args.force = False

        exit_code = cmd_init(args)

        assert exit_code == 0
        assert config_path.exists()

    def test_init_creates_valid_json(self, tmp_path, monkeypatch, capsys):
        """Test that created config is valid JSON"""
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "memori.json"

        args = MagicMock()
        args.force = False

        cmd_init(args)

        # Verify it's valid JSON
        with open(config_path, "r") as f:
            config = json.load(f)

        # Check required sections
        assert "database" in config
        assert "agents" in config
        assert "memory" in config
        assert "logging" in config

    def test_init_config_has_expected_structure(self, tmp_path, monkeypatch):
        """Test that config has all expected fields"""
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "memori.json"

        args = MagicMock()
        args.force = False

        cmd_init(args)

        with open(config_path, "r") as f:
            config = json.load(f)

        # Check database section
        assert "connection_string" in config["database"]
        assert "pool_size" in config["database"]

        # Check agents section
        assert "openai_api_key" in config["agents"]
        assert "default_model" in config["agents"]

        # Check memory section
        assert "namespace" in config["memory"]
        assert "retention_policy" in config["memory"]

        # Check logging section
        assert "level" in config["logging"]

    def test_init_fails_if_file_exists_without_force(self, tmp_path, monkeypatch, capsys):
        """Test that init fails if file exists and --force not used"""
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "memori.json"

        # Create existing file
        config_path.write_text('{"test": "data"}')

        args = MagicMock()
        args.force = False

        exit_code = cmd_init(args)

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "already exists" in captured.out.lower()

    def test_init_overwrites_with_force_flag(self, tmp_path, monkeypatch, capsys):
        """Test that init overwrites existing file with --force"""
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "memori.json"

        # Create existing file
        config_path.write_text('{"old": "data"}')

        args = MagicMock()
        args.force = True

        exit_code = cmd_init(args)

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "overwritten" in captured.out.lower()

        # Verify new content
        with open(config_path, "r") as f:
            config = json.load(f)

        assert "old" not in config
        assert "database" in config

    def test_init_prints_next_steps(self, tmp_path, monkeypatch, capsys):
        """Test that init prints helpful next steps"""
        monkeypatch.chdir(tmp_path)

        args = MagicMock()
        args.force = False

        cmd_init(args)

        captured = capsys.readouterr()
        assert "next steps" in captured.out.lower()
        assert "from memori import" in captured.out.lower()


class TestHealthCommand:
    """Tests for health command"""

    def test_health_basic_check(self, capsys):
        """Test basic health check without config file"""
        args = MagicMock()
        args.config = None
        args.check_db = False

        # Should not fail even without config
        exit_code = cmd_health(args)

        captured = capsys.readouterr()
        assert "health check" in captured.out.lower()
        assert "package import" in captured.out.lower()

    def test_health_checks_package_import(self, capsys):
        """Test that health checks package import"""
        args = MagicMock()
        args.config = None
        args.check_db = False

        cmd_health(args)

        captured = capsys.readouterr()
        # Should show successful import
        assert "memori" in captured.out.lower()
        assert "✓" in captured.out or "success" in captured.out.lower()

    def test_health_checks_dependencies(self, capsys):
        """Test that health checks for required dependencies"""
        args = MagicMock()
        args.config = None
        args.check_db = False

        cmd_health(args)

        captured = capsys.readouterr()
        # Should check for core dependencies
        assert "dependencies" in captured.out.lower()
        output_lower = captured.out.lower()
        # At least some common dependencies should be mentioned
        assert any(
            dep in output_lower
            for dep in ["pydantic", "sqlalchemy", "openai", "litellm"]
        )

    def test_health_warns_if_no_config(self, tmp_path, monkeypatch, capsys):
        """Test that health warns if config file not found"""
        monkeypatch.chdir(tmp_path)

        args = MagicMock()
        args.config = None
        args.check_db = False

        cmd_health(args)

        captured = capsys.readouterr()
        assert "not found" in captured.out.lower() or "⚠" in captured.out

    def test_health_validates_config_if_exists(self, tmp_path, monkeypatch, capsys):
        """Test that health validates config file if it exists"""
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "memori.json"

        # Create valid config
        valid_config = {
            "database": {"connection_string": "sqlite:///test.db"},
            "agents": {"default_model": "gpt-4o-mini"},
            "memory": {"namespace": "test"},
            "logging": {"level": "INFO"},
        }

        with open(config_path, "w") as f:
            json.dump(valid_config, f)

        args = MagicMock()
        args.config = None
        args.check_db = False

        exit_code = cmd_health(args)

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "config file valid" in captured.out.lower() or "✓" in captured.out

    def test_health_detects_invalid_json(self, tmp_path, monkeypatch, capsys):
        """Test that health detects invalid JSON in config"""
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "memori.json"

        # Create invalid JSON
        config_path.write_text("{invalid json content")

        args = MagicMock()
        args.config = None
        args.check_db = False

        exit_code = cmd_health(args)

        captured = capsys.readouterr()
        assert exit_code != 0
        assert "invalid" in captured.out.lower() or "✗" in captured.out

    def test_health_detects_missing_sections(self, tmp_path, monkeypatch, capsys):
        """Test that health detects missing required config sections"""
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "memori.json"

        # Create config missing required sections
        incomplete_config = {"database": {"connection_string": "sqlite:///test.db"}}

        with open(config_path, "w") as f:
            json.dump(incomplete_config, f)

        args = MagicMock()
        args.config = None
        args.check_db = False

        exit_code = cmd_health(args)

        captured = capsys.readouterr()
        assert exit_code != 0
        assert "missing" in captured.out.lower() or "✗" in captured.out

    def test_health_with_custom_config_path(self, tmp_path, monkeypatch, capsys):
        """Test health with custom config path"""
        monkeypatch.chdir(tmp_path)
        custom_config = tmp_path / "custom_config.json"

        # Create valid config at custom path
        valid_config = {
            "database": {"connection_string": "sqlite:///test.db"},
            "agents": {"default_model": "gpt-4o-mini"},
            "memory": {"namespace": "test"},
            "logging": {"level": "INFO"},
        }

        with open(custom_config, "w") as f:
            json.dump(valid_config, f)

        args = MagicMock()
        args.config = str(custom_config)
        args.check_db = False

        exit_code = cmd_health(args)

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "custom_config.json" in captured.out

    def test_health_shows_summary(self, capsys):
        """Test that health shows a summary at the end"""
        args = MagicMock()
        args.config = None
        args.check_db = False

        cmd_health(args)

        captured = capsys.readouterr()
        # Should show summary with pass/fail status
        assert "=" in captured.out  # Separator lines
        output_lower = captured.out.lower()
        assert "passed" in output_lower or "failed" in output_lower


class TestMainFunction:
    """Tests for main CLI entry point"""

    def test_main_no_args_shows_help(self, capsys):
        """Test that running with no args shows help"""
        with patch.object(sys, "argv", ["memori"]):
            exit_code = main()

        captured = capsys.readouterr()
        assert exit_code == 0
        # Should show usage/help
        assert "usage:" in captured.out.lower() or "memori" in captured.out.lower()

    def test_main_init_command(self, tmp_path, monkeypatch, capsys):
        """Test init command through main"""
        monkeypatch.chdir(tmp_path)

        with patch.object(sys, "argv", ["memori", "init"]):
            exit_code = main()

        assert exit_code == 0
        assert (tmp_path / "memori.json").exists()

    def test_main_init_with_force(self, tmp_path, monkeypatch, capsys):
        """Test init --force through main"""
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "memori.json"
        config_path.write_text("{}")

        with patch.object(sys, "argv", ["memori", "init", "--force"]):
            exit_code = main()

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "overwritten" in captured.out.lower()

    def test_main_health_command(self, capsys):
        """Test health command through main"""
        with patch.object(sys, "argv", ["memori", "health"]):
            exit_code = main()

        captured = capsys.readouterr()
        assert "health check" in captured.out.lower()

    def test_main_health_with_flags(self, tmp_path, monkeypatch, capsys):
        """Test health with --config and --check-db flags"""
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "test.json"

        # Create minimal valid config
        with open(config_path, "w") as f:
            json.dump(
                {
                    "database": {},
                    "agents": {},
                    "memory": {},
                    "logging": {},
                },
                f,
            )

        with patch.object(
            sys, "argv", ["memori", "health", "--config", str(config_path)]
        ):
            exit_code = main()

        captured = capsys.readouterr()
        assert "test.json" in captured.out


class TestCLIIntegration:
    """Integration tests for complete CLI workflows"""

    def test_full_workflow_init_and_health(self, tmp_path, monkeypatch, capsys):
        """Test complete workflow: init then health check"""
        monkeypatch.chdir(tmp_path)

        # Step 1: Initialize
        with patch.object(sys, "argv", ["memori", "init"]):
            init_exit = main()

        assert init_exit == 0

        # Step 2: Health check
        with patch.object(sys, "argv", ["memori", "health"]):
            health_exit = main()

        captured = capsys.readouterr()
        assert health_exit == 0
        assert "✓" in captured.out or "passed" in captured.out.lower()

    def test_version_displays_correctly(self, capsys):
        """Test that version command displays properly"""
        with patch.object(sys, "argv", ["memori", "--version"]):
            exit_code = main()

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "memori version" in captured.out.lower()
        # Should have actual version number or 'unknown'
        assert any(
            c.isdigit() for c in captured.out
        ) or "unknown" in captured.out.lower()
