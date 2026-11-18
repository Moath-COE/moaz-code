"""Tests for skill discovery (SkillLoader) and advertisement (render_skills).

API these tests pin down (the module location is open, see the design talk):

    Skill(name: str, description: str, path: Path)
    SkillLoader(roots: list[Path]).load() -> list[Skill]
    render_skills(skills: list[Skill]) -> str

Work through the steps in order. Uncomment ONE step, watch it fail, then make
it pass. Do not uncomment the next step until the current one is green.
"""

from pathlib import Path

import pytest

from app.skills import Skill, SkillLoader, render_skills


def write_skill(root: Path, folder: str, content: str) -> Path:
    """Create <root>/<folder>/SKILL.md with `content`. Returns the SKILL.md path."""
    skill_dir = root / folder
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")
    return skill_file


def skill_md(name: str, description: str, body: str = "Do the thing.") -> str:
    return f"---\nname: {name}\ndescription: {description}\n---\n\n{body}\n"


@pytest.fixture
def root(tmp_path) -> Path:
    return tmp_path / "skills"


# --- Step 1: the simplest case, one valid skill ------------------------------


def test_loads_one_skill_with_name_and_description(root):
    write_skill(root, "apple", skill_md("apple", "Deploys the apple service."))

    skills = SkillLoader([root]).load()

    assert len(skills) == 1
    assert skills[0].name == "apple"
    assert skills[0].description == "Deploys the apple service."


# --- Step 2: nothing to find -------------------------------------------------
# A root that does not exist is normal (most projects have no skills), so it
# must not raise.


def test_missing_root_gives_no_skills(tmp_path):
    skills = SkillLoader([tmp_path / "does-not-exist"]).load()

    assert skills == []


def test_empty_root_gives_no_skills(root):
    root.mkdir()

    assert SkillLoader([root]).load() == []


# --- Step 3: several skills, several roots -----------------------------------


def test_loads_every_skill_in_a_root(root):
    write_skill(root, "apple", skill_md("apple", "Deploys apple."))
    write_skill(root, "grape", skill_md("grape", "Tests grape."))

    skills = SkillLoader([root]).load()

    assert {s.name for s in skills} == {"apple", "grape"}


def test_loads_skills_from_all_roots(tmp_path):
    agents = tmp_path / ".agents" / "skills"
    claude = tmp_path / ".claude" / "skills"
    write_skill(agents, "apple", skill_md("apple", "Deploys apple."))
    write_skill(claude, "grape", skill_md("grape", "Tests grape."))

    skills = SkillLoader([agents, claude]).load()

    assert {s.name for s in skills} == {"apple", "grape"}


def test_result_order_is_stable_and_sorted_by_name(root):
    # Create in non-alphabetical order. The advertisement goes into the
    # prompt, so it must not change between runs.
    for name in ["pear", "apple", "grape"]:
        write_skill(root, name, skill_md(name, f"{name} skill."))

    names = [s.name for s in SkillLoader([root]).load()]

    assert names == ["apple", "grape", "pear"]


# --- Step 4: the same name in two roots --------------------------------------
# The first root wins, so the order of `roots` is a priority order.


def test_first_root_wins_when_a_skill_name_appears_twice(tmp_path):
    agents = tmp_path / ".agents" / "skills"
    claude = tmp_path / ".claude" / "skills"
    write_skill(agents, "apple", skill_md("apple", "From agents."))
    write_skill(claude, "apple", skill_md("apple", "From claude."))

    skills = SkillLoader([agents, claude]).load()

    assert len(skills) == 1
    assert skills[0].description == "From agents."


# --- Step 5: what a Skill remembers ------------------------------------------
# Later stages load the body on demand, so the skill must know where it lives.
# It must NOT hold the body now (level 1 only).


def test_skill_records_the_path_of_its_skill_file(root):
    skill_file = write_skill(root, "apple", skill_md("apple", "Deploys apple."))

    skill = SkillLoader([root]).load()[0]

    assert skill.path == skill_file


def test_name_comes_from_the_folder_name(root):
    # The standard says they must match. If they do not, the folder name is the
    # identity, because later stages invoke skills by folder name.
    write_skill(root, "apple", skill_md("something-else", "Deploys apple."))

    assert SkillLoader([root]).load()[0].name == "apple"


# --- Step 6: YAML that is more than "key: value" -----------------------------
# This is why we use a real parser instead of splitting on ":".


def test_description_may_contain_a_colon(root):
    write_skill(
        root, "apple", '---\ndescription: "Deploys: apple, then grape."\n---\nbody\n'
    )

    assert SkillLoader([root]).load()[0].description == "Deploys: apple, then grape."


def test_description_may_be_a_folded_multiline_block(root):
    content = (
        "---\nname: apple\ndescription: >\n  Deploys the apple\n  service.\n---\nbody\n"
    )
    write_skill(root, "apple", content)

    assert SkillLoader([root]).load()[0].description == "Deploys the apple service."


def test_dashes_inside_the_body_do_not_end_the_frontmatter_early(root):
    body = "First part.\n\n---\n\nSecond part with description: not metadata."
    write_skill(root, "apple", skill_md("apple", "Real description.", body))

    assert SkillLoader([root]).load()[0].description == "Real description."


# --- Step 7: broken skills are skipped, never fatal --------------------------
# One bad skill must not stop the agent from starting. Skip it and keep going.


def test_folder_without_a_skill_file_is_skipped(root):
    (root / "empty-folder").mkdir(parents=True)
    write_skill(root, "apple", skill_md("apple", "Deploys apple."))

    assert [s.name for s in SkillLoader([root]).load()] == ["apple"]


def test_plain_file_in_the_root_is_ignored(root):
    root.mkdir()
    (root / "notes.txt").write_text("not a skill")

    assert SkillLoader([root]).load() == []


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

    assert [s.name for s in SkillLoader([root]).load()] == ["apple"]


def test_skipped_skill_is_reported_on_stderr(root, capsys):
    # Not stdout: stdout must hold only the final answer for the tester.
    write_skill(root, "bad", "no frontmatter\n")

    SkillLoader([root]).load()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "bad" in captured.err


# --- Step 8: the advertisement (exact text, the tester depends on it) --------


def test_render_matches_the_required_format():
    skills = [
        Skill("apple", "Deploys the apple service to production.", Path("a/SKILL.md")),
        Skill(
            "grape",
            "Runs the grape test suite and reports failures.",
            Path("g/SKILL.md"),
        ),
    ]

    assert render_skills(skills) == (
        "You have access to the following skills:\n"
        "\n"
        "- apple: Deploys the apple service to production.\n"
        "- grape: Runs the grape test suite and reports failures."
    )


def test_render_with_no_skills_is_empty():
    # No header with nothing under it. Empty means "send no system message".
    assert render_skills([]) == ""


def test_render_does_not_include_the_body(root):
    write_skill(root, "apple", skill_md("apple", "Deploys apple.", "SECRET BODY TEXT"))

    text = render_skills(SkillLoader([root]).load())

    assert "SECRET BODY TEXT" not in text


def test_render_keeps_a_multiline_description_on_one_line(root):
    content = "---\nname: apple\ndescription: |\n  Line one.\n  Line two.\n---\nbody\n"
    write_skill(root, "apple", content)

    text = render_skills(SkillLoader([root]).load())

    assert "- apple: Line one. Line two." in text
