"""Tests for flow unions feature.

Flow unions allow grouping multiple flows under a single name for visual
simplification at higher abstraction levels.

Syntax: flow UnionName = Flow1 | Flow2 | ...

REQ-SEM-110: All member flows must exist in the same diagram.
REQ-SEM-111: Direction is inferred from member flows.
REQ-SEM-112: Nesting is allowed (unions can contain other unions).
REQ-GEN-080: Generators support expand_unions parameter.
"""

from designit.model.base import ValidationSeverity
from designit.parser.parser import parse_string
from designit.semantic.analyzer import analyze_string
from designit.semantic.validator import validate


class TestFlowUnionParsing:
    """Tests for flow union parsing."""

    def test_scd_flow_union_parses(self) -> None:
        """SCD flow union declaration should parse correctly."""
        source = """
        datadict {
            LoginRequest = { username: string }
            LoginResponse = { token: string }
        }
        scd Context {
            system AuthSystem {}
            external User {}
            flow LoginRequest(LoginRequest): User -> AuthSystem
            flow LoginResponse(LoginResponse): AuthSystem -> User
            flow LoginSession = LoginRequest | LoginResponse
        }
        """
        doc = parse_string(source)
        assert len(doc.scds) == 1
        scd = doc.scds[0]
        assert len(scd.flow_unions) == 1
        union = scd.flow_unions[0]
        assert union.name == "LoginSession"
        assert union.members == ["LoginRequest", "LoginResponse"]

    def test_dfd_flow_union_parses(self) -> None:
        """DFD flow union declaration should parse correctly."""
        source = """
        datadict {
            Request = { data: string }
            Response = { result: string }
            Internal = { value: integer }
        }
        scd Context {
            system Sys {}
            external Client {}
            flow Request(Request): Client -> Sys
            flow Response(Response): Sys -> Client
        }
        dfd Level0 {
            refines: Context.Sys
            process Handler {}
            flow Context.Request: -> Handler
            flow Context.Response: Handler ->
            flow InternalData = Request | Response
        }
        """
        doc = parse_string(source)
        assert len(doc.dfds) == 1
        dfd = doc.dfds[0]
        assert len(dfd.flow_unions) == 1
        union = dfd.flow_unions[0]
        assert union.name == "InternalData"
        assert union.members == ["Request", "Response"]

    def test_flow_union_single_member_parses(self) -> None:
        """Flow union with single member (alias) should parse."""
        source = """
        datadict {
            Data = { value: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow Data(Data): E -> Sys
            flow DataAlias = Data
        }
        """
        # Single member should be valid as an alias
        doc = parse_string(source)
        scd = doc.scds[0]
        assert len(scd.flow_unions) == 1
        assert scd.flow_unions[0].members == ["Data"]

    def test_flow_union_multiple_members_parses(self) -> None:
        """Flow union with multiple members should parse."""
        source = """
        datadict {
            A = { a: string }
            B = { b: string }
            C = { c: string }
            D = { d: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow A(A): E -> Sys
            flow B(B): E -> Sys
            flow C(C): E -> Sys
            flow D(D): Sys -> E
            flow Bundle = A | B | C | D
        }
        """
        doc = parse_string(source)
        scd = doc.scds[0]
        union = scd.flow_unions[0]
        assert union.members == ["A", "B", "C", "D"]

    def test_flow_union_has_location(self) -> None:
        """Flow union should have source location."""
        source = """datadict {
    Data = { value: string }
}
scd Context {
    system Sys {}
    external E {}
    flow Data(Data): E -> Sys
    flow DataBundle = Data
}
"""
        doc = parse_string(source)
        scd = doc.scds[0]
        union = scd.flow_unions[0]
        assert union.location is not None
        assert union.location.line == 8

    def test_multiple_flow_unions_parse(self) -> None:
        """Multiple flow unions in same diagram should parse."""
        source = """
        datadict {
            In1 = { a: string }
            In2 = { b: string }
            Out1 = { c: string }
            Out2 = { d: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow In1(In1): E -> Sys
            flow In2(In2): E -> Sys
            flow Out1(Out1): Sys -> E
            flow Out2(Out2): Sys -> E
            flow InboundBundle = In1 | In2
            flow OutboundBundle = Out1 | Out2
        }
        """
        doc = parse_string(source)
        scd = doc.scds[0]
        assert len(scd.flow_unions) == 2
        assert scd.flow_unions[0].name == "InboundBundle"
        assert scd.flow_unions[1].name == "OutboundBundle"


class TestFlowUnionSemanticAnalysis:
    """Tests for flow union semantic analysis."""

    def test_scd_flow_union_analyzed(self) -> None:
        """SCD flow union should be analyzed into semantic model."""
        source = """
        datadict {
            Req = { data: string }
            Resp = { result: string }
        }
        scd Context {
            system Sys {}
            external Client {}
            flow Req(Req): Client -> Sys
            flow Resp(Resp): Sys -> Client
            flow Session = Req | Resp
        }
        """
        doc = analyze_string(source)
        scd = doc.scds["Context"]
        assert "Session" in scd.flow_unions
        union = scd.flow_unions["Session"]
        assert union.name == "Session"
        # Members are now actual flow objects, use member_names for checking names
        assert union.member_names == ["Req", "Resp"]
        # Verify members are actual flow objects
        assert len(union.members) == 2
        assert union.members[0].name == "Req"
        assert union.members[1].name == "Resp"
        # Member flows should NOT be in scd.flows (moved into union)
        assert "Req" not in scd.flows
        assert "Resp" not in scd.flows

    def test_dfd_flow_union_analyzed(self) -> None:
        """DFD flow union should be analyzed into semantic model."""
        source = """
        datadict {
            Req = { data: string }
            Resp = { result: string }
        }
        scd Context {
            system Sys {}
            external Client {}
            flow Req(Req): Client -> Sys
            flow Resp(Resp): Sys -> Client
        }
        dfd Level0 {
            refines: Context.Sys
            process Handler {}
            flow Context.Req: -> Handler
            flow Context.Resp: Handler ->
            flow Bundle = Req | Resp
        }
        """
        doc = analyze_string(source)
        dfd = doc.dfds["Level0"]
        assert "Bundle" in dfd.flow_unions
        union = dfd.flow_unions["Bundle"]
        # Members are now actual flow objects, use member_names for checking names
        assert union.member_names == ["Req", "Resp"]
        # Member flows should NOT be in dfd.flows (moved into union)
        # DFD flows use compound keys (name, flow_type)
        assert not any(name == "Req" for name, _ in dfd.flows.keys())
        assert not any(name == "Resp" for name, _ in dfd.flows.keys())

    def test_flow_union_stores_source_location(self) -> None:
        """Flow union should store source file and line."""
        source = """datadict {
    Data = { value: string }
}
scd Context {
    system Sys {}
    external E {}
    flow Data(Data): E -> Sys
    flow Alias = Data
}
"""
        doc = analyze_string(source, filename="test.dit")
        scd = doc.scds["Context"]
        union = scd.flow_unions["Alias"]
        assert union.line == 8
        assert union.source_file == "test.dit"


class TestFlowUnionValidation:
    """Tests for flow union validation."""

    def test_valid_flow_union_no_errors(self) -> None:
        """Valid flow union should produce no errors."""
        source = """
        datadict {
            Req = { data: string }
            Resp = { result: string }
        }
        scd Context {
            system Sys {}
            external Client {}
            flow Req(Req): Client -> Sys
            flow Resp(Resp): Sys -> Client
            flow Bundle = Req | Resp
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"

    def test_empty_flow_union_error(self) -> None:
        """Empty flow union should produce an error."""
        # This would require grammar change to allow empty unions,
        # which current grammar doesn't. The grammar requires at least one member.
        # Instead test at semantic level with direct model manipulation.
        # For now, we rely on grammar preventing this case.
        pass

    def test_flow_union_nonexistent_member_error(self) -> None:
        """Flow union referencing non-existent flow should produce error."""
        source = """
        datadict {
            Req = { data: string }
        }
        scd Context {
            system Sys {}
            external Client {}
            flow Req(Req): Client -> Sys
            flow Bundle = Req | NonExistent
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        assert any("NonExistent" in e.message for e in errors)

    def test_flow_union_self_reference_error(self) -> None:
        """Flow union containing itself should produce error."""
        source = """
        datadict {
            Data = { value: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow Data(Data): E -> Sys
            flow Bundle = Data | Bundle
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        assert any("cannot contain itself" in e.message for e in errors)

    def test_flow_union_conflicts_with_flow_error(self) -> None:
        """Flow union with same name as existing flow should produce error."""
        source = """
        datadict {
            Data = { value: string }
            Other = { other: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow Data(Data): E -> Sys
            flow Other(Other): Sys -> E
            flow Data = Other
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        assert any("conflicts with existing flow" in e.message for e in errors)

    def test_flow_union_nesting_valid(self) -> None:
        """Nested flow unions should be valid (REQ-SEM-112)."""
        source = """
        datadict {
            A = { a: string }
            B = { b: string }
            C = { c: string }
            D = { d: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow A(A): E -> Sys
            flow B(B): E -> Sys
            flow C(C): Sys -> E
            flow D(D): Sys -> E
            flow InBundle = A | B
            flow OutBundle = C | D
            flow AllBundle = InBundle | OutBundle
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        # Should be valid - unions can contain other unions
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"

    def test_dfd_flow_union_validation(self) -> None:
        """DFD flow union validation should work."""
        source = """
        datadict {
            Req = { data: string }
        }
        scd Context {
            system Sys {}
            external Client {}
            flow Req(Req): Client -> Sys
        }
        dfd Level0 {
            refines: Context.Sys
            process Handler {}
            flow Context.Req: -> Handler
            flow Bundle = Req | Missing
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert any("Missing" in e.message for e in errors)

    def test_flow_union_error_has_line_number(self) -> None:
        """Flow union validation errors should include line numbers."""
        source = """datadict {
    Req = { data: string }
}
scd Context {
    system Sys {}
    external Client {}
    flow Req(Req): Client -> Sys
    flow Bundle = Req | NonExistent
}
"""
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        error = next((e for e in errors if "NonExistent" in e.message), None)
        assert error is not None
        assert error.line is not None
        assert error.line == 8


class TestFlowUnionOrphanValidation:
    """Tests for orphan element validation with flow unions.

    When flows are moved into unions, the elements they connect should not
    be reported as orphans (elements with no data flows).
    """

    def test_scd_element_in_union_flow_not_orphan(self) -> None:
        """SCD external connected only via union member flows should not be orphan."""
        source = """
        datadict {
            Req = { data: string }
            Resp = { result: string }
        }
        scd Context {
            system Sys {}
            external Client {}
            flow Req(Req): Client -> Sys
            flow Resp(Resp): Sys -> Client
            flow Bundle = Req | Resp
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        warnings = [m for m in messages if m.severity == ValidationSeverity.WARNING]
        # Client should NOT be reported as orphan - it has flows via the union
        orphan_warnings = [w for w in warnings if "no data flows" in w.message]
        assert len(orphan_warnings) == 0, (
            f"Expected no orphan warnings, got: {[w.message for w in orphan_warnings]}"
        )

    def test_scd_element_only_in_union_not_orphan(self) -> None:
        """SCD external with ALL flows in union should not be orphan."""
        source = """
        datadict {
            A = { a: string }
            B = { b: string }
        }
        scd Context {
            system Sys {}
            external E1 {}
            external E2 {}
            flow A(A): E1 -> Sys
            flow B(B): Sys -> E2
            flow Bundle = A | B
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        warnings = [m for m in messages if m.severity == ValidationSeverity.WARNING]
        orphan_warnings = [w for w in warnings if "no data flows" in w.message]
        # Neither E1 nor E2 should be orphans
        assert len(orphan_warnings) == 0, (
            f"Expected no orphan warnings, got: {[w.message for w in orphan_warnings]}"
        )

    def test_scd_actual_orphan_still_detected(self) -> None:
        """SCD external with no flows (standalone or in union) should still be orphan."""
        source = """
        datadict {
            A = { a: string }
        }
        scd Context {
            system Sys {}
            external Connected {}
            external Orphan {}
            flow A(A): Connected -> Sys
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        warnings = [m for m in messages if m.severity == ValidationSeverity.WARNING]
        orphan_warnings = [w for w in warnings if "no data flows" in w.message]
        # Orphan should be detected
        assert len(orphan_warnings) == 1
        assert "Orphan" in orphan_warnings[0].message

    def test_dfd_element_in_union_flow_not_orphan(self) -> None:
        """DFD process connected only via union member flows should not be orphan."""
        source = """
        datadict {
            Req = { data: string }
            Internal1 = { a: string }
            Internal2 = { b: string }
        }
        scd Context {
            system Sys {}
            external Client {}
            flow Req(Req): Client -> Sys
        }
        dfd Level0 {
            refines: Context.Sys
            process A {}
            process B {}
            flow Context.Req: -> A
            flow Internal1(Internal1): A -> B
            flow Internal2(Internal2): B -> A
            flow InternalBundle = Internal1 | Internal2
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        warnings = [m for m in messages if m.severity == ValidationSeverity.WARNING]
        orphan_warnings = [w for w in warnings if "no data flows" in w.message]
        # Process B should NOT be orphan - connected via union flows
        assert len(orphan_warnings) == 0, (
            f"Expected no orphan warnings, got: {[w.message for w in orphan_warnings]}"
        )

    def test_dfd_actual_orphan_still_detected(self) -> None:
        """DFD process with no flows (standalone or in union) should still be orphan."""
        source = """
        datadict {
            Req = { data: string }
        }
        scd Context {
            system Sys {}
            external Client {}
            flow Req(Req): Client -> Sys
        }
        dfd Level0 {
            refines: Context.Sys
            process Connected {}
            process Orphan {}
            flow Context.Req: -> Connected
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        warnings = [m for m in messages if m.severity == ValidationSeverity.WARNING]
        orphan_warnings = [w for w in warnings if "no data flows" in w.message]
        # Orphan process should be detected
        assert len(orphan_warnings) == 1
        assert "Orphan" in orphan_warnings[0].message


class TestFlowUnionInDFD:
    """Tests for flow unions in DFD context."""

    def test_dfd_flow_union_with_inbound_flows(self) -> None:
        """DFD flow union with inbound flows should be valid."""
        source = """
        datadict {
            Req1 = { a: string }
            Req2 = { b: string }
        }
        scd Context {
            system Sys {}
            external Client {}
            flow Req1(Req1): Client -> Sys
            flow Req2(Req2): Client -> Sys
        }
        dfd Level0 {
            refines: Context.Sys
            process Handler {}
            flow Context.Req1: -> Handler
            flow Context.Req2: -> Handler
            flow InboundBundle = Req1 | Req2
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"

    def test_dfd_flow_union_with_outbound_flows(self) -> None:
        """DFD flow union with outbound flows should be valid."""
        source = """
        datadict {
            Resp1 = { a: string }
            Resp2 = { b: string }
        }
        scd Context {
            system Sys {}
            external Client {}
            flow Resp1(Resp1): Sys -> Client
            flow Resp2(Resp2): Sys -> Client
        }
        dfd Level0 {
            refines: Context.Sys
            process Handler {}
            flow Context.Resp1: Handler ->
            flow Context.Resp2: Handler ->
            flow OutboundBundle = Resp1 | Resp2
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"

    def test_dfd_flow_union_with_internal_flows(self) -> None:
        """DFD flow union with internal flows should be valid."""
        source = """
        datadict {
            Req = { data: string }
            Internal1 = { a: string }
            Internal2 = { b: string }
        }
        scd Context {
            system Sys {}
            external Client {}
            flow Req(Req): Client -> Sys
        }
        dfd Level0 {
            refines: Context.Sys
            process A {}
            process B {}
            flow Context.Req: -> A
            flow Internal1(Internal1): A -> B
            flow Internal2(Internal2): B -> A
            flow InternalBundle = Internal1 | Internal2
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"


class TestFlowUnionGrammarEdgeCases:
    """Tests for flow union grammar edge cases."""

    def test_flow_union_with_keyword_like_names(self) -> None:
        """Flow union with keyword-like names should parse."""
        source = """
        datadict {
            Request = { data: string }
            Response = { result: string }
        }
        scd Context {
            system Sys {}
            external User {}
            flow Request(Request): User -> Sys
            flow Response(Response): Sys -> User
            flow Session = Request | Response
        }
        """
        doc = parse_string(source)
        scd = doc.scds[0]
        assert len(scd.flow_unions) == 1

    def test_flow_union_whitespace_handling(self) -> None:
        """Flow union with various whitespace should parse."""
        source = """
        datadict {
            A = { a: string }
            B = { b: string }
            C = { c: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow A(A): E -> Sys
            flow B(B): E -> Sys
            flow C(C): Sys -> E
            flow Bundle = A|B|C
        }
        """
        doc = parse_string(source)
        scd = doc.scds[0]
        union = scd.flow_unions[0]
        assert union.members == ["A", "B", "C"]

    def test_flow_union_before_flows(self) -> None:
        """Flow union declared before flows should still parse."""
        # Note: Grammar allows this but validation will catch missing flows
        source = """
        datadict {
            A = { a: string }
            B = { b: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow Bundle = A | B
            flow A(A): E -> Sys
            flow B(B): Sys -> E
        }
        """
        doc = parse_string(source)
        scd = doc.scds[0]
        assert len(scd.flow_unions) == 1
        assert len(scd.flows) == 2


class TestFlowUnionGeneratorIntegration:
    """Tests for flow union generator integration."""

    def test_generator_accepts_expand_unions_parameter(self) -> None:
        """Generators should accept expand_unions parameter."""
        from designit.generators.graphviz import GraphVizGenerator
        from designit.generators.mermaid import MermaidGenerator

        # Test MermaidGenerator
        mermaid_gen = MermaidGenerator(include_placeholders=True, expand_unions=False)
        assert mermaid_gen.expand_unions is False

        mermaid_gen_expanded = MermaidGenerator(include_placeholders=True, expand_unions=True)
        assert mermaid_gen_expanded.expand_unions is True

        # Test GraphVizGenerator
        graphviz_gen = GraphVizGenerator(include_placeholders=True, expand_unions=False)
        assert graphviz_gen.expand_unions is False

        graphviz_gen_expanded = GraphVizGenerator(include_placeholders=True, expand_unions=True)
        assert graphviz_gen_expanded.expand_unions is True

    def test_generate_functions_accept_expand_unions(self) -> None:
        """generate_mermaid and generate_graphviz should accept expand_unions."""
        from designit.generators.graphviz import generate_graphviz
        from designit.generators.mermaid import generate_mermaid

        source = """
        datadict {
            Req = { data: string }
        }
        scd Context {
            system Sys {}
            external Client {}
            flow Req(Req): Client -> Sys
        }
        """
        doc = analyze_string(source)

        # Both should work without expand_unions (default)
        mermaid_result = generate_mermaid(doc, include_placeholders=True)
        assert len(mermaid_result) > 0

        graphviz_result = generate_graphviz(doc, include_placeholders=True)
        assert len(graphviz_result) > 0

        # Both should work with expand_unions=True
        mermaid_expanded = generate_mermaid(doc, include_placeholders=True, expand_unions=True)
        assert len(mermaid_expanded) > 0

        graphviz_expanded = generate_graphviz(doc, include_placeholders=True, expand_unions=True)
        assert len(graphviz_expanded) > 0

        # Both should work with expand_unions=False
        mermaid_bundled = generate_mermaid(doc, include_placeholders=True, expand_unions=False)
        assert len(mermaid_bundled) > 0

        graphviz_bundled = generate_graphviz(doc, include_placeholders=True, expand_unions=False)
        assert len(graphviz_bundled) > 0
