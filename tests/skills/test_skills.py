"""Tests for skill discovery (SkillsLoader).

API these tests pin down (the module location is open, see the design talk):

    Skill(name: str, description: str, path: Path)
    SkillsLoader(roots: list[Path]).load() -> list[Skill]

Work through the steps in order. Uncomment ONE step, watch it fail, then make
it pass. Do not uncomment the next step until the current one is green.
"""

from pathlib import Path

import pytest

from app.skills import SkillsLoader


def write_skill(root: Path, folder: str, content: str) -> Path:
    """Create <root>/<folder>/SKILL.md with `content`. Returns the SKILL.md path."""
    skill_dir = root / folder
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")
    return skill_file


def skill_md(
    name: str, description: str, body: str = "Do the thing.", extra: str = ""
) -> str:
    return f"---\nname: {name}\ndescription: {description}\n{extra}---\n\n{body}\n"


@pytest.fixture
def root(tmp_path) -> Path:
    return tmp_path / "skills"


# --- Step 1: the simplest case, one valid skill ------------------------------


def test_loads_one_skill_with_name_and_description(root):
    write_skill(root, "apple", skill_md("apple", "Deploys the apple service."))

    skills = SkillsLoader([root]).load()

    assert len(skills) == 1
    assert skills[0].name == "apple"
    assert skills[0].description == "Deploys the apple service."


# --- Step 2: nothing to find -------------------------------------------------
# A root that does not exist is normal (most projects have no skills), so it
# must not raise.


def test_missing_root_gives_no_skills(tmp_path):
    skills = SkillsLoader([tmp_path / "does-not-exist"]).load()

    assert skills == []


def test_empty_root_gives_no_skills(root):
    root.mkdir()

    assert SkillsLoader([root]).load() == []


# --- Step 3: several skills, several roots -----------------------------------


def test_loads_every_skill_in_a_root(root):
    write_skill(root, "apple", skill_md("apple", "Deploys apple."))
    write_skill(root, "grape", skill_md("grape", "Tests grape."))

    skills = SkillsLoader([root]).load()

    assert {s.name for s in skills} == {"apple", "grape"}


def test_loads_skills_from_all_roots(tmp_path):
    agents = tmp_path / ".agents" / "skills"
    claude = tmp_path / ".claude" / "skills"
    write_skill(agents, "apple", skill_md("apple", "Deploys apple."))
    write_skill(claude, "grape", skill_md("grape", "Tests grape."))

    skills = SkillsLoader([agents, claude]).load()

    assert {s.name for s in skills} == {"apple", "grape"}


def test_result_order_is_stable_and_sorted_by_name(root):
    # Create in non-alphabetical order. The advertisement goes into the
    # prompt, so it must not change between runs.
    for name in ["pear", "apple", "grape"]:
        write_skill(root, name, skill_md(name, f"{name} skill."))

    names = [s.name for s in SkillsLoader([root]).load()]

    assert names == ["apple", "grape", "pear"]


# --- Step 4: the same name in two roots --------------------------------------
# The first root wins, so the order of `roots` is a priority order.


def test_first_root_wins_when_a_skill_name_appears_twice(tmp_path):
    agents = tmp_path / ".agents" / "skills"
    claude = tmp_path / ".claude" / "skills"
    write_skill(agents, "apple", skill_md("apple", "From agents."))
    write_skill(claude, "apple", skill_md("apple", "From claude."))

    skills = SkillsLoader([agents, claude]).load()

    assert len(skills) == 1
    assert skills[0].description == "From agents."


# --- Step 5: what a Skill remembers ------------------------------------------
# Later stages load the body on demand, so the skill must know where it lives.
# It must NOT hold the body now (level 1 only).


def test_skill_records_the_path_of_its_skill_file(root):
    skill_file = write_skill(root, "apple", skill_md("apple", "Deploys apple."))

    skill = SkillsLoader([root]).load()[0]

    assert skill.path == skill_file


def test_name_comes_from_the_folder_name(root):
    # The standard says they must match. If they do not, the folder name is the
    # identity, because later stages invoke skills by folder name.
    write_skill(root, "apple", skill_md("something-else", "Deploys apple."))

    assert SkillsLoader([root]).load()[0].name == "apple"


# --- Step 6: YAML that is more than "key: value" -----------------------------
# This is why we use a real parser instead of splitting on ":".


def test_description_may_contain_a_colon(root):
    write_skill(
        root, "apple", '---\ndescription: "Deploys: apple, then grape."\n---\nbody\n'
    )

    assert SkillsLoader([root]).load()[0].description == "Deploys: apple, then grape."


def test_description_may_be_a_folded_multiline_block(root):
    content = (
        "---\nname: apple\ndescription: >\n  Deploys the apple\n  service.\n---\nbody\n"
    )
    write_skill(root, "apple", content)

    assert SkillsLoader([root]).load()[0].description == "Deploys the apple service."


def test_dashes_inside_the_body_do_not_end_the_frontmatter_early(root):
    body = "First part.\n\n---\n\nSecond part with description: not metadata."
    write_skill(root, "apple", skill_md("apple", "Real description.", body))

    assert SkillsLoader([root]).load()[0].description == "Real description."


# --- Step 7: broken skills are skipped, never fatal --------------------------
# One bad skill must not stop the agent from starting. Skip it and keep going.


def test_folder_without_a_skill_file_is_skipped(root):
    (root / "empty-folder").mkdir(parents=True)
    write_skill(root, "apple", skill_md("apple", "Deploys apple."))

    assert [s.name for s in SkillsLoader([root]).load()] == ["apple"]


def test_plain_file_in_the_root_is_ignored(root):
    root.mkdir()
    (root / "notes.txt").write_text("not a skill")

    assert SkillsLoader([root]).load() == []


@pytest.mark.parametrize(
    "content",
    [
        "no frontmatter at all\n",
        "---\nname: apple\n---\nno description key\n",
        "---\ndescription: \n---\nempty description\n",
        "---\nthis: is: not: valid: yaml: [\n---\nbody\n",
        "---\n- just\n- a list\n---\nbody\n",
        "",
    ],
)
def test_invalid_skill_file_is_skipped(root, content):
    write_skill(root, "bad", content)
    write_skill(root, "apple", skill_md("apple", "Deploys apple."))

    assert [s.name for s in SkillsLoader([root]).load()] == ["apple"]


def test_skipped_skill_is_reported_on_stderr(root, capsys):
    # Not stdout: stdout must hold only the final answer for the tester.
    write_skill(root, "bad", "no frontmatter\n")

    SkillsLoader([root]).load()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "bad" in captured.err


# --- context: fork -----------------------------------------------------------


def test_skill_with_context_fork_is_marked_as_fork(root):
    write_skill(
        root, "apple", skill_md("apple", "Apple skill.", extra="context: fork\n")
    )

    skills = SkillsLoader([root]).load()

    assert skills[0].fork is True


def test_skill_without_context_is_not_a_fork(root):
    write_skill(root, "apple", skill_md("apple", "Apple skill."))

    skills = SkillsLoader([root]).load()

    assert skills[0].fork is False


def test_unknown_context_value_is_not_a_fork(root):
    write_skill(
        root, "apple", skill_md("apple", "Apple skill.", extra="context: banana\n")
    )

    skills = SkillsLoader([root]).load()

    assert skills[0].fork is False
