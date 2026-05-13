from peripatos.brain.chapters import ChapterGroup, consolidate_chapters, generate_signposts
from peripatos.models import DialogueTurn, SpeakerRole


def _turn(section_ref: str) -> DialogueTurn:
    return DialogueTurn(speaker=SpeakerRole.HOST, text="t", section_ref=section_ref)


def test_consolidate_empty_input():
    assert consolidate_chapters([]) == []


def test_consolidate_single_section():
    turns = [_turn("intro"), _turn("intro"), _turn("intro")]
    groups = consolidate_chapters(turns, max_chapters=5)
    assert len(groups) == 1
    assert groups[0].title == "intro"
    assert groups[0].turn_indices == [0, 1, 2]
    assert groups[0].section_refs == ["intro"]


def test_consolidate_already_within_limit():
    turns = [
        _turn("a"), _turn("a"),
        _turn("b"),
        _turn("c"), _turn("c"), _turn("c"),
    ]
    groups = consolidate_chapters(turns, max_chapters=5)
    assert len(groups) == 3
    assert [g.title for g in groups] == ["a", "b", "c"]
    assert groups[0].turn_indices == [0, 1]
    assert groups[1].turn_indices == [2]
    assert groups[2].turn_indices == [3, 4, 5]


def test_consolidate_merges_to_max():
    turns = []
    sections = [
        ("s1", 5), ("s2", 1), ("s3", 4), ("s4", 1),
        ("s5", 3), ("s6", 1), ("s7", 2), ("s8", 6),
    ]
    for name, count in sections:
        for _ in range(count):
            turns.append(_turn(name))
    groups = consolidate_chapters(turns, max_chapters=5)
    assert len(groups) == 5


def test_consolidate_no_turns_lost():
    turns = []
    sections = [("s1", 3), ("s2", 2), ("s3", 4), ("s4", 1), ("s5", 5), ("s6", 2), ("s7", 3)]
    for name, count in sections:
        for _ in range(count):
            turns.append(_turn(name))
    total = len(turns)
    groups = consolidate_chapters(turns, max_chapters=3)
    all_indices = []
    for g in groups:
        all_indices.extend(g.turn_indices)
    assert sorted(all_indices) == list(range(total))


def test_consolidate_deterministic():
    turns = []
    sections = [("a", 2), ("b", 5), ("c", 1), ("d", 3), ("e", 4), ("f", 2), ("g", 1)]
    for name, count in sections:
        for _ in range(count):
            turns.append(_turn(name))
    r1 = consolidate_chapters(turns, max_chapters=4)
    r2 = consolidate_chapters(turns, max_chapters=4)
    assert [(g.title, g.turn_indices, g.section_refs) for g in r1] == \
           [(g.title, g.turn_indices, g.section_refs) for g in r2]


def test_signposts_multi_chapter():
    groups = [
        ChapterGroup(title="intro", turn_indices=[0], section_refs=["intro"]),
        ChapterGroup(title="method", turn_indices=[1], section_refs=["method"]),
        ChapterGroup(title="results", turn_indices=[2], section_refs=["results"]),
        ChapterGroup(title="conclusion", turn_indices=[3], section_refs=["conclusion"]),
    ]
    turns = [_turn("intro"), _turn("method"), _turn("results"), _turn("conclusion")]

    signposts = generate_signposts(groups, turns)

    assert len(signposts) == 3


def test_signposts_single_chapter():
    groups = [ChapterGroup(title="intro", turn_indices=[0], section_refs=["intro"])]

    assert generate_signposts(groups, [_turn("intro")]) == []


def test_signposts_text_format():
    groups = [
        ChapterGroup(title="intro", turn_indices=[0], section_refs=["intro"]),
        ChapterGroup(title="method", turn_indices=[1], section_refs=["method"]),
    ]

    signposts = generate_signposts(groups, [_turn("intro"), _turn("method")])

    assert signposts[0].text == "Now, let's turn to method."


def test_signposts_all_host_speaker():
    groups = [
        ChapterGroup(title="intro", turn_indices=[0], section_refs=["intro"]),
        ChapterGroup(title="method", turn_indices=[1], section_refs=["method"]),
    ]

    signposts = generate_signposts(groups, [_turn("intro"), _turn("method")])

    assert all(turn.speaker == SpeakerRole.HOST for turn in signposts)


def test_signposts_is_signpost_flag():
    groups = [
        ChapterGroup(title="intro", turn_indices=[0], section_refs=["intro"]),
        ChapterGroup(title="method", turn_indices=[1], section_refs=["method"]),
    ]

    signposts = generate_signposts(groups, [_turn("intro"), _turn("method")])

    assert all(turn.is_signpost for turn in signposts)


def test_signposts_text_length():
    groups = [
        ChapterGroup(title="intro", turn_indices=[0], section_refs=["intro"]),
        ChapterGroup(title="method", turn_indices=[1], section_refs=["method"]),
        ChapterGroup(title="results", turn_indices=[2], section_refs=["results"]),
    ]

    signposts = generate_signposts(groups, [_turn("intro"), _turn("method"), _turn("results")])

    assert all(len(turn.text.split()) <= 20 for turn in signposts)
