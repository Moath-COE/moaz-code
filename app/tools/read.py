from .base import Tool


class ReadTool(Tool):
    """Tool for reading the contents of a file."""

    def __init__(self):
        super().__init__(
            name="Read",
            description="Read and return the contents of a file",
            properties={
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to read",
                }
            },
            required=["file_path"],
        )

    def run(self, file_path: str) -> str:  # pyright: ignore[reportIncompatibleMethodOverride]
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except (OSError, UnicodeDecodeError) as e:
            return f"Error reading file: {e}"
