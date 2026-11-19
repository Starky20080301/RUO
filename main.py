# -*- coding: utf-8 -*-
"""桌宠 Agent —— 可配置多厂商 LLM 的桌面宠物。

- 厂商档案：OpenAI 兼容协议（DeepSeek/Kimi/GLM/通义/豆包/OpenAI 等）+ Anthropic 原生协议
- 桌宠自定义：序列帧文件夹 / 单个 GIF / 单张静态图（自动呼吸起伏）
- 系统提示词自定义，回复流式显示在聊天窗口，摘要气泡浮在宠物头顶
- Agent 扩展点：见 ChatEngine 与 README「Agent 扩展指南」
"""

import ctypes
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox

import config as cfg_mod
from api_client import LLMError, make_client
from chat_ui import ChatWindow
from pet_ui import Bubble, PetWindow
from settings_ui import PROTOCOL_LABELS, SettingsWindow


def _bubble_summary(text, limit=110):
    """把回复压缩成适合气泡展示的一小段。"""
    flat = " ".join((text or "").split())
    if len(flat) > limit:
        flat = flat[:limit].rstrip() + "……"
    return flat


class ChatEngine:
    """对话引擎（send 在后台线程执行）。

    ====== Agent 扩展点 ======
    将来要加函数调用，三步即可：
    1. 在 config.json 的档案里加 tools 描述（JSON Schema 格式）；
    2. 在 api_client 的 stream 中把 tools 传入请求体，并在 OpenAI 协议
       片段解析中处理 choices[0].delta.tool_calls；
    3. 在本类中检测到 tool_calls 时：暂停输出 → 本地执行工具 → 把
       {"role":"tool", ...} 追加进 history → 再次调用 stream 继续，
       直到模型返回纯文本回复。
    """

    def __init__(self, app):
        self.app = app
        self.history = []  # [{"role": "user"/"assistant", "content": str}]
        self._gen = 0  # 新对话时自增，使进行中的旧请求不再回写

    def reset(self):
        self._gen += 1
        self.history.clear()

    def send(self, text):
        gen = self._gen
        cfg = self.app.cfg
        self.history.append({"role": "user", "content": text})
        limit = max(2, int(cfg["chat"].get("max_history", 20)))
        while len(self.history) > limit:
            self.history.pop(0)
        _, profile = cfg_mod.active_profile(cfg)
        client = make_client(profile)
        parts = []
        try:
            for piece in client.stream(
                cfg.get("system_prompt", ""),
                self.history,
                float(cfg["chat"].get("temperature", 0.8)),
                int(cfg["chat"].get("max_tokens", 1024)),
            ):
                if gen != self._gen:
                    return  # 期间被「新的对话」重置
                parts.append(piece)
                self.app.ui_queue.put(("chunk", piece))
        except LLMError as exc:
            if gen == self._gen:
                self.app.ui_queue.put(("error", exc.message))
            return
        except Exception as exc:  # 未预料异常也友好提示
            if gen == self._gen:
                self.app.ui_queue.put(("error", f"发生意外错误: {exc}"))
            return
        if gen == self._gen:
            full = "".join(parts)
            self.history.append({"role": "assistant", "content": full})
            self.app.ui_queue.put(("done", full))


class PetApp:
    def __init__(self):
        self.first_run = not os.path.exists(cfg_mod.CONFIG_PATH)
        self.cfg = cfg_mod.load_config()
        os.makedirs(cfg_mod.PETS_ROOT, exist_ok=True)
        self.ui_queue = queue.Queue()
        self.busy = False
        self.settings_win = None

        self.engine = ChatEngine(self)
        self.pet = PetWindow(self)
        self.root = self.pet.root  # 主 Tk 根窗口，作为各弹窗的 master
        self.bubble = Bubble(self)
        self.chat = ChatWindow(self)

        self._apply_pet(initial=True)
        self.update_status()
        self.pet.root.after(60, self._poll_queue)

        if self.first_run:
            cfg_mod.save_config(self.cfg)  # 生成 config.json 便于手动编辑
            name = self.cfg["pet"]["name"]
            self.pet.root.after(700, lambda: self.bubble.show(
                f"你好呀，我是{name}！\n"
                "右键我 → 菜单 · 设置 · 换形象\n"
                "双击我 → 打开聊天窗口\n"
                "先在「设置」里填好 API Key 就能陪我聊天啦～"
            ))

    # ---------- 桌宠形象 ----------
    def _apply_pet(self, initial=False):
        pet_cfg = self.cfg["pet"]
        ok = self.pet.set_pet(
            pet_cfg.get("assets_dir", ""),
            pet_cfg.get("frame_ms", 150),
            pet_cfg.get("height", 300),
            pet_cfg.get("animate", True),
            pet_cfg.get("position") if initial else None,
        )
        if not ok:
            self.bubble.show(
                "⚠️ 桌宠图片加载失败，先用内置团子凑合～\n右键 → 更换形象 / 设置 重新配置。",
                duration_s=-1,
            )
        return ok

    def set_pet_height(self, px):
        """设置桌宠像素高度（最长边），立即生效并记住。"""
        px = max(80, min(800, int(px)))
        if px == int(self.cfg["pet"].get("height", 300)):
            return
        self.cfg["pet"]["height"] = px
        self._apply_pet()
        cfg_mod.save_config(self.cfg)

    def adjust_pet_height(self, delta):
        self.set_pet_height(int(self.cfg["pet"].get("height", 300)) + delta)

    def toggle_animate(self):
        on = not bool(self.cfg["pet"].get("animate", True))
        self.cfg["pet"]["animate"] = on
        self.pet.set_animate(on)
        cfg_mod.save_config(self.cfg)
        self.bubble.show("🎞️ 动画已打开" if on else "⏸️ 动画已暂停，更省电")

    def change_pet(self, path):
        if not path:
            return
        rel = os.path.relpath(path, cfg_mod.BASE_DIR)
        if not rel.startswith(".."):
            path = rel.replace(os.sep, "/")
        old = self.cfg["pet"].get("assets_dir")
        self.cfg["pet"]["assets_dir"] = path
        if self._apply_pet():
            cfg_mod.save_config(self.cfg)
            self.bubble.show("换上新衣服啦～ ✨")
        else:
            self.cfg["pet"]["assets_dir"] = old
            self._apply_pet()

    def on_pet_moved(self):
        self.bubble.reposition()

    # ---------- 对话 ----------
    def send_message(self, text):
        if self.busy or not text:
            return
        _, profile = cfg_mod.active_profile(self.cfg)
        if not profile or not (profile.get("api_key") or "").strip():
            msg = "请先填写 API Key：右键桌宠 → 设置"
            self.chat.append_meta(f"🔑 {msg}")
            self.bubble.show("🔑 " + msg)
            return
        self.busy = True
        self.chat.add_user(text)
        self.chat.start_assistant()
        self.chat.set_busy(True)
        self.bubble.show("💭 思考中…", duration_s=-1)
        threading.Thread(target=self.engine.send, args=(text,), daemon=True).start()

    def reset_chat(self):
        if self.busy:
            self.bubble.show("⏳ 等当前回复结束后再开始新对话哦")
            return
        self.engine.reset()
        self.chat.clear_all()
        self.chat.append_meta("✨ 新的对话已开始")
        self.bubble.show("记忆清空啦～ (๑•̀ㅂ•́)و")

    # ---------- 队列轮询（后台线程的结果统一回主线程刷 UI） ----------
    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.ui_queue.get_nowait()
                if kind == "chunk":
                    self.chat.append_chunk(payload)
                elif kind == "done":
                    self.chat.finish_assistant()
                    self.busy = False
                    self.chat.set_busy(False)
                    self.bubble.show(_bubble_summary(payload))
                elif kind == "error":
                    self.chat.fail_assistant(payload)
                    self.busy = False
                    self.chat.set_busy(False)
                    self.bubble.show("⚠️ " + _bubble_summary(payload, 90))
        except queue.Empty:
            pass
        self.pet.root.after(50, self._poll_queue)

    # ---------- 窗口与状态 ----------
    def refresh_topmost(self):
        """聊天/设置窗口打开时让桌宠让出置顶，避免挡住对话框。"""
        try:
            chat = getattr(self, "chat", None)
            chat_open = bool(chat is not None and chat.win.winfo_viewable())
            settings_open = bool(self.settings_win is not None
                                 and self.settings_win.win.winfo_exists())
            self.pet.win.attributes("-topmost", not (chat_open or settings_open))
        except tk.TclError:
            pass

    def toggle_chat(self):
        self.chat.toggle()

    def open_settings(self):
        if self.settings_win is not None and self.settings_win.win.winfo_exists():
            self.settings_win.win.lift()
            return
        self.settings_win = SettingsWindow(self)
        self.refresh_topmost()

    def apply_config(self):
        """设置保存后重新加载形象与状态栏。"""
        self._apply_pet()
        self.update_status()

    def update_status(self):
        name, profile = cfg_mod.active_profile(self.cfg)
        self.chat.set_title(self.cfg["pet"].get("name", "桌宠"))
        if not profile:
            self.chat.set_status("⚠️ 没有可用的厂商档案")
            return
        proto = PROTOCOL_LABELS.get(profile.get("protocol", "openai"), "OpenAI 兼容")
        key_note = "" if (profile.get("api_key") or "").strip() else " · 🔑 Key 未填写"
        self.chat.set_status(f"🔗 {name} | {proto} | {profile.get('model') or '模型未设置'}{key_note}")

    def show_help(self):
        messagebox.showinfo(
            "使用帮助 · 桌宠 Agent",
            "· 拖动桌宠：按住左键拖拽，位置自动记忆\n"
            "· Ctrl + 滚轮：调整桌宠大小\n"
            "· 双击桌宠：打开 / 关闭聊天窗口\n"
            "· 右键桌宠：打开对话 · 新的对话 · 更换形象 · 调整大小 · 动画 · 设置 · 退出\n"
            "· 首次使用：右键 → 设置，选厂商、填 API Key\n"
            "· 自定义形象：右键 → 更换形象，或设置中修改形象资源路径\n"
            "· 自定义人设：设置中修改系统提示词，可把 txt/md 文件直接拖进去\n"
            "· 更多说明见 README.md",
        )

    def quit(self):
        try:
            self.cfg["pet"]["position"] = [self.pet.win.winfo_x(), self.pet.win.winfo_y()]
            cfg_mod.save_config(self.cfg)
        except Exception:
            pass
        self.pet.root.destroy()


_single_instance_handle = None


def _acquire_single_instance():
    """Windows 命名互斥量：避免重复双击启动出好几只桌宠（会拖慢整机）。"""
    global _single_instance_handle
    if os.name != "nt":
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(None, False, "TuanjieDesktopPetAgent_SingleInstance")
        if not handle:
            return True  # 拿不到互斥量时不阻止启动
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            kernel32.CloseHandle(handle)
            return False
        _single_instance_handle = handle
        return True
    except Exception:
        return True


def main():
    if os.name == "nt":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # 高分屏下窗口更清晰
        except Exception:
            pass
    if not _acquire_single_instance():
        try:
            ctypes.windll.user32.MessageBoxW(
                None,
                "桌宠已经在运行啦～\n\n在屏幕右下角找找它，或看看任务栏。\n"
                "重复启动多只桌宠会明显拖慢电脑，所以这里只保留一只。",
                "桌宠 Agent",
                0x40,  # MB_ICONINFORMATION
            )
        except Exception:
            pass
        return
    app = PetApp()
    if "--smoke" in sys.argv:  # 自测模式：启动 1.5 秒后自动退出
        app.pet.root.after(1500, app.quit)
    app.pet.root.mainloop()
    print("APP_EXIT_OK")


if __name__ == "__main__":
    main()
