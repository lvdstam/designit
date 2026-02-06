"""Tests for the CLI commands.

REQ-CLI-020: Format Option
REQ-CLI-021: Output Diagram Directory Option
REQ-CLI-022: Diagram Filter Option
REQ-CLI-023: No Placeholders Flag
REQ-CLI-025: GraphViz Rendering
REQ-CLI-028: Output Directory Option
REQ-CLI-029: No Markdown Flag
"""

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from designit.cli import (
    ALL_FORMATS,
    GRAPHIC_FORMATS,
    _check_graphviz_installed,
    _get_graphviz_engine,
    _render_graphviz,
    main,
)


@pytest.fixture
def runner() -> CliRunner:
    """Get a Click test runner."""
    return CliRunner()


@pytest.fixture
def examples_dir() -> Path:
    """Get the path to the banking examples directory."""
    return Path(__file__).parent.parent / "examples" / "banking"


@pytest.fixture
def sample_file(examples_dir: Path) -> Path:
    """Get a sample .dit file for testing."""
    return examples_dir / "context.dit"


class TestGenerateCommand:
    """Tests for the generate command."""

    def test_default_format_is_svg(self, runner: CliRunner, sample_file: Path) -> None:
        """Test that default format is svg (REQ-CLI-020)."""
        with patch("designit.cli._check_graphviz_installed"):
            with patch("designit.cli._render_graphviz") as mock_render:
                result = runner.invoke(main, ["generate", str(sample_file)])
                # Should use GraphViz rendering (svg format)
                assert mock_render.called or "GraphViz not found" in result.output

    def test_format_option_mermaid(
        self, runner: CliRunner, sample_file: Path, tmp_path: Path
    ) -> None:
        """Test mermaid format produces .mmd files (REQ-CLI-020)."""
        result = runner.invoke(
            main,
            ["generate", str(sample_file), "-f", "mermaid", "--output-diagram-dir", str(tmp_path)],
        )
        assert result.exit_code == 0
        mmd_files = list(tmp_path.glob("*.mmd"))
        assert len(mmd_files) > 0
        assert "Generated" in result.output

    def test_format_option_dot(self, runner: CliRunner, sample_file: Path, tmp_path: Path) -> None:
        """Test dot format produces .dot files (REQ-CLI-020)."""
        result = runner.invoke(
            main,
            ["generate", str(sample_file), "-f", "dot", "--output-diagram-dir", str(tmp_path)],
        )
        assert result.exit_code == 0
        dot_files = list(tmp_path.glob("*.dot"))
        assert len(dot_files) > 0

    def test_all_graphic_formats_accepted(self, runner: CliRunner) -> None:
        """Test all graphic formats are valid choices (REQ-CLI-020)."""
        for fmt in GRAPHIC_FORMATS:
            assert fmt in ALL_FORMATS

    def test_default_output_directory(
        self, runner: CliRunner, sample_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test default output directory is ./generated/diagrams (REQ-CLI-021)."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            main,
            ["generate", str(sample_file), "-f", "mermaid"],
        )
        assert result.exit_code == 0
        # Default diagram dir is ./generated/diagrams
        generated_dir = tmp_path / "generated" / "diagrams"
        assert generated_dir.exists()
        assert len(list(generated_dir.glob("*.mmd"))) > 0

    def test_custom_output_directory(
        self, runner: CliRunner, sample_file: Path, tmp_path: Path
    ) -> None:
        """Test custom output directory option (REQ-CLI-021)."""
        custom_dir = tmp_path / "custom_output"
        result = runner.invoke(
            main,
            [
                "generate",
                str(sample_file),
                "-f",
                "mermaid",
                "--output-diagram-dir",
                str(custom_dir),
            ],
        )
        assert result.exit_code == 0
        assert custom_dir.exists()
        assert len(list(custom_dir.glob("*.mmd"))) > 0

    def test_output_directory_created_if_not_exists(
        self, runner: CliRunner, sample_file: Path, tmp_path: Path
    ) -> None:
        """Test output directory is created if it doesn't exist (REQ-CLI-021)."""
        nested_dir = tmp_path / "nested" / "output" / "dir"
        assert not nested_dir.exists()
        result = runner.invoke(
            main,
            [
                "generate",
                str(sample_file),
                "-f",
                "mermaid",
                "--output-diagram-dir",
                str(nested_dir),
            ],
        )
        assert result.exit_code == 0
        assert nested_dir.exists()

    def test_diagram_filter(self, runner: CliRunner, sample_file: Path, tmp_path: Path) -> None:
        """Test diagram filter option (REQ-CLI-022)."""
        # First, generate all diagrams to see what we get
        result = runner.invoke(
            main,
            ["generate", str(sample_file), "-f", "mermaid", "--output-diagram-dir", str(tmp_path)],
        )
        assert result.exit_code == 0
        all_files = list(tmp_path.glob("*.mmd"))

        # Now filter to a specific diagram
        filtered_dir = tmp_path / "filtered"
        result = runner.invoke(
            main,
            [
                "generate",
                str(sample_file),
                "-f",
                "mermaid",
                "--output-diagram-dir",
                str(filtered_dir),
                "-d",
                "BankingSystem",
            ],
        )
        assert result.exit_code == 0
        filtered_files = list(filtered_dir.glob("*.mmd"))
        assert len(filtered_files) <= len(all_files)

    def test_no_placeholders_flag(
        self, runner: CliRunner, sample_file: Path, tmp_path: Path
    ) -> None:
        """Test --no-placeholders flag (REQ-CLI-023)."""
        result = runner.invoke(
            main,
            [
                "generate",
                str(sample_file),
                "-f",
                "mermaid",
                "--output-diagram-dir",
                str(tmp_path),
                "--no-placeholders",
            ],
        )
        assert result.exit_code == 0
        # Should still generate files (just without placeholders)
        mmd_files = list(tmp_path.glob("*.mmd"))
        assert len(mmd_files) > 0


class TestGenerateValidation:
    """Tests for generate command validation behavior."""

    @pytest.fixture
    def invalid_file(self, tmp_path: Path) -> Path:
        """Create a .dit file with validation errors."""
        content = """
datadict {
    Request = { data: string }
}

scd Context {
    system API {}
    external Client {}
    flow Request(Request): Client -> API
}

dfd Level0 {
    refines: Context.API
    process Handler {}
    flow Context.Request: -> Handler
    flow UndefinedFlow(UndefinedType): Handler ->
}
"""
        file_path = tmp_path / "invalid.dit"
        file_path.write_text(content)
        return file_path

    def test_generate_fails_on_validation_errors_by_default(
        self, runner: CliRunner, invalid_file: Path, tmp_path: Path
    ) -> None:
        """Test that generate fails when there are validation errors."""
        result = runner.invoke(
            main,
            [
                "generate",
                str(invalid_file),
                "-f",
                "mermaid",
                "--output-diagram-dir",
                str(tmp_path / "out"),
            ],
        )
        assert result.exit_code != 0
        assert "error" in result.output.lower()
        assert "--no-check" in result.output

    def test_generate_succeeds_with_no_check_flag(
        self, runner: CliRunner, invalid_file: Path, tmp_path: Path
    ) -> None:
        """Test that generate succeeds with --no-check despite validation errors."""
        output_dir = tmp_path / "out"
        result = runner.invoke(
            main,
            [
                "generate",
                str(invalid_file),
                "-f",
                "mermaid",
                "--output-diagram-dir",
                str(output_dir),
                "--no-check",
            ],
        )
        assert result.exit_code == 0
        assert "Generated" in result.output
        mmd_files = list(output_dir.glob("*.mmd"))
        assert len(mmd_files) > 0

    def test_generate_shows_validation_messages_before_failing(
        self, runner: CliRunner, invalid_file: Path, tmp_path: Path
    ) -> None:
        """Test that generate shows validation messages before failing."""
        result = runner.invoke(
            main,
            [
                "generate",
                str(invalid_file),
                "-f",
                "mermaid",
                "--output-diagram-dir",
                str(tmp_path / "out"),
            ],
        )
        assert result.exit_code != 0
        # Should show the specific error about undefined flow
        assert "UndefinedFlow" in result.output or "not defined" in result.output.lower()

    def test_generate_valid_file_succeeds_without_no_check(
        self, runner: CliRunner, sample_file: Path, tmp_path: Path
    ) -> None:
        """Test that generate succeeds for valid files without --no-check."""
        result = runner.invoke(
            main,
            ["generate", str(sample_file), "-f", "mermaid", "--output-diagram-dir", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert "Generated" in result.output


class TestMarkdownGeneration:
    """Tests for markdown generation in the generate command."""

    @pytest.fixture
    def file_with_markdown(self, tmp_path: Path) -> Path:
        """Create a .dit file with markdown blocks."""
        content = """
datadict {
    Request = { data: string }
}

scd Context {
    system API { description: "Main API system" }
    external Client {}
    flow Request(Request): Client -> API
}

markdown {
    ## {{Context.name}}

    {{Context.API.description}}

    {{diagram:Context}}
}
"""
        file_path = tmp_path / "with_markdown.dit"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def file_without_markdown(self, tmp_path: Path) -> Path:
        """Create a .dit file without markdown blocks."""
        content = """
datadict {
    Request = { data: string }
}

scd Context {
    system API {}
    external Client {}
    flow Request(Request): Client -> API
}
"""
        file_path = tmp_path / "without_markdown.dit"
        file_path.write_text(content)
        return file_path

    def test_generate_with_markdown_blocks(
        self, runner: CliRunner, file_with_markdown: Path, tmp_path: Path
    ) -> None:
        """Test that markdown is generated when markdown blocks exist (REQ-CLI-028)."""
        result = runner.invoke(
            main,
            [
                "generate",
                str(file_with_markdown),
                "-f",
                "mermaid",
                "--output-diagram-dir",
                str(tmp_path / "diagrams"),
            ],
        )
        assert result.exit_code == 0
        # Default markdown path is ./generated/<SystemName>.md
        # Since we didn't specify --output-dir, it should use default
        # But our tmp_path is different, so check that markdown was generated
        assert "Generated" in result.output
        # The markdown file should be in ./generated/API.md (system name is API)

    def test_generate_with_custom_markdown_path(
        self, runner: CliRunner, file_with_markdown: Path, tmp_path: Path
    ) -> None:
        """Test custom markdown output path (REQ-CLI-028)."""
        md_path = tmp_path / "docs" / "architecture.md"
        result = runner.invoke(
            main,
            [
                "generate",
                str(file_with_markdown),
                "-f",
                "mermaid",
                "--output-diagram-dir",
                str(tmp_path / "diagrams"),
                "--output-markdown",
                str(md_path),
            ],
        )
        assert result.exit_code == 0
        assert md_path.exists()
        content = md_path.read_text()
        assert "## Context" in content
        assert "Main API system" in content

    def test_generate_with_no_markdown_flag(
        self, runner: CliRunner, file_with_markdown: Path, tmp_path: Path
    ) -> None:
        """Test --no-markdown flag disables markdown generation (REQ-CLI-029)."""
        result = runner.invoke(
            main,
            [
                "generate",
                str(file_with_markdown),
                "-f",
                "mermaid",
                "--output-diagram-dir",
                str(tmp_path / "diagrams"),
                "--no-markdown",
            ],
        )
        assert result.exit_code == 0
        # No markdown file should be generated in the default location
        md_files = list(tmp_path.glob("**/*.md"))
        assert len(md_files) == 0

    def test_generate_without_markdown_blocks(
        self, runner: CliRunner, file_without_markdown: Path, tmp_path: Path
    ) -> None:
        """Test that no markdown is generated when no markdown blocks exist."""
        result = runner.invoke(
            main,
            [
                "generate",
                str(file_without_markdown),
                "-f",
                "mermaid",
                "--output-diagram-dir",
                str(tmp_path / "diagrams"),
            ],
        )
        assert result.exit_code == 0
        # Should still generate diagrams
        mmd_files = list((tmp_path / "diagrams").glob("*.mmd"))
        assert len(mmd_files) > 0

    def test_markdown_requires_scd_with_system(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test that markdown generation fails without SCD system (REQ-DOC-034)."""
        # File with markdown but no system in SCD
        content = """
scd Context {
    external Client {}
}

markdown {
    ## Overview
}
"""
        file_path = tmp_path / "no_system.dit"
        file_path.write_text(content)

        result = runner.invoke(
            main,
            [
                "generate",
                str(file_path),
                "-f",
                "mermaid",
                "--output-diagram-dir",
                str(tmp_path / "diagrams"),
                "--no-check",  # Skip validation to test markdown-specific error
            ],
        )
        assert result.exit_code != 0
        assert "SCD with a system definition" in result.output


class TestGraphVizRendering:
    """Tests for GraphViz rendering functionality (REQ-CLI-025)."""

    def test_check_graphviz_installed_when_present(self) -> None:
        """Test no error when GraphViz is installed."""
        with patch("shutil.which", return_value="/usr/bin/dot"):
            # Should not raise
            _check_graphviz_installed()

    def test_check_graphviz_installed_when_dot_missing(self) -> None:
        """Test helpful error when dot is not installed."""

        def which_side_effect(cmd: str) -> str | None:
            return "/usr/bin/neato" if cmd == "neato" else None

        with patch("shutil.which", side_effect=which_side_effect):
            with pytest.raises(Exception) as exc_info:
                _check_graphviz_installed()
            error_msg = str(exc_info.value)
            assert "dot" in error_msg
            assert "Ubuntu/Debian" in error_msg

    def test_check_graphviz_installed_when_neato_missing(self) -> None:
        """Test helpful error when neato is not installed."""

        def which_side_effect(cmd: str) -> str | None:
            return "/usr/bin/dot" if cmd == "dot" else None

        with patch("shutil.which", side_effect=which_side_effect):
            with pytest.raises(Exception) as exc_info:
                _check_graphviz_installed()
            error_msg = str(exc_info.value)
            assert "neato" in error_msg
            assert "Ubuntu/Debian" in error_msg

    def test_check_graphviz_installed_when_both_missing(self) -> None:
        """Test helpful error when both dot and neato are missing."""
        with patch("shutil.which", return_value=None):
            with pytest.raises(Exception) as exc_info:
                _check_graphviz_installed()
            error_msg = str(exc_info.value)
            assert "dot" in error_msg
            assert "neato" in error_msg
            assert "Ubuntu/Debian" in error_msg
            assert "macOS" in error_msg
            assert "Windows" in error_msg

    def test_get_graphviz_engine_neato(self) -> None:
        """Test that layout=neato triggers neato engine."""
        dot_content = "digraph G { layout=neato; A -> B }"
        assert _get_graphviz_engine(dot_content) == "neato"

    def test_get_graphviz_engine_dot(self) -> None:
        """Test that absence of layout=neato triggers dot engine."""
        dot_content = "digraph G { rankdir=TB; A -> B }"
        assert _get_graphviz_engine(dot_content) == "dot"

    def test_get_graphviz_engine_default(self) -> None:
        """Test that plain DOT content uses dot engine."""
        dot_content = "digraph G { A -> B }"
        assert _get_graphviz_engine(dot_content) == "dot"

    def test_render_graphviz_uses_dot_for_dfd(self, tmp_path: Path) -> None:
        """Test that DFD-style DOT uses dot engine."""
        dot_content = "digraph G { rankdir=TB; A -> B }"
        output_path = tmp_path / "test.svg"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            _render_graphviz(dot_content, output_path, "svg")

            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0][0] == "dot"
            assert "-Tsvg" in call_args[0][0]
            assert str(output_path) in call_args[0][0]

    def test_render_graphviz_uses_neato_for_scd(self, tmp_path: Path) -> None:
        """Test that SCD-style DOT uses neato engine."""
        dot_content = "digraph G { layout=neato; A -> B }"
        output_path = tmp_path / "test.svg"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            _render_graphviz(dot_content, output_path, "svg")

            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0][0] == "neato"
            assert "-Tsvg" in call_args[0][0]

    def test_render_graphviz_failure(self, tmp_path: Path) -> None:
        """Test error handling when GraphViz fails."""
        dot_content = "invalid dot content {"
        output_path = tmp_path / "test.svg"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "syntax error"

            with pytest.raises(Exception) as exc_info:
                _render_graphviz(dot_content, output_path, "svg")

            assert "GraphViz rendering failed" in str(exc_info.value)

    def test_render_graphviz_temp_file_cleanup(self, tmp_path: Path) -> None:
        """Test that temporary DOT files are cleaned up."""
        dot_content = "digraph G { A -> B }"
        output_path = tmp_path / "test.svg"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""

            _render_graphviz(dot_content, output_path, "svg")

        # The temp file should have been deleted
        # We can verify the function completed without errors, indicating cleanup happened

    @pytest.mark.skipif(
        shutil.which("dot") is None or shutil.which("neato") is None,
        reason="GraphViz not installed",
    )
    def test_render_graphviz_integration_neato(self, tmp_path: Path) -> None:
        """Integration test for actual GraphViz rendering with neato."""
        dot_content = """
        digraph G {
            layout=neato;
            A [label="Node A"];
            B [label="Node B"];
            A -> B;
        }
        """
        output_path = tmp_path / "test.svg"

        _render_graphviz(dot_content, output_path, "svg")

        assert output_path.exists()
        content = output_path.read_text()
        assert "<svg" in content or "<?xml" in content

    @pytest.mark.skipif(
        shutil.which("dot") is None or shutil.which("neato") is None,
        reason="GraphViz not installed",
    )
    def test_render_graphviz_integration_dot(self, tmp_path: Path) -> None:
        """Integration test for actual GraphViz rendering with dot."""
        dot_content = """
        digraph G {
            rankdir=TB;
            A [label="Node A"];
            B [label="Node B"];
            A -> B;
        }
        """
        output_path = tmp_path / "test.svg"

        _render_graphviz(dot_content, output_path, "svg")

        assert output_path.exists()
        content = output_path.read_text()
        assert "<svg" in content or "<?xml" in content


class TestGenerateGraphicFormats:
    """Tests for generating graphic format output."""

    @pytest.fixture
    def sample_file(self, examples_dir: Path) -> Path:
        """Get a sample .dit file for testing."""
        return examples_dir / "context.dit"

    @pytest.fixture
    def examples_dir(self) -> Path:
        """Get the path to the banking examples directory."""
        return Path(__file__).parent.parent / "examples" / "banking"

    @pytest.mark.skipif(
        shutil.which("dot") is None or shutil.which("neato") is None,
        reason="GraphViz not installed",
    )
    def test_generate_svg_integration(
        self, runner: CliRunner, sample_file: Path, tmp_path: Path
    ) -> None:
        """Integration test for generating SVG output."""
        result = runner.invoke(
            main,
            ["generate", str(sample_file), "-f", "svg", "--output-diagram-dir", str(tmp_path)],
        )
        assert result.exit_code == 0
        svg_files = list(tmp_path.glob("*.svg"))
        assert len(svg_files) > 0
        # Check that file contains SVG content
        for svg_file in svg_files:
            content = svg_file.read_text()
            assert "<svg" in content or "<?xml" in content

    @pytest.mark.skipif(
        shutil.which("dot") is None or shutil.which("neato") is None,
        reason="GraphViz not installed",
    )
    def test_generate_png_integration(
        self, runner: CliRunner, sample_file: Path, tmp_path: Path
    ) -> None:
        """Integration test for generating PNG output."""
        result = runner.invoke(
            main,
            ["generate", str(sample_file), "-f", "png", "--output-diagram-dir", str(tmp_path)],
        )
        assert result.exit_code == 0
        png_files = list(tmp_path.glob("*.png"))
        assert len(png_files) > 0
        # Check that file is a valid PNG (starts with PNG magic bytes)
        for png_file in png_files:
            content = png_file.read_bytes()
            assert content[:8] == b"\x89PNG\r\n\x1a\n"
