# recorder.py
# Handles the GIF screen recording loop, flashing red border, and global ESC hook.

import tkinter as tk
import time
import threading
from PIL import ImageGrab
from pynput import keyboard
import theme

class BorderOverlay:
    """
    Creates a transparent window that draws a pulsing red border around the recording bbox.
    It is click-through, allowing interaction with windows inside the region.
    """
    def __init__(self, parent, bbox):
        self.parent = parent
        self.x1, self.y1, self.x2, self.y2 = bbox
        self.w = self.x2 - self.x1
        self.h = self.y2 - self.y1
        
        self.window = tk.Toplevel(self.parent)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        
        # Position slightly offset to frame the selection area
        self.window.geometry(f"{self.w+4}x{self.h+4}+{self.x1-2}+{self.y1-2}")
        
        # Make window transparent in Windows
        self.window.config(bg="black")
        self.window.attributes("-transparentcolor", "black")
        
        self.canvas = tk.Canvas(self.window, bg="black", highlightthickness=0, width=self.w+4, height=self.h+4)
        self.canvas.pack(fill="both", expand=True)
        
        # Red rectangle
        self.rect = self.canvas.create_rectangle(1, 1, self.w+3, self.h+3, outline=theme.ACCENT_RED, width=2)
        
        self.visible = True
        self.flash()

    def flash(self):
        if not self.window.winfo_exists():
            return
        # Toggle border outline between red and black (transparent) to create a flashing effect
        self.visible = not self.visible
        color = theme.ACCENT_RED if self.visible else "black"
        self.canvas.itemconfig(self.rect, outline=color)
        self.window.after(500, self.flash)

    def destroy(self):
        try:
            self.window.destroy()
        except Exception:
            pass


class RecordingControlPanel:
    """
    A small floating draggable control panel showing elapsed time, frame count, and a stop button.
    """
    def __init__(self, parent, bbox, on_stop_callback):
        self.parent = parent
        self.on_stop = on_stop_callback
        self.x1, self.y1, self.x2, self.y2 = bbox
        
        self.window = tk.Toplevel(self.parent)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg=theme.BG_SIDEBAR)
        
        # Determine floating window position: centered below bbox, or above if no space
        panel_w, panel_h = 240, 42
        pos_x = self.x1 + (self.x2 - self.x1) // 2 - panel_w // 2
        
        # Screen constraints
        screen_h = self.window.winfo_screenheight()
        if self.y2 + 60 > screen_h:
            pos_y = self.y1 - panel_h - 10 # Place above
        else:
            pos_y = self.y2 + 10 # Place below
            
        # Fallback to avoid going off screen
        if pos_y < 0:
            pos_y = 10
            
        self.window.geometry(f"{panel_w}x{panel_h}+{pos_x}+{pos_y}")
        
        # Set border
        self.window.config(highlightbackground=theme.BORDER_COLOR, highlightcolor=theme.ACCENT_BLUE, highlightthickness=1)
        
        # Draggable logic
        self.window.bind("<Button-1>", self.on_drag_start)
        self.window.bind("<B1-Motion>", self.on_drag_motion)
        
        # Widgets
        self.status_label = tk.Label(
            self.window, 
            text="🔴 0.0s (0 frames)", 
            fg=theme.TEXT_PRIMARY, 
            bg=theme.BG_SIDEBAR, 
            font=theme.FONT_BOLD
        )
        self.status_label.pack(side="left", padx=(12, 6))
        # Keep labels draggable too
        self.status_label.bind("<Button-1>", self.on_drag_start)
        self.status_label.bind("<B1-Motion>", self.on_drag_motion)
        
        self.stop_btn = tk.Button(
            self.window, 
            text="Stop [ESC]", 
            command=self.on_stop,
            font=theme.FONT_SMALL
        )
        theme.style_button(self.stop_btn, variant="danger")
        self.stop_btn.pack(side="right", padx=(6, 12), pady=6)

    def update(self, elapsed, frame_count):
        if self.window.winfo_exists():
            self.status_label.config(text=f"🔴 {elapsed:.1f}s ({frame_count} frames)")

    def on_drag_start(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def on_drag_motion(self, event):
        x = self.window.winfo_x() - self._drag_x + event.x
        y = self.window.winfo_y() - self._drag_y + event.y
        self.window.geometry(f"+{x}+{y}")

    def destroy(self):
        try:
            self.window.destroy()
        except Exception:
            pass


class GifRecorder:
    def __init__(self, parent, bbox, fps=10, countdown_seconds=0, on_done_callback=None):
        self.parent = parent
        self.bbox = bbox
        self.fps = fps
        self.delay = 1.0 / fps
        self.countdown_seconds = countdown_seconds
        self.on_done = on_done_callback
        
        self.frames = []
        self.is_recording = False
        self.start_time = None
        
        self.border_overlay = None
        self.control_panel = None
        self.listener = None
        
        # Start recording sequence
        if self.countdown_seconds > 0:
            self.run_countdown(self.countdown_seconds)
        else:
            self.start_recording()

    def run_countdown(self, seconds_left):
        """
        Creates a temporary large fullscreen text overlay showing a centered 3..2..1 countdown.
        """
        countdown_win = tk.Toplevel(self.parent)
        countdown_win.overrideredirect(True)
        countdown_win.attributes("-topmost", True)
        
        # Center in the selection area
        x1, y1, x2, y2 = self.bbox
        w, h = x2 - x1, y2 - y1
        countdown_win.geometry(f"{w}x{h}+{x1}+{y1}")
        
        # Make transparent background
        countdown_win.config(bg="black")
        countdown_win.attributes("-transparentcolor", "black")
        
        label = tk.Label(
            countdown_win, 
            text=str(seconds_left), 
            font=("Segoe UI", 48, "bold"), 
            fg=theme.ACCENT_BLUE, 
            bg="black"
        )
        label.pack(expand=True)
        
        def tick(sec):
            if sec > 0:
                label.config(text=str(sec))
                countdown_win.after(1000, lambda: tick(sec - 1))
            else:
                countdown_win.destroy()
                self.start_recording()
                
        countdown_win.after(1000, lambda: tick(seconds_left - 1))

    def start_recording(self):
        self.is_recording = True
        self.frames = []
        self.start_time = time.time()
        
        # 1. Create flashing red border overlay
        self.border_overlay = BorderOverlay(self.parent, self.bbox)
        
        # 2. Create floating control panel
        self.control_panel = RecordingControlPanel(self.parent, self.bbox, self.stop_recording)
        
        # 3. Start keyboard listener for Escape key (runs globally in background)
        def on_press(key):
            if key == keyboard.Key.esc:
                # Stop recording (must run safely on main thread via parent.after)
                self.parent.after(0, self.stop_recording)
                return False
                
        self.listener = keyboard.Listener(on_press=on_press)
        self.listener.start()
        
        # 4. Start recording thread
        self.record_thread = threading.Thread(target=self.record_loop, daemon=True)
        self.record_thread.start()
        
        # 5. Start control panel UI updates
        self.update_ui_loop()

    def record_loop(self):
        next_time = time.time()
        while self.is_recording:
            # Capture frame
            try:
                frame = ImageGrab.grab(bbox=self.bbox)
                self.frames.append(frame)
            except Exception as e:
                print(f"Error capturing frame: {e}")
                
            next_time += self.delay
            sleep_time = next_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                time.sleep(0.001) # Lag recovery

    def update_ui_loop(self):
        if self.is_recording and self.control_panel:
            elapsed = time.time() - self.start_time
            num_frames = len(self.frames)
            self.control_panel.update(elapsed, num_frames)
            self.parent.after(100, self.update_ui_loop)

    def stop_recording(self):
        if not self.is_recording:
            return
        
        self.is_recording = False
        
        # Clean up listeners and overlays
        if self.listener:
            self.listener.stop()
        if self.border_overlay:
            self.border_overlay.destroy()
        if self.control_panel:
            self.control_panel.destroy()
            
        # Call completion callback with the frames
        if self.on_done:
            self.on_done(self.frames)
