# -*- coding: utf-8 -*-
"""聊天窗口：流式输出、消息展示、输入框（支持把文本文件拖进来）。"""

import tkinter as tk
from tkinter import ttk

import config as cfg_mod
from pet_ui import DND_FILES, HAS_DND


class ChatWindow:
    def __init__(self, app):
        self.app = app
        self.win = tk.Toplevel(app.root)
        self.win.title("💬 对话")
        self.win.geometry("440x600")
        self.win.minsize(360, 460)
        self.win.protocol("WM_DELETE_WINDOW", self.hide)  # 关闭仅隐藏，不销毁

        top = ttk.Frame(self.win, padding=(10, 8, 10, 4))
        top.pack(fill="x")
        self._status_line = ""
        self._busy = False
        self.status_var = tk.StringVar(value="加载中…")
        ttk.Label(top, textvariable=self.status_var, foreground="#7A7466").pack(
            side="left", fill="x", expand=True)
        ttk.Button(top, text="新对话", command=self.app.reset_chat).pack(side="left", padx=(4, 0))
        ttk.Button(top, text="设置", command=self.app.open_settings).pack(side="left", padx=(4, 0))

        body = ttk.Frame(self.win, padding=(10, 0, 10, 6))
        body.pack(fill="both", expand=True)
        self.text = tk.Text(
            body, wrap="word", state="disabled", relief="flat",
            bg="#FAFAF6", padx=10, pady=8,
            font=("Microsoft YaHei", 10), spacing1=3, spacing3=5,
        )
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        self.text.tag_configure("user", foreground="#1167A8")
        self.text.tag_configure("assistant", foreground="#33302A")
        self.text.tag_configure("error", foreground="#C0392B")
        self.text.tag_configure("meta", foreground="#9A9384", font=("Microsoft YaHei", 9, "italic"))

        bottom = ttk.Frame(self.win, padding=(10, 6, 10, 10))
        bottom.pack(fill="x")
        self.input = tk.Text(
            bottom, height=3, relief="flat", bg="#FFFFFF",
            padx=8, pady=6, font=("Microsoft YaHei", 10),
        )
        self.input.pack(side="left", fill="both", expand=True)
        self.send_btn = ttk.Button(bottom, text="发送", width=8, command=self._on_send)
        self.input.bind("<Return>", self._on_enter)
        self._setup_drop()

        # 发送按钮先占位（side=right），输入框再吃掉剩余宽度，
        # 否则 expand 的输入框会把按钮挤成 1 像素。
        self.send_btn.pack_forget()
        self.send_btn.pack(side="right", fill="y", padx=(8, 0))
        self.input.pack_forget()
        self.input.pack(side="left", fill="both", expand=True)

        # pack 顺序决定空间分配：必须先给底部输入区占位，
        # 再让正文区 expand 吃掉剩余空间，否则输入框会被挤成 1 像素（打不了字）。
        bottom.pack_forget()
        bottom.pack(side="bottom", fill="x")
        body.pack_forget()
        body.pack(fill="both", expand=True)

        self._intro_done = False
        self.hide()

    def _setup_drop(self):
        """把 txt/md 等文件直接拖进输入框，自动读成文字。"""
        if not HAS_DND:
            return
        try:
            self.input.drop_target_register(DND_FILES)
            self.input.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            pass

    def _on_drop(self, event):
        paths = self.win.tk.splitlist(event.data)
        inserted = 0
        for path in paths:
            try:
                text, truncated = cfg_mod.read_text_file(path)
            except Exception as exc:  # noqa: BLE001
                self.append_meta(f"⚠️ 读不了这个文件：{path}\n{exc}")
                continue
            if inserted:
                self.input.insert("insert", "\n\n")
            self.input.insert("insert", text)
            inserted += 1
            if truncated:
                self.append_meta("⚠️ 文件较大，只导入了前 40 万字符")
        if inserted:
            self.append_meta(f"📄 已导入 {inserted} 个文件，可直接发送")
            self.input.focus_set()
        return event.action

    # ---------- 展示 ----------
    def _insert(self, content, tag, at=None):
        self.text.configure(state="normal")
        self.text.insert(at if at is not None else "end-1c", content, tag)
        self.text.see("end")
        self.text.configure(state="disabled")

    def append_meta(self, text):
        self._insert(f"{text}\n\n", "meta")

    def add_user(self, text):
        self._insert(f"🧑 你\n{text}\n\n", "user")

    def start_assistant(self):
        name = self.app.cfg["pet"].get("name", "桌宠")
        self._insert(f"🐾 {name}\n", "assistant")

    def append_chunk(self, piece):
        # 流式内容始终追加在文本末尾（生成期间无其他插入）
        self._insert(piece, "assistant", at="end-1c")

    def finish_assistant(self):
        self._insert("\n\n", "assistant")

    def fail_assistant(self, message):
        self._insert(f"\n\n⚠️ {message}\n\n", "error")

    def clear_all(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

    # ---------- 状态与窗口切换 ----------
    def set_status(self, line):
        self._status_line = line
        self._refresh_status()

    def set_busy(self, busy):
        self._busy = busy
        self.send_btn.configure(state="disabled" if busy else "normal")
        self._refresh_status()

    def _refresh_status(self):
        self.status_var.set("⏳ 生成中…" if self._busy else self._status_line)

    def set_title(self, name):
        self.win.title(f"💬 和 {name} 聊天")

    def show(self):
        if not self._intro_done:
            self._intro_done = True
            self.append_meta(
                "💡 回车发送 · Shift+回车换行 · 右键桌宠有更多操作\n"
                "📄 也可以把 txt / md 文件直接拖进下面的输入框\n"
                "先在「设置」里填好 API Key 就能开始聊天啦")
        self.win.deiconify()
        self.win.lift()
        # 关键：先把窗口激活，再把键盘焦点交给输入框，
        # 否则焦点会停在 Toplevel 上，打字没有任何反应。
        try:
            self.win.focus_force()
        except tk.TclError:
            pass
        self.input.focus_force()
        self.input.focus_set()
        self.win.after(30, self.input.focus_set)
        self.app.refresh_topmost()

    def hide(self):
        self.win.withdraw()
        self.app.refresh_topmost()

    def toggle(self):
        if self.win.winfo_viewable():
            self.hide()
        else:
            self.show()

    # ---------- 输入 ----------
    def _on_enter(self, event):
        if event.state & 0x0001:  # Shift：正常换行
            return None
        self._on_send()
        return "break"

    def _on_send(self):
        text = self.input.get("1.0", "end").strip()
        if not text or self.app.busy:
            return
        self.input.delete("1.0", "end")
        self.app.send_message(text)
