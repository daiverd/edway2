# Property Tests: Editing Operations (E1-E10)

## Commit
`7e0c462`

## Properties: Pass/Fail Summary

| Test | Property | Result |
|------|----------|--------|
| E1 | Delete then extract is empty | PASS (after bugfix) |
| E2 | Extract duration bounded (per-clip) | PASS |
| E3 | Extract positions non-negative | PASS |
| E4 | Delete preserves outsiders | PASS |
| E5 | Delete clip count bound | PASS |
| E6 | Ripple delete no negative positions | PASS |
| E7 | Shift preserves clip count | PASS |
| E8 | Shift no negative positions | PASS |
| E9 | Ripple delete reduces content | PASS |
| E10 | Make room preserves count | PASS |

## Bugs Found and Fixed

### Bug: Zero-duration clips from floating-point boundary alignment

**File:** `src/edway2/commands/editing.py`

**Symptom:** E1 and E2 failed. After `delete_range`, `extract_clips_in_range` on the same range returned clips with `source_start == source_end` (zero duration). This happened when a clip boundary aligned exactly with the delete range boundary due to floating-point arithmetic.

**Root cause:** Both `delete_range` (lines ~209, 221, 234) and `extract_clips_in_range` (line ~160) could produce clips where the trim/split resulted in `source_end - source_start` being zero or near-zero. For example, a clip at position=0 with duration=14.0 deleted over range [13.114, 14.0) would split, and the "after" part would have source_start == source_end. Due to floating-point imprecision, boundary checks (`clip_end <= start`) could fail to filter these degenerate clips.

**Fix:** Added `duration > 1e-12` guards before appending clips in:
- `delete_range`: all three trim/split branches (trim-end, trim-start, split-into-two)
- `extract_clips_in_range`: the extracted clip append

### E2 test adjustment

The original E2 spec ("total duration <= range duration") does not hold when overlapping clips exist at the same position — this is valid in edway2's layering model. Adjusted E2 to verify each individual extracted clip's duration <= range duration instead of the sum.

## Full Test Output (final run)

```
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.0.2, pluggy-1.6.0

collected 21 items

tests/test_properties.py::test_session_track_count_non_negative PASSED   [  4%]
tests/test_properties.py::test_b1_block_round_trip PASSED                [  9%]
tests/test_properties.py::test_b2_time_ordering PASSED                   [ 14%]
tests/test_properties.py::test_b3_block_contiguity PASSED                [ 19%]
tests/test_properties.py::test_b4_clamp_range PASSED                     [ 23%]
tests/test_properties.py::test_b5_validate_consistency PASSED            [ 28%]
tests/test_properties.py::test_b6_count_non_negative PASSED              [ 33%]
tests/test_properties.py::test_b7_from_time_monotonicity PASSED          [ 38%]
tests/test_properties.py::test_s1_clip_dict_round_trip PASSED            [ 42%]
tests/test_properties.py::test_s2_track_dict_round_trip PASSED           [ 47%]
tests/test_properties.py::test_s3_session_file_round_trip PASSED         [ 52%]
tests/test_properties.py::test_e1_delete_then_extract_is_empty PASSED    [ 57%]
tests/test_properties.py::test_e2_extract_duration_bounded PASSED        [ 61%]
tests/test_properties.py::test_e3_extract_positions_non_negative PASSED  [ 66%]
tests/test_properties.py::test_e4_delete_preserves_outsiders PASSED      [ 71%]
tests/test_properties.py::test_e5_delete_clip_count_bound PASSED         [ 76%]
tests/test_properties.py::test_e6_ripple_delete_no_negative_positions PASSED [ 80%]
tests/test_properties.py::test_e7_shift_preserves_clip_count PASSED      [ 85%]
tests/test_properties.py::test_e8_shift_no_negative_positions PASSED     [ 90%]
tests/test_properties.py::test_e9_ripple_delete_reduces_content PASSED   [ 95%]
tests/test_properties.py::test_e10_make_room_preserves_count PASSED      [100%]

============================= 21 passed in 10.61s =============================
```

Full suite: 292 passed, 2 failed (pre-existing failures in `test_commands_files.py` and `test_project.py`, unrelated to editing changes).
