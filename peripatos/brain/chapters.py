from dataclasses import dataclass, field

from peripatos.models import DialogueTurn


@dataclass
class ChapterGroup:
    title: str
    turn_indices: list[int]
    section_refs: list[str]


def consolidate_chapters(
    turns: list[DialogueTurn],
    max_chapters: int = 5,
    min_chapters: int = 2,
) -> list[ChapterGroup]:
    if not turns:
        return []

    groups: list[ChapterGroup] = []
    for index, turn in enumerate(turns):
        if groups and groups[-1].section_refs[-1] == turn.section_ref:
            groups[-1].turn_indices.append(index)
        else:
            groups.append(
                ChapterGroup(
                    title=turn.section_ref,
                    turn_indices=[index],
                    section_refs=[turn.section_ref],
                )
            )

    while len(groups) > max_chapters:
        best_pair_index = 0
        best_combined_size = len(groups[0].turn_indices) + len(groups[1].turn_indices)
        for i in range(1, len(groups) - 1):
            combined = len(groups[i].turn_indices) + len(groups[i + 1].turn_indices)
            if combined < best_combined_size:
                best_combined_size = combined
                best_pair_index = i

        left = groups[best_pair_index]
        right = groups[best_pair_index + 1]
        merged = ChapterGroup(
            title=f"{left.title} & {right.title}",
            turn_indices=left.turn_indices + right.turn_indices,
            section_refs=left.section_refs + right.section_refs,
        )
        groups = groups[:best_pair_index] + [merged] + groups[best_pair_index + 2:]

    return groups
