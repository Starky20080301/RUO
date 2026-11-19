# -*- coding: utf-8 -*-
"""配置管理：config.json 读写、厂商预设、路径解析、内置人设。"""

import json
import os
import sys

import persona

# APP_DIR：可写目录（开发时是源码目录，打包后是 exe 所在目录），config.json 放这里。
# RESOURCE_DIR：只读资源目录（打包后资源被解到临时目录），assets / vendor 在这里。
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
    RESOURCE_DIR = getattr(sys, "_MEIPASS", BASE_DIR)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    RESOURCE_DIR = BASE_DIR


def _pick_config_dir():
    """找一个真的能写的目录放 config.json。

    首选程序目录；如果放在只读位置（Program Files、被安全软件保护的目录），
    依次退到 %APPDATA%\RuoPet、%LOCALAPPDATA%\RuoPet、%TEMP%\RuoPet。
    """
    candidates = [BASE_DIR]
    for env in ("APPDATA", "LOCALAPPDATA", "TEMP"):
        base = os.environ.get(env)
        if base:
            candidates.append(os.path.join(base, "RuoPet"))
    for cand in candidates:
        try:
            os.makedirs(cand, exist_ok=True)
            probe = os.path.join(cand, ".write_test")
            with open(probe, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(probe)
            return cand
        except Exception:
            continue
    return BASE_DIR


CONFIG_DIR = _pick_config_dir()
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
PETS_ROOT = os.path.join(RESOURCE_DIR, "assets", "pets")

# 人设随程序发布，界面不可修改
SYSTEM_PROMPT = persona.SYSTEM_PROMPT

# 厂商预设。protocol 为 "openai"（OpenAI 兼容协议，覆盖 DeepSeek/Kimi/GLM/通义/豆包等）
# 或 "anthropic"（Anthropic 原生协议）
PRESETS = {
    "DeepSeek": {
        "protocol": "openai",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    },
    "Kimi (Moonshot)": {
        "protocol": "openai",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
    },
    "智谱GLM": {
        "protocol": "openai",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
    },
    "通义千问": {
        "protocol": "openai",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
    },
    "豆包(火山方舟)": {
        "protocol": "openai",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "doubao-1-5-lite-32k-250115",
    },
    "OpenAI": {
        "protocol": "openai",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "Claude (Anthropic)": {
        "protocol": "anthropic",
        "base_url": "https://api.anthropic.com",
        "model": "claude-haiku-4-5",
    },
}

DEFAULT_SYSTEM_PROMPT = """你是「糯米」，住在用户电脑桌面上的可爱桌宠。

# 性格
温柔元气、乐观粘人，有点小吃货。喜欢陪着用户工作，会自然地关心用户的作息和心情。

# 说话规则
- 默认回复要简短（1~3 句），因为你的话会显示在头顶的小气泡里。
- 每条回复最多用 1~2 个颜文字或 emoji。
- 用户问严肃或专业的问题时，切换成可靠助手模式，条理清晰地回答。
- 用户明确要求展开时，可以写长一些。

# 边界
- 你没有视觉能力，也不能操作用户的电脑，不要假装能做到。
- 不清楚的事情就诚实说不知道。"""


def _default_config():
    profiles = {name: dict(preset, api_key="") for name, preset in PRESETS.items()}
    # 内置档案：让收到安装包的人不用填 Key 也能直接聊
    profiles.setdefault(persona.BUILTIN_PROFILE_NAME, {}).update(persona.BUILTIN_PROFILE)
    return {
        "active_profile": persona.BUILTIN_PROFILE_NAME,
        # 每个档案：protocol / base_url / api_key / model
        "profiles": profiles,
        "pet": {
            "name": "若",
            "assets_dir": "assets/pets/neko",
            "height": 300,          # 桌宠显示的像素高度（最长边），可在设置/右键/Ctrl+滚轮调整
            "animate": True,        # 关掉后完全静止，最省电
            "frame_ms": 150,
            "bubble_duration_s": 15,
            "position": None,  # [x, y]，退出时自动记住
        },
        "chat": {
            "max_history": 20,     # 记住的最近消息条数（user+assistant）
            "temperature": 0.8,
            "max_tokens": 1024,
        },
    }


def _deep_merge(base, override):
    """深合并：dict 递归合并，其余类型以 override 为准（保证旧配置补齐新增字段）。"""
    merged = dict(base)
    for key, value in (override or {}).items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _merge_profiles(user_profiles):
    """以用户档案为准：保留用户已建的档案，也允许删掉内置预设。

    同名的内置预设只用来补齐缺失字段（例如升级后新增的字段）。
    """
    merged = {}
    for name, profile in (user_profiles or {}).items():
        if not isinstance(profile, dict):
            continue
        base = dict(PRESETS.get(name, {}))
        base.update(profile)
        merged[name] = {
            "protocol": base.get("protocol", "openai"),
            "base_url": base.get("base_url", ""),
            "api_key": base.get("api_key", ""),
            "model": base.get("model", ""),
        }
    return merged


def load_config():
    """读取 config.json 并与默认配置合并；文件不存在或损坏时使用默认值。

    注意：system_prompt 一律以 persona.py 里的内置人设为准，
    config.json 里的同名字段会被忽略（人设锁定）。
    """
    cfg = _default_config()
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[Config] config.json 读取失败，使用默认配置: {exc}")
            return cfg
        if isinstance(user_cfg, dict):
            user_cfg = dict(user_cfg)
            user_cfg.pop("system_prompt", None)  # 人设锁定：忽略外部文件里的提示词
            profiles = user_cfg.pop("profiles", None)
            cfg = _deep_merge(cfg, user_cfg)
            merged = _merge_profiles(profiles)
            if merged:
                cfg["profiles"] = merged
    cfg["system_prompt"] = SYSTEM_PROMPT
    return cfg


def save_config(cfg):
    """原子写入，避免写一半损坏配置（不写入被锁定的人设）。"""
    data = {k: v for k, v in cfg.items() if k != "system_prompt"}
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG_PATH)


def active_profile(cfg):
    """返回 (档案名, 档案配置)；名称无效时自动回退到第一个。"""
    profiles = cfg.get("profiles") or {}
    name = cfg.get("active_profile")
    if name not in profiles:
        name = next(iter(profiles), None)
    return name, (profiles.get(name) if name else None)


def resolve_path(path):
    """资源路径：绝对路径原样；相对路径先找程序目录，再找打包资源目录。"""
    if not path:
        return ""
    if os.path.isabs(path):
        return os.path.normpath(path)
    candidates = [os.path.normpath(os.path.join(BASE_DIR, path))]
    if RESOURCE_DIR != BASE_DIR:
        candidates.append(os.path.normpath(os.path.join(RESOURCE_DIR, path)))
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[0]


MAX_TEXT_BYTES = 400_000  # 单次导入上限，避免把几十 MB 的文件塞进提示词


def read_text_file(path, limit=MAX_TEXT_BYTES):
    """读取拖入/选中的文本文件，返回 (文本, 是否被截断)。

    自动尝试 UTF-8 / GBK，二进制文件抛 ValueError。
    """
    with open(path, "rb") as f:
        raw = f.read(limit + 1)
    truncated = len(raw) > limit
    raw = raw[:limit]
    if b"\x00" in raw[:4096]:
        raise ValueError("看起来是二进制文件，不是文本")
    text = raw.decode("utf-8", errors="replace")
    if text.count("\ufffd") > max(3, len(text) // 100):
        try:
            text = raw.decode("gbk")
        except UnicodeDecodeError:
            pass
    return text, truncated
