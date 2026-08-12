from __future__ import annotations

import unittest

from mcp import Client

from app.mcp_server import mcp


class MCPServerTest(unittest.IsolatedAsyncioTestCase):
    async def test_expected_tools_are_registered(self) -> None:
        async with Client(mcp) as client:
            result = await client.list_tools()

        self.assertEqual(
            {tool.name for tool in result.tools},
            {"query_transactions", "get_merchant_summary", "detect_anomalies"},
        )


if __name__ == "__main__":
    unittest.main()
