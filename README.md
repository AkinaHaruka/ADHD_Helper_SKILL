# ADHD Helper Skill


这是一个陪你处理“现在不知道从哪开始”的 ADHD 支持工具。
你可以直接告诉它“我卡住了”“注意力乱飞了”“我要出门但找不到东西”，它会先陪你把眼前的事缩小成一个能立刻开始的小动作；也能帮你记下突然冒出的想法、查看课程和日程、整理出门要带的东西。
它不评价你，也不会要求你一次把整天规划好。

---

面向 Agent 的 ADHD 支持 Skill。将 [SKILL.md](SKILL.md) 提供给 Agent 后，Agent 会以低负担、非评判、一次只推进一步的方式，帮助 ADHD 用户应对任务启动、注意力中断、日程、物品和日常过渡；可选接入本仓库的 WakeUp MCP 服务器管理课程表，日程与记忆由 Agent 宿主工具管理。

用户主要通过与 Agent 对话来使用本 Skill；课程表操作通过 MCP 协议调用，不再使用 `classes.py fetch/query/reset` 命令。

## Agent 能提供的支持

- **处理当下卡点**：用户说“卡住”“乱飞”“不知道做什么”时，先减轻阻力，给出一个可见、具体、通常能在 30 秒内开始的动作，而非要求解释背景或制定完整计划。
- **启动与专注**：把抽象目标拆成下一步物理动作；在被打断后从上一处继续；按用户状态提供有限时段、环境调整或“最低完成版”。
- **收集突发想法**：将突然想到的待办、点子或担心先简短记录，默认不打断当前任务，之后再少量清理。
- **日常过渡**：在起床、睡前、出门、迟到或活动切换时，优先提示下一站、必要物品与眼下第一步，并考虑准备、通勤和缓冲时间。
- **日程与课程表**：通过宿主工具查询和管理日程；存在 WakeUp MCP 工具时，支持通过分享码导入课程表并按日期查询，否则从宿主日程工具查询课程。
- **物品与用户记忆**：只在用户主动提供或明确同意后，通过 Agent 宿主提供的记忆工具保存长期有用的偏好、固定安排及物品清单。

完整对话策略、边界与工具调用约定以 [SKILL.md](SKILL.md) 为准。

## Agent 行为边界

本 Skill 要求 Agent：

- 使用短句、具体动词和非评判表达；不把遗忘、拖延或未完成归因于懒惰或意志力。
- 每次优先推进一个动作；需要选择时最多提供两三个低负担选项，允许用户跳过、改变主意或沉默。
- 不擅自填满用户时间、不替用户做重大决定，也不把休息视为失败。
- 创建或修改日程前确认时间、时长、地点/线上方式与冲突；删除日程或重置课程表前确认目标与意图。
- 工具失败时如实说明；不得假装操作已完成。
- 仅通过宿主记忆工具保存用户主动提供或明确同意保存的信息；用户更正或要求遗忘时，更新或删除相关记忆，不把猜测写成事实。
- 宿主未提供记忆工具或调用失败时，如实说明无法持久化，仅使用当前对话中已知的信息，不声称已保存，也不在 Skill 包内另建用户记忆文件。

## 给 Agent 宿主的部署说明

### 1. 获取 Skill 及子模块

WakeUp MCP 为可选组件，不接入时直接加载 [SKILL.md](SKILL.md)，课程查询使用宿主日程工具。需要接入时，课程表导入依赖 Git submodule [airline233/WakeUpDecoder](https://github.com/airline233/WakeUpDecoder)。克隆时应递归初始化：

```powershell
git clone --recurse-submodules <仓库地址>
cd ADHDHelper.SKILL
```

对于已经普通克隆的工作副本，执行：

```powershell
git submodule update --init --recursive
```

若未初始化子模块，MCP 仍可启动、查询已有课程表及重置，但无法导入新课程表。

### 2. 配置 Agent 使用的 Python 解释器

MCP 服务器需要 Python **3.10 或更高版本**。推荐创建独立虚拟环境，让宿主以该解释器启动服务器：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

Windows 下使用 `.venv\Scripts\python.exe`，macOS/Linux 使用 `.venv/bin/python`。宿主配置中的解释器及服务器入口均应使用绝对路径，不依赖宿主的工作目录。

若使用 PyCharm 维护或调试本 Skill：打开 **File → Settings → Project → Python Interpreter**，通过 **Add Interpreter → Add Local Interpreter → Existing** 选择 `.venv\Scripts\python.exe`。也可选择 **Virtualenv** 由 PyCharm 新建 `.venv`。

### 3. 安装依赖

安装服务器与子模块声明的依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r mcp/depends/wakeup_decoder/requirements.txt
```

子模块已自带 WakeUp APK，无需自行准备或配置。MCP 服务器将解码工作委托给子模块现有入口，以子模块目录为工作目录，让其自行发现 APK 并完成解码。

### 4. 配置 MCP 服务器并加载 Skill

将 [SKILL.md](SKILL.md) 作为 Agent 的 Skill 指令加载。在支持 stdio MCP 的宿主中添加服务器，例如：

```json
{
  "mcpServers": {
    "wakeup": {
      "command": "E:/PyCharm/ADHDHelper.SKILL/.venv/Scripts/python.exe",
      "args": ["E:/PyCharm/ADHDHelper.SKILL/mcp/wakeup_mcp.py"]
    }
  }
}
```

将示例路径替换为实际路径；具体配置位置和格式以宿主为准。宿主只在启动时运行 Python 服务器，之后所有课程操作均通过 MCP 的 `tools/list` 和 `tools/call` 完成。服务器使用 [官方 MCP Python SDK 的 FastMCP](https://py.sdk.modelcontextprotocol.io/v1/)，依赖限制为 `mcp>=1.28,<2`。

| 工具 | 参数 | 返回结果 |
| --- | --- | --- |
| `wakeup_fetch` | `share_id: string` | 导入并覆盖课程表，返回 `tableName` 和 `courseCount` |
| `wakeup_query` | `day: string`，`YYYY-MM-DD` | 课程列表，包含节次、时间、地点等；`[]` 表示无课 |
| `wakeup_reset` | 无 | 删除课程表，返回 `deleted`；重复调用返回 `false` |

SDK 为课程列表提供结构化结果 `{"result": [...]}`，其中 `result: []` 表示当天无课。未导入、日期错误、导入失败等通过 MCP 的 `isError` 返回，不作为空课表处理；失败的导入不会替换已有课表。重置前遵守 Skill 中的确认约定。

可选环境变量：

| 变量 | 用途与默认值 |
| --- | --- |
| `WAKEUP_DATA_DIR` | 课表存储目录；默认 `mcp/data/classes/`，沿用原课表；多用户部署需为每个用户设置不同的绝对路径 |

Skill 根据实际可用工具选择课程来源：有 `wakeup_query` 时查询 WakeUp，否则从宿主日程工具查询；不回退到 CLI。日程的查询、创建、修改、删除始终通过宿主工具进行。

用户记忆与物品清单由宿主提供的记忆工具管理。宿主应向 Agent 暴露相应工具及其接口、权限约定；本 Skill 不绑定特定工具名称。未提供记忆工具时，Agent 仍可使用当前对话中的信息提供支持，但无法持久化用户记忆。

## 持久化数据与隐私

用户记忆和日程由 Agent 宿主的工具持久化，存储位置、访问权限及保留策略由宿主管理，不写入 Skill 包。课程表由 MCP 服务器存储：

| 路径 | 内容 | 写入时机 |
| --- | --- | --- |
| `mcp/data/classes/classes.json`（或 `WAKEUP_DATA_DIR/classes.json`） | 导入后清洗的 WakeUp 课程表 | `wakeup_fetch` |

## 项目结构

```text
ADHDHelper.SKILL/
├── SKILL.md                         # Agent 的核心行为、边界与工具约定
├── requirements.txt                # MCP 服务器与解码器依赖
├── mcp/
│   ├── wakeup_mcp.py                # stdio MCP 服务器入口，暴露三个 wakeup_* 工具
│   ├── classes.py                   # 课程表业务逻辑，解码委托给子模块现有入口
│   ├── data/                        # 运行时个人数据，已忽略
│   └── depends/wakeup_decoder/      # Git submodule：WakeUpDecoder
├── tests/test_wakeup_mcp.py         # 导入逻辑与 stdio MCP 集成测试
└── .gitmodules                      # 子模块来源配置
```

使用配置好的解释器运行验证：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

测试使用临时目录及模拟上游数据，不读取或修改已有课表，不连接真实 WakeUp 服务。

## 致谢

- 感谢 [airline233/WakeUpDecoder](https://github.com/airline233/WakeUpDecoder)（本项目的 Git submodule），提供 WakeUp 课程表分享数据的解析能力。
- 感谢 [ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd)，本技能的输出方式借鉴并融入了其行动优先、分步呈现、跨轮状态、具体估时与可见进度等原则。
- 感谢 **Codex** 与 **Google Gemini** 在项目开发过程中的协作支持。
