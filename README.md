# ADHD Helper Skill


这是一个陪你处理“现在不知道从哪开始”的 ADHD 支持工具。
你可以直接告诉它“我卡住了”“注意力乱飞了”“我要出门但找不到东西”，它会先陪你把眼前的事缩小成一个能立刻开始的小动作；也能帮你记下突然冒出的想法、查看课程和日程、整理出门要带的东西。
它不评价你，也不会要求你一次把整天规划好。

---

面向 Agent 的 ADHD 支持 Skill。将 [SKILL.md](SKILL.md) 提供给 Agent 后，Agent 会以低负担、非评判、一次只推进一步的方式，帮助 ADHD 用户应对任务启动、注意力中断、日程、物品和日常过渡；并可按需调用本仓库的本地脚本管理课程表与日程。

它不是一个面向终端用户的 CLI 产品：`scripts/` 是供 Agent 执行的工具实现，用户主要通过与 Agent 对话来使用本 Skill。

## Agent 能提供的支持

- **处理当下卡点**：用户说“卡住”“乱飞”“不知道做什么”时，先减轻阻力，给出一个可见、具体、通常能在 30 秒内开始的动作，而非要求解释背景或制定完整计划。
- **启动与专注**：把抽象目标拆成下一步物理动作；在被打断后从上一处继续；按用户状态提供有限时段、环境调整或“最低完成版”。
- **收集突发想法**：将突然想到的待办、点子或担心先简短记录，默认不打断当前任务，之后再少量清理。
- **日常过渡**：在起床、睡前、出门、迟到或活动切换时，优先提示下一站、必要物品与眼下第一步，并考虑准备、通勤和缓冲时间。
- **日程与课程表**：在信息充分且涉及创建、修改、删除时得到用户确认后，查询或管理本地日程；支持通过 WakeUp 分享码导入课程表并按日期查询。
- **物品与用户记忆**：只在用户主动提供或明确同意后，将长期有用的偏好、固定安排及物品清单写入 [USER.md](USER.md)。

完整对话策略、边界、命令参数与工具调用约定以 [SKILL.md](SKILL.md) 为准。

## Agent 行为边界

本 Skill 要求 Agent：

- 使用短句、具体动词和非评判表达；不把遗忘、拖延或未完成归因于懒惰或意志力。
- 每次优先推进一个动作；需要选择时最多提供两三个低负担选项，允许用户跳过、改变主意或沉默。
- 不擅自填满用户时间、不替用户做重大决定，也不把休息视为失败。
- 创建或修改日程前确认时间、时长、地点/线上方式与冲突；删除日程或重置课程表前确认目标与意图。
- 工具失败时如实说明；不得假装操作已完成。
- 仅保存用户主动提供或明确同意保存的信息，并在更新 `USER.md` 时标注最后修改时间。

## 给 Agent 宿主的部署说明

### 1. 获取 Skill 及子模块

此仓库的课程表导入能力依赖 Git submodule [airline233/WakeUpDecoder](https://github.com/airline233/WakeUpDecoder)。克隆时应递归初始化：

```powershell
git clone --recurse-submodules <仓库地址>
cd ADHDHelper.SKILL
```

对于已经普通克隆的工作副本，执行：

```powershell
git submodule update --init --recursive
```

若未初始化子模块，Agent 仍能进行纯对话支持及本地日程管理，但无法执行 WakeUp 课程表导入。

### 2. 配置 Agent 使用的 Python 解释器

运行 `scripts/` 的 Agent 宿主需要 Python **3.9 或更高版本**。推荐为本 Skill 创建独立虚拟环境，并让 Agent 的命令执行环境使用该解释器：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

Windows 下，应让 Agent 调用 `.\.venv\Scripts\python.exe`，或在已激活虚拟环境后调用 `python`；不要假定 `python3` 一定可用。macOS/Linux 可使用 `.venv/bin/python`。

若使用 PyCharm 维护或调试本 Skill：打开 **File → Settings → Project → Python Interpreter**，通过 **Add Interpreter → Add Local Interpreter → Existing** 选择 `.venv\Scripts\python.exe`。也可选择 **Virtualenv** 由 PyCharm 新建 `.venv`。

### 3. 安装 Agent 工具依赖

安装主脚本与子模块的依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r scripts/depends/wakeup_decoder/requirements.txt
```

### 4. 将 Skill 暴露给 Agent

将 [SKILL.md](SKILL.md) 作为 Agent 的 Skill 指令加载，并确保 Agent 的工作目录为仓库根目录、可调用上一步配置的 Python 解释器。Agent 应遵循 `SKILL.md` 中的命令格式：

```text
<python> ./scripts/classes.py fetch <WakeUp 分享码>
<python> ./scripts/classes.py query <YYYY-MM-DD>
<python> ./scripts/tasks.py query <YYYY-MM-DD>
<python> ./scripts/tasks.py add <名称> <地点> <Unix 秒级时间戳> <持续分钟数> <优先级>
```

其中 `<python>` 应替换为宿主实际配置的解释器路径。对会改变数据的命令，Agent 必须先遵守 `SKILL.md` 规定的确认流程。

## 持久化数据与隐私

Agent 的运行时数据存储在 `scripts/data/`：

| 路径 | 内容 | 写入时机 |
| --- | --- | --- |
| `USER.md` | 用户同意保存的偏好、固定安排、物品与支持方式 | Agent 获得明确同意后 |
| `scripts/data/classes/classes.json` | 导入后清洗的 WakeUp 课程表 | `classes.py fetch` |
| `scripts/data/tasks/YYYYMMDD.json` | 按日期保存的本地日程 | `tasks.py` 增改删 |

## 项目结构

```text
ADHDHelper.SKILL/
├── SKILL.md                         # Agent 的核心行为、边界与工具约定
├── USER.md                          # 用户记忆模板及持久化位置
├── scripts/
│   ├── classes.py                   # Agent 调用的 WakeUp 课程表工具
│   ├── tasks.py                     # Agent 调用的本地日程工具
│   ├── requirments.txt              # 主工具依赖（仓库既有拼写）
│   ├── data/                        # 运行时个人数据，已忽略
│   └── depends/wakeup_decoder/      # Git submodule：WakeUpDecoder
└── .gitmodules                      # 子模块来源配置
```

## 致谢

- 感谢 [airline233/WakeUpDecoder](https://github.com/airline233/WakeUpDecoder)（本项目的 Git submodule），提供 WakeUp 课程表分享数据的解析能力。
- 感谢 [ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd)，本技能的输出方式借鉴并融入了其行动优先、分步呈现、跨轮状态、具体估时与可见进度等原则。
- 感谢 **Codex** 与 **Google Gemini** 在项目开发过程中的协作支持。
