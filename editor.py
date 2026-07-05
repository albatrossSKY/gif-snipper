# editor.py
# Implements the GIF editing workspace including spatial cropping, timeline trimming, scaling, drawing annotations, and exporting.

import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import theme
import os
import threading
import subprocess

def apply_annotations(img, annotations, active_shape=None):
    """
    Renders committed drawings and active drawing shapes onto a PIL Image.
    Operates in RGBA mode to support transparent layers for highlighter.
    """
    working_img = img.convert("RGBA")
    overlay = Image.new("RGBA", working_img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    shapes = list(annotations)
    if active_shape:
        shapes.append(active_shape)
        
    for shape in shapes:
        t = shape["type"]
        color = shape.get("color", "#f38ba8")
        size = shape.get("size", 4)
        
        # Convert hex color to RGBA tuple
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        
        if t == "brush":
            pts = shape["points"]
            if len(pts) > 1:
                draw.line(pts, fill=(r, g, b, 255), width=size, joint="round")
        elif t == "arrow":
            start = shape["start"]
            end = shape["end"]
            draw.line([start, end], fill=(r, g, b, 255), width=size, joint="round")
            
            # Draw arrowhead polygon at the destination point
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length = (dx*dx + dy*dy)**0.5
            if length > 0:
                ux = dx / length
                uy = dy / length
                arrow_size = max(10, size * 3.5)
                # Perpendicular vectors
                px = -uy
                py = ux
                # Left corner
                lx = end[0] - ux * arrow_size + px * arrow_size * 0.45
                ly = end[1] - uy * arrow_size + py * arrow_size * 0.45
                # Right corner
                rx = end[0] - ux * arrow_size - px * arrow_size * 0.45
                ry = end[1] - uy * arrow_size - py * arrow_size * 0.45
                draw.polygon([end, (lx, ly), (rx, ry)], fill=(r, g, b, 255))
        elif t == "highlight":
            x1, y1, x2, y2 = shape["rect"]
            # Draw semi-transparent highlighter box
            draw.rectangle([x1, y1, x2, y2], fill=(r, g, b, 120))
        elif t == "redact":
            x1, y1, x2, y2 = shape["rect"]
            # Draw solid opaque black redact box
            draw.rectangle([x1, y1, x2, y2], fill=(0, 0, 0, 255))
            
    combined = Image.alpha_composite(working_img, overlay)
    return combined.convert("RGB")


class RangeSlider(tk.Canvas):
    """
    A custom-drawn dual-handle range slider widget for timeline trimming.
    """
    def __init__(self, parent, val_min, val_max, width=500, height=40, on_change_callback=None):
        super().__init__(parent, width=width, height=height, bg=theme.BG_MAIN, bd=0, highlightthickness=0)
        self.val_min = val_min
        self.val_max = max(val_min + 1, val_max)
        self.left_val = val_min
        self.right_val = val_max
        self.on_change = on_change_callback
        
        self.padding = 20
        self.w = width
        self.h = height
        
        self.active_handle = None
        self.handle_radius = 8
        
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Configure>", self.on_resize)
        
        self.redraw()

    def val_to_x(self, val):
        usable_w = self.w - 2 * self.padding
        ratio = (val - self.val_min) / (self.val_max - self.val_min)
        return self.padding + ratio * usable_w

    def x_to_val(self, x):
        usable_w = self.w - 2 * self.padding
        ratio = (x - self.padding) / usable_w
        val = self.val_min + ratio * (self.val_max - self.val_min)
        return int(round(max(self.val_min, min(self.val_max, val))))

    def redraw(self):
        self.delete("all")
        cy = self.h / 2
        x_start = self.padding
        x_end = self.w - self.padding
        
        # Draw background bar
        self.create_line(x_start, cy, x_end, cy, fill=theme.BG_CARD, width=6, capstyle="round")
        
        # Highlight active range
        xl = self.val_to_x(self.left_val)
        xr = self.val_to_x(self.right_val)
        self.create_line(xl, cy, xr, cy, fill=theme.ACCENT_BLUE, width=6, capstyle="round")
        
        # Draw handles
        self.create_oval(
            xl - self.handle_radius, cy - self.handle_radius,
            xl + self.handle_radius, cy + self.handle_radius,
            fill=theme.ACCENT_GREEN, outline=theme.BORDER_COLOR, width=2, tags="handle_l"
        )
        self.create_oval(
            xr - self.handle_radius, cy - self.handle_radius,
            xr + self.handle_radius, cy + self.handle_radius,
            fill=theme.ACCENT_GREEN, outline=theme.BORDER_COLOR, width=2, tags="handle_r"
        )
        
        # Labels
        self.create_text(xl, cy - 14, text=str(self.left_val), fill=theme.TEXT_PRIMARY, font=theme.FONT_SMALL)
        self.create_text(xr, cy + 14, text=str(self.right_val), fill=theme.TEXT_PRIMARY, font=theme.FONT_SMALL)

    def on_click(self, event):
        xl = self.val_to_x(self.left_val)
        xr = self.val_to_x(self.right_val)
        
        dist_l = abs(event.x - xl)
        dist_r = abs(event.x - xr)
        
        if dist_l < dist_r and dist_l < 25:
            self.active_handle = "left"
        elif dist_r < dist_l and dist_r < 25:
            self.active_handle = "right"
        else:
            self.active_handle = None

    def on_drag(self, event):
        if not self.active_handle:
            return
            
        val = self.x_to_val(event.x)
        
        if self.active_handle == "left":
            self.left_val = max(self.val_min, min(val, self.right_val - 1))
        elif self.active_handle == "right":
            self.right_val = min(self.val_max, max(val, self.left_val + 1))
            
        self.redraw()
        if self.on_change:
            self.on_change(self.left_val, self.right_val)

    def on_release(self, event):
        self.active_handle = None

    def on_resize(self, event):
        self.w = event.width
        self.h = event.height
        self.redraw()

    def set_range(self, l_val, r_val):
        self.left_val = max(self.val_min, min(l_val, self.val_max - 1))
        self.right_val = min(self.val_max, max(r_val, self.left_val + 1))
        self.redraw()


class EditorWindow:
    def __init__(self, parent, frames, fps=10):
        self.parent = parent
        self.original_frames = frames.copy()
        self.frames = frames.copy()
        self.fps = fps
        
        # Timeline State
        self.num_frames = len(self.frames)
        self.start_frame = 0
        self.end_frame = self.num_frames - 1
        self.current_frame_idx = 0
        
        self.is_playing = True
        self.crop_mode = False
        
        # --- Annotations & Drawing State ---
        self.draw_tool = None # None, "brush", "arrow", "highlight", "redact"
        self.draw_color = "#f38ba8" # default red
        self.draw_size = 5
        self.annotations = [] # list of committed drawing dicts
        self.current_points = None # active coordinates during click-and-drag
        
        # Dimensions
        self.orig_w, self.orig_h = self.frames[0].size
        self.preview_max_w = 660
        self.preview_max_h = 460
        
        # Scaling properties
        self.scale_factor = 1.0
        self.lock_aspect_ratio = True
        
        # Window setup
        self.window = tk.Toplevel(self.parent)
        self.window.title("GIF Snipper - Editor")
        self.window.geometry("1020x680")
        self.window.configure(bg=theme.BG_MAIN)
        self.window.focus_force()
        
        # Handle close
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Setup UI
        self.create_widgets()
        
        # Select first drawing color button
        self.select_color("#f38ba8")
        
        # Render first frames
        self.update_preview_size()
        self.animate_loop()

    def create_widgets(self):
        # 1. Main Layout: Sidebar (left) and Workspace (right)
        self.sidebar = tk.Frame(self.window, width=300, bg=theme.BG_SIDEBAR, padx=15, pady=15)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        
        self.workspace = tk.Frame(self.window, bg=theme.BG_MAIN, padx=15, pady=15)
        self.workspace.pack(side="right", fill="both", expand=True)
        
        # --- Sidebar Widgets ---
        # Title
        title_lbl = tk.Label(self.sidebar, text="GIF EDITOR", font=theme.FONT_TITLE, fg=theme.ACCENT_BLUE, bg=theme.BG_SIDEBAR)
        title_lbl.pack(anchor="w", pady=(0, 15))
        
        # Section A: Timeline & Trimming
        trim_group = tk.LabelFrame(self.sidebar, text="Timeline", font=theme.FONT_BOLD, fg=theme.TEXT_PRIMARY, bg=theme.BG_SIDEBAR, bd=1, relief="solid", padx=8, pady=6)
        trim_group.configure(highlightbackground=theme.BORDER_COLOR, highlightthickness=0)
        trim_group.pack(fill="x", pady=5)
        
        self.trim_info_lbl = tk.Label(trim_group, text="Frames: 0 - 0\nDuration: 0.0s", font=theme.FONT_SMALL, fg=theme.TEXT_MUTED, bg=theme.BG_SIDEBAR, justify="left")
        self.trim_info_lbl.pack(anchor="w")
        
        # Section B: Crop & Resize
        crop_group = tk.LabelFrame(self.sidebar, text="Crop & Scale", font=theme.FONT_BOLD, fg=theme.TEXT_PRIMARY, bg=theme.BG_SIDEBAR, bd=1, relief="solid", padx=8, pady=6)
        crop_group.configure(highlightbackground=theme.BORDER_COLOR, highlightthickness=0)
        crop_group.pack(fill="x", pady=5)
        
        crop_btns = tk.Frame(crop_group, bg=theme.BG_SIDEBAR)
        crop_btns.pack(fill="x", pady=2)
        
        self.crop_btn = tk.Button(crop_btns, text="Crop Box", command=self.toggle_crop_mode, font=theme.FONT_SMALL)
        theme.style_button(self.crop_btn, variant="secondary")
        self.crop_btn.pack(side="left", fill="x", expand=True, padx=(0, 2))
        
        self.apply_crop_btn = tk.Button(crop_btns, text="Apply Crop", command=self.apply_crop, font=theme.FONT_SMALL, state="disabled")
        theme.style_button(self.apply_crop_btn, variant="success")
        self.apply_crop_btn.pack(side="right", fill="x", expand=True, padx=(2, 0))
        
        # Dimensions
        dim_layout = tk.Frame(crop_group, bg=theme.BG_SIDEBAR, pady=4)
        dim_layout.pack(fill="x")
        
        tk.Label(dim_layout, text="W:", font=theme.FONT_SMALL, fg=theme.TEXT_MUTED, bg=theme.BG_SIDEBAR).grid(row=0, column=0, padx=2)
        self.w_entry = tk.Entry(dim_layout, width=5)
        theme.style_entry(self.w_entry)
        self.w_entry.grid(row=0, column=1, padx=2)
        self.w_entry.bind("<KeyRelease>", lambda e: self.on_dim_entry_change("width"))
        
        tk.Label(dim_layout, text="H:", font=theme.FONT_SMALL, fg=theme.TEXT_MUTED, bg=theme.BG_SIDEBAR).grid(row=0, column=2, padx=2)
        self.h_entry = tk.Entry(dim_layout, width=5)
        theme.style_entry(self.h_entry)
        self.h_entry.grid(row=0, column=3, padx=2)
        self.h_entry.bind("<KeyRelease>", lambda e: self.on_dim_entry_change("height"))
        
        self.aspect_var = tk.BooleanVar(value=True)
        self.aspect_cb = tk.Checkbutton(
            crop_group, text="Lock Aspect Ratio", variable=self.aspect_var, 
            fg=theme.TEXT_PRIMARY, bg=theme.BG_SIDEBAR, selectcolor=theme.BG_MAIN, 
            activebackground=theme.BG_SIDEBAR, activeforeground=theme.TEXT_PRIMARY, font=theme.FONT_SMALL
        )
        self.aspect_cb.pack(anchor="w", pady=(2, 0))
        
        # Section C: Annotate & Draw
        draw_group = tk.LabelFrame(self.sidebar, text="Draw & Annotate", font=theme.FONT_BOLD, fg=theme.TEXT_PRIMARY, bg=theme.BG_SIDEBAR, bd=1, relief="solid", padx=8, pady=6)
        draw_group.configure(highlightbackground=theme.BORDER_COLOR, highlightthickness=0)
        draw_group.pack(fill="x", pady=5)
        
        # Tools selector
        tools_frame1 = tk.Frame(draw_group, bg=theme.BG_SIDEBAR)
        tools_frame1.pack(fill="x", pady=2)
        
        self.btn_brush = tk.Button(tools_frame1, text="🖌 Brush", font=theme.FONT_SMALL, command=lambda: self.select_tool("brush"))
        theme.style_button(self.btn_brush, variant="secondary")
        self.btn_brush.pack(side="left", fill="x", expand=True, padx=(0, 2))
        
        self.btn_arrow = tk.Button(tools_frame1, text="↗ Arrow", font=theme.FONT_SMALL, command=lambda: self.select_tool("arrow"))
        theme.style_button(self.btn_arrow, variant="secondary")
        self.btn_arrow.pack(side="right", fill="x", expand=True, padx=(2, 0))
        
        tools_frame2 = tk.Frame(draw_group, bg=theme.BG_SIDEBAR)
        tools_frame2.pack(fill="x", pady=2)
        
        self.btn_high = tk.Button(tools_frame2, text="🖍 Highlight", font=theme.FONT_SMALL, command=lambda: self.select_tool("highlight"))
        theme.style_button(self.btn_high, variant="secondary")
        self.btn_high.pack(side="left", fill="x", expand=True, padx=(0, 2))
        
        self.btn_redact = tk.Button(tools_frame2, text="⬛ Redact", font=theme.FONT_SMALL, command=lambda: self.select_tool("redact"))
        theme.style_button(self.btn_redact, variant="secondary")
        self.btn_redact.pack(side="right", fill="x", expand=True, padx=(2, 0))
        
        self.tool_buttons = {
            "brush": self.btn_brush,
            "arrow": self.btn_arrow,
            "highlight": self.btn_high,
            "redact": self.btn_redact
        }
        
        # Colors Selection row
        color_frame = tk.Frame(draw_group, bg=theme.BG_SIDEBAR, pady=4)
        color_frame.pack(fill="x")
        
        self.color_buttons = {}
        colors_hex = {
            "red": "#f38ba8",
            "yellow": "#f9e2af",
            "green": "#a6e3a1",
            "blue": "#89b4fa",
            "white": "#ffffff",
            "black": "#11111b"
        }
        
        for name, hex_val in colors_hex.items():
            btn = tk.Button(
                color_frame, text="", bg=hex_val, activebackground=hex_val,
                width=2, height=1, bd=0, cursor="hand2", relief="flat",
                command=lambda h=hex_val: self.select_color(h)
            )
            btn.pack(side="left", padx=2, expand=True)
            self.color_buttons[hex_val] = btn
            
        # Brush size slider
        size_frame = tk.Frame(draw_group, bg=theme.BG_SIDEBAR)
        size_frame.pack(fill="x", pady=(4, 0))
        tk.Label(size_frame, text="Size:", font=theme.FONT_SMALL, fg=theme.TEXT_MUTED, bg=theme.BG_SIDEBAR).pack(side="left")
        
        self.brush_size_slider = tk.Scale(
            size_frame, from_=2, to=20, orient="horizontal",
            fg=theme.TEXT_PRIMARY, bg=theme.BG_SIDEBAR, bd=0, highlightthickness=0,
            troughcolor=theme.BG_MAIN, activebackground=theme.ACCENT_BLUE,
            command=self.on_brush_size_change
        )
        self.brush_size_slider.set(self.draw_size)
        self.brush_size_slider.pack(side="right", fill="x", expand=True, padx=4)
        
        # Clear annotations
        self.clear_draw_btn = tk.Button(draw_group, text="Clear Annotations", command=self.clear_annotations, font=theme.FONT_SMALL)
        theme.style_button(self.clear_draw_btn, variant="secondary")
        self.clear_draw_btn.pack(fill="x", pady=(6, 2))
        
        # Section D: GIF Optimization Settings
        opt_group = tk.LabelFrame(self.sidebar, text="Size Optimization", font=theme.FONT_BOLD, fg=theme.TEXT_PRIMARY, bg=theme.BG_SIDEBAR, bd=1, relief="solid", padx=8, pady=6)
        opt_group.configure(highlightbackground=theme.BORDER_COLOR, highlightthickness=0)
        opt_group.pack(fill="x", pady=5)
        
        # Colors Dropdown
        tk.Label(opt_group, text="Max Colors:", font=theme.FONT_SMALL, fg=theme.TEXT_MUTED, bg=theme.BG_SIDEBAR).pack(anchor="w")
        self.opt_colors_var = tk.StringVar(value="256 Colors")
        opt_colors = ["256 Colors", "128 Colors", "64 Colors", "32 Colors"]
        self.colors_menu = tk.OptionMenu(opt_group, self.opt_colors_var, *opt_colors)
        self.colors_menu.config(bg=theme.BG_CARD, fg=theme.TEXT_PRIMARY, bd=0, highlightthickness=0, font=theme.FONT_SMALL, cursor="hand2")
        self.colors_menu["menu"].config(bg=theme.BG_CARD, fg=theme.TEXT_PRIMARY, font=theme.FONT_SMALL)
        self.colors_menu.pack(fill="x", pady=(2, 6))
        
        # Frame Skipping Dropdown
        tk.Label(opt_group, text="Frame Skipping:", font=theme.FONT_SMALL, fg=theme.TEXT_MUTED, bg=theme.BG_SIDEBAR).pack(anchor="w")
        self.opt_skip_var = tk.StringVar(value="None")
        opt_skips = ["None", "Skip 1 of 2 frames (Even)", "Skip 2 of 3 frames"]
        self.skips_menu = tk.OptionMenu(opt_group, self.opt_skip_var, *opt_skips)
        self.skips_menu.config(bg=theme.BG_CARD, fg=theme.TEXT_PRIMARY, bd=0, highlightthickness=0, font=theme.FONT_SMALL, cursor="hand2")
        self.skips_menu["menu"].config(bg=theme.BG_CARD, fg=theme.TEXT_PRIMARY, font=theme.FONT_SMALL)
        self.skips_menu.pack(fill="x", pady=(2, 2))
        
        # Action Buttons Panel (Save / Copy)
        action_panel = tk.Frame(self.sidebar, bg=theme.BG_SIDEBAR)
        action_panel.pack(side="bottom", fill="x", pady=(15, 0))
        
        self.save_btn = tk.Button(action_panel, text="💾 Save GIF...", command=self.save_gif)
        theme.style_button(self.save_btn, variant="success")
        self.save_btn.pack(fill="x", ipady=2, pady=(0, 4))
        
        self.copy_btn = tk.Button(action_panel, text="📋 Copy to Clipboard", command=self.copy_to_clipboard)
        theme.style_button(self.copy_btn, variant="primary")
        self.copy_btn.pack(fill="x", ipady=2)
        
        # --- Workspace Widgets ---
        # 1. Preview Container
        self.preview_frame = tk.Frame(self.workspace, bg=theme.BG_MAIN, bd=1, relief="solid")
        self.preview_frame.configure(highlightbackground=theme.BORDER_COLOR, highlightthickness=0)
        self.preview_frame.pack(fill="both", expand=True)
        
        self.canvas = tk.Canvas(self.preview_frame, bg=theme.BG_MAIN, bd=0, highlightthickness=0)
        self.canvas.pack(expand=True)
        
        # Mouse event binds for both cropping and drawing
        self.canvas.bind("<Button-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Motion>", self.on_canvas_hover)
        
        # 2. Playback Control Bar
        self.control_bar = tk.Frame(self.workspace, bg=theme.BG_MAIN, pady=6)
        self.control_bar.pack(fill="x")
        
        self.play_btn = tk.Button(self.control_bar, text="⏸ Pause", command=self.toggle_play, width=9)
        theme.style_button(self.play_btn, variant="secondary")
        self.play_btn.pack(side="left", padx=3)
        
        self.prev_btn = tk.Button(self.control_bar, text="⏮ Step", command=self.step_prev)
        theme.style_button(self.prev_btn, variant="secondary")
        self.prev_btn.pack(side="left", padx=3)
        
        self.next_btn = tk.Button(self.control_bar, text="Step ⏭", command=self.step_next)
        theme.style_button(self.next_btn, variant="secondary")
        self.next_btn.pack(side="left", padx=3)
        
        self.reset_btn = tk.Button(self.control_bar, text="🔄 Revert All", command=self.reset_edits)
        theme.style_button(self.reset_btn, variant="secondary")
        self.reset_btn.pack(side="right", padx=3)
        
        self.frame_lbl = tk.Label(self.control_bar, text="Frame: 0 / 0", font=theme.FONT_BOLD, fg=theme.TEXT_PRIMARY, bg=theme.BG_MAIN)
        self.frame_lbl.pack(side="right", padx=10)
        
        # 3. Timeline Slider Widget
        slider_frame = tk.Frame(self.workspace, bg=theme.BG_MAIN)
        slider_frame.pack(fill="x", pady=(2, 0))
        
        self.range_slider = RangeSlider(
            slider_frame, 
            val_min=0, 
            val_max=self.num_frames - 1, 
            height=35,
            on_change_callback=self.on_trim_change
        )
        self.range_slider.pack(fill="x")
        
        # Initialize display labels
        self.update_trim_labels()
        self.reset_dimension_entries()

    # --- Tool & Color Selector Handlers ---
    def select_tool(self, tool_name):
        # Clear crop mode if active
        if self.crop_mode:
            self.toggle_crop_mode()
            
        if self.draw_tool == tool_name:
            # Toggle off
            self.draw_tool = None
            self.canvas.config(cursor="")
        else:
            self.draw_tool = tool_name
            if tool_name == "brush":
                self.canvas.config(cursor="pencil")
            else:
                self.canvas.config(cursor="crosshair")
                
        # Highlight active button visually
        for name, btn in self.tool_buttons.items():
            if name == self.draw_tool:
                theme.style_button(btn, variant="success")
            else:
                theme.style_button(btn, variant="secondary")

    def select_color(self, hex_val):
        self.draw_color = hex_val
        for val, btn in self.color_buttons.items():
            if val == hex_val:
                btn.config(text="✓", fg="#11111b" if hex_val != "#11111b" else "#ffffff", font=theme.FONT_BOLD)
            else:
                btn.config(text="")

    def on_brush_size_change(self, value):
        self.draw_size = int(value)

    def clear_annotations(self):
        if self.annotations:
            if messagebox.askyesno("Clear Drawings", "Clear all drawings and annotations?"):
                self.annotations = []
                self.render_current_frame()

    # --- UI Status Info Helpers ---
    def update_trim_labels(self):
        duration = (self.end_frame - self.start_frame + 1) / self.fps
        text = f"Frame Range: {self.start_frame} - {self.end_frame}\nTotal frames: {self.end_frame - self.start_frame + 1}\nDuration: {duration:.2f}s"
        self.trim_info_lbl.config(text=text)

    def reset_dimension_entries(self):
        curr_w, curr_h = self.frames[0].size
        self.w_entry.delete(0, "end")
        self.w_entry.insert(0, str(int(curr_w * self.scale_factor)))
        self.h_entry.delete(0, "end")
        self.h_entry.insert(0, str(int(curr_h * self.scale_factor)))

    # --- Playback Logic ---
    def toggle_play(self):
        self.is_playing = not self.is_playing
        self.play_btn.config(text="⏸ Pause" if self.is_playing else "▶ Play")

    def step_prev(self):
        self.is_playing = False
        self.play_btn.config(text="▶ Play")
        self.current_frame_idx -= 1
        if self.current_frame_idx < self.start_frame:
            self.current_frame_idx = self.end_frame
        self.render_current_frame()

    def step_next(self):
        self.is_playing = False
        self.play_btn.config(text="▶ Play")
        self.current_frame_idx += 1
        if self.current_frame_idx > self.end_frame:
            self.current_frame_idx = self.start_frame
        self.render_current_frame()

    def on_trim_change(self, left, right):
        self.start_frame = left
        self.end_frame = right
        
        if self.current_frame_idx < self.start_frame or self.current_frame_idx > self.end_frame:
            self.current_frame_idx = self.start_frame
            
        self.update_trim_labels()
        self.render_current_frame()

    # --- Screen Sizing & Rendering ---
    def update_preview_size(self):
        img_w, img_h = self.frames[0].size
        w_ratio = self.preview_max_w / img_w
        h_ratio = self.preview_max_h / img_h
        self.preview_scale = min(w_ratio, h_ratio, 1.0)
        
        self.canvas_w = int(img_w * self.preview_scale)
        self.canvas_h = int(img_h * self.preview_scale)
        
        self.canvas.config(width=self.canvas_w, height=self.canvas_h)
        if not self.crop_mode:
            self.crop_prev_box = [4, 4, self.canvas_w - 4, self.canvas_h - 4]

    def render_current_frame(self):
        if not self.frames:
            return
            
        # Get raw background frame
        frame = self.frames[self.current_frame_idx]
        
        # 1. Apply drawing annotations directly on the high-resolution copy of PIL image
        active_shape = None
        if self.current_points:
            if self.draw_tool == "brush":
                active_shape = {"type": "brush", "points": self.current_points, "color": self.draw_color, "size": self.draw_size}
            elif self.draw_tool == "arrow" and len(self.current_points) > 1:
                active_shape = {"type": "arrow", "start": self.current_points[0], "end": self.current_points[1], "color": self.draw_color, "size": self.draw_size}
            elif self.draw_tool == "highlight" and len(self.current_points) > 1:
                start = self.current_points[0]
                end = self.current_points[1]
                active_shape = {
                    "type": "highlight",
                    "rect": (min(start[0], end[0]), min(start[1], end[1]), max(start[0], end[0]), max(start[1], end[1])),
                    "color": self.draw_color,
                    "size": self.draw_size
                }
            elif self.draw_tool == "redact" and len(self.current_points) > 1:
                start = self.current_points[0]
                end = self.current_points[1]
                active_shape = {
                    "type": "redact",
                    "rect": (min(start[0], end[0]), min(start[1], end[1]), max(start[0], end[0]), max(start[1], end[1]))
                }
                
        annotated_frame = apply_annotations(frame, self.annotations, active_shape)
        
        # 2. Resize the annotated image for canvas preview
        prev_w = int(annotated_frame.width * self.preview_scale)
        prev_h = int(annotated_frame.height * self.preview_scale)
        preview_img = annotated_frame.resize((prev_w, prev_h), Image.Resampling.NEAREST)
        
        self.photo = ImageTk.PhotoImage(preview_img)
        
        self.canvas.delete("all")
        self.canvas.create_image(self.canvas_w // 2, self.canvas_h // 2, image=self.photo)
        self.frame_lbl.config(text=f"Frame: {self.current_frame_idx} / {self.end_frame}")
        
        # 3. Draw crop overlay outline strictly on top (in vector space) if crop mode is enabled
        if self.crop_mode:
            self.draw_crop_ui()

    def animate_loop(self):
        if self.window.winfo_exists():
            if self.is_playing:
                self.current_frame_idx += 1
                if self.current_frame_idx > self.end_frame or self.current_frame_idx < self.start_frame:
                    self.current_frame_idx = self.start_frame
                self.render_current_frame()
                
            delay_ms = int(1000 / self.fps)
            self.window.after(delay_ms, self.animate_loop)

    # --- Sizing Entries Handlers ---
    def on_dim_entry_change(self, field):
        try:
            curr_w, curr_h = self.frames[0].size
            if field == "width":
                w_val = self.w_entry.get()
                if w_val.isdigit():
                    w = int(w_val)
                    self.scale_factor = w / curr_w
                    if self.lock_aspect_ratio:
                        h = int(curr_h * self.scale_factor)
                        self.h_entry.delete(0, "end")
                        self.h_entry.insert(0, str(h))
            else:
                h_val = self.h_entry.get()
                if h_val.isdigit():
                    h = int(h_val)
                    self.scale_factor = h / curr_h
                    if self.lock_aspect_ratio:
                        w = int(curr_w * self.scale_factor)
                        self.w_entry.delete(0, "end")
                        self.w_entry.insert(0, str(w))
        except Exception:
            pass

    # --- Mouse Event Router (Crop vs. Draw) ---
    def on_canvas_press(self, event):
        # Map canvas coordinate to original full resolution image coordinate
        orig_x = int(event.x / self.preview_scale)
        orig_y = int(event.y / self.preview_scale)
        
        orig_x = max(0, min(self.orig_w, orig_x))
        orig_y = max(0, min(self.orig_h, orig_y))
        
        if self.crop_mode:
            self.on_crop_press(event)
        elif self.draw_tool:
            # Pause player while drawing
            self.is_playing = False
            self.play_btn.config(text="▶ Play")
            
            if self.draw_tool == "brush":
                self.current_points = [(orig_x, orig_y)]
            else:
                self.current_points = [(orig_x, orig_y), (orig_x, orig_y)]
            self.render_current_frame()

    def on_canvas_drag(self, event):
        orig_x = int(event.x / self.preview_scale)
        orig_y = int(event.y / self.preview_scale)
        
        orig_x = max(0, min(self.orig_w, orig_x))
        orig_y = max(0, min(self.orig_h, orig_y))
        
        if self.crop_mode:
            self.on_crop_drag(event)
        elif self.draw_tool and self.current_points:
            if self.draw_tool == "brush":
                # Only add point if it's different from the last point to optimize
                if (orig_x, orig_y) != self.current_points[-1]:
                    self.current_points.append((orig_x, orig_y))
            else:
                # Update endpoint coordinates
                self.current_points[1] = (orig_x, orig_y)
            self.render_current_frame()

    def on_canvas_release(self, event):
        if self.crop_mode:
            self.on_crop_release(event)
        elif self.draw_tool and self.current_points:
            orig_x = int(event.x / self.preview_scale)
            orig_y = int(event.y / self.preview_scale)
            orig_x = max(0, min(self.orig_w, orig_x))
            orig_y = max(0, min(self.orig_h, orig_y))
            
            if self.draw_tool == "brush":
                if len(self.current_points) > 1:
                    self.annotations.append({
                        "type": "brush",
                        "points": self.current_points,
                        "color": self.draw_color,
                        "size": self.draw_size
                    })
            elif self.draw_tool == "arrow":
                start = self.current_points[0]
                end = (orig_x, orig_y)
                if start != end:
                    self.annotations.append({
                        "type": "arrow",
                        "start": start,
                        "end": end,
                        "color": self.draw_color,
                        "size": self.draw_size
                    })
            elif self.draw_tool == "highlight":
                start = self.current_points[0]
                end = (orig_x, orig_y)
                x1, y1 = min(start[0], end[0]), min(start[1], end[1])
                x2, y2 = max(start[0], end[0]), max(start[1], end[1])
                if x2 - x1 > 2 and y2 - y1 > 2:
                    self.annotations.append({
                        "type": "highlight",
                        "rect": (x1, y1, x2, y2),
                        "color": self.draw_color
                    })
            elif self.draw_tool == "redact":
                start = self.current_points[0]
                end = (orig_x, orig_y)
                x1, y1 = min(start[0], end[0]), min(start[1], end[1])
                x2, y2 = max(start[0], end[0]), max(start[1], end[1])
                if x2 - x1 > 2 and y2 - y1 > 2:
                    self.annotations.append({
                        "type": "redact",
                        "rect": (x1, y1, x2, y2)
                    })
                    
            self.current_points = None
            self.render_current_frame()

    def on_canvas_hover(self, event):
        if self.crop_mode:
            self.on_crop_hover(event)

    # --- Spatial Crop Logic ---
    def toggle_crop_mode(self):
        self.crop_mode = not self.crop_mode
        if self.crop_mode:
            # Disable drawing tool
            if self.draw_tool:
                self.select_tool(self.draw_tool) # Toggle off
            self.is_playing = False
            self.play_btn.config(text="▶ Play")
            self.crop_btn.config(text="Disable Crop")
            self.crop_prev_box = [4, 4, self.canvas_w - 4, self.canvas_h - 4]
            self.apply_crop_btn.config(state="normal")
            self.canvas.config(cursor="arrow")
        else:
            self.crop_btn.config(text="Crop Box")
            self.apply_crop_btn.config(state="disabled")
            self.canvas.config(cursor="")
            
        self.render_current_frame()

    def draw_crop_ui(self):
        cx1, cy1, cx2, cy2 = self.crop_prev_box
        self.canvas.create_rectangle(0, 0, self.canvas_w, cy1, fill="black", stipple="gray50", borderwidth=0)
        self.canvas.create_rectangle(0, cy2, self.canvas_w, self.canvas_h, fill="black", stipple="gray50", borderwidth=0)
        self.canvas.create_rectangle(0, cy1, cx1, cy2, fill="black", stipple="gray50", borderwidth=0)
        self.canvas.create_rectangle(cx2, cy1, self.canvas_w, cy2, fill="black", stipple="gray50", borderwidth=0)
        
        self.canvas.create_rectangle(cx1, cy1, cx2, cy2, outline=theme.ACCENT_MAUVE, width=2, dash=(4, 4))
        
        handles = self.get_crop_handles()
        for name, (hx, hy) in handles.items():
            self.canvas.create_rectangle(
                hx - 5, hy - 5, hx + 5, hy + 5,
                fill=theme.ACCENT_GREEN, outline=theme.BG_SIDEBAR, width=1
            )
            
        w_orig = int((cx2 - cx1) / self.preview_scale)
        h_orig = int((cy2 - cy1) / self.preview_scale)
        self.canvas.create_text(
            cx1 + 5, cy1 + 15, text=f"{w_orig} x {h_orig}",
            fill=theme.TEXT_PRIMARY, font=theme.FONT_BOLD, anchor="w",
            bbox=dict(fill=theme.BG_SIDEBAR, outline=theme.BORDER_COLOR, boxstyle="round,pad=0.2")
        )

    def get_crop_handles(self):
        cx1, cy1, cx2, cy2 = self.crop_prev_box
        mx = cx1 + (cx2 - cx1) / 2
        my = cy1 + (cy2 - cy1) / 2
        return {
            "nw": (cx1, cy1), "n": (mx, cy1), "ne": (cx2, cy1),
            "e": (cx2, my), "se": (cx2, cy2), "s": (mx, cy2),
            "sw": (cx1, cy2), "w": (cx1, my)
        }

    def on_crop_hover(self, event):
        handles = self.get_crop_handles()
        found = False
        for name, (hx, hy) in handles.items():
            if abs(event.x - hx) < 8 and abs(event.y - hy) < 8:
                if name in ["nw", "se"]: self.canvas.config(cursor="size_nw_se")
                elif name in ["ne", "sw"]: self.canvas.config(cursor="size_ne_sw")
                elif name in ["n", "s"]: self.canvas.config(cursor="size_ns")
                elif name in ["e", "w"]: self.canvas.config(cursor="size_we")
                found = True
                break
        if not found:
            self.canvas.config(cursor="arrow")

    def on_crop_press(self, event):
        handles = self.get_crop_handles()
        self.active_crop_handle = None
        for name, (hx, hy) in handles.items():
            if abs(event.x - hx) < 10 and abs(event.y - hy) < 10:
                self.active_crop_handle = name
                break

    def on_crop_drag(self, event):
        if not self.active_crop_handle:
            return
        cx1, cy1, cx2, cy2 = self.crop_prev_box
        mx = max(0, min(self.canvas_w, event.x))
        my = max(0, min(self.canvas_h, event.y))
        min_size = 20
        
        if self.active_crop_handle == "nw":
            cx1, cy1 = min(mx, cx2 - min_size), min(my, cy2 - min_size)
        elif self.active_crop_handle == "ne":
            cx2, cy1 = max(mx, cx1 + min_size), min(my, cy2 - min_size)
        elif self.active_crop_handle == "se":
            cx2, cy2 = max(mx, cx1 + min_size), max(my, cy1 + min_size)
        elif self.active_crop_handle == "sw":
            cx1, cy2 = min(mx, cx2 - min_size), max(my, cy1 + min_size)
        elif self.active_crop_handle == "n": cy1 = min(my, cy2 - min_size)
        elif self.active_crop_handle == "s": cy2 = max(my, cy1 + min_size)
        elif self.active_crop_handle == "e": cx2 = max(mx, cx1 + min_size)
        elif self.active_crop_handle == "w": cx1 = min(mx, cx2 - min_size)
            
        self.crop_prev_box = [cx1, cy1, cx2, cy2]
        self.render_current_frame()

    def on_crop_release(self, event):
        self.active_crop_handle = None

    def apply_crop(self):
        cx1, cy1, cx2, cy2 = self.crop_prev_box
        orig_x1 = int(cx1 / self.preview_scale)
        orig_y1 = int(cy1 / self.preview_scale)
        orig_x2 = int(cx2 / self.preview_scale)
        orig_y2 = int(cy2 / self.preview_scale)
        
        w, h = orig_x2 - orig_x1, orig_y2 - orig_y1
        if w <= 10 or h <= 10:
            return
            
        # Crop frames in memory
        self.frames = [f.crop((orig_x1, orig_y1, orig_x2, orig_y2)) for f in self.frames]
        
        # Shift drawing annotation positions accordingly to keep them aligned
        for shape in self.annotations:
            t = shape["type"]
            if t == "brush":
                shape["points"] = [(x - orig_x1, y - orig_y1) for x, y in shape["points"]]
            elif t == "arrow":
                shape["start"] = (shape["start"][0] - orig_x1, shape["start"][1] - orig_y1)
                shape["end"] = (shape["end"][0] - orig_x1, shape["end"][1] - orig_y1)
            elif t in ["highlight", "redact"]:
                x1, y1, x2, y2 = shape["rect"]
                shape["rect"] = (x1 - orig_x1, y1 - orig_y1, x2 - orig_x1, y2 - orig_y1)
                
        self.crop_mode = False
        self.crop_btn.config(text="Crop Box")
        self.apply_crop_btn.config(state="disabled")
        self.canvas.config(cursor="")
        
        self.orig_w, self.orig_h = self.frames[0].size
        self.update_preview_size()
        self.reset_dimension_entries()
        self.render_current_frame()

    # --- Revert Edits ---
    def reset_edits(self):
        if messagebox.askyesno("Reset Edits", "Are you sure you want to revert all crop, resize, trimming, and drawing changes?"):
            self.frames = self.original_frames.copy()
            self.num_frames = len(self.frames)
            self.start_frame = 0
            self.end_frame = self.num_frames - 1
            self.current_frame_idx = 0
            self.scale_factor = 1.0
            self.annotations = []
            
            # Turn off drawing tool & crop
            if self.draw_tool:
                self.select_tool(self.draw_tool)
            self.crop_mode = False
            self.crop_btn.config(text="Crop Box")
            self.apply_crop_btn.config(state="disabled")
            
            self.range_slider.val_max = self.num_frames - 1
            self.range_slider.set_range(0, self.num_frames - 1)
            
            self.orig_w, self.orig_h = self.frames[0].size
            self.update_preview_size()
            self.reset_dimension_entries()
            self.update_trim_labels()
            self.render_current_frame()

    # --- Exporter Compiler Logic (Applies all filters) ---
    def compile_processed_frames(self):
        """
        Applies frame-skipping, drawings annotations, resizing, and color quantization.
        Returns a list of quantized frames and the correct frame delay in ms.
        """
        # 1. Frame Skipping
        skip_mode = self.opt_skip_var.get()
        step = 1
        delay_mult = 1
        if "Skip 1 of 2" in skip_mode:
            step = 2
            delay_mult = 2
        elif "Skip 2 of 3" in skip_mode:
            step = 3
            delay_mult = 3
            
        range_frames = self.frames[self.start_frame : self.end_frame + 1]
        skipped = range_frames[::step]
        
        # 2. Colors limit
        num_colors_map = {"256 Colors": 256, "128 Colors": 128, "64 Colors": 64, "32 Colors": 32}
        color_limit = num_colors_map.get(self.opt_colors_var.get(), 256)
        
        processed = []
        for frame in skipped:
            # Apply drawing layers
            annotated = apply_annotations(frame, self.annotations)
            
            # Apply spatial scaling
            if abs(self.scale_factor - 1.0) > 0.01:
                new_w = max(1, int(annotated.width * self.scale_factor))
                new_h = max(1, int(annotated.height * self.scale_factor))
                annotated = annotated.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
            # Quantize color palette
            quantized = annotated.quantize(colors=color_limit, method=Image.Quantize.FASTOCTREE)
            processed.append(quantized)
            
        delay_ms = int((1000 / self.fps) * delay_mult)
        return processed, delay_ms

    # --- Save to Disk ---
    def save_gif(self):
        self.is_playing = False
        self.play_btn.config(text="▶ Play")
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".gif",
            filetypes=[("GIF Image", "*.gif")],
            title="Save Animated GIF"
        )
        if not filename:
            return
            
        # Draw progress popup
        progress_win = tk.Toplevel(self.window)
        progress_win.title("Saving...")
        progress_win.geometry("300x100")
        progress_win.configure(bg=theme.BG_MAIN)
        progress_win.attributes("-topmost", True)
        progress_win.transient(self.window)
        
        label = tk.Label(progress_win, text="Compiling & optimizing GIF...", fg=theme.TEXT_PRIMARY, bg=theme.BG_MAIN, font=theme.FONT_BODY)
        label.pack(pady=25)
        progress_win.update()
        
        def save_task():
            try:
                output_frames, delay = self.compile_processed_frames()
                if not output_frames:
                    raise Exception("No frames generated.")
                    
                output_frames[0].save(
                    filename,
                    save_all=True,
                    append_images=output_frames[1:],
                    duration=delay,
                    loop=0,
                    optimize=True
                )
                self.window.after(0, lambda: self.on_save_success(progress_win, filename))
            except Exception as e:
                self.window.after(0, lambda: self.on_save_fail(progress_win, str(e)))
                
        threading.Thread(target=save_task, daemon=True).start()

    def on_save_success(self, progress_win, path):
        progress_win.destroy()
        messagebox.showinfo("Success", f"GIF successfully saved:\n{os.path.basename(path)}")
        self.window.destroy()

    def on_save_fail(self, progress_win, error_msg):
        progress_win.destroy()
        messagebox.showerror("Error", f"Failed to save GIF:\n{error_msg}")

    # --- Copy to Windows Clipboard ---
    def copy_to_clipboard(self):
        self.is_playing = False
        self.play_btn.config(text="▶ Play")
        
        # Compile to a temporary file in script directory
        temp_dir = os.path.dirname(os.path.abspath(__file__))
        temp_path = os.path.join(temp_dir, "temp_clipboard.gif")
        
        # Draw progress popup
        progress_win = tk.Toplevel(self.window)
        progress_win.title("Copying...")
        progress_win.geometry("300x100")
        progress_win.configure(bg=theme.BG_MAIN)
        progress_win.attributes("-topmost", True)
        progress_win.transient(self.window)
        
        label = tk.Label(progress_win, text="Rendering GIF to clipboard...", fg=theme.TEXT_PRIMARY, bg=theme.BG_MAIN, font=theme.FONT_BODY)
        label.pack(pady=25)
        progress_win.update()
        
        def copy_task():
            try:
                output_frames, delay = self.compile_processed_frames()
                if not output_frames:
                    raise Exception("No frames generated.")
                    
                # Save temp file
                output_frames[0].save(
                    temp_path,
                    save_all=True,
                    append_images=output_frames[1:],
                    duration=delay,
                    loop=0,
                    optimize=True
                )
                
                # Copy file path to Windows Clipboard using PowerShell file-drop format (CF_HDROP)
                abs_path = os.path.abspath(temp_path).replace('/', '\\')
                cmd = ["powershell", "-NoProfile", "-Command", f"Set-Clipboard -Path '{abs_path}'"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.window.after(0, lambda: self.on_copy_success(progress_win))
                else:
                    raise Exception(result.stderr)
            except Exception as e:
                self.window.after(0, lambda: self.on_copy_fail(progress_win, str(e)))
                
        threading.Thread(target=copy_task, daemon=True).start()

    def on_copy_success(self, progress_win):
        progress_win.destroy()
        messagebox.showinfo("Clipboard Copied", "GIF successfully copied to clipboard!\nYou can now paste (Ctrl+V) directly into chat apps (Discord, Slack, Teams) or Explorer folders.")

    def on_copy_fail(self, progress_win, error_msg):
        progress_win.destroy()
        messagebox.showerror("Clipboard Copy Failed", f"Failed to copy to clipboard:\n{error_msg}")

    def on_close(self):
        if messagebox.askyesno("Exit Editor", "Discard this recording and exit?"):
            # Clean up temp file if it exists
            temp_dir = os.path.dirname(os.path.abspath(__file__))
            temp_path = os.path.join(temp_dir, "temp_clipboard.gif")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            self.window.destroy()
