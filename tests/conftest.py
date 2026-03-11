import pytest

def pytest_collection_modifyitems(items):
    """
    Automatically mark tests based on their directory.
    """
    for item in items:
        fspath = str(item.fspath)
        if "tests/unit" in fspath:
            item.add_marker(pytest.mark.unit)
        elif "tests/property" in fspath:
            item.add_marker(pytest.mark.property)
        elif "tests/integration" in fspath:
            item.add_marker(pytest.mark.integration)
