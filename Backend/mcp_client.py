
import asyncio
import json
import os
import sys

from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# =========================================================
# CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_SERVER_PATH = (
    BASE_DIR / "Backend" / "mcp_server.py"
)

MCP_SERVER_PATH = Path(
    os.getenv(
        "MCP_SERVER_PATH",
        str(DEFAULT_SERVER_PATH),
    )
).resolve()

MCP_SERVER_TIMEOUT = float(
    os.getenv("MCP_SERVER_TIMEOUT", "30")
)


# =========================================================
# SERVER CONFIGURATION
# =========================================================

def _get_server_parameters():
    """
    Create MCP server launch configuration.
    The server runs as a separate Python process over stdio.
    """

    if not MCP_SERVER_PATH.exists():
        raise FileNotFoundError(
            f"MCP server file not found: {MCP_SERVER_PATH}"
        )

    return StdioServerParameters(
        command=sys.executable,
        args=[str(MCP_SERVER_PATH)],
        env=os.environ.copy(),
    )


# =========================================================
# RESULT CONVERSION
# =========================================================

def _convert_content(content):
    """
    Convert MCP content blocks into JSON-friendly values.
    """

    if content is None:
        return None

    if isinstance(content, list):
        return [
            _convert_content(item)
            for item in content
        ]

    text_value = getattr(content, "text", None)

    if text_value is not None:
        try:
            return json.loads(text_value)
        except (ValueError, TypeError):
            return text_value

    image_data = getattr(content, "data", None)

    if image_data is not None:
        return {
            "type": "image",
            "mimeType": getattr(
                content,
                "mimeType",
                None,
            ),
            "data": image_data,
        }

    return str(content)


def _tool_to_dict(tool):
    """
    Convert an MCP Tool object into a dictionary.
    """

    return {
        "name": tool.name,
        "description": tool.description or "",
        "inputSchema": tool.inputSchema or {},
    }


# =========================================================
# ASYNC MCP CONNECTION
# =========================================================

async def _list_tools_async():
    server_parameters = _get_server_parameters()

    async with stdio_client(
        server_parameters,
    ) as (read_stream, write_stream):

        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            await asyncio.wait_for(
                session.initialize(),
                timeout=MCP_SERVER_TIMEOUT,
            )

            result = await asyncio.wait_for(
                session.list_tools(),
                timeout=MCP_SERVER_TIMEOUT,
            )

            return [
                _tool_to_dict(tool)
                for tool in result.tools
            ]


async def _call_tool_async(
    tool_name,
    arguments,
):
    server_parameters = _get_server_parameters()

    async with stdio_client(
        server_parameters,
    ) as (read_stream, write_stream):

        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            await asyncio.wait_for(
                session.initialize(),
                timeout=MCP_SERVER_TIMEOUT,
            )

            result = await asyncio.wait_for(
                session.call_tool(
                    tool_name,
                    arguments=arguments,
                ),
                timeout=MCP_SERVER_TIMEOUT,
            )

            return {
                "success": not result.isError,
                "tool_name": tool_name,
                "content": _convert_content(
                    result.content
                ),
                "structuredContent": getattr(
                    result,
                    "structuredContent",
                    None,
                ),
                "is_error": result.isError,
            }


# =========================================================
# SAFE ASYNC RUNNER
# =========================================================

def _run_async(coroutine):
    """
    Run an async MCP operation from synchronous FastAPI routes.
    """

    try:
        asyncio.get_running_loop()

    except RuntimeError:
        return asyncio.run(coroutine)

    # If an event loop already exists in this thread,
    # execute the coroutine in a separate thread.
    import threading

    result = {}
    error = {}

    def run_in_thread():
        try:
            result["value"] = asyncio.run(coroutine)
        except Exception as exception:
            error["value"] = exception

    thread = threading.Thread(
        target=run_in_thread,
        daemon=True,
    )

    thread.start()
    thread.join()

    if "value" in error:
        raise error["value"]

    return result.get("value")


# =========================================================
# GET AVAILABLE MCP TOOLS
# =========================================================

def get_available_tools():
    """
    Return all tools exposed by the configured MCP server.
    """

    try:
        tools = _run_async(
            _list_tools_async()
        )

        return {
            "success": True,
            "connected": True,
            "tools": tools,
            "count": len(tools),
            "server": str(MCP_SERVER_PATH),
        }

    except Exception as error:
        return {
            "success": False,
            "connected": False,
            "tools": [],
            "count": 0,
            "server": str(MCP_SERVER_PATH),
            "error": str(error),
        }


# =========================================================
# EXECUTE MCP TOOL
# =========================================================

def execute_mcp_tool(
    tool_name,
    arguments=None,
):
    """
    Execute a tool exposed by the MCP server.
    """

    tool_name = str(tool_name or "").strip()

    if not tool_name:
        return {
            "success": False,
            "error": "Tool name is required.",
        }

    if arguments is None:
        arguments = {}

    if not isinstance(arguments, dict):
        return {
            "success": False,
            "error": "Tool arguments must be a dictionary.",
        }

    try:
        # Verify that the requested tool exists.
        available = _run_async(
            _list_tools_async()
        )

        matching_tool = next(
            (
                tool for tool in available
                if tool["name"] == tool_name
            ),
            None,
        )

        if matching_tool is None:
            return {
                "success": False,
                "error": (
                    f"MCP tool '{tool_name}' was not found."
                ),
                "available_tools": [
                    tool["name"]
                    for tool in available
                ],
            }

        result = _run_async(
            _call_tool_async(
                tool_name,
                arguments,
            )
        )

        return result

    except Exception as error:
        return {
            "success": False,
            "tool_name": tool_name,
            "error": str(error),
        }
