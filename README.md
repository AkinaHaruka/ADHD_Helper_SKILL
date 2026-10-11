# ADHD Helper Skill

一个面向 ADHD 用户的对话辅助 Skill。它以低负担、非评判的方式，协助用户把当下的困难拆成能立刻开始的一个动作，并配套提供本地课程表与日程管理工具。

## 能做什么

- **降低启动阻力**：在卡住、注意力飘走、焦虑或低能量时，优先给出一个具体、可见、通常可在 30 秒内开始的动作。
- **任务与注意力支持**：将大任务拆成下一步物理动作；记录突发想法到“收集箱”，减少被打断时的切换成本。
- **日常节奏支持**：协助处理起床、睡前、出门和活动过渡；在时间紧张时提供“最低完成版”。
- **日程管理**：在本地新增、查询、修改和删除按日保存的日程。
- **WakeUp 课程表**：通过 WakeUp 分享码导入课程表，并按日期查询当天课程。
- **用户记忆**：在用户明确提供或同意后，将长期有用的偏好、物品清单和固定安排写入 `USER.md`。

对话行为规范与全部工具约定见 [SKILL.md](SKILL.md)；初始用户记忆模板见 [USER.md](USER.md)。

## 环境要求

- Git（需要支持 submodule）
- Python **3.9 或更高版本**；项目当前 PyCharm 配置为 Python 3.13
- 可访问 GitHub（初始化子模块与导入课程表所需依赖均需要网络）

> Windows 上建议始终用 `py -3` 或虚拟环境内的 `python` 运行命令，不要依赖可能指向其他版本的 `python3`。在 macOS/Linux 中，可将下文的 `py -3` 替换为 `python3`。

## 部署

以下命令在仓库根目录执行。

### 1. 克隆并初始化 Git 子模块

首次克隆时，推荐直接递归克隆：

```powershell
git clone --recurse-submodules <仓库地址>
cd ADHDHelper.SKILL
```

如果仓库已经克隆但 `scripts/depends/wakeup_decoder` 为空，或从普通克隆切换而来，执行：

```powershell
git submodule update --init --recursive
```

子模块 [airline233/WakeUpDecoder](https://github.com/airline233/WakeUpDecoder) 是 WakeUp 分享课程表解析器。没有它，`classes.py fetch` 无法导入课程表。

### 2. 创建并配置 Python 解释器

推荐为项目创建独立虚拟环境：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install --upgrade pip
```

如果 PowerShell 因执行策略拒绝激活脚本，可以不激活，直接使用解释器的绝对相对路径：

```powershell
.\.venv\Scripts\python.exe --version
```

在 **PyCharm** 中配置：

1. 打开 **File → Settings → Project → Python Interpreter**。
2. 点击解释器下拉框旁的 **Add Interpreter**，选择 **Add Local Interpreter**。
3. 选择 **Existing**，并指定项目中的 `.venv\Scripts\python.exe`；若尚未创建虚拟环境，也可选择 **Virtualenv** 让 PyCharm 新建 `.venv`。
4. 保存后，在 PyCharm Terminal 中运行 `python --version`，确认它指向 `.venv`。

### 3. 安装 Python 依赖

项目的主依赖清单文件名为 `scripts/requirments.txt`（保留了仓库中的拼写），子模块另有自己的依赖清单。激活虚拟环境后运行：

```powershell
python -m pip install -r scripts/requirments.txt
python -m pip install -r scripts/depends/wakeup_decoder/requirements.txt
```

也可以不激活虚拟环境：

```powershell
.\.venv\Scripts\python.exe -m pip install -r scripts/requirments.txt
.\.venv\Scripts\python.exe -m pip install -r scripts/depends/wakeup_decoder/requirements.txt
```

当前依赖包括 `requests` 与 `cryptography`；两份清单均应安装，以保证主脚本及课程表解析器可运行。

### 4. 验证安装

```powershell
python scripts/tasks.py query 2026-10-11
python scripts/classes.py query 2026-10-11
```

第一条在没有日程时输出空数组。第二条若尚未导入课程表会提示先执行 `fetch`，这是正常现象。

## 使用方式

### 导入与查询 WakeUp 课程表

在 WakeUp 中获取课程表分享码后：

```powershell
python scripts/classes.py fetch <分享码>
python scripts/classes.py query 2026-10-11
```

重新开始时可清除本地已导入课程表：

```powershell
python scripts/classes.py reset
```

### 管理本地日程

```powershell
# 查询指定日期
python scripts/tasks.py query 2026-10-11

# 新建：名称、地点、秒级 Unix 时间戳、持续分钟数、优先级
python scripts/tasks.py add "复习" "图书馆" 1791712800 60 high

# 修改：只提供需要修改的字段
python scripts/tasks.py update <日程ID> --location "宿舍" --during 90

# 删除
python scripts/tasks.py delete <日程ID>
```

`query` 的日期格式固定为 `YYYY-MM-DD`。创建日程时会输出日程 ID；更新和删除需要使用该 ID。日程工具在每次运行时会清理“今天起三天前（含）”的历史日程文件，请勿将它作为长期归档。

### 在对话系统中作为 Skill 使用

将本项目作为 Skill 提供给对话代理后，代理会遵循 `SKILL.md`：以短句、非评判语言推进单个下一步，并在获得必要信息和用户确认后调用上述脚本。`USER.md` 只应记录用户主动提供或明确同意保存的信息。

## 项目结构与数据位置

```text
ADHDHelper.SKILL/
├── SKILL.md                         # 对话策略、边界与工具调用约定
├── USER.md                          # 用户记忆模板（可由 Skill 在获同意后更新）
├── scripts/
│   ├── classes.py                   # WakeUp 课程表导入、查询、重置
│   ├── tasks.py                     # 本地日程增删改查
│   ├── requirments.txt              # 主项目 Python 依赖（文件名为仓库既有拼写）
│   ├── data/                        # 运行时个人数据，不纳入 Git
│   │   ├── classes/classes.json     # 已导入并清洗后的课程表
│   │   └── tasks/YYYYMMDD.json      # 按日期保存的日程
│   └── depends/
│       └── wakeup_decoder/          # Git submodule：WakeUpDecoder
│           └── requirements.txt     # 子模块 Python 依赖
└── .gitmodules                      # 子模块来源配置
```

`scripts/data/` 已在 `.gitignore` 中忽略，避免将个人课程表和日程提交到版本库。`USER.md` 目前不在 Git 忽略规则中；若其中将记录真实个人信息，建议在提交前自行检查，或按团队的隐私策略将其加入忽略规则。

## 致谢

- 感谢 [airline233/WakeUpDecoder](https://github.com/airline233/WakeUpDecoder)（本项目的 Git submodule），提供 WakeUp 课程表分享数据的解析能力。
- 感谢 **Codex** 与 **Google Gemini** 在项目开发过程中的协作支持。
