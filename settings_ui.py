# -*- coding: utf-8 -*-
"""设置窗口：厂商配置档案、系统提示词、桌宠外观、对话参数。"""

import copy
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

import config as cfg_mod
from config import BASE_DIR, PETS_ROOT, PRESETS

PROTOCOL_LABELS = {"openai": "OpenAI 兼容", "anthropic": "Anthropic Claude"}
LABEL_TO_PROTOCOL = {label: proto for proto, label in PROTOCOL_LABELS.items()}


def _relativize(path):
    """尽量存为项目相对路径，便于整个文件夹拷贝。"""
    try:
        rel = os.path.relpath(path, BASE_DIR)
    except ValueError:
        return path
    if rel.startswith(".."):
        return path
    return rel.replace(os.sep, "/")


class SettingsWindow:
    def __init__(self, app):
        self.app = app
        self.cfg = copy.deepcopy(app.cfg)
        self.win = tk.Toplevel(app.root)
        self.win.title("设置 - 桌宠 Agent")
        # 自适应屏幕：小屏 / 高缩放下也不会把底部按钮挤出屏幕
        sw, sh = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
        w = min(760, max(560, sw - 80))
        h = min(1100, max(460, sh - 160))
        self.win.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 3)}")
        self.win.minsize(560, 420)
        self.win.protocol("WM_DELETE_WINDOW", self._cancel)
        self.win.bind("<Escape>", lambda e: self._cancel())
        try:
            self.win.grab_set()
        except tk.TclError:
            pass

        # 内容放进可滚动画布：内容比窗口高时可以滚动，按钮栏固定在底部
        outer = ttk.Frame(self.win)
        canvas = tk.Canvas(outer, highlightthickness=0, bd=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        container = ttk.Frame(canvas)
        canvas_id = canvas.create_window((0, 0), window=container, anchor="nw")
        container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(canvas_id, width=e.width))
        self.win.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))
        app.refresh_topmost()

        # ===== AI 厂商 =====
        box = ttk.LabelFrame(container, text=" AI 厂商（可建多个档案随时切换） ", padding=(12, 8))
        box.pack(fill="x", padx=14, pady=(14, 4))

        row = ttk.Frame(box)
        row.pack(fill="x", pady=(0, 4))
        ttk.Label(row, text="配置档案:", width=9).pack(side="left")
        self.profile_var = tk.StringVar()
        self.profile_cb = ttk.Combobox(row, textvariable=self.profile_var, state="readonly")
        self.profile_cb.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.profile_cb.bind("<<ComboboxSelected>>", lambda e: self._load_profile_fields())
        ttk.Button(row, text="新建", width=5, command=self._new_profile).pack(side="left", padx=2)
        ttk.Button(row, text="删除", width=5, command=self._delete_profile).pack(side="left", padx=2)

        ttk.Label(box, text="快速套用（新建或重置同名档案，保留已填的 Key）：",
                  foreground="#8B8577").pack(anchor="w", pady=(4, 0))
        presets_grid = ttk.Frame(box)
        presets_grid.pack(fill="x", pady=2)
        cols = 3  # 3 列可完整显示「Claude (Anthropic)」这类长名字
        for i, pname in enumerate(PRESETS):
            ttk.Button(presets_grid, text=pname, command=lambda n=pname: self._apply_preset(n)).grid(
                row=i // cols, column=i % cols, sticky="ew", padx=2, pady=2)
        for c in range(cols):
            presets_grid.columnconfigure(c, weight=1)

        self.protocol_var = tk.StringVar()
        self.base_var = tk.StringVar()
        self.key_var = tk.StringVar()
        self.model_var = tk.StringVar()
        self._form_row(box, "协议:", self.protocol_var, ttk.Combobox,
                       dict(values=list(PROTOCOL_LABELS.values()), state="readonly"))
        self._form_row(box, "API 地址:", self.base_var, ttk.Entry)
        self._form_row(box, "API Key:", self.key_var, ttk.Entry, dict(show="*"))
        self._form_row(box, "模型:", self.model_var, ttk.Entry)

        # ===== 系统提示词（已锁定） =====
        box2 = ttk.LabelFrame(container, text=" 角色人设（随程序发布，已锁定） ", padding=(12, 8))
        box2.pack(fill="x", padx=14, pady=4)
        ttk.Label(box2, text="🔒 人设由程序内置，界面不提供修改入口。",
                  foreground="#5A6472", font=("Microsoft YaHei", 10, "bold")).pack(anchor="w")
        ttk.Label(box2, text="想换人设请在打包前修改 persona.py 后重新生成安装包。",
                  foreground="#8B8577").pack(anchor="w", pady=(2, 0))

        # ===== 桌宠 =====
        box3 = ttk.LabelFrame(container, text=" 桌宠 ", padding=(12, 8))
        box3.pack(fill="x", padx=14, pady=4)
        self.name_var = tk.StringVar(value=self.cfg["pet"].get("name", "若"))
        self._form_row(box3, "名字:", self.name_var, ttk.Entry)
        dir_row = ttk.Frame(box3)
        dir_row.pack(fill="x", pady=2)
        ttk.Label(dir_row, text="形象资源:", width=9).pack(side="left")
        self.dir_var = tk.StringVar(value=self.cfg["pet"].get("assets_dir", ""))
        ttk.Entry(dir_row, textvariable=self.dir_var).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(dir_row, text="浏览文件夹", command=self._browse_dir).pack(side="left", padx=2)
        ttk.Button(dir_row, text="选图片/GIF", command=self._browse_file).pack(side="left", padx=2)

        nums = ttk.Frame(box3)
        nums.pack(fill="x", pady=2)
        self.frame_ms_var = tk.StringVar(value=str(self.cfg["pet"].get("frame_ms", 150)))
        self.dur_var = tk.StringVar(value=str(self.cfg["pet"].get("bubble_duration_s", 15)))
        self.height_var = tk.StringVar(value=str(self.cfg["pet"].get("height", 300)))
        self.animate_var = tk.BooleanVar(value=bool(self.cfg["pet"].get("animate", True)))
        ttk.Label(nums, text="大小(像素):").pack(side="left")
        ttk.Spinbox(nums, from_=80, to=800, increment=20, textvariable=self.height_var, width=6).pack(
            side="left", padx=(2, 14))
        ttk.Label(nums, text="帧间隔(ms):").pack(side="left")
        ttk.Spinbox(nums, from_=40, to=2000, increment=20, textvariable=self.frame_ms_var, width=6).pack(
            side="left", padx=(2, 14))
        ttk.Label(nums, text="气泡停留(秒):").pack(side="left")
        ttk.Spinbox(nums, from_=2, to=600, increment=1, textvariable=self.dur_var, width=6).pack(
            side="left", padx=2)

        anim_row = ttk.Frame(box3)
        anim_row.pack(fill="x", pady=(2, 0))
        ttk.Checkbutton(anim_row, text="播放动画（关掉最省电，宠物会静止不动）",
                        variable=self.animate_var).pack(side="left")
        ttk.Label(
            box3,
            text="形象支持三种形式：① 序列帧文件夹（多张图按文件名排序）② 单个动态 GIF\n"
                 "③ 单张静态图（自动上下起伏呼吸）。右键桌宠 → 更换形象 可随时切换。\n"
                 "建议透明底 PNG；「大小」指角色最长边的像素，也可以 Ctrl+滚轮 在桌面上直接缩放。",
            foreground="#8B8577", justify="left",
        ).pack(anchor="w", pady=(4, 0))

        # ===== 对话参数 =====
        box4 = ttk.LabelFrame(container, text=" 对话参数 ", padding=(12, 8))
        box4.pack(fill="x", padx=14, pady=4)
        chat = self.cfg.get("chat", {})
        self.temp_var = tk.StringVar(value=str(chat.get("temperature", 0.8)))
        self.tokens_var = tk.StringVar(value=str(chat.get("max_tokens", 1024)))
        self.hist_var = tk.StringVar(value=str(chat.get("max_history", 20)))
        row4 = ttk.Frame(box4)
        row4.pack(fill="x")
        ttk.Label(row4, text="温度:").pack(side="left")
        ttk.Spinbox(row4, from_=0.0, to=2.0, increment=0.1, textvariable=self.temp_var, width=5).pack(
            side="left", padx=(2, 14))
        ttk.Label(row4, text="回复上限:").pack(side="left")
        ttk.Spinbox(row4, from_=64, to=16384, increment=64, textvariable=self.tokens_var, width=7).pack(
            side="left", padx=(2, 14))
        ttk.Label(row4, text="记忆条数:").pack(side="left")
        ttk.Spinbox(row4, from_=2, to=100, increment=2, textvariable=self.hist_var, width=5).pack(
            side="left", padx=2)
        ttk.Label(box4, text="（记忆条数 = 最多保留多少条历史消息；回复上限 max_tokens）",
                  foreground="#8B8577").pack(anchor="w", pady=(4, 0))

        # ===== 按钮（固定在窗口底部，不随内容滚动） =====
        btns = ttk.Frame(self.win, padding=(14, 8, 14, 12))
        # 先放按钮再放提示文字：窗口偏窄时优先保证「保存/取消」可见
        ttk.Button(btns, text="取消", command=self._cancel).pack(side="right")
        ttk.Button(btns, text="保存", command=self._save).pack(side="right", padx=(0, 8))
        ttk.Label(btns, text="保存后立即生效；也可直接编辑 config.json。",
                  foreground="#8B8577").pack(side="left", fill="x", expand=True)
        btns.pack(side="bottom", fill="x")
        outer.pack(fill="both", expand=True)

        self._init_profile()

    # ---------- 通用行 ----------
    def _form_row(self, parent, label, var, widget_cls, extra=None):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=label, width=9).pack(side="left")
        kw = {"textvariable": var}
        kw.update(extra or {})
        widget_cls(row, **kw).pack(side="left", fill="x", expand=True)

    # ---------- 档案管理 ----------
    def _init_profile(self):
        if not self.cfg["profiles"]:
            self.cfg["profiles"] = {"自定义": {"protocol": "openai", "base_url": "", "api_key": "", "model": ""}}
        if self.cfg.get("active_profile") not in self.cfg["profiles"]:
            self.cfg["active_profile"] = next(iter(self.cfg["profiles"]))
        self.profile_var.set(self.cfg["active_profile"])
        self._refresh_profile_values()
        self._load_profile_fields()

    def _refresh_profile_values(self):
        self.profile_cb.configure(values=list(self.cfg["profiles"].keys()))

    def _load_profile_fields(self):
        p = self.cfg["profiles"].get(self.profile_var.get(), {})
        self.protocol_var.set(PROTOCOL_LABELS.get(p.get("protocol", "openai"), PROTOCOL_LABELS["openai"]))
        self.base_var.set(p.get("base_url", ""))
        self.key_var.set(p.get("api_key", ""))
        self.model_var.set(p.get("model", ""))

    def _collect_profile_fields(self):
        name = self.profile_var.get().strip()
        if not name:
            messagebox.showwarning("提示", "请先选择或新建一个配置档案。", parent=self.win)
            return None
        p = self.cfg["profiles"].setdefault(name, {})
        p["protocol"] = LABEL_TO_PROTOCOL.get(self.protocol_var.get(), "openai")
        p["base_url"] = self.base_var.get().strip()
        p["api_key"] = self.key_var.get().strip()
        p["model"] = self.model_var.get().strip()
        return name

    def _apply_preset(self, preset_name):
        preset = PRESETS[preset_name]
        p = self.cfg["profiles"].setdefault(preset_name, {})
        keep_key = p.get("api_key", "")
        p.update(protocol=preset["protocol"], base_url=preset["base_url"],
                 model=preset["model"], api_key=keep_key)
        self.profile_var.set(preset_name)
        self._refresh_profile_values()
        self._load_profile_fields()

    def _new_profile(self):
        name = simpledialog.askstring("新建档案", "档案名称（例如：我的厂商）:", parent=self.win)
        if not name or not name.strip():
            return
        name = name.strip()
        if name in self.cfg["profiles"]:
            messagebox.showinfo("提示", f"档案「{name}」已存在。", parent=self.win)
            return
        self.cfg["profiles"][name] = {"protocol": "openai", "base_url": "", "api_key": "", "model": ""}
        self.profile_var.set(name)
        self._refresh_profile_values()
        self._load_profile_fields()

    def _delete_profile(self):
        name = self.profile_var.get()
        if len(self.cfg["profiles"]) <= 1:
            messagebox.showinfo("提示", "至少保留一个配置档案。", parent=self.win)
            return
        if not messagebox.askyesno("确认", f"删除档案「{name}」？", parent=self.win):
            return
        self.cfg["profiles"].pop(name, None)
        self.profile_var.set(next(iter(self.cfg["profiles"])))
        self._refresh_profile_values()
        self._load_profile_fields()

    # ---------- 桌宠资源选择 ----------
    def _browse_dir(self):
        init = PETS_ROOT if os.path.isdir(PETS_ROOT) else BASE_DIR
        path = filedialog.askdirectory(title="选择序列帧文件夹", initialdir=init, parent=self.win)
        if path:
            self.dir_var.set(_relativize(path))

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="选择图片或GIF", parent=self.win,
            filetypes=[("图片", "*.png *.gif *.jpg *.jpeg *.webp *.bmp")],
        )
        if path:
            self.dir_var.set(_relativize(path))

    # ---------- 保存 ----------
    @staticmethod
    def _to_int(var, default, lo, hi):
        try:
            v = int(float(var.get()))
        except (ValueError, TypeError):
            return default
        return max(lo, min(hi, v))

    def _save(self):
        name = self._collect_profile_fields()
        if name is None:
            return
        if not self.key_var.get().strip():
            if not messagebox.askyesno("提示", "API Key 还是空的，暂时无法发送消息。\n仍然保存？", parent=self.win):
                return
        self.cfg["active_profile"] = name

        pet = self.cfg["pet"]
        pet["name"] = self.name_var.get().strip() or "若"
        pet["assets_dir"] = self.dir_var.get().strip() or "assets/pets/default"
        pet["frame_ms"] = self._to_int(self.frame_ms_var, 150, 40, 2000)
        pet["bubble_duration_s"] = self._to_int(self.dur_var, 15, 2, 600)
        pet["height"] = self._to_int(self.height_var, 300, 80, 800)
        pet["animate"] = bool(self.animate_var.get())

        chat = self.cfg["chat"]
        try:
            temperature = float(self.temp_var.get())
        except (ValueError, TypeError):
            temperature = 0.8
        chat["temperature"] = max(0.0, min(2.0, temperature))
        chat["max_tokens"] = self._to_int(self.tokens_var, 1024, 64, 16384)
        chat["max_history"] = self._to_int(self.hist_var, 20, 2, 100)

        try:
            cfg_mod.save_config(self.cfg)
        except OSError as exc:
            messagebox.showerror("保存失败", str(exc), parent=self.win)
            return
        self.app.cfg = self.cfg
        self.app.apply_config()
        self._close()
        self.app.bubble.show("设置保存好啦～ (๑•̀ㅂ•́)و✧")

    def _cancel(self):
        self._close()

    def _close(self):
        try:
            self.win.grab_release()
        except tk.TclError:
            pass
        self.win.destroy()
        self.app.settings_win = None
        self.app.refresh_topmost()
