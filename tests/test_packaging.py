"""Packaging smoke tests.

Deliberately thin: the renderer has not landed yet. These exist so CI
is meaningful from the first commit rather than green because it ran
nothing.
"""

import plate_overview


def test_package_imports_and_reports_a_version():
    assert isinstance(plate_overview.__version__, str)
    assert plate_overview.__version__


def test_package_is_headless():
    """No GUI toolkit may enter the dependency graph.

    The whole point of this package is that it draws without a display.
    An accidental napari or Qt import would make it unusable on the
    cluster, which is where every real plate is rendered.
    """
    import sys

    forbidden = {"napari", "qtpy", "PyQt5", "PyQt6", "PySide2", "PySide6"}
    assert not forbidden & set(sys.modules)
