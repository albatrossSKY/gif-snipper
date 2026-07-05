# theme.py
# Modern, sleek theme configuration for the GIF Snipper app.
# Based on a modern dark palette (Catppuccin Mocha inspired)

# Colors
BG_MAIN = "#1e1e2e"       # Main background
BG_SIDEBAR = "#181825"    # Sidebar or secondary surface background
BG_CARD = "#313244"       # Cards, input backgrounds, active outlines
TEXT_PRIMARY = "#cdd6f4"  # Main text
TEXT_MUTED = "#a6adc8"    # Subtext / labels
ACCENT_BLUE = "#89b4fa"   # Primary action buttons
ACCENT_RED = "#f38ba8"    # Recording / warning
ACCENT_GREEN = "#a6e3a1"  # Success / save / active state
ACCENT_MAUVE = "#cba6f7"  # Secondary highlights
BORDER_COLOR = "#45475a"  # Borders

# Fonts
FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_SUBTITLE = ("Segoe UI", 12, "bold")
FONT_BODY = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_SMALL = ("Segoe UI", 9)
FONT_MONO = ("Consolas", 10)

def style_window(root):
    root.configure(bg=BG_MAIN)

def style_label(label, font=FONT_BODY, fg=TEXT_PRIMARY, bg=BG_MAIN):
    label.configure(font=font, fg=fg, bg=bg)

def style_frame(frame, bg=BG_MAIN):
    frame.configure(bg=bg)

def style_button(button, variant="primary"):
    """
    Applies flat modern styling with hover effects.
    """
    if variant == "primary":
        bg_color = ACCENT_BLUE
        fg_color = "#11111b"
        active_bg = "#b4befe"
    elif variant == "danger":
        bg_color = ACCENT_RED
        fg_color = "#11111b"
        active_bg = "#f38ba8"
    elif variant == "success":
        bg_color = ACCENT_GREEN
        fg_color = "#11111b"
        active_bg = "#a6e3a1"
    else: # secondary / outline
        bg_color = BG_CARD
        fg_color = TEXT_PRIMARY
        active_bg = BORDER_COLOR

    button.configure(
        font=FONT_BOLD,
        bg=bg_color,
        fg=fg_color,
        activebackground=active_bg,
        activeforeground=fg_color if variant != "secondary" else TEXT_PRIMARY,
        bd=0,
        padx=12,
        pady=6,
        relief="flat",
        cursor="hand2"
    )
    
    # Hover effects
    def on_enter(e):
        if variant == "primary":
            button.configure(bg="#a6e3a1") # turn green or lighter blue on hover
        elif variant == "danger":
            button.configure(bg="#f8bd96") # lighter red/peach
        elif variant == "success":
            button.configure(bg="#94e2d5") # lighter teal/green
        else:
            button.configure(bg=BORDER_COLOR)

    def on_leave(e):
        button.configure(bg=bg_color)

    button.bind("<Enter>", on_enter)
    button.bind("<Leave>", on_leave)

def style_entry(entry):
    entry.configure(
        font=FONT_BODY,
        bg=BG_SIDEBAR,
        fg=TEXT_PRIMARY,
        insertbackground=TEXT_PRIMARY,
        bd=1,
        relief="flat",
        highlightbackground=BORDER_COLOR,
        highlightcolor=ACCENT_BLUE,
        highlightthickness=1
    )
