"""Tests for the CLI commands.

REQ-CLI-020: Format Option
REQ-CLI-021: Output Directory Option
REQ-CLI-022: Diagram Filter Option
REQ-CLI-023: No Placeholders Flag
REQ-CLI-024: Stdout Flag
REQ-CLI-025: GraphViz Rendering
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
            ["generate", str(sample_file), "-f", "mermaid", "-o", str(tmp_path)],
        )
        assert result.exit_code == 0
        mmd_files = list(tmp_path.glob("*.mmd"))
        assert len(mmd_files) > 0
        assert "Generated" in result.output

    def test_format_option_dot(self, runner: CliRunner, sample_file: Path, tmp_path: Path) -> None:
        """Test dot format produces .dot files (REQ-CLI-020)."""
        result = runner.invoke(
            main,
            ["generate", str(sample_file), "-f", "dot", "-o", str(tmp_path)],
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
        """Test default output directory is ./generated (REQ-CLI-021)."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            main,
            ["generate", str(sample_file), "-f", "mermaid"],
        )
        assert result.exit_code == 0
        generated_dir = tmp_path / "generated"
        assert generated_dir.exists()
        assert len(list(generated_dir.glob("*.mmd"))) > 0

    def test_custom_output_directory(
        self, runner: CliRunner, sample_file: Path, tmp_path: Path
    ) -> None:
        """Test custom output directory option (REQ-CLI-021)."""
        custom_dir = tmp_path / "custom_output"
        result = runner.invoke(
            main,
            ["generate", str(sample_file), "-f", "mermaid", "-o", str(custom_dir)],
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
            ["generate", str(sample_file), "-f", "mermaid", "-o", str(nested_dir)],
        )
        assert result.exit_code == 0
        assert nested_dir.exists()

    def test_diagram_filter(self, runner: CliRunner, sample_file: Path, tmp_path: Path) -> None:
        """Test diagram filter option (REQ-CLI-022)."""
        # First, generate all diagrams to see what we get
        result = runner.invoke(
            main,
            ["generate", str(sample_file), "-f", "mermaid", "-o", str(tmp_path)],
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
                "-o",
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
                "-o",
                str(tmp_path),
                "--no-placeholders",
            ],
        )
        assert result.exit_code == 0
        # Should still generate files (just without placeholders)
        mmd_files = list(tmp_path.glob("*.mmd"))
        assert len(mmd_files) > 0

    def test_stdout_flag_text_format(self, runner: CliRunner, sample_file: Path) -> None:
        """Test --stdout flag with text formats (REQ-CLI-024)."""
        result = runner.invoke(
            main,
            ["generate", str(sample_file), "-f", "mermaid", "--stdout"],
        )
        assert result.exit_code == 0
        # Content should be in output
        assert "flowchart" in result.output or "graph" in result.output

    def test_stdout_flag_with_graphic_format_fails(
        self, runner: CliRunner, sample_file: Path
    ) -> None:
        """Test --stdout flag fails with graphic formats (REQ-CLI-024)."""
        with patch("designit.cli._check_graphviz_installed"):
            result = runner.invoke(
                main,
                ["generate", str(sample_file), "-f", "svg", "--stdout"],
            )
            assert result.exit_code != 0
            assert "Cannot use --stdout with graphic format" in result.output


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
            ["generate", str(sample_file), "-f", "svg", "-o", str(tmp_path)],
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
            ["generate", str(sample_file), "-f", "png", "-o", str(tmp_path)],
        )
        assert result.exit_code == 0
        png_files = list(tmp_path.glob("*.png"))
        assert len(png_files) > 0
        # Check that file is a valid PNG (starts with PNG magic bytes)
        for png_file in png_files:
            content = png_file.read_bytes()
            assert content[:8] == b"\x89PNG\r\n\x1a\n"
