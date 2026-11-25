import logging

logger = logging.getLogger(__name__)

BASE_PROMPT = """"""


def build_system_prompt(skills_prompt: str) -> str:
    """Build the system prompt dynamically."""
    FULL_PROMPT = f"""{BASE_PROMPT}\n{skills_prompt}
"""
    logger.info("System prompt:\n---%s---", FULL_PROMPT)
    return FULL_PROMPT
