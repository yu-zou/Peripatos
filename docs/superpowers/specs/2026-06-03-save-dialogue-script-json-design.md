# Save Dialogue Script JSON — Design Spec

## Goal
After generating a dialogue script, save it as JSON alongside the output MP3 for logging/inspection purposes.

## Behavior
- File saved next to output MP3 with `.json` extension (e.g., `output.mp3` → `output.json`)
- Automatic — no user config or CLI flag needed
- Format: JSON-serialized `DialogueScript` (title, intro_turns, chapters, outro_turns)
- On write failure: warn but don't abort (MP3 is primary output)

## Implementation
One change in `peripatos_core/cli.py`, in `cmd_generate()`, after `gen.generate()` returns the script and before TTS synthesis begins. The existing `DialogueScript` dataclass is already compatible with JSON via `dataclasses.asdict()` or a simple custom serializer (dataclasses.asdict handles nested dataclasses with `field(default_factory=list)` patterns).

## JSON Format
```json
{
  "title": "Paper Title",
  "intro_turns": [{"speaker": "Host", "text": "...", "archetype": "peer"}],
  "chapters": [
    {
      "title": "Introduction",
      "turns": [{"speaker": "Host", "text": "...", "archetype": "peer"}],
      "transition_in_text": null
    }
  ],
  "outro_turns": [{"speaker": "Host", "text": "...", "archetype": "peer"}]
}
```

## Error Handling
If the JSON file can't be written (disk full, permission denied), log a warning but continue with MP3 synthesis.

## Dependencies
- No new dependencies — `json` is stdlib, `dataclasses` already used
