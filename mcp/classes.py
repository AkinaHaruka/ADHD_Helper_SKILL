"""WakeUp 课程表的导入、查询和存储逻辑，供 MCP 服务器直接调用。"""

import json
import os
import subprocess
import sys
from datetime import date, datetime
from json import JSONDecodeError
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
DECODER_DIR = SCRIPT_DIR / "depends" / "wakeup_decoder"
CLASSES_FILE = Path(os.environ.get("WAKEUP_DATA_DIR", SCRIPT_DIR / "data" / "classes")) / "classes.json"


def fetch(share_id: str) -> List[dict]:
    """从 WakeUp 分享读取课程表，失败时抛出带原因的异常。"""
    if not share_id.strip():
        raise ValueError("WakeUp 课程表分享码不能为空。")
    entrypoint = DECODER_DIR / "main.py"
    if not entrypoint.is_file():
        raise RuntimeError("WakeUp 解码器尚未初始化，请先执行 git submodule update --init --recursive。")
    try:
        result = subprocess.run(
            [sys.executable, str(entrypoint), "--code", share_id,
             "--android-id", "0000000000000000"],
            cwd=DECODER_DIR,
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            timeout=90,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("WakeUp 解析器执行超时，请稍后重试。") from error
    except OSError as error:
        raise RuntimeError(f"无法启动 WakeUp 解析器：{error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()
        message = detail[-1] if detail else "没有错误输出"
        raise RuntimeError(f"WakeUp 解析器执行失败（退出码 {result.returncode}）：{message}")
    try:
        data = json.loads(result.stdout)["shareData"].split("\n")
        return [json.loads(item) for item in data]
    except (JSONDecodeError, KeyError, TypeError, AttributeError) as error:
        raise ValueError("WakeUp 返回的课程表数据格式不正确。") from error


def _clean_schedule(raw_data: List[dict]) -> dict:
    """只保留按日期查询所需的字段，去除 WakeUp 的展示配置。"""
    if len(raw_data) < 5 or not isinstance(raw_data[2], dict):
        raise ValueError("WakeUp 返回的课程表数据格式不正确。")
    node_times, table, courses, lessons = raw_data[1], raw_data[2], raw_data[3], raw_data[4]
    if (not isinstance(node_times, list) or not isinstance(courses, list)
            or not isinstance(lessons, list) or not table.get("startDate")):
        raise ValueError("WakeUp 返回的课程表数据格式不正确。")

    names = {item["id"]: item.get("courseName", "未命名课程") for item in courses
             if isinstance(item, dict) and "id" in item}
    cleaned = []
    for lesson in lessons:
        if not isinstance(lesson, dict) or lesson.get("id") not in names:
            continue
        cleaned.append({
            "courseName": names[lesson["id"]], "day": lesson.get("day"),
            "startWeek": lesson.get("startWeek"), "endWeek": lesson.get("endWeek"),
            "step": lesson.get("step", 1), "startNode": lesson.get("startNode"),
            "room": lesson.get("room", ""), "teacher": lesson.get("teacher", ""),
            "courseNote": lesson.get("courseNote", ""),
            "ownTime": lesson.get("ownTime", False),
            "customStartTime": lesson.get("startTime", ""),
            "customEndTime": lesson.get("endTime", ""),
        })
    times = {
        str(item["node"]): {"startTime": item.get("startTime", ""), "endTime": item.get("endTime", "")}
        for item in node_times
        if isinstance(item, dict) and isinstance(item.get("node"), int)
    }
    return {"startDate": table["startDate"], "tableName": table.get("tableName", "课程表"),
            "nodeTimes": times, "courses": cleaned}


def _load_schedule() -> Optional[dict]:
    try:
        with CLASSES_FILE.open("r", encoding="utf-8") as file:
            schedule = json.load(file)
    except (FileNotFoundError, JSONDecodeError, OSError):
        return None
    return schedule if isinstance(schedule, dict) else None


def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError("日期必须使用 YYYY-MM-DD 格式。") from error


def query(day: str) -> List[dict]:
    """查询某日课程；未导入课程表时抛出 ``FileNotFoundError``。"""
    schedule = _load_schedule()
    if schedule is None:
        raise FileNotFoundError("尚未导入课程表，请先调用 wakeup_fetch 导入 WakeUp 分享码。")

    target, start = _parse_date(day), _parse_date(schedule["startDate"])
    offset = (target - start).days
    if offset < 0:
        return []
    week_index, weekday_index = divmod(offset, 7)
    week, weekday = week_index + 1, weekday_index + 1  # WakeUp: 周一为 1
    result = []
    node_times = schedule.get("nodeTimes", {})
    for lesson in schedule.get("courses", []):
        start_week, end_week, step = (lesson.get(key) for key in ("startWeek", "endWeek", "step"))
        if not all(isinstance(value, int) for value in (start_week, end_week, step)) or step < 1:
            continue
        # WakeUp 的 step 是课程连续占用的节次数，而不是隔周频率。
        # 例如 step=2 表示从 startNode 起连续两节课。
        if lesson.get("day") == weekday and start_week <= week <= end_week:
            item = dict(lesson)
            item["week"] = week
            if isinstance(item.get("startNode"), int):
                item["endNode"] = item["startNode"] + step - 1
                start_slot = node_times.get(str(item["startNode"]), {})
                end_slot = node_times.get(str(item["endNode"]), {})
                if item.get("ownTime") and item.get("customStartTime"):
                    item["startTime"] = item["customStartTime"]
                    item["endTime"] = item.get("customEndTime", "")
                else:
                    item["startTime"] = start_slot.get("startTime", "")
                    item["endTime"] = end_slot.get("endTime", "")
            item.pop("ownTime", None)
            item.pop("customStartTime", None)
            item.pop("customEndTime", None)
            result.append(item)
    return sorted(result, key=lambda item: (item.get("startNode") is None, item.get("startNode", 0)))


def _save_schedule(raw_data: List[dict]) -> dict:
    schedule = _clean_schedule(raw_data)
    CLASSES_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=CLASSES_FILE.parent,
                                suffix=".tmp", delete=False) as file:
            temporary = Path(file.name)
            json.dump(schedule, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary, CLASSES_FILE)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return schedule


def reset() -> bool:
    """删除已导入的课程表，返回是否实际删除了文件。"""
    try:
        CLASSES_FILE.unlink()
    except FileNotFoundError:
        return False
    return True
