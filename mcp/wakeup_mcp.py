"""通过 stdio MCP 暴露 WakeUp 课程表工具；stdout 仅用于 MCP 协议。"""

from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

import classes


mcp = FastMCP("wakeup")


@mcp.tool(structured_output=True, annotations=ToolAnnotations(
    readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True,
))
def wakeup_fetch(
    share_id: Annotated[str, Field(description="WakeUp 课程表分享码，不能为空。")],
) -> dict[str, Any]:
    """从 WakeUp 分享导入课程表，覆盖原表。

    成功返回 tableName（表名）和 courseCount（课程条目数）。
    分享码无效、解码失败或写入失败时返回工具错误，保留原课表。
    """
    schedule = classes._save_schedule(classes.fetch(share_id))
    return {"tableName": schedule["tableName"], "courseCount": len(schedule["courses"])}


@mcp.tool(structured_output=True, annotations=ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False,
))
def wakeup_query(
    day: Annotated[str, Field(description="查询课程的日期，格式 YYYY-MM-DD，例如 2026-10-22。")],
) -> list[dict[str, Any]]:
    """查询指定日期的课程，返回课程名称、节次、时间、地点和教师等信息。

    结构化结果为 {"result": [课程条目, ...]}；result 为 [] 表示当天无课。
    尚未导入课程表时返回工具错误，应先通过 wakeup_fetch 导入；
    日期错误也返回工具错误，均不表示当天无课。
    """
    return classes.query(day)


@mcp.tool(structured_output=True, annotations=ToolAnnotations(
    readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=False,
))
def wakeup_reset() -> dict[str, bool]:
    """删除已导入的课程表，无需参数，调用前须确认用户意图。

    返回 {"deleted": true} 表示已删除，false 表示原本没有课表。
    重复调用不会报错；文件删除失败时返回工具错误。
    """
    return {"deleted": classes.reset()}


if __name__ == "__main__":
    mcp.run(transport="stdio")
