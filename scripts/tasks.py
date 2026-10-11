"""按天保存个人日程的命令行工具。"""

import argparse
import json
import sys
import time as time_module
from datetime import date, datetime, timedelta
from json import JSONDecodeError
from pathlib import Path
from typing import Optional


TASKS_DIR = Path(__file__).resolve().parent / "data" / "tasks"


def _parse_time(value: str) -> str:
    """验证并规范化日程时间。"""
    if not isinstance(value, str):
        raise ValueError("日程时间必须使用 YYYY-MM-DD-HH-MM 格式。")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d-%H-%M")
    except ValueError as error:
        raise ValueError("日程时间必须使用 YYYY-MM-DD-HH-MM 格式。") from error
    if parsed.strftime("%Y-%m-%d-%H-%M") != value:
        raise ValueError("日程时间必须使用 YYYY-MM-DD-HH-MM 格式。")
    return value


def _day_for_time(value: str) -> str:
    return _parse_time(value)[:10].replace("-", "")


def _path_for_day(day: str) -> Path:
    return TASKS_DIR / f"{day}.json"


def _parse_day(value: str) -> str:
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y%m%d")
    except ValueError as error:
        raise ValueError("日期必须使用 YYYY-MM-DD 格式。") from error


def _load_day(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as file:
            tasks = json.load(file)
    except (JSONDecodeError, OSError) as error:
        raise ValueError(f"日程文件无法读取：{path.name}") from error
    if not isinstance(tasks, list) or not all(isinstance(task, dict) for task in tasks):
        raise ValueError(f"日程文件格式不正确：{path.name}")
    return tasks


def _save_day(path: Path, tasks: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(tasks, file, ensure_ascii=False, indent=2)
        file.write("\n")


def _iter_task_files():
    if not TASKS_DIR.exists():
        return []
    return sorted(path for path in TASKS_DIR.glob("????????.json") if path.stem.isdigit())


def _find_task(task_id: int) -> tuple[Path, list[dict], int]:
    for path in _iter_task_files():
        tasks = _load_day(path)
        for index, task in enumerate(tasks):
            if task.get("id") == task_id:
                return path, tasks, index
    raise KeyError(f"未找到 ID 为 {task_id} 的日程。")


def _new_id() -> int:
    used_ids = {task.get("id") for path in _iter_task_files() for task in _load_day(path)}
    task_id = time_module.time_ns() // 1_000_000
    while task_id in used_ids:
        task_id += 1
    return task_id


def _garbage_collect() -> None:
    """删除今天起三天前（含）的日程文件。"""
    cutoff = date.today() - timedelta(days=3)
    for path in _iter_task_files():
        try:
            file_day = datetime.strptime(path.stem, "%Y%m%d").date()
        except ValueError:
            continue
        if file_day <= cutoff:
            path.unlink()


def add(name: str, location: str, time: str, during: int, priority: str) -> int:
    """创建日程并返回新日程 ID。"""
    time = _parse_time(time)
    day_path = _path_for_day(_day_for_time(time))
    tasks = _load_day(day_path)
    task_id = _new_id()
    tasks.append({"id": task_id, "name": name, "location": location,
                  "time": time, "during": during, "priority": priority})
    _save_day(day_path, tasks)
    return task_id


def delete(id: int) -> None:
    """删除指定 ID 的日程。"""
    path, tasks, index = _find_task(id)
    tasks.pop(index)
    _save_day(path, tasks)


def query(day: str) -> list[dict]:
    """查询指定日期的全部日程。"""
    return _load_day(_path_for_day(_parse_day(day)))


def update(id: int, name: Optional[str] = None, location: Optional[str] = None,
           time: Optional[str] = None, during: Optional[int] = None,
           priority: Optional[str] = None) -> None:
    """修改指定 ID 的日程；修改时间时自动移动到对应日期文件。"""
    path, tasks, index = _find_task(id)
    task = tasks[index]
    if time is not None:
        time = _parse_time(time)
    changes = {"name": name, "location": location, "time": time,
               "during": during, "priority": priority}
    task.update({key: value for key, value in changes.items() if value is not None})

    if time is not None:
        destination = _path_for_day(_day_for_time(time))
        if destination != path:
            tasks.pop(index)
            _save_day(path, tasks)
            destination_tasks = _load_day(destination)
            destination_tasks.append(task)
            _save_day(destination, destination_tasks)
            return
    _save_day(path, tasks)


def main() -> int:
    """执行日程 CLI，并在每次执行时清理过期文件。"""
    _garbage_collect()
    parser = argparse.ArgumentParser(description="日程管理工具")
    commands = parser.add_subparsers(dest="command", required=True)

    add_parser = commands.add_parser("add", help="创建日程")
    add_parser.add_argument("name")
    add_parser.add_argument("location")
    add_parser.add_argument("time", help="开始时间，格式 YYYY-MM-DD-HH-MM")
    add_parser.add_argument("during", type=int, help="持续分钟数")
    add_parser.add_argument("priority")

    delete_parser = commands.add_parser("delete", help="删除日程")
    delete_parser.add_argument("id", type=int)

    query_parser = commands.add_parser("query", help="查询某天的日程")
    query_parser.add_argument("day", help="日期，格式 YYYY-MM-DD")

    update_parser = commands.add_parser("update", help="修改日程")
    update_parser.add_argument("id", type=int)
    update_parser.add_argument("--name")
    update_parser.add_argument("--location")
    update_parser.add_argument("--time", help="开始时间，格式 YYYY-MM-DD-HH-MM")
    update_parser.add_argument("--during", type=int)
    update_parser.add_argument("--priority")
    args = parser.parse_args()

    try:
        if args.command == "add":
            print(add(args.name, args.location, args.time, args.during, args.priority))
        elif args.command == "delete":
            delete(args.id)
        elif args.command == "query":
            print(json.dumps(query(args.day), ensure_ascii=False, indent=2))
        else:
            update(args.id, args.name, args.location, args.time, args.during, args.priority)
    except (KeyError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
