"""验证解码器委托调用和真实 stdio MCP 协议，不接触用户课表或外网。"""

import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))

import classes


RAW = [
    {},
    [{"node": 1, "startTime": "08:00", "endTime": "08:45"},
     {"node": 2, "startTime": "08:55", "endTime": "09:40"}],
    {"startDate": "2026-8-31", "tableName": "测试课表"},
    [{"id": 1, "courseName": "数学"}],
    [{"id": 1, "day": 1, "startWeek": 1, "endWeek": 16, "step": 2,
      "startNode": 1, "room": "101", "teacher": "张老师"}],
]


class ImportTests(unittest.TestCase):
    def test_fetch_delegates_to_submodule(self):
        payload = json.dumps({"shareData": "\n".join(json.dumps(row) for row in RAW)})
        with patch.object(classes.subprocess, "run", return_value=subprocess.CompletedProcess(
            args=[], returncode=0, stdout=payload, stderr="",
        )) as run:
            self.assertEqual(classes.fetch("分享码"), RAW)
            args, kwargs = run.call_args
            self.assertEqual(args[0], [sys.executable, str(classes.DECODER_DIR / "main.py"),
                                      "--code", "分享码", "--android-id", "0000000000000000"])
            self.assertEqual(kwargs["cwd"], classes.DECODER_DIR)
            self.assertTrue(kwargs["capture_output"])
            run.return_value.stdout = '{"error": "invalid response"}'
            with self.assertRaisesRegex(ValueError, "数据格式"):
                classes.fetch("分享码")
            run.return_value.returncode = 1
            run.return_value.stderr = "decoder error"
            with self.assertRaisesRegex(RuntimeError, "decoder error"):
                classes.fetch("分享码")
            run.side_effect = subprocess.TimeoutExpired("decoder", 90)
            with self.assertRaisesRegex(RuntimeError, "超时"):
                classes.fetch("分享码")

    def test_failed_write_preserves_existing_schedule(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            classes, "CLASSES_FILE", Path(directory) / "classes.json",
        ):
            classes._save_schedule(RAW)
            original = classes.CLASSES_FILE.read_bytes()
            with patch.object(classes.os, "replace", side_effect=OSError("write failed")):
                with self.assertRaises(OSError):
                    classes._save_schedule(RAW)
            self.assertEqual(classes.CLASSES_FILE.read_bytes(), original)
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_production_entrypoint(self):
        with tempfile.TemporaryDirectory() as directory:
            params = StdioServerParameters(
                command=sys.executable, args=[str(ROOT / "mcp" / "wakeup_mcp.py")],
                cwd=directory, env={**os.environ, "WAKEUP_DATA_DIR": directory},
            )
            with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as errors:
                async with stdio_client(params, errlog=errors) as (reader, writer):
                    async with ClientSession(reader, writer) as client:
                        await client.initialize()
                        listed = await client.list_tools()
                        tools = {tool.name: tool for tool in listed.tools}
                        self.assertEqual(set(tools), {"wakeup_fetch", "wakeup_query", "wakeup_reset"})
                        self.assertEqual(tools["wakeup_query"].inputSchema["required"], ["day"])
                        self.assertEqual(tools["wakeup_fetch"].inputSchema["required"], ["share_id"])
                        for tool_name, parameter in (("wakeup_query", "day"), ("wakeup_fetch", "share_id")):
                            schema = tools[tool_name].inputSchema["properties"][parameter]
                            self.assertEqual(schema["type"], "string")
                            self.assertTrue(schema["description"].strip())
                        self.assertTrue(tools["wakeup_query"].annotations.readOnlyHint)
                        self.assertTrue(tools["wakeup_reset"].annotations.destructiveHint)
                        missing = await client.call_tool("wakeup_query", {"day": "2026-08-31"})
                        self.assertTrue(missing.isError)
                        self.assertIn("wakeup_fetch", missing.content[0].text)
                        invalid = await client.call_tool("wakeup_query", {})
                        self.assertTrue(invalid.isError)
                        empty_code = await client.call_tool("wakeup_fetch", {"share_id": " "})
                        self.assertTrue(empty_code.isError)
                        result = await client.call_tool("wakeup_reset", {})
                        self.assertFalse(result.isError)
                        self.assertEqual(result.structuredContent, {"deleted": False})

    async def test_import_query_reset_over_stdio(self):
        # 只替换网络取数，MCP 调度、存储、查询及重置均运行真实实现。
        bootstrap = (
            f"import sys; sys.path.insert(0, {str(ROOT / 'mcp')!r}); "
            "import wakeup_mcp as server; "
            f"server.classes.fetch = lambda share_id: {RAW!r} if share_id == 'valid' else []; "
            "server.mcp.run(transport='stdio')"
        )
        with tempfile.TemporaryDirectory() as directory:
            params = StdioServerParameters(
                command=sys.executable, args=["-c", bootstrap], cwd=directory,
                env={**os.environ, "WAKEUP_DATA_DIR": directory},
            )
            with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as errors:
                async with stdio_client(params, errlog=errors) as (reader, writer):
                    async with ClientSession(reader, writer) as client:
                        await client.initialize()
                        imported = await client.call_tool("wakeup_fetch", {"share_id": "valid"})
                        self.assertFalse(imported.isError)
                        self.assertEqual(imported.structuredContent, {"tableName": "测试课表", "courseCount": 1})
                        queried = await client.call_tool("wakeup_query", {"day": "2026-08-31"})
                        self.assertFalse(queried.isError)
                        lesson, = queried.structuredContent["result"]
                        self.assertEqual((lesson["courseName"], lesson["room"]), ("数学", "101"))
                        self.assertEqual((lesson["startTime"], lesson["endTime"]), ("08:00", "09:40"))
                        self.assertEqual(lesson["endNode"], 2)
                        for day in ("2026-08-30", "2026-09-01", "2026-12-28"):
                            empty = await client.call_tool("wakeup_query", {"day": day})
                            self.assertFalse(empty.isError)
                            self.assertEqual(empty.structuredContent, {"result": []})
                        invalid_date = await client.call_tool("wakeup_query", {"day": "2026-02-30"})
                        self.assertTrue(invalid_date.isError)
                        invalid_import = await client.call_tool("wakeup_fetch", {"share_id": "invalid"})
                        self.assertTrue(invalid_import.isError)
                        preserved = await client.call_tool("wakeup_query", {"day": "2026-08-31"})
                        self.assertEqual(preserved.structuredContent, queried.structuredContent)
                        for expected in (True, False):
                            reset = await client.call_tool("wakeup_reset", {})
                            self.assertFalse(reset.isError)
                            self.assertEqual(reset.structuredContent, {"deleted": expected})
                        missing = await client.call_tool("wakeup_query", {"day": "2026-08-31"})
                        self.assertTrue(missing.isError)


if __name__ == "__main__":
    unittest.main()
