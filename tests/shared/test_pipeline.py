"""Data processing pipeline — tests for context building, JSON parsing, and step execution."""

from shared.pipeline import (
    PipelineContext,
    build_context_package,
    parse_llm_json_response,
    run_pipeline,
)


# ── Context building ───��──────────────────────────────────

class TestBuildContextPackage:
    def test_includes_all_sections_when_they_fit(self):
        sections = {
            "listing": '{"title": "Alexan Braker Pointe", "price": 1445}',
            "neighborhood": "Walk Score: 72, Transit Score: 45",
            "reviews": "Great maintenance, quiet building",
        }
        parts = build_context_package(sections, max_tokens=200_000)
        assert len(parts) == 3
        assert "Alexan Braker Pointe" in parts[0]

    def test_respects_priority_order(self):
        sections = {
            "low_priority": "This is low priority data",
            "high_priority": "This is critical listing data",
            "medium_priority": "This is neighborhood data",
        }
        parts = build_context_package(
            sections,
            priority_order=["high_priority", "medium_priority"],
            max_tokens=200_000,
        )
        assert "critical listing data" in parts[0]
        assert "neighborhood data" in parts[1]

    def test_truncates_when_exceeding_budget(self):
        sections = {
            "small": "Brief overview of the property.",
            "huge": "x " * 500_000,  # Way over any budget
        }
        parts = build_context_package(sections, max_tokens=1_000, reserve_for_output=100)
        # Should include small section and truncated huge section
        assert any("Brief overview" in part for part in parts)
        assert any("truncated" in part for part in parts)

    def test_skips_empty_sections(self):
        sections = {
            "listing": "Real data here",
            "empty": "",
            "also_empty": None,
        }
        parts = build_context_package(sections, max_tokens=200_000)
        assert len(parts) == 1

    def test_returns_empty_for_no_data(self):
        parts = build_context_package({}, max_tokens=200_000)
        assert parts == []


# ── LLM JSON response parsing ────────────────────────────

class TestParseLlmJsonResponse:
    def test_parses_clean_json(self):
        result = parse_llm_json_response('{"score": 85, "verdict": "Fair price"}')
        assert result["score"] == 85
        assert result["verdict"] == "Fair price"

    def test_parses_markdown_fenced_json(self):
        response = '```json\n{"score": 92, "red_flags": ["No dishwasher"]}\n```'
        result = parse_llm_json_response(response)
        assert result["score"] == 92
        assert "No dishwasher" in result["red_flags"]

    def test_parses_json_with_surrounding_text(self):
        response = 'Here is the analysis:\n{"livability": 78}\nHope that helps!'
        result = parse_llm_json_response(response)
        assert result["livability"] == 78

    def test_returns_none_for_empty(self):
        assert parse_llm_json_response("") is None
        assert parse_llm_json_response(None) is None

    def test_returns_none_for_unparseable(self):
        assert parse_llm_json_response("No JSON here, just text.") is None

    def test_parses_json_array(self):
        response = '```\n["Pool", "Gym", "Parking"]\n```'
        result = parse_llm_json_response(response)
        assert result == ["Pool", "Gym", "Parking"]

    def test_handles_nested_json(self):
        response = '{"overview": "Nice place", "scores": {"location": 8, "value": 7}}'
        result = parse_llm_json_response(response)
        assert result["scores"]["location"] == 8


# ── Pipeline execution ────────────────────────────────────

class TestRunPipeline:
    def test_runs_steps_in_order(self):
        execution_order = []

        def step_gather(context):
            execution_order.append("gather")
            context.gathered["listing_title"] = "Alexan Braker Pointe"

        def step_process(context):
            execution_order.append("process")
            context.processed["title"] = context.gathered["listing_title"].upper()

        context = PipelineContext()
        result = run_pipeline(context, [
            ("gather", step_gather),
            ("process", step_process),
        ])

        assert execution_order == ["gather", "process"]
        assert result.processed["title"] == "ALEXAN BRAKER POINTE"
        assert result.steps_completed == ["gather", "process"]

    def test_continues_after_failed_step(self):
        def step_that_fails(context):
            raise RuntimeError("API timeout")

        def step_that_succeeds(context):
            context.result["status"] = "completed despite earlier failure"

        context = PipelineContext()
        result = run_pipeline(context, [
            ("failing_step", step_that_fails),
            ("recovery_step", step_that_succeeds),
        ])

        assert "failing_step" in result.errors
        assert "API timeout" in result.errors["failing_step"]
        assert result.result["status"] == "completed despite earlier failure"
        assert "recovery_step" in result.steps_completed

    def test_records_all_errors(self):
        def fail_one(context):
            raise ValueError("Bad data")

        def fail_two(context):
            raise ConnectionError("Network down")

        context = PipelineContext()
        result = run_pipeline(context, [
            ("validation", fail_one),
            ("fetch", fail_two),
        ])

        assert len(result.errors) == 2
        assert "Bad data" in result.errors["validation"]
        assert "Network down" in result.errors["fetch"]

    def test_empty_pipeline_returns_context_unchanged(self):
        context = PipelineContext(source_data={"listing_id": 42})
        result = run_pipeline(context, [])
        assert result.source_data == {"listing_id": 42}
        assert result.steps_completed == []

    def test_context_flows_between_steps(self):
        """Data set by step 1 is available to step 2."""
        def gather_price(context):
            context.gathered["price"] = 1445.0
            context.gathered["area_median"] = 1600.0

        def analyze_price(context):
            price = context.gathered["price"]
            median = context.gathered["area_median"]
            savings_percent = round((1 - price / median) * 100)
            context.result["verdict"] = f"Below market by {savings_percent}%"

        context = PipelineContext()
        result = run_pipeline(context, [
            ("gather_price", gather_price),
            ("analyze_price", analyze_price),
        ])

        assert result.result["verdict"] == "Below market by 10%"
