# -*- coding: utf-8 -*-
"""桌宠主窗口（透明、无边框、置顶、可拖拽、右键菜单）与头顶气泡。"""

import os
import sys
import tkinter as tk
from tkinter import filedialog

from PIL import Image, ImageChops, ImageDraw, ImageSequence, ImageTk

# 内置的拖放库（vendor/tkinterdnd2），缺失时自动降级为「从文件导入」按钮
_VENDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")
if os.path.isdir(_VENDOR) and _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    HAS_DND = True
except Exception:  # noqa: BLE001 - 缺库不应影响主功能
    DND_FILES = None
    TkinterDnD = None
    HAS_DND = False

from config import BASE_DIR, PETS_ROOT, resolve_path

# 透明键色：窗口中该颜色的像素变为全透明且点击穿透（Windows color-key 透明）
KEY_RGB = (1, 2, 3)
KEY_COLOR = "#010203"
SUPPORTED_EXTS = (".png", ".gif", ".jpg", ".jpeg", ".webp", ".bmp")


def _composite_on_key(rgba):
    """RGBA 图压到键色底上得到 RGB 图：完全透明区域变成键色（窗口级透明）。
    不透明像素保留原色，避免抗锯齿边缘被键色污染出现明显黑边。"""
    alpha = rgba.getchannel("A")
    solid_mask = alpha.point(lambda v: 255 if v >= 200 else 0)
    over = Image.alpha_composite(Image.new("RGBA", rgba.size, KEY_RGB + (255,)), rgba).convert("RGB")
    over.paste(rgba.convert("RGB"), (0, 0), solid_mask)
    return over


def load_pet_frames(assets_dir):
    """加载桌宠资源，返回 (帧列表, 每帧时长列表或 None)。支持三种形式：
    1. 目录：多张图片按文件名排序组成序列帧（每个文件取 1 帧）
    2. 单个动态 GIF：自动拆帧，并使用 GIF 自带的每帧时长
    3. 单张静态图：自动生成 6 帧上下轻微起伏的呼吸动画
    """
    path = resolve_path(assets_dir)
    raw = []
    durations = None
    if os.path.isfile(path):
        with Image.open(path) as im:
            per_durs = []
            for frame in ImageSequence.Iterator(im):
                raw.append(frame.convert("RGBA"))
                d = frame.info.get("duration")
                per_durs.append(int(d) if isinstance(d, (int, float)) and d > 0 else 0)
        if len(raw) > 1 and any(per_durs):
            durations = per_durs
    elif os.path.isdir(path):
        files = sorted(name for name in os.listdir(path) if name.lower().endswith(SUPPORTED_EXTS))
        for name in files:
            with Image.open(os.path.join(path, name)) as im:
                raw.append(im.convert("RGBA"))
    else:
        raise FileNotFoundError(f"未找到桌宠图像: {path}")
    if not raw:
        raise FileNotFoundError(f"\"{path}\" 下没有可用图片（支持 {'/'.join(SUPPORTED_EXTS)}）")

    if len(raw) == 1:  # 静态图 → 呼吸起伏动画
        src = raw[0]
        amp = max(2, src.height // 18)
        bobbed = []
        # 画布比原图高 2*amp，静止帧贴着画布底部（脚踩地面），
        # 起伏帧向上移动，最高帧的头顶正好到画布顶端，不会被裁掉。
        for off in (0, -amp, -amp * 2, -amp, 0, 0):
            canvas = Image.new("RGBA", (src.width, src.height + amp * 2), (0, 0, 0, 0))
            canvas.paste(src, (0, amp * 2 + off))
            bobbed.append(canvas)
        raw = bobbed

    # 统一画布尺寸并居中
    max_w = max(f.width for f in raw)
    max_h = max(f.height for f in raw)
    frames = []
    for f in raw:
        if f.size != (max_w, max_h):
            canvas = Image.new("RGBA", (max_w, max_h), (0, 0, 0, 0))
            canvas.paste(f, ((max_w - f.width) // 2, (max_h - f.height) // 2), f)
            f = canvas
        frames.append(_composite_on_key(f))
    return frames, durations


def _fallback_frames():
    """资源完全不可用时内置的占位团子，保证程序永远有形象可显示。"""
    size = 150
    frames = []
    for closed in (False, False, True, False, False, False):
        im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse((18, 30, size - 18, size - 6), fill=(255, 235, 205, 255), outline=(146, 116, 88, 255), width=3)
        if closed:
            d.line((52, 82, 68, 82), fill=(74, 52, 36, 255), width=5)
            d.line((size - 68, 82, size - 52, 82), fill=(74, 52, 36, 255), width=5)
        else:
            d.ellipse((50, 72, 68, 94), fill=(74, 52, 36, 255))
            d.ellipse((size - 68, 72, size - 50, 94), fill=(74, 52, 36, 255))
        d.ellipse((36, 98, 52, 110), fill=(255, 168, 168, 180))
        d.ellipse((size - 52, 98, size - 36, 110), fill=(255, 168, 168, 180))
        d.arc((size // 2 - 12, 92, size // 2 + 12, 108), 20, 160, fill=(146, 96, 66, 255), width=3)
        frames.append(_composite_on_key(im))
    return frames


def _content_bbox(frame):
    """返回角色实际内容的包围盒（帧是压在键色上的 RGB，透明区=键色）。"""
    if "A" in frame.getbands():
        return frame.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    key = Image.new("RGB", frame.size, KEY_RGB)
    diff = ImageChops.difference(frame.convert("RGB"), key).convert("L")
    return diff.point(lambda v: 255 if v > 8 else 0).getbbox()


def _scale_to_height(frames, height):
    """按「角色实际内容」的最长边缩放到 height，透明留白不计入尺寸。"""
    boxes = [b for b in (_content_bbox(f) for f in frames) if b]
    if not boxes:
        return frames
    content_w = max(b[2] - b[0] for b in boxes)
    content_h = max(b[3] - b[1] for b in boxes)
    longest = max(content_w, content_h)
    if longest <= 0:
        return frames
    ratio = height / float(longest)
    if abs(ratio - 1.0) < 0.02:
        return frames
    return [
        f.resize((max(1, round(f.width * ratio)), max(1, round(f.height * ratio))), Image.LANCZOS)
        for f in frames
    ]


class PetWindow:
    """透明无边框置顶窗口，显示序列帧动画。"""

    def __init__(self, app):
        self.app = app
        # 根窗口只负责事件循环：隐藏起来。
        # 如果把「无边框(overrideredirect)」直接用在根窗口上，Tk 的焦点模型会失效，
        # 聊天窗口里的输入框永远拿不到键盘焦点（表现为「打字没反应」）。
        self.root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
        self.root.withdraw()
        self.win = tk.Toplevel(self.root)
        self.win.title("桌宠 Agent")
        self.win.overrideredirect(True)   # 无边框
        self.win.attributes("-topmost", True)
        self.win.config(bg=KEY_COLOR)
        try:
            self.win.attributes("-transparentcolor", KEY_COLOR)
        except tk.TclError:
            pass  # 系统不支持颜色键透明时退化为不透明窗口
        self.label = tk.Label(self.win, bg=KEY_COLOR, bd=0, highlightthickness=0, cursor="hand2")
        self.label.pack(fill="both", expand=True)

        self._photos = []
        self._durations = None
        self._frame_ms = 150
        self._height = 300
        self._animate = True
        self._idx = 0
        self._anim_job = None
        self._placed = False
        self._size = (180, 204)
        self._drag = None

        self._build_menu()
        self._bind_events()

    # ---------- 形象加载与动画 ----------
    def set_pet(self, assets_dir, frame_ms, height=300, animate=True, position=None):
        """加载形象；失败自动回退到内置团子。返回是否加载成功。"""
        try:
            frames, durations = load_pet_frames(assets_dir)
            ok = True
        except Exception:
            frames, durations = _fallback_frames(), None
            ok = False
        self._durations = durations
        self._frame_ms = max(40, int(frame_ms or 150))
        self._height = max(80, int(height or 300))
        self._animate = bool(animate)
        frames = _scale_to_height(frames, self._height)
        self._photos = [ImageTk.PhotoImage(frame, master=self.win) for frame in frames]
        w, h = frames[0].size

        old_w, old_h = self._size
        if self._placed:
            # 缩放时保持「脚踩的位置」不动，避免宠物跳走
            x = self.win.winfo_x() + (old_w - w) // 2
            y = self.win.winfo_y() + (old_h - h)
        elif position:
            x, y = position
        else:
            x = self.win.winfo_screenwidth() - w - 70
            y = self.win.winfo_screenheight() - h - 90
        sw, sh = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
        x = min(max(0, int(x)), max(0, sw - w))
        y = min(max(0, int(y)), max(0, sh - h))
        self.win.geometry(f"{w}x{h}+{x}+{y}")
        self._size = (w, h)
        self._placed = True
        self._idx = 0
        self._show_frame()
        self._schedule_next()
        return ok

    def _show_frame(self):
        if self._photos:
            self.label.configure(image=self._photos[self._idx])

    def set_animate(self, animate):
        """开关动画：关闭后停在同一帧，CPU 占用降到接近 0。"""
        self._animate = bool(animate)
        if not self._animate:
            if self._anim_job is not None:
                try:
                    self.root.after_cancel(self._anim_job)
                except Exception:
                    pass
                self._anim_job = None
        else:
            self._schedule_next()

    def _schedule_next(self):
        if self._anim_job is not None:
            try:
                self.root.after_cancel(self._anim_job)
            except Exception:
                pass
            self._anim_job = None
        if len(self._photos) < 2 or not self._animate:
            return
        delay = self._frame_ms
        if self._durations:
            d = self._durations[self._idx % len(self._durations)]
            if d:
                delay = max(20, d)
        self._anim_job = self.root.after(delay, self._tick)

    def _tick(self):
        self._anim_job = None
        self._idx = (self._idx + 1) % len(self._photos)
        self._show_frame()
        self._schedule_next()

    # ---------- 菜单 ----------
    def _build_menu(self):
        font = ("Microsoft YaHei", 10)
        self.menu = tk.Menu(self.win, tearoff=0, font=font)
        self.menu.add_command(label="💬 打开对话", command=self.app.toggle_chat)
        self.menu.add_command(label="🔄 新的对话", command=self.app.reset_chat)
        self.menu.add_separator()
        self.shape_menu = tk.Menu(self.menu, tearoff=0, font=font)
        self.menu.add_cascade(label="🖼️ 更换形象", menu=self.shape_menu)

        self.size_var = tk.IntVar(value=300)
        self.size_menu = tk.Menu(self.menu, tearoff=0, font=font)
        for label, px in (("迷你 · 160px", 160), ("小 · 220px", 220), ("标准 · 300px", 300),
                          ("大 · 380px", 380), ("超大 · 460px", 460)):
            self.size_menu.add_radiobutton(
                label=label, value=px, variable=self.size_var,
                command=lambda p=px: self.app.set_pet_height(p))
        self.menu.add_cascade(label="📏 调整大小", menu=self.size_menu)
        self.anim_var = tk.BooleanVar(value=True)
        self.menu.add_checkbutton(label="🎞️ 播放动画（更耗电）", variable=self.anim_var,
                                  command=self.app.toggle_animate)
        self.menu.add_command(label="⚙️ 设置", command=self.app.open_settings)
        self.menu.add_separator()
        self.menu.add_command(label="ℹ️ 使用帮助", command=self.app.show_help)
        self.menu.add_command(label="❌ 退出", command=self.app.quit)

    def _rebuild_shape_menu(self):
        self.shape_menu.delete(0, "end")
        if os.path.isdir(PETS_ROOT):
            for name in sorted(os.listdir(PETS_ROOT)):
                if os.path.isdir(os.path.join(PETS_ROOT, name)):
                    self.shape_menu.add_command(
                        label=name,
                        command=lambda p=f"assets/pets/{name}": self.app.change_pet(p),
                    )
        self.shape_menu.add_separator()
        self.shape_menu.add_command(label="📂 选择图片文件夹…", command=self.pick_pet_dir)
        self.shape_menu.add_command(label="📄 选择图片或GIF…", command=self.pick_pet_file)

    def pick_pet_dir(self):
        init = PETS_ROOT if os.path.isdir(PETS_ROOT) else BASE_DIR
        path = filedialog.askdirectory(title="选择序列帧文件夹", initialdir=init)
        if path:
            self.app.change_pet(path)

    def pick_pet_file(self):
        path = filedialog.askopenfilename(
            title="选择图片或GIF",
            filetypes=[("图片", "*.png *.gif *.jpg *.jpeg *.webp *.bmp")],
        )
        if path:
            self.app.change_pet(path)

    # ---------- 交互 ----------
    def _bind_events(self):
        self.label.bind("<Button-1>", self._on_press)
        self.label.bind("<B1-Motion>", self._on_drag)
        self.label.bind("<ButtonRelease-1>", self._on_release)
        self.label.bind("<Double-Button-1>", lambda e: self.app.toggle_chat())
        self.label.bind("<Button-3>", self._on_menu)
        self.label.bind("<Control-MouseWheel>", self._on_wheel)

    def _on_wheel(self, event):
        """Ctrl + 滚轮：直接缩放桌宠。"""
        self.app.adjust_pet_height(20 if event.delta > 0 else -20)
        return "break"

    def _on_press(self, event):
        self._drag = (event.x_root - self.win.winfo_x(), event.y_root - self.win.winfo_y())

    def _on_drag(self, event):
        if not self._drag:
            return
        dx, dy = self._drag
        self.win.geometry(f"+{event.x_root - dx}+{event.y_root - dy}")
        self.app.on_pet_moved()

    def _on_release(self, event):
        self._drag = None

    def _on_menu(self, event):
        self._rebuild_shape_menu()
        self.size_var.set(int(self.app.cfg["pet"].get("height", 300)))
        self.anim_var.set(bool(self.app.cfg["pet"].get("animate", True)))
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()


class Bubble:
    """宠物头顶的对话气泡，展示最新回复并自动隐藏。"""

    def __init__(self, app):
        self.app = app
        self.win = tk.Toplevel(app.root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.label = tk.Label(
            self.win,
            bg="#FFFBEF",
            fg="#3D3428",
            font=("Microsoft YaHei", 10),
            wraplength=280,
            justify="left",
            padx=12,
            pady=8,
            highlightbackground="#E4D2A2",
            highlightthickness=1,
        )
        self.label.pack(fill="both", expand=True)
        self.label.bind("<Button-1>", lambda e: self.hide())
        self.win.withdraw()
        self._job = None

    def show(self, text, duration_s=None):
        """显示气泡。duration_s=None 用配置的显示时长；<0 表示常驻直到下一次覆盖。"""
        if not text:
            return
        self.label.configure(text=text)
        self.win.deiconify()
        self.win.update_idletasks()
        self._reposition()
        self._cancel_timer()
        if duration_s is None:
            duration_s = self.app.cfg["pet"].get("bubble_duration_s", 15)
        if duration_s and duration_s > 0:
            self._job = self.win.after(int(duration_s * 1000), self.hide)

    def hide(self):
        self._cancel_timer()
        self.win.withdraw()

    def _cancel_timer(self):
        if self._job is not None:
            try:
                self.win.after_cancel(self._job)
            except Exception:
                pass
            self._job = None

    def _reposition(self):
        pet = self.app.pet.win
        bw, bh = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        px, py = pet.winfo_x(), pet.winfo_y()
        pw, ph = pet.winfo_width(), pet.winfo_height()
        x = px + (pw - bw) // 2
        y = py - bh - 14
        if y < 4:  # 顶部放不下就放到宠物下方
            y = py + ph + 14
        x = max(4, min(x, pet.winfo_screenwidth() - bw - 4))
        y = max(4, y)
        self.win.geometry(f"+{x}+{y}")
        self.win.lift()

    def reposition(self):
        if self.win.winfo_viewable():
            self._reposition()
