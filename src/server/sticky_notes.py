import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from src.core.config import get_settings
from src.core.logging_server import get_logger

# Create an MCP server
MCP_SERVER_Id = "sticky_notes"

settings = get_settings()
logger = get_logger(MCP_SERVER_Id)

mcp = FastMCP(
    name=MCP_SERVER_Id,
    retry_interval=100,
    debug=True,
    port=50053
)

NOTES_FILE = Path(__file__).parent.parent.parent.joinpath("assets","sticky_notes","notes.txt")

def ensure_file():
    if not NOTES_FILE.is_file():
        with open(NOTES_FILE, "w") as f:
            f.write("")

@mcp.tool()
def add_note(message: str) -> str:
    """
    Append a new note to the sticky note file.

    Args:
        message (str): The note content to be added.

    Returns:
        str: Confirmation message indicating the note was saved.
    """
    logger.info(f"Adding note: {message}")
    ensure_file()
    with open(NOTES_FILE, "a") as f:
        f.write(message + "\n")
    return "Note saved!"

@mcp.tool()
def read_notes() -> str:
    """
    Read and return all notes from the sticky note file.

    Returns:
        str: All notes as a single string separated by line breaks.
             If no notes exist, a default message is returned.
    """
    logger.info("Reading all notes.")
    ensure_file()
    with open(NOTES_FILE) as f:
        content = f.read().strip()
    return content or "No notes yet."

@mcp.resource("notes://latest")
def get_latest_note() -> str:
    """
    Get the most recently added note from the sticky note file.

    Returns:
        str: The last note entry. If no notes exist, a default message is returned.
    """
    logger.info("Fetching the latest note.")
    ensure_file()
    with open(NOTES_FILE) as f:
        lines = f.readlines()
    return lines[-1].strip() if lines else "No notes yet."

@mcp.prompt()
def note_summary_prompt() -> str:
    """
    Generate a prompt asking the AI to summarize all current notes.

    Returns:
        str: A prompt string that includes all notes and asks for a summary.
             If no notes exist, a message will be shown indicating that.
    """
    logger.info("Generating note summary prompt.")
    ensure_file()
    with open(NOTES_FILE) as f:
        content = f.read().strip()
    if not content:
        return "There are no notes yet."

    return f"Summarize the current notes: {content}"


def main():
    # Initialize and run the server
    logger.info(f"Initializing MCP Server - [{MCP_SERVER_Id}]...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
    """MCP Everything Server - Comprehensive conformance test server."""
