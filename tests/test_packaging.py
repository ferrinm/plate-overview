"""Packaging and headlessness tests.

These guard the two promises the package makes before it draws
anything: it installs and reports a version, and it never needs a
display.
"""

import os
import subprocess
import sys
import textwrap

import plate_overview

_GUI_TOOLKITS = ("napari", "qtpy", "PyQt5", "PyQt6", "PySide2", "PySide6")


def _run_probe(probe: str) -> str:
    """Run *probe* in a clean subprocess and return its stdout.

    ``MPLBACKEND`` is removed, so matplotlib picks a backend the way it
    would on a machine that this repository's CI does not configure.
    """
    env = dict(os.environ)
    env.pop("MPLBACKEND", None)
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(probe)],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    return result.stdout.strip()


def test_package_imports_and_reports_a_version():
    assert isinstance(plate_overview.__version__, str)
    assert plate_overview.__version__


def test_the_public_names_are_importable():
    assert plate_overview.render_plate_overview
    assert plate_overview.PlateFacts
    assert plate_overview.WellSource


def test_importing_the_package_pulls_in_no_gui_toolkit():
    """This package must draw without a display.

    A GUI toolkit in the import graph would make it unusable on the
    cluster, which is where every real plate is rendered.

    Checked in a subprocess rather than against this interpreter's
    ``sys.modules``: pytest autoloads plugins from every installed
    distribution, and one of those importing napari says nothing about
    what ``plate_overview`` imports.
    """
    pulled_in = _run_probe(f"""
        import sys
        import plate_overview  # noqa: F401
        forbidden = set({_GUI_TOOLKITS!r})
        print(",".join(sorted(forbidden & set(sys.modules))))
        """)
    assert not pulled_in, f"importing plate_overview pulled in {pulled_in}"


def test_rendering_a_figure_pulls_in_no_gui_toolkit():
    """Drawing must stay headless too, not only importing.

    The figure is built against the Agg canvas rather than through
    ``pyplot``, so no backend selection happens and no toolkit loads.
    """
    pulled_in = _run_probe(f"""
        import sys
        import tempfile
        from pathlib import Path

        import numpy as np

        from plate_overview._figure import render_combo_png

        with tempfile.TemporaryDirectory() as tmp:
            render_combo_png(
                combo=(1,),
                combo_channel_indices=[0],
                well_thumbs={{(1, 1): np.zeros((1, 8, 8), np.float32)}},
                contrast_for_combo=[(0.0, 1.0)],
                combo_colors=["cyan"],
                channel_names={{1: "ChannelOne"}},
                plate_rows=1,
                plate_cols=1,
                cell_h=8,
                cell_w=8,
                plate_id="SYNTHETIC-PLATE",
                objective_mag=None,
                field_label="1",
                timepoint_label="0",
                z_label="all",
                ffc_label="off",
                stitch_fields=False,
                um_per_thumb_pixel=1.0,
                scalebar_um=None,
                outpath=Path(tmp) / "out.png",
            )
        forbidden = set({_GUI_TOOLKITS!r})
        print(",".join(sorted(forbidden & set(sys.modules))))
        """)
    assert not pulled_in, f"rendering pulled in {pulled_in}"
