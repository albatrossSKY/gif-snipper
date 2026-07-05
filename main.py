# main.py
# Entry point for the GIF Snipper application. Displays the control dashboard.

import tkinter as tk
import theme
from capture_overlay import CaptureOverlay
from recorder import GifRecorder
from editor import EditorWindow
import ctypes

# Enable DPI awareness on Windows so coordinate systems align perfectly
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

class GifSnipperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GIF Snipper")
        self.root.geometry("460x300")
        self.root.resizable(False, False)
        
        # Configure window theme
        theme.style_window(self.root)
        
        # UI variables
        self.fps_var = tk.StringVar(value="12")
        self.countdown_var = tk.StringVar(value="None")
        
        self.create_widgets()

    def create_widgets(self):
        # Master padding container
        main_frame = tk.Frame(self.root, bg=theme.BG_MAIN, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # App Title
        title_lbl = tk.Label(main_frame, text="🎬 GIF SNIPPER", font=theme.FONT_TITLE, fg=theme.ACCENT_BLUE, bg=theme.BG_MAIN)
        title_lbl.pack(anchor="w", pady=(0, 2))
        
        subtitle_lbl = tk.Label(main_frame, text="Capture screen regions directly to animated GIFs", font=theme.FONT_SMALL, fg=theme.TEXT_MUTED, bg=theme.BG_MAIN)
        subtitle_lbl.pack(anchor="w", pady=(0, 20))
        
        # Settings Grid
        settings_frame = tk.Frame(main_frame, bg=theme.BG_MAIN)
        settings_frame.pack(fill="x", pady=10)
        
        # 1. FPS Settings
        fps_lbl = tk.Label(settings_frame, text="Target Frame Rate (FPS):", font=theme.FONT_BOLD, fg=theme.TEXT_PRIMARY, bg=theme.BG_MAIN)
        fps_lbl.grid(row=0, column=0, sticky="w", pady=6, padx=(0, 10))
        
        fps_options = ["5", "10", "12", "15", "20", "24"]
        fps_menu = tk.OptionMenu(settings_frame, self.fps_var, *fps_options)
        fps_menu.config(bg=theme.BG_CARD, fg=theme.TEXT_PRIMARY, bd=0, highlightthickness=0, font=theme.FONT_BODY, width=8, cursor="hand2")
        fps_menu["menu"].config(bg=theme.BG_CARD, fg=theme.TEXT_PRIMARY, font=theme.FONT_BODY)
        fps_menu.grid(row=0, column=1, sticky="w", pady=6)
        
        # 2. Countdown Settings
        countdown_lbl = tk.Label(settings_frame, text="Delay Before Recording:", font=theme.FONT_BOLD, fg=theme.TEXT_PRIMARY, bg=theme.BG_MAIN)
        countdown_lbl.grid(row=1, column=0, sticky="w", pady=6, padx=(0, 10))
        
        countdown_options = ["None", "2 Seconds", "5 Seconds"]
        countdown_menu = tk.OptionMenu(settings_frame, self.countdown_var, *countdown_options)
        countdown_menu.config(bg=theme.BG_CARD, fg=theme.TEXT_PRIMARY, bd=0, highlightthickness=0, font=theme.FONT_BODY, width=8, cursor="hand2")
        countdown_menu["menu"].config(bg=theme.BG_CARD, fg=theme.TEXT_PRIMARY, font=theme.FONT_BODY)
        countdown_menu.grid(row=1, column=1, sticky="w", pady=6)
        
        # Separation line
        sep = tk.Frame(main_frame, height=1, bg=theme.BORDER_COLOR)
        sep.pack(fill="x", pady=15)
        
        # Big Snipping/Recording Action button
        self.record_btn = tk.Button(main_frame, text="✂ New Snip / Record GIF", command=self.start_snip_selection)
        theme.style_button(self.record_btn, variant="danger")
        self.record_btn.pack(fill="x", ipady=6)
        
        # Help footer info
        info_lbl = tk.Label(main_frame, text="Drag a region to snip. Press ESC globally to stop recording and edit.", font=theme.FONT_SMALL, fg=theme.TEXT_MUTED, bg=theme.BG_MAIN)
        info_lbl.pack(pady=(12, 0))

    def start_snip_selection(self):
        # Open region-selection overlay
        CaptureOverlay(self.root, self.on_region_selected)

    def on_region_selected(self, bbox):
        if not bbox:
            # Selection cancelled, main window is already restored by capture overlay
            return
            
        # Hide main window completely during recording
        self.root.withdraw()
        
        # Parse inputs
        fps = int(self.fps_var.get())
        
        countdown_map = {"None": 0, "2 Seconds": 2, "5 Seconds": 5}
        countdown = countdown_map.get(self.countdown_var.get(), 0)
        
        # Launch background GIF recorder
        self.recorder = GifRecorder(
            parent=self.root,
            bbox=bbox,
            fps=fps,
            countdown_seconds=countdown,
            on_done_callback=self.on_recording_done
        )

    def on_recording_done(self, frames):
        if not frames:
            # Recording was empty or failed, restore dashboard
            self.root.deiconify()
            tk.messagebox.showwarning("Recording Cancelled", "No frames were captured during the recording.")
            return
            
        # Launch Editor window with captured frames
        fps = int(self.fps_var.get())
        editor = EditorWindow(self.root, frames, fps=fps)
        
        # Bind the editor's close event to safely restore the main dashboard
        editor.window.bind("<Destroy>", lambda e: self.restore_main_window(e, editor.window))

    def restore_main_window(self, event, editor_window):
        # Only restore when the top-level editor window itself is destroyed, not child widgets
        if event.widget == editor_window:
            self.root.deiconify()

if __name__ == "__main__":
    root = tk.Tk()
    app = GifSnipperApp(root)
    root.mainloop()
