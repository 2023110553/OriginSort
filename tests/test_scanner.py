from pathlib import Path

from originsort.scanner import RuleCandidate


def test_single_destination_is_confirmed_candidate() -> None:
    candidate = RuleCandidate(
        source_key="eclass.dongguk.edu:ubboard:150765",
        destinations={Path("전공/시스템소프트웨어"): 3},
    )

    assert candidate.status == "확정 후보"
    assert candidate.evidence_count == 3


def test_multiple_destinations_are_a_conflict() -> None:
    candidate = RuleCandidate(
        source_key="eclass.dongguk.edu:ubboard:150765",
        destinations={Path("과목/A"): 2, Path("과목/B"): 1},
    )

    assert candidate.status == "충돌"
