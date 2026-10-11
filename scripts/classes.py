"""WakeUp 课程表的导入、查询和重置命令行工具。"""

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime
from json import JSONDecodeError
from pathlib import Path
from typing import List


SCRIPT_DIR = Path(__file__).resolve().parent
CLASSES_FILE = SCRIPT_DIR / "data" / "classes" /"classes.json"


def fetch(share_id: str) -> List[dict]:
    """从 WakeUp 分享读取课程表，失败时抛出带原因的异常。"""
    command = [
        sys.executable,
        str(SCRIPT_DIR / "depends" / "wakeup_decoder" / "main.py"),
        "--code", share_id, "--android-id", "0000000000000000",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
    except OSError as error:
        raise RuntimeError(f"无法启动 WakeUp 解析器：{error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()
        message = detail[-1] if detail else "没有错误输出"
        raise RuntimeError(f"WakeUp 解析器执行失败（退出码 {result.returncode}）：{message}")
    try:
        data = json.loads(result.stdout)["shareData"].split("\n")
        return [json.loads(item) for item in data]
    except (JSONDecodeError, KeyError, TypeError) as error:
        raise ValueError("WakeUp 返回的课程表数据格式不正确。") from error


def _clean_schedule(raw_data: List[dict]) -> dict:
    """只保留按日期查询所需的字段，去除 WakeUp 的展示配置。"""
    if len(raw_data) < 5 or not isinstance(raw_data[2], dict):
        raise ValueError("WakeUp 返回的课程表数据格式不正确。")
    table, courses, lessons = raw_data[2], raw_data[3], raw_data[4]
    if not isinstance(courses, list) or not isinstance(lessons, list) or not table.get("startDate"):
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
        })
    return {"startDate": table["startDate"], "tableName": table.get("tableName", "课程表"),
            "courses": cleaned}


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
        raise FileNotFoundError("尚未导入课程表，请先执行 classes.py fetch {shareID}。")

    target, start = _parse_date(day), _parse_date(schedule["startDate"])
    offset = (target - start).days
    if offset < 0:
        return []
    week_index, weekday_index = divmod(offset, 7)
    week, weekday = week_index + 1, weekday_index + 1  # WakeUp: 周一为 1
    result = []
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
            result.append(item)
    return sorted(result, key=lambda item: (item.get("startNode") is None, item.get("startNode", 0)))


def _save_schedule(raw_data: List[dict]) -> dict:
    schedule = _clean_schedule(raw_data)
    CLASSES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CLASSES_FILE.open("w", encoding="utf-8") as file:
        json.dump(schedule, file, ensure_ascii=False, indent=2)
        file.write("\n")
    return schedule


def main() -> int:
    parser = argparse.ArgumentParser(description="WakeUp 课程表工具")
    commands = parser.add_subparsers(dest="command", required=True)
    fetch_parser = commands.add_parser("fetch", help="导入 WakeUp 分享课程表")
    fetch_parser.add_argument("share_id", help="WakeUp 课程表分享码")
    query_parser = commands.add_parser("query", help="查询某天的课程")
    query_parser.add_argument("day", help="日期，格式 YYYY-MM-DD")
    commands.add_parser("reset", help="删除已导入的课程表")
    args = parser.parse_args()

    if args.command == "fetch":
        try:
            raw_data = fetch(args.share_id)
            schedule = _save_schedule(raw_data)
        except (RuntimeError, ValueError) as error:
            print(f"课程表导入失败：{error}", file=sys.stderr)
            return 1
        print(f"课程表“{schedule['tableName']}”已导入。")
        return 0

    if args.command == "query":
        try:
            classes = query(args.day)
        except (FileNotFoundError, ValueError, KeyError) as error:
            print(error, file=sys.stderr)
            return 1
        print(json.dumps(classes, ensure_ascii=False, indent=2))
        return 0

    if CLASSES_FILE.exists():
        CLASSES_FILE.unlink()
        print("已删除课程表，可重新执行 fetch 导入。")
    else:
        print("当前没有已导入的课程表，可直接执行 fetch 导入。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
