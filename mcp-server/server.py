"""Minimal FastMCP server for Saarthi tools."""

from pathlib import Path
import sys

from fastmcp import FastMCP
from fastmcp.server.auth import MultiAuth
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.logging import setup_logging  # noqa: E402
from shared.notifications.whatsapp import send_whatsapp_message as send_whatsapp_transport  # noqa: E402
from shared.settings import McpSettings, get_mcp_settings  # noqa: E402


def build_mcp_auth(settings: McpSettings) -> MultiAuth:
    """Build bearer-token auth for the MCP server."""
    verifier = StaticTokenVerifier(
        tokens={
            settings.mcp_token: {
                "client_id": "saarthi",
                "scopes": ["saarthi:mcp"],
            }
        }
    )
    return MultiAuth(verifiers=[verifier])


mcp = FastMCP("saarthi-mcp", auth=build_mcp_auth(get_mcp_settings()))


def send_personal_whatsapp_message(message: str) -> dict[str, bool | str]:
    """Send a WhatsApp message to the configured personal target."""
    if not message.strip():
        raise ValueError("message must not be empty")

    settings = get_mcp_settings()
    setup_logging(settings.logging_settings())
    sent = send_whatsapp_transport(
        message=message,
        whatsapp_settings=settings.whatsapp_settings_for_mcp(),
    )
    if sent:
        return {"success": True, "message": "WhatsApp message sent"}
    return {"success": False, "message": "Failed to send WhatsApp message"}


@mcp.tool(name="send_whatsapp_message")
def send_whatsapp_message_tool(message: str) -> dict[str, bool | str]:
    """Send a WhatsApp message to the configured personal target."""
    return send_personal_whatsapp_message(message)


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8001, path="/mcp")
