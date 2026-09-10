"""Packaging smoke tests.

Deliberately thin: the renderer has not landed yet. These exist so CI
is meaningful from the first commit rather than green because it ran
nothing.
"""

import subprocess
import sys
import textwrap

import plate_overview

_GUI_TOOLKITS = ("napari", "qtpy", "PyQt5", "PyQt6", "PySide2", "PySide6")


def test_package_imports_and_reports_a_version():
    assert isinstance(plate_overview.__version__, str)
    assert plate_overview.__version__


def test_importing_the_package_pulls_in_no_gui_toolkit():
    """This package must draw without a display.

    A GUI toolkit in the import graph would make it unusable on the
    cluster, which is where every real plate is rendered.

    Checked in a subprocess rather than against this interpreter's
    ``sys.modules``: pytest autoloads plugins from every installed
    distribution, and one of those importing napari says nothing about
    what ``plate_overview`` imports.
    """
    probe = textwrap.dedent(
        f"""
        import sys
        import plate_overview  # noqa: F401
        forbidden = set({_GUI_TOOLKITS!r})
        print(",".join(sorted(forbidden & set(sys.modules))))
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        check=True,
    )
    pulled_in = result.stdout.strip()
    assert not pulled_in, f"importing plate_overview pulled in {pulled_in}"
