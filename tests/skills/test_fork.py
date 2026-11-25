"""Tests for the fork service: run a `context: fork` skill in a subagent.

API these tests pin down:

    run_forked_skill(skills, spawner, name, args="") -> str
        the subagent's raw answer; raises on any failure, never error text
    frame_fork_result(name, answer) -> str
        the text the main conversation sees

Both the Skill tool (model calls the skill) and main (user types /skill) use
them, so the two paths cannot drift apart.
"""

import pytest

from app.skills import SkillRegistry, SkillsLoader
from app.skills.fork import frame_fork_result, run_forked_skill
from tests.fakes import FakeSpawner
from tests.instructions import expected_instructions


def forked_skills(tmp_path, body: str = "Say blueberry.") -> SkillRegistry:
    skill_dir = tmp_path / "apple"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        f"---\ndescription: Does things.\ncontext: fork\n---\n\n{body}\n",
        encoding="utf-8",
    )
    return SkillRegistry(SkillsLoader([tmp_path]).load())


def test_spec_prompt_is_the_expanded_body(tmp_path):
    spawner = FakeSpawner()

    run_forked_skill(forked_skills(tmp_path), spawner, "apple")

    assert [spec.prompt for spec in spawner.specs] == [
        expected_instructions(tmp_path, "Say blueberry.")
    ]


def test_spec_prompt_has_the_arguments_filled_in(tmp_path):
    spawner = FakeSpawner()

    run_forked_skill(
        forked_skills(tmp_path, "Checksum of $ARGUMENTS"), spawner, "apple", "4127"
    )

    assert spawner.specs[0].prompt.endswith("Checksum of 4127")


def test_spec_is_labelled_with_the_skill_name(tmp_path):
    spawner = FakeSpawner()

    run_forked_skill(forked_skills(tmp_path), spawner, "apple")

    assert spawner.specs[0].label == "skill:apple"


def test_returns_the_raw_answer_without_framing(tmp_path):
    answer = run_forked_skill(
        forked_skills(tmp_path), FakeSpawner(answer="blueberry"), "apple"
    )

    assert answer == "blueberry"


def test_spawner_exceptions_propagate(tmp_path):
    spawner = FakeSpawner(error=ConnectionError("network down"))

    with pytest.raises(ConnectionError, match="network down"):
        run_forked_skill(forked_skills(tmp_path), spawner, "apple")


def test_frame_fork_result_is_the_exact_stage_text():
    assert (
        frame_fork_result("apple", "blueberry")
        == "Skill apple ran in a separate context and returned: blueberry"
    )
