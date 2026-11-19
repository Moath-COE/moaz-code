import logging

logger = logging.getLogger(__name__)

BASE_PROMPT = """
You are a helpful coding assistant agent. The user is building very basic python programs and you should help them with that. Use your tools whenever required.
"""


def build_system_prompt(skills_prompt: str) -> str:
    """Build the system prompt dynamically."""
    FULL_PROMPT = f"""{BASE_PROMPT}\n{skills_prompt}
"""
    logger.info("System prompt:\n---%s---", FULL_PROMPT)
    return FULL_PROMPT
