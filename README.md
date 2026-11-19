# 🐾 桌宠 Agent

一只住在 Windows 桌面上的 AI 桌宠：透明置顶、可拖拽、会呼吸，随时和你聊天。

**核心特点：厂商随你换，形象随你换，人设随你改。** 内置 DeepSeek / Kimi / 智谱 GLM / 通义千问 / 豆包 / OpenAI / Claude 七套预设，
也可以填任意 OpenAI 兼容或 Anthropic 协议的服务地址，用自己的 API Key 对话。

![桌宠预览](docs/preview.png)

![呼吸动画](docs/preview.gif)

## 分发给别人（Windows 安装包）

`安装包/` 下有两个约 26 MB 的完整安装包（免装 Python），可以直接通过微信/QQ 发出去：

| 文件 | 说明 |
| --- | --- |
| `若桌宠安装包.exe` | 已内置你的 Key，对方装完就能直接聊 |
| `若桌宠安装包-免Key版.exe` | 不带 Key，对方第一次启动后在「设置」里填自己的 Key |

安装流程：

1. 双击安装包 → 自动挑一个可写位置（`%LOCALAPPDATA%\RuoPet` → `%APPDATA%\RuoPet` → `%USERPROFILE%\RuoPet`），
   三处都被安全软件拦住时会弹窗让用户自己选目录
2. 创建桌面 / 开始菜单的「若」图标，并立即启动桌宠
3. 卸载：开始菜单 → 桌宠若 → 卸载

安装包里内置：Python 运行时、Pillow/requests、拖放库、桌宠素材、**你写死的人设**（含 Key 版还内置了模型 Key）。
安装失败时安装包旁边会生成「安装日志.txt」，记录每个候选路径和失败原因，方便排查。

> ⚠️ **含 Key 版的风险**：Key 会随安装包分发，拿到的人可以反编译取出并消耗你的额度。
> 请使用限额/可随时吊销的 Key；对外分发建议用**免 Key 版**。

## 人设锁定

角色设定已经从 `config.json` 移到 `persona.py`，并在启动时强制覆盖：

- 设置窗口里**不再有提示词编辑框**，只显示「🔒 人设由程序内置」
- `config.json` 里的 `system_prompt` 会被忽略，程序也不会再把它写回配置
- 人设原文保存在 **`persona.txt`**（方便你直接编辑）
- 改人设：编辑 `persona.txt` → 运行 `python packaging/make_persona.py` → 重新打包

## 功能

- **多厂商 API**：预设 7 家；可新建任意档案，自定义协议、API 地址、模型、Key，随时切换
- **流式对话**：回复逐字显示在聊天窗口，同时把摘要显示在宠物头顶的气泡里
- **可拖入文件**：把 txt / md / json 等文本直接拖进聊天输入框，
  适合角色扮演的长设定、长开场白（单文件上限 40 万字符，超过会提示截断）
- **自定义桌宠**：序列帧文件夹 / 动态 GIF / 单张静态图（自动呼吸起伏），右键随时换形象
- **自由缩放**：设置里按像素调大小，或右键「调整大小」，或在桌面上 `Ctrl + 滚轮` 直接缩放
- **顺手的小细节**：位置自动记忆、透明背景点击穿透、气泡自动消失、高分屏 DPI 适配
- **单实例保护**：重复双击只会提示「已经在运行」，不会开出好几只桌宠拖慢电脑
- **纯本地**：只有一个 `config.json` 存配置，不经过任何中间服务器

## 快速开始（开发/自己用）

环境要求：Windows 10/11 + Python 3.9 及以上（tkinter 随官方安装包自带）。

1. 双击 **`start.bat`**（首次运行会自动安装 `Pillow`、`requests`）
2. 宠物出现在屏幕右下角。**右键宠物 → 设置**
3. 选一个厂商（或新建档案），填上 API Key，点「保存」
4. **双击宠物** 打开聊天窗口，输入内容回车发送

也可以手动启动：

```bat
pip install -r requirements.txt
python main.py
```

> 拖放库 `tkinterdnd2` 已经放进 `vendor/`，不需要额外安装；万一目录被删，程序会自动降级，
> 设置里仍然可以用「📄 从文件导入…」按钮导入提示词。

## 配置 AI 厂商

设置窗口里点厂商按钮即可套用预设，内置：

| 厂商 | 协议 | API 地址 | 默认模型 |
| --- | --- | --- | --- |
| DeepSeek | OpenAI 兼容 | `https://api.deepseek.com/v1` | `deepseek-chat` |
| Kimi (Moonshot) | OpenAI 兼容 | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| 智谱 GLM | OpenAI 兼容 | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` |
| 通义千问 | OpenAI 兼容 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |
| 豆包（火山方舟） | OpenAI 兼容 | `https://ark.cn-beijing.volces.com/api/v3` | `doubao-1-5-lite-32k-250115` |
| OpenAI | OpenAI 兼容 | `https://api.openai.com/v1` | `gpt-4o-mini` |
| Claude | Anthropic | `https://api.anthropic.com` | `claude-haiku-4-5` |

> 模型名会随厂商更新，以各家文档为准；填错时一般会收到 `HTTP 404` 或「模型不存在」。

**接入其他厂商**：设置里点「新建」建一个档案，然后填：

- 协议：对方提供 OpenAI 兼容接口就选「OpenAI 兼容」，Claude 官方接口选「Anthropic Claude」
- API 地址：OpenAI 兼容通常以 `/v1` 结尾（程序会自动拼 `/chat/completions`）
- 模型 / API Key：照抄厂商文档

DeepSeek、硅基流动、OpenRouter、Ollama（`http://localhost:11434/v1`）等都能用同样的方式接入。

## 自定义桌宠形象

右键宠物 → **更换形象**，可以直接选文件夹、选 GIF，或选一张静态图；设置里也能改「形象资源」路径。
支持三种形式：

1. **序列帧文件夹**：目录下的图片按文件名排序循环播放，推荐 `idle_00.png`、`idle_01.png`……
2. **单个动态 GIF**：自动拆帧，并使用 GIF 自带的每帧时长
3. **单张静态图**：自动生成上下轻微起伏的呼吸动画

建议用**透明底 PNG**，尺寸 200px 左右（程序会自动缩放并对齐），形状差别太大的图会显得跳。

### 用 AI 生成的宫格图做形象

如果你拿到的是「4×4 宫格」整图（常见于 AI 绘图），用自带工具一键切成透明底序列帧：

```bat
python tools/build_pet_frames.py --sheet assets/pets/_source/default_sheet.png --out assets/pets/default --cols 4 --rows 4 --size 200
```

它会自动完成：按网格切分 → 抠掉棋盘格/纯色假透明底 → 去掉零散噪点与浅色描边 → 底边对齐（减少抖动）→ 输出 `idle_00.png` 起头的序列帧。
背景不是标准棋盘格时，可用 `--min-bright`、`--warm` 两个参数微调判定。

内置的备用形象就是用它切出 16 帧，再整理成「轻微呼吸 + 眨眼」的循环；源图保留在 `assets/pets/_source/default_sheet.png`。
当前默认形象是 `assets/pets/neko/`（单张立绘，自动生成呼吸动画），原图备份在 `assets/pets/_source/neko.jpg`。

## 自定义人设（系统提示词）

设置窗口的「系统提示词」框就是模型的 system prompt，随便改：性格、说话风格、称呼、能做什么不能做什么。
默认人设是「糯米」——一只温柔元气的桌宠，默认要求 1~3 句短回复（因为回复会显示在头顶小气泡里）。

> 小技巧：想让它当正经助手，就在提示词里写「回答技术问题时可以详细展开，用列表说明」。

## 使用说明

| 操作 | 效果 |
| --- | --- |
| 左键拖动 | 移动宠物，退出时记住位置 |
| 双击宠物 | 打开 / 关闭聊天窗口 |
| `Ctrl + 滚轮` | 在桌面上直接放大 / 缩小宠物 |
| 右键宠物 | 对话、新的对话、更换形象、调整大小、动画开关、设置、帮助、退出 |
| 把 txt/md 拖进输入框 | 自动读成文字并插入，可直接发送 |
| `Enter` | 发送消息 |
| `Shift + Enter` | 输入框内换行 |
| 点击气泡 | 立即收起气泡 |

## 目录结构

```
desktop-pet-agent/
├─ main.py                 # 入口：应用装配、对话引擎、队列轮询、单实例保护
├─ persona.py              # 锁定的人设 + 内置厂商档案（打包时生成）
├─ persona.txt             # 人设原文（你编辑这个，再重新生成）
├─ config.py               # 配置读写、厂商预设、路径解析、文本文件读取
├─ api_client.py           # OpenAI 兼容 / Anthropic 两种协议的流式客户端
├─ pet_ui.py               # 透明置顶宠物窗口、缩放、动画、气泡
├─ chat_ui.py              # 聊天窗口（流式输出、输入框、拖放导入）
├─ settings_ui.py          # 设置窗口（厂商档案、形象、对话参数；人设只读）
├─ packaging/              # 打包工具链（生成 Windows 安装包）
│  ├─ build_windows.ps1    # 一键构建
│  ├─ make_persona.py      # config.json → persona.py（锁定人设）
│  ├─ make_package.py      # 组装精简 Python 运行时 + 程序
│  ├─ zip_app.py           # 打成 app.zip
│  ├─ Launcher.cs          # 「若.exe」启动器
│  ├─ Setup.cs             # 安装器（内嵌 app.zip）
│  ├─ Uninstall.cs         # 卸载器
│  └─ make_icon.py         # 立绘 → app.ico
├─ 安装包/
│  ├─ 若桌宠安装包.exe      # 分发给别人的安装包（26 MB）
│  └─ 使用说明.txt
├─ tools/
│  ├─ build_pet_frames.py  # 宫格图 → 透明底序列帧
│  └─ selftest.py          # 离线自测（协议解析、配置、素材、文本导入）
├─ vendor/tkinterdnd2/     # 内置的拖放库（免安装）
├─ assets/pets/
│  ├─ neko/                # 默认形象（单张立绘 → 自动呼吸动画）
│  ├─ default/             # 备用形象（16 帧 idle_00~15，带眨眼）
│  └─ _source/             # 原始素材备份
├─ docs/                   # README 用的预览图
├─ requirements.txt
└─ start.bat               # 双击启动（自动装依赖）
```

## config.json

首次运行会在程序目录生成 `config.json`，也可以直接手改（改完重启生效）：

```jsonc
{
  "active_profile": "DeepSeek",          // 当前使用的厂商档案
  "profiles": {
    "DeepSeek": {
      "protocol": "openai",              // openai | anthropic
      "base_url": "https://api.deepseek.com/v1",
      "api_key": "sk-...",
      "model": "deepseek-chat"
    }
  },
  "system_prompt": "（已移到 persona.py，这里写了也会被忽略）",
  "pet": {
    "name": "若",                       // 宠物名字（聊天标题、气泡）
    "assets_dir": "assets/pets/neko",   // 形象资源：目录 / GIF / 图片
    "height": 300,                      // 显示高度（像素，最长边）
    "animate": true,                    // 是否播放动画（关掉最省电）
    "frame_ms": 150,                    // 序列帧间隔（毫秒）
    "bubble_duration_s": 15,            // 气泡停留秒数
    "position": [1500, 800]             // 窗口位置，退出时自动写入
  },
  "chat": {
    "max_history": 20,                  // 记忆的消息条数
    "temperature": 0.8,
    "max_tokens": 1024
  }
}
```

`config.json` 已在 `.gitignore` 中，不会被误提交。

## 重新打包

改了人设或代码后，重新生成安装包：

```bat
python packaging\make_persona.py                 :: 把 persona.txt 里的人设写进 persona.py
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
```

产物：`安装包\若桌宠安装包.exe`。构建脚本会临时组装一份精简的 Python 运行时
（约 57 MB，压成安装包约 26 MB），所以目标机器不需要安装 Python。

## Android 版

`android/` 下是完整的安卓工程（**悬浮桌宠 + 原生接口调用**，Java，零第三方依赖）：

- 桌宠以悬浮窗形式浮在手机桌面上，可拖动、点一下打开聊天
- 聊天直连 OpenAI 兼容接口（DeepSeek 等），SSE 流式输出
- 人设同样锁定在 `Persona.java` 里（由 `persona.txt` 生成）
- 两个版本：免 Key（用户自己填）与含 Key（`-BuiltinKey sk-xxx`）

**打包环境已装好，全部在 D 盘**（JDK 17 + Android SDK 33 + Gradle 8.2.1，约 1.1 GB，
C 盘只多了一个 3.5 MB 的签名证书）。已经编译好的 APK：

- `安装包\安卓\若-免Key版.apk`（353 KB）
- `安装包\安卓\若-含Key版.apk`（386 KB）

重新构建：

```bat
cd /d E:\Tuanjie\desktop-pet-agent\android
powershell -ExecutionPolicy Bypass -File build_apk.ps1
powershell -ExecutionPolicy Bypass -File build_apk.ps1 -BuiltinKey sk-xxx   :: 含 Key 版
```

装到手机：`adb install -r 安装包\安卓\若-免Key版.apk`，或直接把 APK 发到手机点击安装。
详细步骤见 [`android/打包步骤.md`](android/打包步骤.md)。



## Agent 扩展指南

目前是「对话型桌宠」，代码为**函数调用（tool calling）**留好了位置，加工具只需三步：

1. **声明工具**：给档案加 `tools` 字段（JSON Schema 格式），随请求发送；
2. **解析调用**：在 `api_client.py` 的 `OpenAICompatClient.stream` 中把 `tools` 放进请求体，
   并在解析 `choices[0].delta.tool_calls` 时把片段拼成完整调用；
3. **执行并回灌**：在 `main.py` 的 `ChatEngine.send` 里检测到 tool_calls 时暂停输出 → 本地执行工具 →
   把 `{"role": "tool", "content": ...}` 追加进 `history` → 再次调用 `stream`，直到模型返回纯文本。

工具可以做的事完全本地化，例如：查时间、读写笔记、打开网页、控制音量、播报提醒。

## 常见问题

**填了 Key 还是不能聊？**
右键 → 设置，看聊天窗口顶部的状态栏是否显示「Key 未填写」；设置里保存后状态栏会变。

**报 `HTTP 401`**：Key 不对或未生效（有的厂商要实名/创建应用后才可用）。
**报 `HTTP 404`**：`base_url` 写错，OpenAI 兼容接口通常要求以 `/v1` 结尾，程序会自己拼 `/chat/completions`。
**报 `HTTP 429`**：限流或额度不足。
**提示网络/代理错误**：检查系统代理是否可用；公司网络可能需要给 `requests` 配代理。

**宠物周围有一圈白边？** 形象图是「假透明」底（棋盘格画进像素里），用 `tools/build_pet_frames.py` 重新抠一次即可。

**宠物显示成一个小方块/不显示？** 检查设置里的「形象资源」路径是否存在、图片是否损坏；加载失败会自动退回内置团子。

**换了屏幕/分辨率位置跑偏？** 位置会记录在 `config.json` 的 `position`，删掉该字段即可回到默认右下角。

**电脑变卡？** 先确认只有一只桌宠在跑（重复启动现在会被拦下并提示）。
仍然卡的话：右键 → 取消「播放动画」，或把「调整大小」调小、在设置里降低帧率；
动画关闭后程序几乎不占 CPU（实测单实例静态时 < 0.5%）。

**拖文件没反应？** 说明 `vendor/tkinterdnd2` 缺失或被安全软件拦了；
设置里的「📄 从文件导入…」按钮功能完全等价，不受影响。

## 性能说明

桌宠是一个「透明 + 置顶」的分层窗口，每帧只重绘自身那一小块（默认约 200×300 像素）。
在 2520×1680 @150% 的机器上实测：**动画开启时单实例约占 1~4% 单核、70~80MB 内存**；
关闭动画后接近 0%。真正的卡顿通常来自**同时开了多只桌宠**，所以程序加了单实例保护。

## 安全与隐私

- API Key 以明文存在本机 `config.json`（桌面宠物类工具常见做法），请勿把整个文件夹发给别人；
- 对话内容只发给你配置的厂商接口，不经过其他服务器；
- 拖入/导入的文件只在本机读取文本，不会上传（除非你把内容发给了模型）。

## 开发与自测

```bat
python tools/selftest.py     # 离线自测：协议解析、配置读写、素材加载、文本导入，最后输出 SELFTEST_OK
python main.py --smoke       # 启动 1.5 秒后自动退出，用于检查环境是否正常
```
