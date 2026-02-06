"""Tests for markdown document generation feature.

REQ-DOC-001: Markdown block declaration
REQ-DOC-002: Markdown block ordering
REQ-DOC-010: Diagram insertion
REQ-DOC-011: Element property access
REQ-DOC-012: Collection iteration
REQ-DOC-020: Template validation
REQ-DOC-021: Document generation pipeline
"""

from designit.generators.markdown import (
    MarkdownGenerator,
    TemplateExprType,
    TemplateParser,
    TemplateValidator,
    generate_document,
    unescape_braces,
)
from designit.model.base import DesignDocument
from designit.parser.parser import parse_string
from designit.semantic.analyzer import analyze_string


class TestMarkdownParsing:
    """Tests for markdown block parsing (REQ-DOC-001)."""

    def test_markdown_block_parses(self) -> None:
        """Markdown blocks should parse correctly."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system API {}
            external Client {}
            flow Request(Request): Client -> API
        }

        markdown {
            ## System Overview

            This is documentation.
        }
        """
        doc = parse_string(source)
        assert len(doc.markdowns) == 1
        assert "## System Overview" in doc.markdowns[0].content

    def test_multiple_markdown_blocks(self) -> None:
        """Multiple markdown blocks should parse."""
        source = """
        markdown {
            ## First Section
        }

        scd Context {
            system API {}
        }

        markdown {
            ## Second Section
        }
        """
        doc = parse_string(source)
        assert len(doc.markdowns) == 2
        assert "First Section" in doc.markdowns[0].content
        assert "Second Section" in doc.markdowns[1].content

    def test_markdown_with_template_expressions(self) -> None:
        """Markdown with template expressions should parse."""
        source = """
        scd Context {
            system API {}
        }

        markdown {
            ## {{Context.name}}

            {{diagram:Context}}
        }
        """
        doc = parse_string(source)
        assert len(doc.markdowns) == 1
        assert "{{diagram:Context}}" in doc.markdowns[0].content

    def test_markdown_with_escaped_braces(self) -> None:
        """Markdown with escaped braces should parse."""
        source = r"""
        markdown {
            Code example: \{ key: value \}
        }
        """
        doc = parse_string(source)
        assert len(doc.markdowns) == 1
        assert r"\{ key: value \}" in doc.markdowns[0].content

    def test_markdown_node_has_location(self) -> None:
        """Markdown nodes should have source location."""
        source = """scd C { system S {} }
markdown {
    Content here
}
"""
        doc = parse_string(source)
        assert len(doc.markdowns) == 1
        md = doc.markdowns[0]
        assert md.location is not None
        assert md.location.line == 2

    def test_line_numbers_preserved_after_multiline_markdown(self) -> None:
        """Line numbers should be correct for elements after multi-line markdown blocks.

        Regression test: The markdown extraction was replacing multi-line blocks
        with single-line placeholders, causing all subsequent line numbers to be
        offset by the number of removed newlines.
        """
        source = """scd Context {
    system API {}
}

markdown {
    Line 1
    Line 2
    Line 3
    Line 4
    Line 5
}

erd DataModel {
    entity User {
        id: integer
    }
}
"""
        doc = parse_string(source)

        # Verify we parsed the ERD
        assert len(doc.erds) == 1
        erd = doc.erds[0]

        # The entity User should be on line 14 (after markdown block ends at line 11,
        # empty line 12, erd on line 13, entity on line 14)
        assert len(erd.entities) == 1
        entity = erd.entities[0]
        assert entity.location is not None
        assert entity.location.line == 14, (
            f"Entity should be on line 14, got {entity.location.line}"
        )


class TestTemplateParser:
    """Tests for template expression parsing."""

    def test_parse_diagram_expression(self) -> None:
        """{{diagram:Name}} should parse as DIAGRAM type."""
        parser = TemplateParser()
        exprs = parser.parse("{{diagram:TestDiagram}}")

        assert len(exprs) == 1
        assert exprs[0].expr_type == TemplateExprType.DIAGRAM
        assert exprs[0].diagram_name == "TestDiagram"

    def test_parse_property_expression(self) -> None:
        """Property expressions should parse correctly."""
        parser = TemplateParser()
        exprs = parser.parse("{{Context.API.description}}")

        assert len(exprs) == 1
        assert exprs[0].expr_type == TemplateExprType.PROPERTY
        assert exprs[0].property_path == ["Context", "API", "description"]

    def test_parse_single_property(self) -> None:
        """Single-part property in #each context should parse."""
        parser = TemplateParser()
        exprs = parser.parse("{{name}}")

        assert len(exprs) == 1
        assert exprs[0].expr_type == TemplateExprType.PROPERTY
        assert exprs[0].property_path == ["name"]

    def test_parse_each_start(self) -> None:
        """{{#each Diagram.collection}} should parse as EACH_START."""
        parser = TemplateParser()
        exprs = parser.parse("{{#each Context.externals}}")

        assert len(exprs) == 1
        assert exprs[0].expr_type == TemplateExprType.EACH_START
        assert exprs[0].each_diagram == "Context"
        assert exprs[0].each_collection == "externals"

    def test_parse_each_end(self) -> None:
        """{{/each}} should parse as EACH_END."""
        parser = TemplateParser()
        exprs = parser.parse("{{/each}}")

        assert len(exprs) == 1
        assert exprs[0].expr_type == TemplateExprType.EACH_END

    def test_parse_text_and_expressions(self) -> None:
        """Mixed text and expressions should parse."""
        parser = TemplateParser()
        exprs = parser.parse("Hello {{name}}, welcome!")

        assert len(exprs) == 3
        assert exprs[0].expr_type == TemplateExprType.TEXT
        assert exprs[0].content == "Hello "
        assert exprs[1].expr_type == TemplateExprType.PROPERTY
        assert exprs[2].expr_type == TemplateExprType.TEXT
        assert exprs[2].content == ", welcome!"

    def test_escaped_braces_not_parsed(self) -> None:
        r"""Escaped \{{ should not be parsed as expression."""
        parser = TemplateParser()
        # Note: the regex matches non-escaped braces
        exprs = parser.parse(r"Value is \{{name}}")

        # The escaped \{{ should not match, so it's text
        # But the closing }} without escaped { will match partially
        # Actually, the regex (?<!\\)\{\{(.+?)(?<!\\)\}\} won't match \{{...}}
        # So the whole thing should be text
        assert len(exprs) == 1
        assert exprs[0].expr_type == TemplateExprType.TEXT

    def test_expression_has_line_info(self) -> None:
        """Expressions should have line information."""
        parser = TemplateParser(start_line=5)
        exprs = parser.parse("Line 1\nLine 2\n{{name}}")

        prop_expr = [e for e in exprs if e.expr_type == TemplateExprType.PROPERTY][0]
        assert prop_expr.line == 7  # Started at 5, +2 newlines


class TestTemplateValidator:
    """Tests for template validation (REQ-DOC-020)."""

    def _make_document(self, source: str) -> DesignDocument:
        """Helper to create a design document from source."""
        return analyze_string(source)

    def test_validate_valid_diagram_reference(self) -> None:
        """Valid diagram reference should pass validation."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system API {}
            external Client {}
            flow Request(Request): Client -> API
        }
        """
        doc = self._make_document(source)
        parser = TemplateParser()
        exprs = parser.parse("{{diagram:Context}}")

        validator = TemplateValidator(doc)
        result = validator.validate(exprs)

        assert result.is_valid

    def test_validate_invalid_diagram_reference(self) -> None:
        """Invalid diagram reference should fail validation."""
        source = """
        scd Context {
            system API {}
        }
        """
        doc = self._make_document(source)
        parser = TemplateParser()
        exprs = parser.parse("{{diagram:NonExistent}}")

        validator = TemplateValidator(doc)
        result = validator.validate(exprs)

        assert not result.is_valid
        assert len(result.errors) == 1
        assert "Unknown diagram" in result.errors[0].message

    def test_validate_valid_property_access(self) -> None:
        """Valid property access should pass validation."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system API { description: "The API" }
            external Client {}
            flow Request(Request): Client -> API
        }
        """
        doc = self._make_document(source)
        parser = TemplateParser()
        exprs = parser.parse("{{Context.API.description}}")

        validator = TemplateValidator(doc)
        result = validator.validate(exprs)

        assert result.is_valid

    def test_validate_invalid_element_reference(self) -> None:
        """Invalid element reference should fail validation."""
        source = """
        scd Context {
            system API {}
        }
        """
        doc = self._make_document(source)
        parser = TemplateParser()
        exprs = parser.parse("{{Context.NonExistent.name}}")

        validator = TemplateValidator(doc)
        result = validator.validate(exprs)

        assert not result.is_valid
        assert "not found" in result.errors[0].message

    def test_validate_valid_each_collection(self) -> None:
        """Valid #each collection should pass validation."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system API {}
            external Client {}
            flow Request(Request): Client -> API
        }
        """
        doc = self._make_document(source)
        parser = TemplateParser()
        exprs = parser.parse("{{#each Context.externals}}{{name}}{{/each}}")

        validator = TemplateValidator(doc)
        result = validator.validate(exprs)

        assert result.is_valid

    def test_validate_invalid_collection(self) -> None:
        """Invalid collection name should fail validation."""
        source = """
        scd Context {
            system API {}
        }
        """
        doc = self._make_document(source)
        parser = TemplateParser()
        exprs = parser.parse("{{#each Context.invalid}}{{/each}}")

        validator = TemplateValidator(doc)
        result = validator.validate(exprs)

        assert not result.is_valid
        assert "Invalid collection" in result.errors[0].message

    def test_validate_property_without_context(self) -> None:
        """Property access without #each context should fail."""
        source = """
        scd Context {
            system API {}
        }
        """
        doc = self._make_document(source)
        parser = TemplateParser()
        exprs = parser.parse("{{name}}")  # No #each context

        validator = TemplateValidator(doc)
        result = validator.validate(exprs)

        assert not result.is_valid
        assert "requires context" in result.errors[0].message

    def test_validate_max_errors_limit(self) -> None:
        """Validation should stop after MAX_ERRORS."""
        source = """
        scd Context {
            system API {}
        }
        """
        doc = self._make_document(source)

        # Create many invalid references
        template = " ".join([f"{{{{diagram:Bad{i}}}}}" for i in range(15)])
        parser = TemplateParser()
        exprs = parser.parse(template)

        validator = TemplateValidator(doc)
        result = validator.validate(exprs)

        assert len(result.errors) <= TemplateValidator.MAX_ERRORS


class TestMarkdownGenerator:
    """Tests for markdown generation."""

    def _make_document(self, source: str) -> DesignDocument:
        """Helper to create a design document from source."""
        return analyze_string(source)

    def test_generate_diagram_reference(self) -> None:
        """Diagram reference should generate image link."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system API {}
            external Client {}
            flow Request(Request): Client -> API
        }
        """
        doc = self._make_document(source)
        parser = TemplateParser()
        exprs = parser.parse("{{diagram:Context}}")

        generator = MarkdownGenerator(doc, diagram_format="svg", diagram_dir="images")
        result = generator.generate(exprs)

        # Diagram reference includes type prefix to match generator output filenames
        assert "![Context](images/scd_Context.svg)" in result.content
        assert len(result.diagram_refs) == 1
        assert result.diagram_refs[0].name == "Context"

    def test_generate_property_value(self) -> None:
        """Property access should generate value."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system API { description: "The API system" }
            external Client {}
            flow Request(Request): Client -> API
        }
        """
        doc = self._make_document(source)
        parser = TemplateParser()
        exprs = parser.parse("Name: {{Context.API.name}}")

        generator = MarkdownGenerator(doc)
        result = generator.generate(exprs)

        assert "Name: API" in result.content

    def test_generate_each_iteration(self) -> None:
        """#each should iterate over collection."""
        source = """
        datadict {
            F1 = { data: string }
            F2 = { data: string }
        }
        scd Context {
            system API {}
            external Client1 {}
            external Client2 {}
            flow F1(F1): Client1 -> API
            flow F2(F2): Client2 -> API
        }
        """
        doc = self._make_document(source)
        parser = TemplateParser()
        exprs = parser.parse("{{#each Context.externals}}- {{name}}\n{{/each}}")

        generator = MarkdownGenerator(doc)
        result = generator.generate(exprs)

        assert "- Client1" in result.content
        assert "- Client2" in result.content

    def test_unescape_braces(self) -> None:
        """Escaped braces should be unescaped in output."""
        content = r"Code: \{ key: value \}"
        result = unescape_braces(content)
        assert result == "Code: { key: value }"

    def test_escaped_braces_surrounding_template_expression(self) -> None:
        r"""Escaped braces around template expression should render correctly.

        Input: \{{{Context.API.name}}\}
        Expected: {API}
        """
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system API { description: "The API" }
            external Client {}
            flow Request(Request): Client -> API
        }
        """
        doc = self._make_document(source)
        parser = TemplateParser()
        # Use raw string to preserve backslashes
        exprs = parser.parse(r"Value: \{{{Context.API.name}}\}")

        generator = MarkdownGenerator(doc)
        result = generator.generate(exprs)

        # The escaped braces should become literal braces around the rendered value
        assert "Value: {API}" in result.content

    def test_diagram_reference_includes_type_prefix(self) -> None:
        """Diagram references should include type prefix in filename."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system API {}
            external Client {}
            flow Request(Request): Client -> API
        }
        dfd ProcessFlow {
            refines: Context.API
            process Handler {}
            flow Context.Request: -> Handler
        }
        """
        doc = self._make_document(source)
        parser = TemplateParser()

        # Test SCD gets scd_ prefix
        exprs = parser.parse("{{diagram:Context}}")
        generator = MarkdownGenerator(doc, diagram_format="svg", diagram_dir="diagrams")
        result = generator.generate(exprs)
        assert "![Context](diagrams/scd_Context.svg)" in result.content

        # Test DFD gets dfd_ prefix
        exprs = parser.parse("{{diagram:ProcessFlow}}")
        generator = MarkdownGenerator(doc, diagram_format="png", diagram_dir="images")
        result = generator.generate(exprs)
        assert "![ProcessFlow](images/dfd_ProcessFlow.png)" in result.content


class TestGenerateDocument:
    """Tests for the generate_document function (REQ-DOC-021)."""

    def test_generate_simple_document(self) -> None:
        """Simple document with markdown should generate."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system API { description: "Main API" }
            external Client {}
            flow Request(Request): Client -> API
        }

        markdown {
            ## {{Context.name}}

            {{Context.API.description}}
        }
        """
        doc_node = parse_string(source)
        design_doc = analyze_string(source)

        markdown_contents = [
            (
                md.content,
                md.location.file if md.location else None,
                md.location.line if md.location else None,
            )
            for md in doc_node.markdowns
        ]

        result = generate_document(
            document=design_doc,
            markdown_contents=markdown_contents,
            diagram_format="svg",
            diagram_dir="diagrams",
        )

        assert result.errors == []
        assert "## Context" in result.content
        assert "Main API" in result.content

    def test_generate_document_with_diagram(self) -> None:
        """Document with diagram reference should list diagram refs."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system API {}
            external Client {}
            flow Request(Request): Client -> API
        }

        markdown {
            {{diagram:Context}}
        }
        """
        doc_node = parse_string(source)
        design_doc = analyze_string(source)

        markdown_contents: list[tuple[str, str | None, int | None]] = [
            (md.content, None, None) for md in doc_node.markdowns
        ]

        result = generate_document(
            document=design_doc,
            markdown_contents=markdown_contents,
        )

        assert len(result.diagram_refs) == 1
        assert result.diagram_refs[0].name == "Context"
        assert result.diagram_refs[0].diagram_type == "scd"

    def test_generate_document_with_errors(self) -> None:
        """Document with invalid template should return errors."""
        source = """
        scd Context {
            system API {}
        }
        """
        design_doc = analyze_string(source)

        markdown_contents: list[tuple[str, str | None, int | None]] = [
            ("{{diagram:NonExistent}}", "test.dit", 1),
        ]

        result = generate_document(
            document=design_doc,
            markdown_contents=markdown_contents,
        )

        assert len(result.errors) > 0
        assert "Unknown diagram" in result.errors[0].message


class TestNestedFlowIteration:
    """Tests for nested flows iteration within element blocks (REQ-DOC-015)."""

    def _make_document(self, source: str) -> DesignDocument:
        """Helper to create a design document from source."""
        return analyze_string(source)

    def test_validate_nested_flows_in_scd_externals(self) -> None:
        """{{#each flows}} should be valid inside {{#each Context.externals}}."""
        source = """
        datadict {
            Request = { data: string }
            Response = { data: string }
        }
        scd Context {
            system API {}
            external Client {}
            flow Request(Request): Client -> API { description: "Client request" }
            flow Response(Response): API -> Client { description: "Server response" }
        }
        """
        doc = self._make_document(source)
        parser = TemplateParser()
        exprs = parser.parse(
            "{{#each Context.externals}}{{name}}:{{#each flows}}{{name}}{{/each}}{{/each}}"
        )

        validator = TemplateValidator(doc)
        result = validator.validate(exprs)

        assert result.is_valid, f"Errors: {[e.message for e in result.errors]}"

    def test_validate_nested_flows_in_dfd_processes(self) -> None:
        """{{#each flows}} should be valid inside {{#each DFD.processes}}."""
        source = """
        datadict {
            Request = { data: string }
            CacheOp = { data: string }
        }
        scd Context {
            system API {}
            external Client {}
            flow Request(Request): Client -> API
        }
        dfd Handler {
            refines: Context.API
            process Processor {}
            datastore Cache {}
            flow Context.Request: -> Processor
            flow CacheOp(CacheOp): Processor -> Cache { description: "Cache operation" }
        }
        """
        doc = self._make_document(source)
        parser = TemplateParser()
        exprs = parser.parse(
            "{{#each Handler.processes}}{{name}}:{{#each flows}}{{name}}{{/each}}{{/each}}"
        )

        validator = TemplateValidator(doc)
        result = validator.validate(exprs)

        assert result.is_valid, f"Errors: {[e.message for e in result.errors]}"

    def test_validate_flow_properties_in_nested_context(self) -> None:
        """Flow properties should be accessible in nested {{#each flows}} context."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system API {}
            external Client {}
            flow Request(Request): Client -> API { description: "Client request" }
        }
        """
        doc = self._make_document(source)
        parser = TemplateParser()
        # Access flow name, direction, description
        exprs = parser.parse(
            "{{#each Context.externals}}"
            "{{#each flows}}{{name}}-{{direction}}-{{description}}{{/each}}"
            "{{/each}}"
        )

        validator = TemplateValidator(doc)
        result = validator.validate(exprs)

        assert result.is_valid, f"Errors: {[e.message for e in result.errors]}"

    def test_validate_invalid_nested_collection(self) -> None:
        """Invalid nested collection should fail validation."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system API {}
            external Client {}
            flow Request(Request): Client -> API
        }
        """
        doc = self._make_document(source)
        parser = TemplateParser()
        # 'invalid' is not a valid nested collection
        exprs = parser.parse(
            "{{#each Context.externals}}{{#each invalid}}{{name}}{{/each}}{{/each}}"
        )

        validator = TemplateValidator(doc)
        result = validator.validate(exprs)

        assert not result.is_valid
        assert any("Invalid" in e.message or "invalid" in e.message for e in result.errors)

    def test_generate_nested_flows_scd_external(self) -> None:
        """Nested flows iteration should render for SCD externals."""
        source = """
        datadict {
            Request = { data: string }
            Response = { data: string }
        }
        scd Context {
            system API {}
            external Client {}
            flow Request(Request): Client -> API { description: "Client request" }
            flow Response(Response): API -> Client { description: "Server response" }
        }
        """
        doc = self._make_document(source)
        parser = TemplateParser()
        exprs = parser.parse(
            "{{#each Context.externals}}"
            "### {{name}}\n"
            "{{#each flows}}"
            "- {{name}} ({{direction}}): {{description}}\n"
            "{{/each}}"
            "{{/each}}"
        )

        generator = MarkdownGenerator(doc)
        result = generator.generate(exprs)

        assert "### Client" in result.content
        assert "- Request (inbound): Client request" in result.content
        assert "- Response (outbound): Server response" in result.content

    def test_generate_nested_flows_dfd_process(self) -> None:
        """Nested flows iteration should render for DFD processes."""
        source = """
        datadict {
            Request = { data: string }
            CacheOp = { data: string }
        }
        scd Context {
            system API {}
            external Client {}
            flow Request(Request): Client -> API
        }
        dfd Handler {
            refines: Context.API
            process Processor {}
            datastore Cache {}
            flow Context.Request: -> Processor { description: "Incoming request" }
            flow CacheOp(CacheOp): Processor -> Cache { description: "Cache operation" }
        }
        """
        doc = self._make_document(source)
        parser = TemplateParser()
        exprs = parser.parse(
            "{{#each Handler.processes}}"
            "### {{name}}\n"
            "{{#each flows}}"
            "- {{name}}: {{description}}\n"
            "{{/each}}"
            "{{/each}}"
        )

        generator = MarkdownGenerator(doc)
        result = generator.generate(exprs)

        assert "### Processor" in result.content
        assert "- Request: Incoming request" in result.content
        assert "- CacheOp: Cache operation" in result.content

    def test_generate_nested_flows_empty(self) -> None:
        """Nested flows iteration should handle elements with no flows."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system API {}
            external Client1 {}
            external Client2 {}
            flow Request(Request): Client1 -> API
        }
        """
        doc = self._make_document(source)
        parser = TemplateParser()
        exprs = parser.parse(
            "{{#each Context.externals}}### {{name}}\n{{#each flows}}- {{name}}\n{{/each}}{{/each}}"
        )

        generator = MarkdownGenerator(doc)
        result = generator.generate(exprs)

        # Client1 should have the flow
        assert "### Client1" in result.content
        assert "- Request" in result.content
        # Client2 should appear but have no flows listed
        assert "### Client2" in result.content


class TestCollectionValidation:
    """Tests for collection validation per diagram type (REQ-DOC-012)."""

    def test_scd_valid_collections(self) -> None:
        """SCD should accept valid collections: externals, datastores, flows."""
        source = """
        datadict {
            Request = { data: string }
            Data = { value: string }
        }
        scd Context {
            system API {}
            external Client {}
            datastore DB {}
            flow Request(Request): Client -> API
            flow Data(Data): API -> DB
        }
        """
        doc = analyze_string(source)
        parser = TemplateParser()

        for collection in ["externals", "datastores", "flows"]:
            exprs = parser.parse(f"{{{{#each Context.{collection}}}}}{{{{/each}}}}")
            validator = TemplateValidator(doc)
            result = validator.validate(exprs)
            assert result.is_valid, f"Collection {collection} should be valid for SCD"

    def test_dfd_valid_collections(self) -> None:
        """DFD should accept valid collections: processes, datastores, flows."""
        source = """
        datadict {
            F = { data: string }
            CacheOp = { value: string }
        }
        scd Ctx {
            system Sys {}
            external E {}
            flow F(F): E -> Sys
        }
        dfd MyDFD {
            refines: Ctx.Sys
            process Handler {}
            datastore Cache {}
            flow Ctx.F: -> Handler
            flow CacheOp(CacheOp): Handler -> Cache
        }
        """
        doc = analyze_string(source)
        parser = TemplateParser()

        for collection in ["processes", "datastores", "flows"]:
            exprs = parser.parse(f"{{{{#each MyDFD.{collection}}}}}{{{{/each}}}}")
            validator = TemplateValidator(doc)
            result = validator.validate(exprs)
            assert result.is_valid, f"Collection {collection} should be valid for DFD"

    def test_erd_valid_collections(self) -> None:
        """ERD should accept valid collections: entities, relationships."""
        source = """
        erd Model {
            entity User {
                id: integer [pk]
            }
            entity Profile {
                id: integer [pk]
            }
            relationship has_profile: User -1:1-> Profile
        }
        """
        doc = analyze_string(source)
        parser = TemplateParser()

        for collection in ["entities", "relationships"]:
            exprs = parser.parse(f"{{{{#each Model.{collection}}}}}{{{{/each}}}}")
            validator = TemplateValidator(doc)
            result = validator.validate(exprs)
            assert result.is_valid, f"Collection {collection} should be valid for ERD"

    def test_std_valid_collections(self) -> None:
        """STD should accept valid collections: states, transitions."""
        source = """
        std Lifecycle {
            initial: Draft
            state Draft {}
            state Published {}
            transition publish: Draft -> Published
        }
        """
        doc = analyze_string(source)
        parser = TemplateParser()

        for collection in ["states", "transitions"]:
            exprs = parser.parse(f"{{{{#each Lifecycle.{collection}}}}}{{{{/each}}}}")
            validator = TemplateValidator(doc)
            result = validator.validate(exprs)
            assert result.is_valid, f"Collection {collection} should be valid for STD"

    def test_structure_valid_collections(self) -> None:
        """Structure should accept valid collections: modules."""
        source = """
        structure App {
            module Main {}
            module Helper {}
        }
        """
        doc = analyze_string(source)
        parser = TemplateParser()

        exprs = parser.parse("{{#each App.modules}}{{/each}}")
        validator = TemplateValidator(doc)
        result = validator.validate(exprs)
        assert result.is_valid, "Collection modules should be valid for Structure"
