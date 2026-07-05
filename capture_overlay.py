# capture_overlay.py
# Implements the full-screen dim selection overlay for snipping a region.

import tkinter as tk
from PIL import Image, ImageTk, ImageEnhance, ImageGrab
import ctypes

# Enable DPI awareness on Windows so that screen coordinates align exactly with pixel coordinates
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1) # System DPI awareness
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

class CaptureOverlay:
    def __init__(self, parent_window, on_selection_callback):
        self.parent = parent_window
        self.callback = on_selection_callback
        
        # Hide parent window
        self.parent.withdraw()
        
        # Take full screen screenshot
        self.original_img = ImageGrab.grab(all_screens=True)
        self.screen_width, self.screen_height = self.original_img.size
        
        # Create dark overlay (dimmed image)
        enhancer = ImageEnhance.Brightness(self.original_img)
        self.dimmed_img = enhancer.enhance(0.4) # Dim to 40% brightness
        
        # Create fullscreen borderless overlay window
        self.overlay = tk.Toplevel(self.parent)
        self.overlay.overrideredirect(True)
        self.overlay.geometry(f"{self.screen_width}x{self.screen_height}+0+0")
        self.overlay.attributes("-topmost", True)
        self.overlay.config(cursor="cross")
        
        # Convert dimmed image to Tk PhotoImage
        self.dimmed_photo = ImageTk.PhotoImage(self.dimmed_img)
        
        # Create canvas
        self.canvas = tk.Canvas(
            self.overlay, 
            width=self.screen_width, 
            height=self.screen_height, 
            bd=0, 
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)
        
        # Draw background dimmed image
        self.canvas.create_image(0, 0, image=self.dimmed_photo, anchor="nw")
        
        # Selection coordinates
        self.start_x = None
        self.start_y = None
        
        # Selection items on canvas
        self.reveal_image_id = self.canvas.create_image(0, 0, anchor="nw", state="hidden")
        self.rect_id = self.canvas.create_rectangle(0, 0, 0, 0, outline="#89b4fa", width=2, state="hidden")
        self.text_id = self.canvas.create_text(0, 0, fill="#ffffff", font=("Segoe UI", 10, "bold"), anchor="sw", state="hidden")
        self.text_bg_id = self.canvas.create_rectangle(0, 0, 0, 0, fill="#181825", outline="#45475a", state="hidden")
        
        # Keep reference to ImageTk objects to prevent garbage collection
        self.crop_photo = None
        
        # Bindings
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.overlay.bind("<Escape>", self.on_cancel)
        
        # Force focus
        self.overlay.focus_force()

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        
        # Show selection overlay elements
        self.canvas.itemconfig(self.reveal_image_id, state="normal")
        self.canvas.itemconfig(self.rect_id, state="normal")
        self.canvas.itemconfig(self.text_id, state="normal")
        self.canvas.itemconfig(self.text_bg_id, state="normal")

    def on_drag(self, event):
        cur_x, cur_y = event.x, event.y
        
        # Calculate bounding box
        x1 = min(self.start_x, cur_x)
        y1 = min(self.start_y, cur_y)
        x2 = max(self.start_x, cur_x)
        y2 = max(self.start_y, cur_y)
        
        w = x2 - x1
        h = y2 - y1
        
        if w > 0 and h > 0:
            # Crop the subregion from original bright screenshot
            crop_img = self.original_img.crop((x1, y1, x2, y2))
            self.crop_photo = ImageTk.PhotoImage(crop_img)
            
            # Update revealed image on canvas
            self.canvas.itemconfig(self.reveal_image_id, image=self.crop_photo)
            self.canvas.coords(self.reveal_image_id, x1, y1)
            
            # Update blue border rectangle
            self.canvas.coords(self.rect_id, x1, y1, x2, y2)
            
            # Update text overlay showing dimensions
            size_text = f" {w} x {h} px "
            self.canvas.itemconfig(self.text_id, text=size_text)
            
            # Position text label just above top-left, or inside if near edges
            text_x = x1
            text_y = y1 - 5 if y1 - 25 > 0 else y1 + 20
            self.canvas.coords(self.text_id, text_x, text_y)
            
            # Draw background box for text readability
            bbox = self.canvas.bbox(self.text_id)
            if bbox:
                self.canvas.coords(self.text_bg_id, bbox[0]-2, bbox[1]-2, bbox[2]+2, bbox[3]+2)

    def on_release(self, event):
        cur_x, cur_y = event.x, event.y
        
        x1 = min(self.start_x, cur_x)
        y1 = min(self.start_y, cur_y)
        x2 = max(self.start_x, cur_x)
        y2 = max(self.start_y, cur_y)
        
        width = x2 - x1
        height = y2 - y1
        
        self.overlay.destroy()
        self.parent.deiconify()
        
        # Require a minimum drag size (e.g. 5x5) to prevent accidental single clicks
        if width > 5 and height > 5:
            self.callback((x1, y1, x2, y2))
        else:
            self.callback(None)

    def on_cancel(self, event=None):
        self.overlay.destroy()
        self.parent.deiconify()
        self.callback(None)
