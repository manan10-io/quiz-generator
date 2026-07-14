import pytest
from app.schemas.parser import ParseOptions


@pytest.fixture
def default_options() -> ParseOptions:
    return ParseOptions()


@pytest.fixture
def no_ai_options() -> ParseOptions:
    return ParseOptions(ai_cleanup=False)
