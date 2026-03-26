# Serialization Round-Trip Property Tests Report

## Commit

`2351add20e9b2b729513af8ff35c150172e688e4`

## Properties Tested

| Property | Description | Result |
|----------|-------------|--------|
| S1 | Clip dict round-trip (`Clip.from_dict(clip.to_dict())`) | PASS |
| S2 | Track dict round-trip (`Track.from_dict(track.to_dict())`) | PASS |
| S3 | Session file round-trip (`to_file` / `from_file`) | PASS |

All three properties pass with `max_examples=200`.

## Bugs Found

None. The serialization code in `src/edway2/session.py` correctly round-trips all data types:

- Clip fields (source, source_start, source_end, position, gain, fade_in, fade_out, effects)
- Track fields (name, start_time, selected, muted, soloed, record, gain, effects, clips)
- Session scalar fields (name, sample_rate, block_duration_ms, master_gain, current_position, current_track)
- Session marks (dict[str, float])
- Session regions (dict[str, tuple[float, float]] -- JSON round-trips through lists, `from_file` converts back with `tuple(v)`)

## Full Test Output (final run)

```
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.0.2, pluggy-1.6.0
hypothesis profile 'default'
rootdir: C:\Users\Q\src\edway2
configfile: pyproject.toml
testpaths: tests
plugins: hypothesis-6.151.9, mock-3.15.1
collected 284 items

tests\test_blocks.py ...........................                         [  9%]
tests\test_cli.py ......                                                 [ 11%]
tests\test_commands_editing.py ....................................      [ 24%]
tests\test_commands_export.py .........                                  [ 27%]
tests\test_commands_files.py ........F                                   [ 30%]
tests\test_commands_marks.py ..............                              [ 35%]
tests\test_commands_misc.py .........                                    [ 38%]
tests\test_commands_playback.py ..........                               [ 42%]
tests\test_commands_tracks.py ................................           [ 53%]
tests\test_git_undo.py .........................                         [ 62%]
tests\test_parser.py ....................................................[80%]
.....                                                                    [ 82%]
tests\test_project.py ............F...                                   [ 87%]
tests\test_properties.py ...........                                     [ 91%]
tests\test_repl.py .......                                               [ 94%]
tests\test_session.py .................                                  [100%]

2 failed, 282 passed in 31.61s
```

The 2 failures are pre-existing Windows-specific issues unrelated to serialization:
- `test_info_no_project`: PermissionError on temp directory cleanup (Windows file locking)
- `test_resolve_path_inside_project`: Backslash vs forward slash path separator on Windows
