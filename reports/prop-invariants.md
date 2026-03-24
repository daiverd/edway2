# Property Test Report: Clip/Track/Parser/Proxy Invariants

**Commit:** 89bba14

## Properties tested

### Clip/Track invariants (C1-C4)

| ID | Property | Result |
|----|----------|--------|
| C1 | Clip duration == source_end - source_start, duration >= 0 | PASS |
| C2 | Track duration == 0.0 iff empty | PASS |
| C3 | Track duration >= max(clip.position + clip.duration) | PASS |
| C4 | clips_at finds every clip at its own position | PASS |

### Parser properties (P1-P5)

| ID | Property | Result |
|----|----------|--------|
| P1 | parse() never returns None for valid command strings | PASS |
| P2 | Time address precision (@M:SS and @M:SS.mmm) | PASS |
| P3 | Number address round-trip (n -> parse -> addr1.value == n) | PASS |
| P4 | Every COMMANDS entry is parseable | PASS |
| P5 | Range requires addr1 (addr2 != None implies addr1 != None) | PASS |

### Mute/Solo proxy properties (X1-X4)

| ID | Property | Result |
|----|----------|--------|
| X1 | muted_tracks.add(i) then i in muted_tracks | PASS |
| X2 | soloed_tracks.add(i) then discard(i) then i not in soloed_tracks | PASS |
| X3 | selected_tracks() never empty (with valid current_track) | PASS |
| X4 | selected_tracks() defaults to [current_track] when none selected | PASS |

## Bugs found

None. All 13 properties passed on first run with max_examples=200.

## Housekeeping

Removed unused import `insert_clips_at` from `tests/test_properties.py`.

## Full test output

```
tests/test_properties.py::test_session_track_count_non_negative PASSED   [  2%]
tests/test_properties.py::test_b1_block_round_trip PASSED                [  5%]
tests/test_properties.py::test_b2_time_ordering PASSED                   [  8%]
tests/test_properties.py::test_b3_block_contiguity PASSED                [ 11%]
tests/test_properties.py::test_b4_clamp_range PASSED                     [ 14%]
tests/test_properties.py::test_b5_validate_consistency PASSED            [ 17%]
tests/test_properties.py::test_b6_count_non_negative PASSED              [ 20%]
tests/test_properties.py::test_b7_from_time_monotonicity PASSED          [ 22%]
tests/test_properties.py::test_s1_clip_dict_round_trip PASSED            [ 25%]
tests/test_properties.py::test_s2_track_dict_round_trip PASSED           [ 28%]
tests/test_properties.py::test_s3_session_file_round_trip PASSED         [ 31%]
tests/test_properties.py::test_e1_delete_then_extract_is_empty PASSED    [ 34%]
tests/test_properties.py::test_e2_extract_duration_bounded PASSED        [ 37%]
tests/test_properties.py::test_e3_extract_positions_non_negative PASSED  [ 40%]
tests/test_properties.py::test_e4_delete_preserves_outsiders PASSED      [ 42%]
tests/test_properties.py::test_e5_delete_clip_count_bound PASSED         [ 45%]
tests/test_properties.py::test_e6_ripple_delete_no_negative_positions PASSED [ 48%]
tests/test_properties.py::test_e7_shift_preserves_clip_count PASSED      [ 51%]
tests/test_properties.py::test_e8_shift_no_negative_positions PASSED     [ 54%]
tests/test_properties.py::test_e9_ripple_delete_reduces_content PASSED   [ 57%]
tests/test_properties.py::test_e10_make_room_preserves_count PASSED      [ 60%]
tests/test_properties.py::test_c1_clip_duration_consistency PASSED       [ 62%]
tests/test_properties.py::test_c2_track_duration_zero_iff_empty PASSED   [ 65%]
tests/test_properties.py::test_c3_track_duration_covers_all_clips PASSED [ 68%]
tests/test_properties.py::test_c4_clips_at_finds_clip_at_own_position PASSED [ 71%]
tests/test_properties.py::test_p1_parse_never_returns_none PASSED        [ 74%]
tests/test_properties.py::test_p2_time_address_precision PASSED          [ 77%]
tests/test_properties.py::test_p2_time_address_millis PASSED             [ 80%]
tests/test_properties.py::test_p3_number_address_round_trip PASSED       [ 82%]
tests/test_properties.py::test_p4_every_command_parseable PASSED         [ 85%]
tests/test_properties.py::test_p5_range_requires_addr1 PASSED            [ 88%]
tests/test_properties.py::test_x1_mute_add_contains PASSED               [ 91%]
tests/test_properties.py::test_x2_solo_discard_contains PASSED           [ 94%]
tests/test_properties.py::test_x3_selected_tracks_never_empty PASSED     [ 97%]
tests/test_properties.py::test_x4_selected_tracks_default PASSED         [100%]

============================= 35 passed in 19.55s =============================
```

Full suite: 306 passed, 2 failed (pre-existing Windows path separator issues in test_project.py and test_commands_files.py, unrelated to these changes).
