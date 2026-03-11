from unittest.mock import patch
from hypothesis import given, settings, strategies as st
from src.contextanchor.cli import _render_context


@given(
    snapshot_id=st.text(
        min_size=5, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))
    ),
    goals=st.text(min_size=5, max_size=50),
    rationale=st.text(min_size=5, max_size=50),
    next_steps=st.lists(st.text(min_size=5, max_size=50), min_size=1, max_size=5),
)
@settings(max_examples=50)
def test_property_render_correctness(snapshot_id, goals, rationale, next_steps):
    """
    Property 55: Render Correctness
    Validates: Requirements 3.2, 5.1
    Ensure essential fields are always present in the rendered text format.
    """
    context_data = {
        "snapshot_id": snapshot_id,
        "goals": goals,
        "rationale": rationale,
        "next_steps": next_steps,
    }

    with patch("src.contextanchor.cli.console.print") as mock_print:
        _render_context(context_data, "text")

    with patch("src.contextanchor.cli.console.print") as mock_print:
        _render_context(context_data, "text")

        # The first call to print should be our Panel
        panel = mock_print.call_args_list[0].args[0]
        
        # Check title/subtitle for snapshot_id
        assert snapshot_id in panel.title
        
        # Check Markdown content for goals, rationale, next_steps
        markdown_obj = panel.renderable
        # In rich, Markdown object stores its source in .markup attribute
        assert goals in markdown_obj.markup
        assert rationale in markdown_obj.markup
        for step in next_steps:
             assert step in markdown_obj.markup
