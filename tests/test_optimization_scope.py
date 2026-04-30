from harness.excel_reader import OptimizationRecord, group_records_by_optimization_scope


def test_optimization_scope_controls_grouping_keys():
    records = [
        _record("scene_a", "sub_1"),
        _record("scene_a", "sub_2"),
        _record("scene_b", "sub_1"),
    ]

    by_scene = group_records_by_optimization_scope(records=records, scope="scene")
    by_sub_scene = group_records_by_optimization_scope(records=records, scope="sub_scene")
    by_both = group_records_by_optimization_scope(records=records, scope="scene_sub_scene")
    by_scene_and_sub_scene = group_records_by_optimization_scope(records=records, scope="scene_and_sub_scene")

    assert sorted((key.scene_key, key.sub_scene_key) for key in by_scene) == [("scene_a", ""), ("scene_b", "")]
    assert sorted((key.scene_key, key.sub_scene_key) for key in by_sub_scene) == [("", "sub_1"), ("", "sub_2")]
    assert sorted((key.scene_key, key.sub_scene_key) for key in by_both) == [
        ("scene_a", "sub_1"),
        ("scene_a", "sub_2"),
        ("scene_b", "sub_1"),
    ]
    assert sorted((key.scene_key, key.sub_scene_key) for key in by_scene_and_sub_scene) == [
        ("scene_a", ""),
        ("scene_a", "sub_1"),
        ("scene_a", "sub_2"),
        ("scene_b", ""),
        ("scene_b", "sub_1"),
    ]


def test_scene_and_sub_scene_scope_skips_empty_sub_scene_group():
    records = [_record("scene_a", "")]

    grouped = group_records_by_optimization_scope(records=records, scope="scene_and_sub_scene")

    assert sorted((key.scene_key, key.sub_scene_key) for key in grouped) == [("scene_a", "")]


def _record(scene_key: str, sub_scene_key: str) -> OptimizationRecord:
    return OptimizationRecord(
        scene_raw=scene_key,
        scene_key=scene_key,
        content="content",
        sub_scene_raw=sub_scene_key,
        sub_scene_key=sub_scene_key,
        domain="domain",
        row_index=1,
    )
