from app.tools.base import Tool


class WriteTool(Tool):
    """A tool that writes content to a file."""

    def __init__(self):
        super().__init__(
            name="Write",
            description="Write content to a file",
            properties={
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to write to",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file",
                },
            },
            required=["file_path", "content"],
        )

    def run(self, file_path: str, content: str) -> str:  # pyright: ignore[reportIncompatibleMethodOverride]
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to {file_path}"
        except OSError as e:
            return f"Error writing to file: {e}"
