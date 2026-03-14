# Water Meal Agent

一个基于 Python + PySide6 的 macOS 菜单栏常驻提醒应用。

当前功能：

- 每隔 45 分钟提醒喝水
- 12:00 提醒午饭
- 18:30 提醒晚饭
- 主状态面板，展示今日进度、下一次提醒和快捷操作
- 最近 14 天历史记录
- macOS 原生通知
- 登录时自动启动
- 自定义菜单栏图标和应用图标
- 防连发提醒（用户未操作时有冷却窗口）
- 睡眠/唤醒后自动恢复调度
- 错误日志自动落盘
- 桌面宠物（可拖拽、提醒气泡、点击打开聊天）
- 情绪对话（本地规则版，不触发设置或操作）
- 可选 LLM 情绪对话（开启后失败会直接显示错误，便于调试）
- 提醒后支持：
  - 我喝了 / 我吃了
  - 按设置里的分钟数稍后提醒
  - 今天跳过
- 菜单栏图标常驻
- 简单设置窗口
- 记录今日喝水次数、午饭/晚饭完成状态

## 项目结构

```text
.
├── README.md
├── requirements.txt
├── requirements-dev.txt
├── scripts
│   ├── build_macos_app.sh
│   ├── build_iconset.py
│   ├── install_launch_agent.sh
│   └── uninstall_launch_agent.sh
└── watermeal_agent
    ├── __init__.py
    ├── __main__.py
    ├── app.py
    ├── assets
    │   ├── app_icon.svg
    │   └── tray_icon.svg
    ├── icons.py
    ├── macos.py
    ├── companion.py
    ├── models.py
    ├── scheduler.py
    ├── storage.py
    └── ui
        ├── __init__.py
        ├── companion_chat.py
        ├── dashboard_window.py
        ├── desktop_pet.py
        ├── reminder_dialog.py
        └── settings_window.py
```

## 安装依赖

建议使用 Python 3.11+。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 启动

```bash
python -m watermeal_agent
```

程序启动后会直接打开主面板；关闭窗口后，应用仍会常驻后台。

## LLM 对话配置（可选）

在设置里勾选“启用 LLM 情绪对话”后，聊天将优先走 LLM。

推荐直接编辑项目根目录下的 `.env`（程序启动会自动读取）：

```bash
OPENAI_API_KEY=你的key
WATERMEAL_OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
WATERMEAL_LLM_MODEL=qwen-plus
```

需要环境变量：

```bash
export OPENAI_API_KEY="你的key"
```

可选变量：

```bash
export WATERMEAL_OPENAI_API_KEY="你的key"
export WATERMEAL_OPENAI_BASE_URL="https://api.openai.com/v1"
export WATERMEAL_LLM_MODEL="gpt-4o-mini"
```

说明：
- 当前调试模式下，LLM 失败不会回退本地规则回复，会直接在聊天窗口显示 `[LLM错误] ...`

首次运行后会在 `~/Library/Application Support/WaterMealAgent/` 下生成：

- `config.json`：用户配置
- `state.json`：运行状态、今日统计和历史记录
- `app.log`：运行日志和异常日志

## 开机自启

有两种方式：

- 在应用设置里勾选“登录时自动启动”
- 或者手动执行：

```bash
bash scripts/install_launch_agent.sh
```

取消开机自启：

```bash
bash scripts/uninstall_launch_agent.sh
```

## 打包成 .app

先安装开发依赖：

```bash
pip install -r requirements-dev.txt
```

然后执行：

```bash
bash scripts/build_macos_app.sh
```

产物在：

```text
dist/Water Meal Agent.app
```

打包脚本会先把 [app_icon.svg](/Users/zhanghan/workspace/watermeal-agent/watermeal_agent/assets/app_icon.svg) 转成 `.icns`，再用于 `.app` 图标。

## 说明

- 应用会常驻在 macOS 菜单栏。
- 点击菜单栏图标会打开主状态面板。
- 原生通知通过 `osascript` 调用 macOS 通知中心；如果没有通知，请检查“系统设置 -> 通知”权限。
- 开机自启通过 `~/Library/LaunchAgents/com.zhanghan.watermealagent.plist` 实现。
