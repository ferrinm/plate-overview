"""End-to-end tests for the gathering loop and the sidecar."""

from __future__ import annotations

import json

import numpy as np
import pytest
from PIL import Image as PILImage
from synthetic import FakeWellSource, make_well

from plate_overview import render_plate_overview

WELL_PX = 16


def render(source, plate, output_dir, **kwargs):
    """Render the synthetic plate with fast, quiet defaults."""
    kwargs.setdefault("well_px", WELL_PX)
    kwargs.setdefault("verbose", False)
    return render_plate_overview(source, plate, output_dir, **kwargs)


def read_sidecar(written):
    return json.loads(written[-1].read_text())


def test_it_writes_one_png_per_channel_combo_and_one_sidecar(
    well_source, plate_facts, tmp_path
):
    written = render(well_source, plate_facts, tmp_path)
    names = [p.name for p in written]
    assert names == [
        "SYNTHETIC-PLATE_overview_ch1.png",
        "SYNTHETIC-PLATE_overview_ch2.png",
        "SYNTHETIC-PLATE_overview_merge_all.png",
        "SYNTHETIC-PLATE_overview.json",
    ]
    for path in written:
        assert path.exists()
        assert path.stat().st_size > 0


def test_a_partial_merge_is_named_after_its_channels(plate_facts, tmp_path):
    plate_facts["channel_ids"] = [1, 2, 3]
    plate_facts["channel_names"][3] = "ChannelThree"
    wells = {
        (row, col): make_well(seed=100 * row + col, channels=3)
        for (row, col) in plate_facts["well_field_map"]
    }
    source = FakeWellSource(wells, channel_ids=[1, 2, 3])
    written = render(source, plate_facts, tmp_path)
    names = [p.name for p in written]
    assert "SYNTHETIC-PLATE_overview_ch1+ch3.png" in names
    assert "SYNTHETIC-PLATE_overview_merge_all.png" in names
    assert len(names) == 2**3


def test_every_png_opens_at_the_same_size(well_source, plate_facts, tmp_path):
    written = render(well_source, plate_facts, tmp_path)
    sizes = {PILImage.open(p).size for p in written[:-1]}
    assert len(sizes) == 1


def test_the_plate_is_read_once_however_many_pngs_are_written(
    well_source, plate_facts, tmp_path
):
    """The gathering loop is single-pass.

    Three PNGs come out of six well reads, not eighteen. A second pass
    would read the whole plate again for every channel combo.
    """
    render(well_source, plate_facts, tmp_path)
    assert len(well_source.calls) == len(plate_facts["well_field_map"])


def test_it_reads_the_first_field_of_each_well_by_default(
    well_source, plate_facts, tmp_path
):
    render(well_source, plate_facts, tmp_path)
    assert all(call["field"] == 1 for call in well_source.calls)
    assert all(call["stitch_fields"] is False for call in well_source.calls)


def test_a_fixed_field_is_applied_to_every_well(
    well_source, plate_facts, tmp_path
):
    render(well_source, plate_facts, tmp_path, field=2)
    assert all(call["field"] == 2 for call in well_source.calls)


def test_a_well_without_the_fixed_field_is_skipped(
    well_source, plate_facts, tmp_path
):
    plate_facts["well_field_map"][(1, 1)] = [1]
    render(well_source, plate_facts, tmp_path, field=2)
    read_wells = {(c["row"], c["column"]) for c in well_source.calls}
    assert (1, 1) not in read_wells
    assert len(read_wells) == len(plate_facts["well_field_map"]) - 1


def test_stitched_mode_asks_for_every_field_at_once(
    well_source, plate_facts, tmp_path
):
    render(well_source, plate_facts, tmp_path, field="stitched")
    assert all(call["field"] is None for call in well_source.calls)
    assert all(call["stitch_fields"] is True for call in well_source.calls)


def test_a_single_z_plane_is_passed_on_as_a_list(
    well_source, plate_facts, tmp_path
):
    render(well_source, plate_facts, tmp_path, z_slices=1)
    assert all(call["z_slices"] == [1] for call in well_source.calls)


def test_the_selected_timepoint_reaches_the_source(
    well_source, plate_facts, tmp_path
):
    render(well_source, plate_facts, tmp_path, timepoint=1)
    assert all(call["timepoint"] == 1 for call in well_source.calls)


def test_the_first_timepoint_is_the_default(
    well_source, plate_facts, tmp_path
):
    render(well_source, plate_facts, tmp_path)
    assert all(call["timepoint"] == 0 for call in well_source.calls)


def test_a_channel_subset_reaches_the_source_and_the_output(
    well_source, plate_facts, tmp_path
):
    written = render(well_source, plate_facts, tmp_path, channels=[2])
    assert all(call["channels"] == [2] for call in well_source.calls)
    assert [p.name for p in written] == [
        "SYNTHETIC-PLATE_overview_ch2.png",
        "SYNTHETIC-PLATE_overview.json",
    ]


def test_the_ffc_flag_reaches_the_source(well_source, plate_facts, tmp_path):
    render(well_source, plate_facts, tmp_path, apply_ffc=False)
    assert all(call["apply_ffc"] is False for call in well_source.calls)


def test_the_output_directory_is_created(well_source, plate_facts, tmp_path):
    target = tmp_path / "new" / "nested"
    render(well_source, plate_facts, target)
    assert target.is_dir()


def test_wells_of_different_sizes_are_padded_into_one_grid(
    plate_facts, tmp_path
):
    """A well with fewer fields must not shift the grid.

    Cells are placed at a fixed pitch, so a short thumbnail is padded
    rather than allowed to move its neighbors.
    """
    wells = {}
    for row, col in plate_facts["well_field_map"]:
        well = make_well(seed=100 * row + col)
        if (row, col) == (1, 1):
            well = well[:, :, : well.shape[2] // 2]
        wells[(row, col)] = well
    source = FakeWellSource(wells)
    written = render(source, plate_facts, tmp_path)
    assert written[0].exists()


def test_an_empty_plate_still_writes_a_sidecar(plate_facts, tmp_path):
    plate_facts["well_field_map"] = {}
    written = render(FakeWellSource({}), plate_facts, tmp_path)
    sidecar = read_sidecar(written)
    assert sidecar["plate_contrast_limits"] == {
        "1": [0.0, 1.0],
        "2": [0.0, 1.0],
    }


# --- the sidecar -----------------------------------------------------


def test_the_sidecar_records_the_run(well_source, plate_facts, tmp_path):
    written = render(well_source, plate_facts, tmp_path, scalebar_um=25.0)
    sidecar = read_sidecar(written)
    assert sidecar["plate_id"] == "SYNTHETIC-PLATE"
    assert sidecar["plate_layout"] == {"rows": 2, "columns": 3}
    assert sidecar["parameters"]["well_px"] == WELL_PX
    assert sidecar["parameters"]["scalebar_um"] == 25.0
    assert sidecar["parameters"]["channels"] == [1, 2]
    assert sidecar["channel_names"] == {"1": "ChannelOne", "2": "ChannelTwo"}
    assert sidecar["channel_colormaps"] == {"1": "cyan", "2": "magenta"}
    assert sidecar["objective_magnification"] == "20"
    assert isinstance(sidecar["plate_overview_version"], str)


def test_the_sidecar_records_a_basename_not_a_path(
    well_source, plate_facts, tmp_path
):
    """A sidecar pasted into a public issue must leak no layout."""
    plate_facts["source_name"] = "/mnt/lab-share/2026-01-01/run-042/"
    written = render(well_source, plate_facts, tmp_path)
    sidecar = read_sidecar(written)
    assert sidecar["source_name"] == "run-042"
    assert "/" not in json.dumps(sidecar["source_name"])


def test_a_windows_path_is_reduced_to_a_basename(
    well_source, plate_facts, tmp_path
):
    plate_facts["source_name"] = r"D:\lab-share\2026-01-01\run-042"
    written = render(well_source, plate_facts, tmp_path)
    assert read_sidecar(written)["source_name"] == "run-042"


def test_the_sidecar_lists_filenames_not_paths(
    well_source, plate_facts, tmp_path
):
    written = render(well_source, plate_facts, tmp_path)
    sidecar = read_sidecar(written)
    assert sidecar["output_files"] == [p.name for p in written[:-1]]
    assert all("/" not in name for name in sidecar["output_files"])


def test_the_sidecar_records_the_scale_the_bar_was_drawn_at(
    well_source, plate_facts, tmp_path
):
    written = render(well_source, plate_facts, tmp_path)
    sidecar = read_sidecar(written)
    assert sidecar["pixel_size_m"] == [3.0e-07, 3.0e-07]
    # 64 px wide, downsampled to 16 px: 4× the physical pitch of 0.3 µm.
    assert sidecar["um_per_thumb_pixel"] == pytest.approx(1.2)


def test_provenance_is_merged_into_the_sidecar(
    well_source, plate_facts, tmp_path
):
    written = render(
        well_source,
        plate_facts,
        tmp_path,
        provenance={"consumer_version": "1.2.3"},
    )
    assert read_sidecar(written)["consumer_version"] == "1.2.3"


def test_provenance_cannot_overwrite_a_recorded_fact(
    well_source, plate_facts, tmp_path
):
    written = render(
        well_source,
        plate_facts,
        tmp_path,
        provenance={"source_name": "/absolute/path/that/must/not/win"},
    )
    assert read_sidecar(written)["source_name"] == "synthetic-run"


def test_the_sidecar_records_both_the_computed_and_the_used_contrast(
    well_source, plate_facts, tmp_path
):
    """An override must not erase what the plate actually measured."""
    written = render(
        well_source,
        plate_facts,
        tmp_path,
        contrast_limits={1: (10.0, 20.0)},
    )
    sidecar = read_sidecar(written)
    assert sidecar["rendering_contrast_limits"]["1"] == [10.0, 20.0]
    assert sidecar["plate_contrast_limits"]["1"] != [10.0, 20.0]
    assert (
        sidecar["plate_contrast_limits"]["2"]
        == sidecar["rendering_contrast_limits"]["2"]
    )
    assert sidecar["parameters"]["contrast_limits_override"] == {
        "1": [10.0, 20.0]
    }


def test_an_override_for_an_unselected_channel_is_ignored(
    well_source, plate_facts, tmp_path
):
    written = render(
        well_source,
        plate_facts,
        tmp_path,
        channels=[1],
        contrast_limits={2: (10.0, 20.0)},
    )
    sidecar = read_sidecar(written)
    assert "2" not in sidecar["rendering_contrast_limits"]


# --- optional plate facts --------------------------------------------


def test_colors_are_assigned_by_channel_order_when_none_are_supplied(
    well_source, plate_facts, tmp_path
):
    del plate_facts["channel_colors"]
    written = render(well_source, plate_facts, tmp_path)
    assert read_sidecar(written)["channel_colormaps"] == {
        "1": "cyan",
        "2": "magenta",
    }


def test_an_absent_objective_and_source_name_are_recorded_as_such(
    well_source, plate_facts, tmp_path
):
    del plate_facts["objective_magnification"]
    del plate_facts["source_name"]
    sidecar = read_sidecar(render(well_source, plate_facts, tmp_path))
    assert sidecar["objective_magnification"] is None
    assert sidecar["source_name"] == ""


# --- rejected input --------------------------------------------------


def test_a_non_positive_scalebar_is_rejected(
    well_source, plate_facts, tmp_path
):
    with pytest.raises(ValueError, match="scalebar_um must be positive"):
        render(well_source, plate_facts, tmp_path, scalebar_um=0)


def test_a_channel_that_was_never_acquired_is_rejected(
    well_source, plate_facts, tmp_path
):
    with pytest.raises(ValueError, match="No selected channels overlap"):
        render(well_source, plate_facts, tmp_path, channels=[99])


def test_a_timepoint_that_was_never_acquired_is_rejected(
    well_source, plate_facts, tmp_path
):
    with pytest.raises(ValueError, match="not in acquired timepoints"):
        render(well_source, plate_facts, tmp_path, timepoint=7)


def test_a_source_that_returns_the_wrong_shape_is_rejected(
    plate_facts, tmp_path
):
    """Name the well. An adapter author needs to know which read broke."""
    wells = {
        key: np.zeros((2, 8, 8), dtype=np.uint16)
        for key in plate_facts["well_field_map"]
    }
    with pytest.raises(ValueError, match=r"\(C, Z, Y, X\)"):
        render(FakeWellSource(wells), plate_facts, tmp_path)
