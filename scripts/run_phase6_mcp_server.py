"""Launch the local EcoPilot Phase 6 MCP server over stdio."""

from mcp_service.server import run_stdio_server


def main() -> int:
    run_stdio_server()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
