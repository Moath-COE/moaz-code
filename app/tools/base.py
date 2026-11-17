from abc import ABC, abstractmethod


class Tool(ABC):
    """Base class for all tools."""

    def __init__(
        self, name: str, description: str, properties: dict, required: list[str]
    ):
        self.name = name
        self.description = description
        self.properties = properties
        self.required = required

    @abstractmethod
    def run(self, **kwargs) -> str:
        """Execute the tool and return its output as a string."""

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {**self.properties},
                    "required": self.required,
                },
            },
        }
