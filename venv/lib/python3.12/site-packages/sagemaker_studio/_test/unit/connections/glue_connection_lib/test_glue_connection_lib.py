"""Tests for GlueConnectionLib module."""

import pytest


@pytest.mark.xfail
def test_that_you_wrote_tests():
    """Test that you wrote tests."""
    from textwrap import dedent

    assertion_string = dedent(
        """\
    No, you have not written tests.

    However, unless a test is run, the pytest execution will fail
    due to no tests or missing coverage. So, write a real test and
    then remove this!
    """
    )
    assert False, assertion_string


def test_glue_connection_lib_importable():
    """Test glue_connection_lib is importable."""
    import sagemaker_studio.connections.glue_connection_lib  # noqa: F401
