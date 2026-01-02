import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import keyboard
from pynput import keyboard as pynput_keyboard
from pynput import mouse as pynput_mouse
import sys
import ctypes
from ctypes import windll
import dxcam
import win32api
import win32con
import win32gui
import mss
from PIL import Image, ImageTk, ImageEnhance, ImageOps, ImageDraw
import requests
from io import BytesIO
import time
import json
import os
import tempfile
import gc
from datetime import datetime
import numpy as np
import pyautogui

# Disable pyautogui's built-in delay for RDP responsiveness
pyautogui.PAUSE = 0

# System tray support
try:
    import pystray
    from pystray import MenuItem as item
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

# --- CONFIGURATION ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

THEME_BG = "#000000"
THEME_CARD = "#2b2b2b"
THEME_ACCENT = "#ff8d00"
THEME_TEXT = "#ffffff"

FONT_MAIN = ("Segoe UI", 12)
FONT_BOLD = ("Segoe UI", 13, "bold")
FONT_TITLE = ("Segoe UI", 24, "bold")
FONT_SMALL = ("Segoe UI", 10)

# RESOURCES
TITLE_LOGO_URL = "https://image2url.com/images/1765149562249-ff56b103-b5ea-4402-a896-0ed38202b804.png"
PROFILE_ICON_URL = "https://i.pinimg.com/736x/f1/bb/3d/f1bb3d7b7b2fe3dbf46915f380043be9.jpg"
VIVI_URL = "https://static0.srcdn.com/wordpress/wp-content/uploads/2023/10/vivi.jpg?q=49&fit=crop&w=825&dpr=2"
DUCK_URL = "https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fi.ytimg.com%2Fvi%2FX8YUuU7OpOA%2Fmaxresdefault.jpg&f=1&nofb=1&ipt=6d669298669fff2e4f438b54453c1f59c1655ca19fa2407ea1c42e471a4d7ab6"
NOTIF_AUDIO_URL = "https://www.dropbox.com/scl/fi/u9563mn42ay8rkgm33aod/igoronly.mp3?rlkey=vsqye9u2227x4c36og1myc8eb&st=3pdh75ks&dl=1"
NOTIF_ICON_URL = "https://media.discordapp.net/attachments/776428933603786772/1447747919246528543/IMG_8252.png?ex=6938bfd1&is=69376e51&hm=ab1926f5459273c16aa1c6498ea96d74ae15b08755ed930a1b5bf615ffc0c31b&=&format=webp&quality=lossless&width=1214&height=1192"

STATS_FILE = "karoo_stats.json"
CONFIG_FILE = "karoo_config.json"

# --- MANAGERS ---
try:
    import easyocr
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


class OCRManager:
    def __init__(self, app):
        self.app = app
        self.reader = None
        self.last_scan = 0
        if OCR_AVAILABLE:
            try:
                self.reader = easyocr.Reader(['en'], gpu=False)
            except:
                pass

    def scan_for_spawn(self):
        if not self.reader or time.time() - self.last_scan < 5.0:
            return
        self.last_scan = time.time()

        try:
            w, h = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
            monitor = {"top": 0, "left": int(w * 0.3), "width": int(w * 0.4), "height": int(h * 0.2)}

            with mss.mss() as sct:
                img = np.array(sct.grab(monitor))

            results = self.reader.readtext(img, detail=0)
            text = " ".join(results).lower()

            if "spawned" in text:
                words = text.split()
                fruit_name = "Unknown Fruit"
                for i, word in enumerate(words):
                    if "spawned" in word:
                        if i > 0:
                            fruit_name = words[i - 1]
                        if i > 2:
                            fruit_name = f"{words[i - 3]} {words[i - 2]} {words[i - 1]}"
                        break

                self.app.webhook_manager.send_fruit_spawn(fruit_name.title())

        except Exception as e:
            print(f"OCR Error: {e}")

    def scan_for_catch(self):
        if not self.reader:
            return False
        try:
            w, h = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
            monitor = {"top": int(h * 0.1), "left": int(w * 0.3), "width": int(w * 0.4), "height": int(h * 0.15)}
            with mss.mss() as sct:
                img = np.array(sct.grab(monitor))

            results = self.reader.readtext(img, detail=0)
            text = " ".join(results).lower()

            if "caught" in text and ("fruit" in text or "mi" in text):
                return True
        except:
            pass
        return False


class WebhookManager:
    def __init__(self, app):
        self.app = app
        self.devil_fruit_count = 0

    def send_webhook(self, title, description, color, fields=None, content=None):
        url = self.app.webhook_url_var.get()
        if not url or not self.app.notify_enabled_var.get():
            return
        try:
            embed = {
                "title": title, "description": description, "color": color,
                "footer": {"text": "Karoo Fish - Perfect Edition"},
                "timestamp": datetime.utcnow().isoformat()
            }
            if fields:
                embed["fields"] = fields
            data = {"embeds": [embed], "username": "Karoo Bot"}
            if content:
                data["content"] = content

            requests.post(url, json=data, timeout=5)
        except:
            pass

    def send_fishing_progress(self):
        self.send_webhook(
            "Fishing Progress",
            f"Caught **{self.app.session_loops}** fish this session!",
            0x00ff00,
            [{"name": "Total Caught", "value": str(self.app.stats['total_caught'] + self.app.session_loops), "inline": True}]
        )

    def send_fruit_spawn(self, fruit_name):
        self.send_webhook(
            "Devil Fruit Spawned!",
            f"A **{fruit_name}** has spawned!",
            0xFFD700,
            [{"name": "Fruit", "value": fruit_name, "inline": True}],
            content="@here"
        )

    def send_devil_fruit_drop(self, drop_info=None):
        self.devil_fruit_count += 1
        desc = "Devil fruit detected and stored!"
        if drop_info:
            desc += f"\nInfo: {drop_info}"
        self.send_webhook(
            "Devil Fruit Caught!",
            desc,
            0x9c27b0,
            [
                {"name": "Session Fruits", "value": str(self.devil_fruit_count), "inline": True},
                {"name": "Total Fish", "value": str(self.app.stats['total_caught']), "inline": True}
            ],
            content="@everyone RARE DROP!"
        )

    def send_purchase(self, amount):
        self.send_webhook(
            "Auto Purchase",
            f"Successfully purchased **{amount}** bait.",
            0xffa500,
            [{"name": "Status", "value": "Complete", "inline": True}]
        )

    def test(self):
        self.send_webhook("Test", "Webhook is working!", 0x0099ff)


class BaitManager:
    def __init__(self, app):
        self.app = app

    def select_top_bait(self):
        if not self.app.auto_bait_var.get():
            return
        p6 = self.app.point_coords.get(6)
        if not p6:
            return
        try:
            hold_time = self.app.adaptive_delay.get_click_hold()
            self.app.click(p6, "Bait Select", hold_time=hold_time)
            time.sleep(self.app.adaptive_delay.get_step_delay())
            self.app.move_to(self.app.point_coords[4])
        except:
            pass

    def select_bait_before_cast(self):
        self.select_top_bait()


class AdaptiveDelayManager:
    """Manages adaptive delays for RDP/variable latency conditions"""

    def __init__(self, app):
        self.app = app
        self.response_times = []
        self.max_samples = 20

        # Base delays (will be adjusted)
        self.base_click_hold = 0.05
        self.base_step_delay = 0.5
        self.base_key_hold = 0.1

        # Latency multiplier (learned from response times)
        self.latency_multiplier = 1.0

        # Frame timing tracking
        self.frame_times = []
        self.last_frame_time = time.time()
        self.detected_fps = 60.0

    def record_response(self, action_start, response_received):
        """Record a response time to adapt delays"""
        response_time = response_received - action_start
        self.response_times.append(response_time)
        if len(self.response_times) > self.max_samples:
            self.response_times.pop(0)
        self._update_multiplier()

    def record_frame_time(self):
        """Track frame timing to detect FPS drops"""
        now = time.time()
        frame_delta = now - self.last_frame_time
        self.last_frame_time = now

        if frame_delta > 0:
            self.frame_times.append(frame_delta)
            if len(self.frame_times) > 30:
                self.frame_times.pop(0)

            # Calculate detected FPS
            if len(self.frame_times) >= 5:
                avg_delta = np.mean(self.frame_times[-10:])
                self.detected_fps = min(60.0, 1.0 / max(avg_delta, 0.001))

    def _update_multiplier(self):
        """Update the latency multiplier based on response times"""
        if len(self.response_times) < 3:
            return

        avg_response = np.mean(self.response_times)
        max_response = np.max(self.response_times[-5:]) if len(self.response_times) >= 5 else avg_response

        # Calculate multiplier: higher response times = higher multiplier
        # Base expectation: 50ms response time = 1.0 multiplier
        self.latency_multiplier = max(1.0, min(4.0, max_response / 0.05))

        # Also factor in FPS drops
        fps_factor = 60.0 / max(self.detected_fps, 20.0)
        self.latency_multiplier *= fps_factor

    def get_click_hold(self):
        """Get adaptive click hold time"""
        if self.app.use_rdp_mode_var.get():
            return self.base_click_hold * self.latency_multiplier * 2
        return self.base_click_hold

    def get_step_delay(self):
        """Get adaptive step delay"""
        if self.app.use_rdp_mode_var.get():
            return self.base_step_delay * self.latency_multiplier
        return self.base_step_delay * 0.6

    def get_key_hold(self):
        """Get adaptive key hold time"""
        if self.app.use_rdp_mode_var.get():
            return self.base_key_hold * self.latency_multiplier * 1.5
        return self.base_key_hold

    def get_wait_for_ui(self):
        """Get wait time for UI elements to appear"""
        base = 0.5
        if self.app.use_rdp_mode_var.get():
            return base * self.latency_multiplier * 1.5
        return base

    def get_animation_wait(self):
        """Get wait time for game animations"""
        base = 1.0
        if self.app.use_rdp_mode_var.get():
            return base * self.latency_multiplier
        return base


class CollapsibleSection(ctk.CTkFrame):
    """A collapsible section widget for organizing UI"""

    def __init__(self, parent, title, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.expanded = True

        # Header frame
        self.header = ctk.CTkFrame(self, fg_color=THEME_CARD, corner_radius=8)
        self.header.pack(fill="x", pady=(5, 0))

        # Toggle button
        self.toggle_btn = ctk.CTkButton(
            self.header,
            text="▼",
            width=24,
            height=24,
            fg_color="transparent",
            hover_color=THEME_ACCENT,
            command=self.toggle,
            font=("Segoe UI", 10)
        )
        self.toggle_btn.pack(side="left", padx=5, pady=5)

        # Title
        self.title_label = ctk.CTkLabel(
            self.header,
            text=title,
            font=FONT_BOLD,
            text_color=THEME_ACCENT
        )
        self.title_label.pack(side="left", padx=5, pady=5)

        # Content frame
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(fill="x", padx=10, pady=5)

    def toggle(self):
        self.expanded = not self.expanded
        if self.expanded:
            self.content.pack(fill="x", padx=10, pady=5)
            self.toggle_btn.configure(text="▼")
        else:
            self.content.pack_forget()
            self.toggle_btn.configure(text="▶")

    def get_content(self):
        return self.content


class MiniWidget(tk.Toplevel):
    """Floating mini-widget showing session stats"""

    def __init__(self, app):
        super().__init__(app)
        self.app = app

        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.attributes('-alpha', 0.9)
        self.configure(bg=THEME_BG)

        # Position in bottom-right
        screen_w = win32api.GetSystemMetrics(0)
        screen_h = win32api.GetSystemMetrics(1)
        self.geometry(f"150x80+{screen_w - 170}+{screen_h - 130}")

        # Dragging support
        self.drag_start_x = 0
        self.drag_start_y = 0

        # Main frame with border
        self.main_frame = tk.Frame(self, bg=THEME_ACCENT, padx=2, pady=2)
        self.main_frame.pack(fill="both", expand=True)

        self.inner_frame = tk.Frame(self.main_frame, bg=THEME_BG)
        self.inner_frame.pack(fill="both", expand=True)

        # Status indicator
        self.status_frame = tk.Frame(self.inner_frame, bg=THEME_BG)
        self.status_frame.pack(fill="x", padx=5, pady=2)

        self.status_dot = tk.Label(self.status_frame, text="●", fg="red", bg=THEME_BG, font=("Segoe UI", 12))
        self.status_dot.pack(side="left")

        self.status_text = tk.Label(self.status_frame, text="OFF", fg="white", bg=THEME_BG, font=("Segoe UI", 10, "bold"))
        self.status_text.pack(side="left", padx=5)

        # Session count
        self.count_label = tk.Label(self.inner_frame, text="0", fg=THEME_ACCENT, bg=THEME_BG, font=("Segoe UI", 24, "bold"))
        self.count_label.pack()

        self.sub_label = tk.Label(self.inner_frame, text="fish caught", fg="gray", bg=THEME_BG, font=("Segoe UI", 9))
        self.sub_label.pack()

        # Bind dragging
        self.inner_frame.bind('<Button-1>', self.start_drag)
        self.inner_frame.bind('<B1-Motion>', self.on_drag)
        self.count_label.bind('<Button-1>', self.start_drag)
        self.count_label.bind('<B1-Motion>', self.on_drag)

        # Double-click to show main window
        self.inner_frame.bind('<Double-Button-1>', lambda e: self.app.deiconify())

        self.update_display()

    def start_drag(self, event):
        self.drag_start_x = event.x_root - self.winfo_x()
        self.drag_start_y = event.y_root - self.winfo_y()

    def on_drag(self, event):
        x = event.x_root - self.drag_start_x
        y = event.y_root - self.drag_start_y
        self.geometry(f"+{x}+{y}")

    def update_display(self):
        if not self.winfo_exists():
            return

        # Update count
        self.count_label.configure(text=str(self.app.session_loops))

        # Update status
        if self.app.fishing_active:
            self.status_dot.configure(fg="#00ff00")
            self.status_text.configure(text="FISHING")
        else:
            self.status_dot.configure(fg="red")
            self.status_text.configure(text="OFF")

        # Schedule next update
        self.after(500, self.update_display)


class SystemTrayManager:
    """Manages system tray icon and menu"""

    def __init__(self, app):
        self.app = app
        self.icon = None
        self.running = False

        if not TRAY_AVAILABLE:
            return

        # Create icon image
        self.create_icon()

    def create_icon(self):
        """Create the tray icon"""
        if not TRAY_AVAILABLE:
            return

        # Create a simple icon (orange circle)
        img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([8, 8, 56, 56], fill=THEME_ACCENT)
        draw.text((20, 18), "KF", fill="black", font=None)

        self.icon = pystray.Icon(
            "KarooFish",
            img,
            "Karoo Fish",
            menu=pystray.Menu(
                item('Show Window', self.show_window),
                item('Toggle Fishing (F1)', self.toggle_fishing),
                item(lambda text: f'Session: {self.app.session_loops} fish', None, enabled=False),
                item(lambda text: f'Status: {"ON" if self.app.fishing_active else "OFF"}', None, enabled=False),
                pystray.Menu.SEPARATOR,
                item('Exit', self.exit_app)
            )
        )

    def start(self):
        """Start the tray icon in a thread"""
        if not TRAY_AVAILABLE or self.running:
            return

        self.running = True
        threading.Thread(target=self._run_icon, daemon=True).start()

    def _run_icon(self):
        """Run the icon (blocking)"""
        try:
            self.icon.run()
        except:
            pass

    def stop(self):
        """Stop the tray icon"""
        if self.icon and self.running:
            try:
                self.icon.stop()
            except:
                pass
            self.running = False

    def show_window(self):
        """Show the main window"""
        self.app.after(0, self.app.deiconify)
        self.app.after(0, self.app.lift)

    def toggle_fishing(self):
        """Toggle fishing from tray"""
        self.app.after(0, self.app.toggle_fishing)

    def exit_app(self):
        """Exit the application"""
        self.app.after(0, self.app.exit_app)

    def update_tooltip(self):
        """Update the tooltip with current stats"""
        if self.icon:
            status = "ON" if self.app.fishing_active else "OFF"
            self.icon.title = f"Karoo Fish - {status} | Session: {self.app.session_loops}"


# --- MAIN APP ---
class KarooFish(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Karoo Fish - Perfect Edition")
        self.geometry("520x900")
        self.minsize(400, 600)
        self.configure(fg_color=THEME_BG)
        self.attributes('-topmost', True)

        # --- CORE VARS INIT (Early) ---
        self.rod_key_var = ctk.StringVar(value="1")
        self.use_rdp_mode_var = ctk.BooleanVar(value=False)
        self.auto_zoom_var = ctk.BooleanVar(value=True)
        self.webhook_url_var = ctk.StringVar(value="")
        self.notify_enabled_var = ctk.BooleanVar(value=True)

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

        # --- STATE ---
        self.fishing_active = False
        self.reroll_active = False
        self.overlay_active = False
        self.afk_mode_active = False

        self.overlay_window = None
        self.is_clicking = False
        self.is_performing_action = False
        self.last_cast_time = 0.0
        self.last_user_activity = time.time()

        self.last_notification_time = 0
        self.cached_audio_path = None
        self.cached_notif_icon = None

        # --- CONFIG VARS ---
        self.base_width = win32api.GetSystemMetrics(0)
        self.base_height = win32api.GetSystemMetrics(1)
        self.resize_threshold = 10
        self.dragging = False
        self.resizing = False
        self.resize_edge = None
        self.border_size = 5

        self.purchase_counter = 0
        self.session_loops = 0
        self.kp = 0.15
        self.kd = 0.5
        self.previous_error = 0
        self.scan_timeout = 15.0
        self.rdp_click_hold = 0.05
        self.purchase_delay_after_key = 0.5
        self.clean_step_delay = 0.8
        self.success_rate = 1.0
        self.recent_catches = []

        # Real-time metrics
        self.current_fps = 0.0
        self.frames_processed = 0
        self.last_fps_update = time.time()

        # CTK Vars
        self.auto_purchase_var = ctk.BooleanVar(value=False)
        self.amount_var = ctk.IntVar(value=10)
        self.loops_var = ctk.IntVar(value=10)
        self.item_check_var = ctk.BooleanVar(value=True)
        self.auto_bait_var = ctk.BooleanVar(value=False)
        self.auto_afk_var = ctk.BooleanVar(value=True)
        self.auto_afk_seconds_var = ctk.IntVar(value=60)
        self.kp_var = ctk.DoubleVar(value=0.15)
        self.kd_var = ctk.DoubleVar(value=0.5)
        self.timeout_var = ctk.DoubleVar(value=15.0)
        self.notify_enabled_var = ctk.BooleanVar(value=True)
        self.webhook_url_var = ctk.StringVar(value="")
        self.auto_zoom_var = ctk.BooleanVar(value=True)
        self.use_rdp_mode_var = ctk.BooleanVar(value=False)
        self.rod_key_var = ctk.StringVar(value="1")

        # NEW: Configurable pixel thresholds
        self.saturation_threshold_var = ctk.IntVar(value=20)
        self.brightness_low_var = ctk.IntVar(value=40)
        self.brightness_high_var = ctk.IntVar(value=210)

        # Color tolerance for detection (0 = exact match like working version, increase for RDP/compression)
        self.color_tolerance_var = ctk.IntVar(value=0)

        self.dpi_scale = self.get_dpi_scale()
        w, h = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
        self.overlay_area = {'x': 100, 'y': 100, 'width': int(180 * self.dpi_scale), 'height': int(500 * self.dpi_scale)}
        self.ocr_overlay_area = {'x': int(w * 0.3), 'y': 0, 'width': int(w * 0.4), 'height': int(h * 0.2)}

        self.hotkeys = {'toggle_loop': 'f1', 'toggle_overlay': 'f2', 'exit': 'f3', 'toggle_afk': 'f4'}
        self.point_coords = {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None, 8: None}
        self.point_labels = {}

        self.camera = None
        self.overlay_window = None
        self.ocr_overlay_window = None
        self.stats = self.load_stats()

        # Managers
        self.webhook_manager = WebhookManager(self)
        self.bait_manager = BaitManager(self)
        self.ocr_manager = OCRManager(self)
        self.adaptive_delay = AdaptiveDelayManager(self)
        self.tray_manager = SystemTrayManager(self)

        # Mini widget
        self.mini_widget = None

        # Assets
        self.bg_image = None
        self.profile_image = None
        self.logo_image = None
        threading.Thread(target=self.load_images, daemon=True).start()
        threading.Thread(target=self.cache_notification_assets, daemon=True).start()

        self.setup_ui()
        self.load_config()
        self.register_hotkeys()

        self.bind("<Any-KeyPress>", self.reset_afk_timer)
        self.bind("<Any-ButtonPress>", self.reset_afk_timer)
        self.bind("<Configure>", self.on_window_resize)
        self.check_auto_afk()

        # Start tray icon
        self.tray_manager.start()

        # Start status bar updates
        self.update_status_bar()

    def on_window_resize(self, event=None):
        """Handle window resize events"""
        pass  # UI is now responsive by default

    def load_images(self):
        try:
            r = requests.get(VIVI_URL, stream=True)
            if r.status_code == 200:
                img = Image.open(r.raw)
                img = ImageEnhance.Brightness(img).enhance(0.3)
                self.bg_image = ctk.CTkImage(img, size=(520, 900))
                self.after(0, self.update_bg)

            r = requests.get(PROFILE_ICON_URL, stream=True)
            if r.status_code == 200:
                img = Image.open(r.raw)
                mask = Image.new("L", (100, 100), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, 100, 100), fill=255)
                img = ImageOps.fit(img, (100, 100))
                img.putalpha(mask)
                self.profile_image = ctk.CTkImage(img, size=(60, 60))
                self.after(0, self.update_profile_icon)

        except Exception as e:
            print(f"Asset Error: {e}")

    def update_bg(self):
        if self.bg_image:
            self.bg_label = ctk.CTkLabel(self, text="", image=self.bg_image)
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            self.bg_label.lower()

    def update_profile_icon(self):
        if hasattr(self, 'profile_btn') and self.profile_image:
            self.profile_btn.configure(image=self.profile_image, text="")

    def cache_notification_assets(self):
        try:
            temp_dir = tempfile.gettempdir()
            audio_path = os.path.join(temp_dir, "karoo_igor_v2.mp3")
            if not os.path.exists(audio_path):
                r = requests.get(NOTIF_AUDIO_URL)
                with open(audio_path, 'wb') as f:
                    f.write(r.content)
            self.cached_audio_path = audio_path
        except:
            pass
        try:
            response = requests.get(NOTIF_ICON_URL)
            img = Image.open(BytesIO(response.content)).convert("RGBA")
            img = img.resize((64, 64), Image.Resampling.LANCZOS)
            self.cached_notif_icon = ImageTk.PhotoImage(img)
        except:
            pass

    def play_notification_sound(self):
        if not self.cached_audio_path:
            return

        def _play():
            try:
                ctypes.windll.winmm.mciSendStringW(f"close karoo_alert", None, 0, None)
                ctypes.windll.winmm.mciSendStringW(f'open "{self.cached_audio_path}" type mpegvideo alias karoo_alert', None, 0, None)
                ctypes.windll.winmm.mciSendStringW(f"play karoo_alert", None, 0, None)
            except:
                pass

        threading.Thread(target=_play, daemon=True).start()

    def trigger_rare_catch_notification(self):
        """Trigger notification for rare catch"""
        self.play_notification_sound()

    def get_dpi_scale(self):
        try:
            return self.winfo_fpixels('1i') / 96.0
        except:
            return 1.0

    # --- SAVE/LOAD ---
    def load_stats(self):
        if os.path.exists(STATS_FILE):
            try:
                return json.load(open(STATS_FILE, 'r'))
            except:
                pass
        return {"total_caught": 0, "history": [], "rare_catches": []}

    def save_stats(self):
        with open(STATS_FILE, 'w') as f:
            json.dump(self.stats, f, indent=4)

    def record_session(self):
        if self.session_loops > 0:
            self.stats["total_caught"] += self.session_loops
            entry = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "count": self.session_loops}
            self.stats["history"].insert(0, entry)
            self.stats["history"] = self.stats["history"][:50]
            self.save_stats()
            self.session_loops = 0

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
            if "points" in data:
                for k, v in data["points"].items():
                    if v:
                        idx = int(k)
                        self.point_coords[idx] = tuple(v)
                        if idx in self.point_labels:
                            self.point_labels[idx].configure(text=f"{int(v[0])},{int(v[1])}", text_color="#00ff00")
            if "hotkeys" in data:
                self.hotkeys.update(data["hotkeys"])
            self.auto_purchase_var.set(data.get("auto_purchase", False))
            self.amount_var.set(data.get("amount", 10))
            self.loops_var.set(data.get("loops", 10))
            self.item_check_var.set(data.get("item_check", True))
            self.auto_bait_var.set(data.get("auto_bait", False))
            self.auto_afk_var.set(data.get("auto_afk", True))
            self.auto_afk_seconds_var.set(data.get("afk_seconds", 60))
            self.kp_var.set(data.get("kp", 0.15))
            self.kd_var.set(data.get("kd", 0.5))
            self.timeout_var.set(data.get("timeout", 15.0))
            self.notify_enabled_var.set(data.get("notify_enabled", True))
            self.webhook_url_var.set(data.get("webhook_url", ""))
            self.auto_zoom_var.set(data.get("auto_zoom", True))
            self.use_rdp_mode_var.set(data.get("use_rdp", False))
            self.rod_key_var.set(data.get("rod_key", "1"))
            if "overlay_area" in data:
                self.overlay_area = data["overlay_area"]
            if "ocr_overlay_area" in data:
                self.ocr_overlay_area = data["ocr_overlay_area"]
            # NEW: Load pixel thresholds
            self.saturation_threshold_var.set(data.get("saturation_threshold", 20))
            self.brightness_low_var.set(data.get("brightness_low", 40))
            self.brightness_high_var.set(data.get("brightness_high", 210))
            self.color_tolerance_var.set(data.get("color_tolerance", 0))
        except:
            pass

    def save_config(self):
        data = {
            "points": self.point_coords, "hotkeys": self.hotkeys, "auto_purchase": self.auto_purchase_var.get(),
            "amount": self.amount_var.get(), "loops": self.loops_var.get(), "item_check": self.item_check_var.get(),
            "auto_bait": self.auto_bait_var.get(), "auto_afk": self.auto_afk_var.get(),
            "afk_seconds": self.auto_afk_seconds_var.get(), "kp": self.kp_var.get(), "kd": self.kd_var.get(),
            "timeout": self.timeout_var.get(), "notify_enabled": self.notify_enabled_var.get(),
            "webhook_url": self.webhook_url_var.get(), "auto_zoom": self.auto_zoom_var.get(),
            "use_rdp": self.use_rdp_mode_var.get(), "overlay_area": self.overlay_area,
            "ocr_overlay_area": self.ocr_overlay_area,
            "rod_key": self.rod_key_var.get(),
            # NEW: Save pixel thresholds
            "saturation_threshold": self.saturation_threshold_var.get(),
            "brightness_low": self.brightness_low_var.get(),
            "brightness_high": self.brightness_high_var.get(),
            "color_tolerance": self.color_tolerance_var.get()
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        self.status_msg.configure(text="Settings Saved!", text_color="#00ff00")

    # --- UI ---
    def setup_ui(self):
        # Background
        self.bg_frame = ctk.CTkFrame(self, fg_color=THEME_BG)
        self.bg_frame.place(x=0, y=0, relwidth=1, relheight=1)

        # Profile Header
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=20, pady=(15, 5))

        self.profile_btn = ctk.CTkButton(self.header, text="IMG", width=60, height=60, fg_color="transparent", border_width=2, border_color=THEME_ACCENT, corner_radius=30)
        self.profile_btn.pack(side="left")

        self.title_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        self.title_frame.pack(side="left", padx=15)
        ctk.CTkLabel(self.title_frame, text="Fisher", font=("Segoe UI", 20, "bold"), text_color="white").pack(anchor="w")
        ctk.CTkLabel(self.title_frame, text="The One And Only Karoo", font=("Segoe UI", 12), text_color=THEME_ACCENT).pack(anchor="w")

        # Main Tabs
        self.tabview = ctk.CTkTabview(self, fg_color=THEME_CARD, corner_radius=15)
        self.tabview.pack(padx=10, pady=5, fill="both", expand=True)

        self.tab_fishing = self.tabview.add("Fishing Bot")
        self.tab_reroll = self.tabview.add("Race Reroll")

        self.create_fishing_tab()
        self.create_reroll_tab()

        # --- STATUS BAR (NEW) ---
        self.create_status_bar()

        # Status Footer
        self.status_msg = ctk.CTkLabel(self, text="Ready", text_color=THEME_ACCENT, font=FONT_SMALL)
        self.status_msg.pack(pady=2)

        # AFK Overlay (Hidden)
        self.afk_frame = ctk.CTkFrame(self, fg_color=THEME_BG, corner_radius=0)

        ctk.CTkLabel(self.afk_frame, text="AFK MODE", font=("Segoe UI", 40, "bold"), text_color=THEME_ACCENT).place(relx=0.5, rely=0.2, anchor="center")
        ctk.CTkLabel(self.afk_frame, text="Session Catch:", font=("Segoe UI", 16)).place(relx=0.5, rely=0.4, anchor="center")
        self.afk_session_lbl = ctk.CTkLabel(self.afk_frame, text="0", font=("Segoe UI", 80, "bold"), text_color="white")
        self.afk_session_lbl.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(self.afk_frame, text="Total:", font=("Segoe UI", 14), text_color="gray").place(relx=0.5, rely=0.7, anchor="center")
        self.afk_total_lbl = ctk.CTkLabel(self.afk_frame, text="0", font=("Segoe UI", 24, "bold"))
        self.afk_total_lbl.place(relx=0.5, rely=0.75, anchor="center")

        ctk.CTkLabel(self.afk_frame, text="Press F4 to Resume", font=("Segoe UI", 12), text_color="gray").place(relx=0.5, rely=0.9, anchor="center")

    def create_status_bar(self):
        """Create the dedicated status bar with real-time metrics"""
        self.status_bar = ctk.CTkFrame(self, fg_color="#111111", corner_radius=10, height=50)
        self.status_bar.pack(fill="x", padx=10, pady=5)
        self.status_bar.pack_propagate(False)

        # Left: Status indicator with dot
        status_left = ctk.CTkFrame(self.status_bar, fg_color="transparent")
        status_left.pack(side="left", padx=10, fill="y")

        self.status_dot = ctk.CTkLabel(status_left, text="●", font=("Segoe UI", 16), text_color="red")
        self.status_dot.pack(side="left")

        self.status_text = ctk.CTkLabel(status_left, text="OFF", font=FONT_BOLD, text_color="white")
        self.status_text.pack(side="left", padx=5)

        # Separator
        ctk.CTkFrame(self.status_bar, fg_color=THEME_ACCENT, width=2).pack(side="left", fill="y", pady=8)

        # Center: Metrics
        metrics_frame = ctk.CTkFrame(self.status_bar, fg_color="transparent")
        metrics_frame.pack(side="left", expand=True, fill="both", padx=10)

        # FPS
        fps_frame = ctk.CTkFrame(metrics_frame, fg_color="transparent")
        fps_frame.pack(side="left", padx=15)
        ctk.CTkLabel(fps_frame, text="FPS", font=FONT_SMALL, text_color="gray").pack()
        self.fps_label = ctk.CTkLabel(fps_frame, text="0", font=FONT_BOLD, text_color=THEME_ACCENT)
        self.fps_label.pack()

        # Success Rate
        rate_frame = ctk.CTkFrame(metrics_frame, fg_color="transparent")
        rate_frame.pack(side="left", padx=15)
        ctk.CTkLabel(rate_frame, text="SUCCESS", font=FONT_SMALL, text_color="gray").pack()
        self.rate_label = ctk.CTkLabel(rate_frame, text="100%", font=FONT_BOLD, text_color="#00ff00")
        self.rate_label.pack()

        # Session Count
        session_frame = ctk.CTkFrame(metrics_frame, fg_color="transparent")
        session_frame.pack(side="left", padx=15)
        ctk.CTkLabel(session_frame, text="SESSION", font=FONT_SMALL, text_color="gray").pack()
        self.session_label = ctk.CTkLabel(session_frame, text="0", font=FONT_BOLD, text_color="white")
        self.session_label.pack()

        # Latency (for RDP mode)
        latency_frame = ctk.CTkFrame(metrics_frame, fg_color="transparent")
        latency_frame.pack(side="left", padx=15)
        ctk.CTkLabel(latency_frame, text="ADAPT", font=FONT_SMALL, text_color="gray").pack()
        self.latency_label = ctk.CTkLabel(latency_frame, text="1.0x", font=FONT_BOLD, text_color="white")
        self.latency_label.pack()

        # Separator
        ctk.CTkFrame(self.status_bar, fg_color=THEME_ACCENT, width=2).pack(side="left", fill="y", pady=8)

        # Right: Mini widget toggle
        self.mini_btn = ctk.CTkButton(
            self.status_bar, text="Mini", width=50, height=30,
            fg_color=THEME_ACCENT, text_color="black",
            hover_color="#cc7000", corner_radius=8,
            command=self.toggle_mini_widget
        )
        self.mini_btn.pack(side="right", padx=10)

    def update_status_bar(self):
        """Update status bar metrics"""
        # Update status
        if self.fishing_active:
            self.status_dot.configure(text_color="#00ff00")
            self.status_text.configure(text="FISHING")
        else:
            self.status_dot.configure(text_color="red")
            self.status_text.configure(text="OFF")

        # Update FPS
        self.fps_label.configure(text=f"{self.current_fps:.0f}")

        # Update success rate
        rate = self.success_rate * 100
        self.rate_label.configure(text=f"{rate:.0f}%")
        if rate >= 80:
            self.rate_label.configure(text_color="#00ff00")
        elif rate >= 50:
            self.rate_label.configure(text_color=THEME_ACCENT)
        else:
            self.rate_label.configure(text_color="red")

        # Update session count
        self.session_label.configure(text=str(self.session_loops))

        # Update adaptive multiplier
        self.latency_label.configure(text=f"{self.adaptive_delay.latency_multiplier:.1f}x")

        # Update tray tooltip
        self.tray_manager.update_tooltip()

        # Schedule next update
        self.after(500, self.update_status_bar)

    def toggle_mini_widget(self):
        """Toggle the floating mini widget"""
        if self.mini_widget and self.mini_widget.winfo_exists():
            self.mini_widget.destroy()
            self.mini_widget = None
            self.mini_btn.configure(text="Mini")
        else:
            self.mini_widget = MiniWidget(self)
            self.mini_btn.configure(text="Hide")

    def create_fishing_tab(self):
        frame = ctk.CTkScrollableFrame(self.tab_fishing, fg_color="transparent")
        frame.pack(fill="both", expand=True)

        # Status Card
        st = ctk.CTkFrame(frame, fg_color="#111111", border_color=THEME_ACCENT, border_width=1, corner_radius=15)
        st.pack(fill="x", padx=5, pady=5)
        self.fishing_status_lbl = ctk.CTkLabel(st, text="Fishing: OFF", font=FONT_BOLD, text_color="red")
        self.fishing_status_lbl.pack(pady=5)
        self.overlay_status = ctk.CTkLabel(st, text="Overlay: OFF", font=FONT_MAIN, text_color="gray")
        self.overlay_status.pack(pady=5)

        # --- COLLAPSIBLE SECTIONS ---

        # Settings Section
        settings_section = CollapsibleSection(frame, "Settings")
        settings_section.pack(fill="x", padx=5)
        settings_content = settings_section.get_content()

        self.create_toggle(settings_content, "RDP / Compat Mode", self.use_rdp_mode_var, command=self.update_store_ui)
        self.create_toggle(settings_content, "Auto Zoom Reset", self.auto_zoom_var)
        self.create_input(settings_content, "Kp:", self.kp_var)
        self.create_input(settings_content, "Kd:", self.kd_var)
        self.create_input(settings_content, "Base Timeout:", self.timeout_var)
        self.create_input(settings_content, "Color Tolerance (0=exact):", self.color_tolerance_var)

        # Auto Purchase Section
        purchase_section = CollapsibleSection(frame, "Auto Purchase")
        purchase_section.pack(fill="x", padx=5)
        purchase_content = purchase_section.get_content()

        self.create_toggle(purchase_content, "Active", self.auto_purchase_var)
        self.create_input(purchase_content, "Amount:", self.amount_var)
        self.create_input(purchase_content, "Loops/Buy:", self.loops_var)

        ctk.CTkLabel(purchase_content, text="Coordinates:", font=FONT_BOLD).pack(anchor="w", pady=5)
        for i in range(1, 5):
            self.create_point_row(purchase_content, i, f"Pt {i}")

        # Auto Store Section
        store_section = CollapsibleSection(frame, "Auto Store")
        store_section.pack(fill="x", padx=5)
        self.store_frame = store_section.get_content()
        self.update_store_ui()

        # Auto Bait Section
        bait_section = CollapsibleSection(frame, "Auto Bait")
        bait_section.pack(fill="x", padx=5)
        bait_content = bait_section.get_content()

        self.create_toggle(bait_content, "Enable", self.auto_bait_var)
        self.create_point_row(bait_content, 6, "Pt 6 (Select)")

        # Webhook Section
        webhook_section = CollapsibleSection(frame, "Webhook")
        webhook_section.pack(fill="x", padx=5)
        webhook_content = webhook_section.get_content()

        ctk.CTkEntry(webhook_content, textvariable=self.webhook_url_var, placeholder_text="Discord Webhook URL", corner_radius=10).pack(fill="x", pady=5)

        # Actions Section
        actions_section = CollapsibleSection(frame, "Actions")
        actions_section.pack(fill="x", padx=5)
        actions_content = actions_section.get_content()

        btn_row = ctk.CTkFrame(actions_content, fg_color="transparent")
        btn_row.pack(fill="x", pady=5)
        ctk.CTkButton(btn_row, text="Save Settings", fg_color=THEME_ACCENT, text_color="black", hover_color="#cc7000", corner_radius=10, command=self.save_config).pack(side="left", padx=5, expand=True)
        ctk.CTkButton(btn_row, text="Test Webhook", fg_color="#333333", hover_color="#444444", corner_radius=10, command=self.webhook_manager.test).pack(side="right", padx=5, expand=True)
        ctk.CTkButton(actions_content, text="Update Check", fg_color="#333333", hover_color="#444444", corner_radius=10, command=self.check_for_updates).pack(fill="x", pady=5)

    def update_store_ui(self):
        for widget in self.store_frame.winfo_children():
            widget.destroy()

        self.create_toggle(self.store_frame, "Enable", self.item_check_var)
        self.create_input(self.store_frame, "Rod Key (1-9):", self.rod_key_var)
        self.create_point_row(self.store_frame, 5, "Pt 5 (Store)")

        if self.use_rdp_mode_var.get():
            ctk.CTkLabel(self.store_frame, text="RDP Mode: Pixel Check Active", text_color=THEME_ACCENT).pack(anchor="w")
            self.create_point_row(self.store_frame, 7, "Pt 7 (Check)")

            # NEW: Configurable thresholds
            threshold_frame = ctk.CTkFrame(self.store_frame, fg_color="transparent")
            threshold_frame.pack(fill="x", pady=5)
            ctk.CTkLabel(threshold_frame, text="Pixel Thresholds:", font=FONT_BOLD, text_color=THEME_ACCENT).pack(anchor="w")

            self.create_input(self.store_frame, "Saturation Thresh:", self.saturation_threshold_var)
            self.create_input(self.store_frame, "Brightness Low:", self.brightness_low_var)
            self.create_input(self.store_frame, "Brightness High:", self.brightness_high_var)
        else:
            ctk.CTkLabel(self.store_frame, text="Local Mode: OCR Active (No Pt 7 needed)", text_color="#00ff00").pack(anchor="w")

    def create_reroll_tab(self):
        ctk.CTkLabel(self.tab_reroll, text="Race Reroll Bot", font=FONT_TITLE, text_color=THEME_ACCENT).pack(pady=20)
        self.create_point_row(self.tab_reroll, 8, "Pt 8 (Reroll Button)")
        self.reroll_status_lbl = ctk.CTkLabel(self.tab_reroll, text="Reroll: OFF", font=FONT_BOLD, text_color="red")
        self.reroll_status_lbl.pack(pady=10)

    # --- UI HELPERS ---
    def create_section(self, p, txt):
        ctk.CTkLabel(p, text=txt, font=FONT_BOLD, text_color=THEME_ACCENT).pack(anchor="w", padx=10, pady=(15, 2))
        ctk.CTkFrame(p, height=2, fg_color=THEME_ACCENT).pack(fill="x", padx=10, pady=2)

    def create_toggle(self, p, txt, var, **kwargs):
        ctk.CTkSwitch(p, text=txt, variable=var, switch_width=40, switch_height=20, **kwargs).pack(anchor="w", pady=2)

    def create_input(self, p, lbl, var):
        f = ctk.CTkFrame(p, fg_color="transparent")
        f.pack(fill="x", pady=2)
        ctk.CTkLabel(f, text=lbl).pack(side="left")
        ctk.CTkEntry(f, textvariable=var, width=80, corner_radius=10).pack(side="right")

    def create_point_row(self, p, idx, txt):
        f = ctk.CTkFrame(p, fg_color="transparent")
        f.pack(fill="x", pady=2)
        ctk.CTkLabel(f, text=txt).pack(side="left")
        self.point_labels[idx] = ctk.CTkLabel(f, text="Not Set", text_color="red", font=("Consolas", 10))
        self.point_labels[idx].pack(side="right", padx=5)
        ctk.CTkButton(f, text="Set", width=50, fg_color=THEME_ACCENT, text_color="black", hover_color="#cc7000", corner_radius=10, command=lambda: self.capture_pt(idx)).pack(side="right")

    # --- LOGIC ---
    def capture_pt(self, idx):
        self.status_msg.configure(text=f"Click for Pt {idx}...", text_color=THEME_ACCENT)

        def on_click(x, y, button, pressed):
            if pressed:
                self.point_coords[idx] = (x, y)
                self.after(0, lambda: self.point_labels[idx].configure(text=f"{x},{y}", text_color="#00ff00"))
                return False

        pynput_mouse.Listener(on_click=on_click).start()

    def check_for_updates(self):
        try:
            repo_url = "https://api.github.com/repos/arielldev/gpo-fishing/commits/main"
            response = requests.get(repo_url, timeout=5)
            if response.status_code == 200:
                latest_hash = response.json()['sha'][:7]
                msg = f"Latest Commit: {latest_hash}\nClick OK to open GitHub."
                if messagebox.askokcancel("Update Check", msg):
                    import webbrowser
                    webbrowser.open("https://github.com/arielldev/gpo-fishing")
        except:
            pass

    def reset_afk_timer(self, event=None):
        self.last_user_activity = time.time()

    def check_auto_afk(self):
        if self.auto_afk_var.get() and self.fishing_active and not self.afk_mode_active:
            idle_time = time.time() - self.last_user_activity
            if idle_time > self.auto_afk_seconds_var.get():
                self.toggle_afk()
        self.after(1000, self.check_auto_afk)

    def toggle_afk(self):
        self.afk_mode_active = not self.afk_mode_active
        if self.afk_mode_active:
            self.title("AFK MODE - FISHING")
            self.afk_session_lbl.configure(text=str(self.session_loops))
            self.afk_total_lbl.configure(text=str(self.stats['total_caught'] + self.session_loops))
            self.afk_frame.place(x=0, y=0, relwidth=1, relheight=1)
            self.afk_frame.lift()
        else:
            self.title("Karoo Fish - Perfect Edition")
            self.afk_frame.place_forget()
        self.last_user_activity = time.time()

    def register_hotkeys(self):
        keyboard.unhook_all()
        keyboard.add_hotkey(self.hotkeys['toggle_loop'], lambda: self.after(0, self.toggle_loop))
        keyboard.add_hotkey(self.hotkeys['toggle_overlay'], lambda: self.after(0, self.toggle_overlay))
        keyboard.add_hotkey(self.hotkeys['exit'], lambda: self.after(0, self.exit_app))
        keyboard.add_hotkey(self.hotkeys['toggle_afk'], lambda: self.after(0, self.toggle_afk))

    def toggle_loop(self):
        if self.tabview.get() == "Fishing Bot":
            self.toggle_fishing()
        else:
            self.toggle_reroll()

    def toggle_fishing(self):
        self.fishing_active = not self.fishing_active
        if self.fishing_active:
            self.fishing_status_lbl.configure(text="Fishing: ON", text_color="#00ff00")
            if self.overlay_window:
                self.set_overlay_click_through(True)
            threading.Thread(target=self.run_fishing_loop, daemon=True).start()
        else:
            self.fishing_status_lbl.configure(text="Fishing: OFF", text_color="red")
            self.is_clicking = False
            pyautogui.mouseUp()
            if self.overlay_window:
                self.set_overlay_click_through(False)

    def toggle_reroll(self):
        self.reroll_active = not self.reroll_active
        if self.reroll_active:
            self.reroll_status_lbl.configure(text="Reroll: ON", text_color="#00ff00")
            threading.Thread(target=self.run_reroll_loop, daemon=True).start()
        else:
            self.reroll_status_lbl.configure(text="Reroll: OFF", text_color="red")

    def toggle_overlay(self):
        self.overlay_active = not self.overlay_active
        if self.overlay_active:
            self.overlay_status.configure(text="Overlay: ON", text_color=THEME_ACCENT)
            self.overlay_window = self.create_overlay_window(self.overlay_area, "Fishing Zone", THEME_ACCENT)
            self.ocr_overlay_window = self.create_overlay_window(self.ocr_overlay_area, "OCR Zone", THEME_ACCENT)

            if self.fishing_active:
                self.set_overlay_click_through(True)
        else:
            self.overlay_status.configure(text="Overlay: OFF", text_color="gray")
            self.destroy_overlay()

    def create_overlay_window(self, area_ref, title, color):
        win = tk.Toplevel(self)
        win.overrideredirect(True)
        win.attributes('-topmost', True)
        win.attributes('-alpha', 0.3)
        win.geometry(f"{area_ref['width']}x{area_ref['height']}+{area_ref['x']}+{area_ref['y']}")
        win.configure(bg=color)

        canvas = tk.Canvas(win, bg=color, highlightthickness=self.border_size, highlightbackground=color)
        canvas.pack(fill='both', expand=True)

        lbl = tk.Label(win, text=title, bg=color, fg="white", font=("Segoe UI", 10, "bold"))
        lbl.place(x=5, y=5)

        canvas.bind('<Button-1>', lambda e: self.on_overlay_down(e, win, area_ref))
        canvas.bind('<B1-Motion>', lambda e: self.on_overlay_drag(e, win, area_ref))
        canvas.bind('<Motion>', lambda e: self.on_overlay_move(e, win, canvas))

        return win

    def set_overlay_click_through(self, enable):
        for win in [self.overlay_window, self.ocr_overlay_window]:
            if not win:
                continue
            try:
                hwnd = win32gui.GetParent(win.winfo_id())
                style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                if enable:
                    style = style | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
                else:
                    style = style & ~win32con.WS_EX_TRANSPARENT
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
            except:
                pass

    def on_overlay_move(self, event, win, canvas):
        x, y = event.x, event.y
        w = win.winfo_width()
        h = win.winfo_height()
        edge = 15

        left = x < edge
        right = x > w - edge
        top = y < edge
        bottom = y > h - edge

        if top and left:
            canvas.config(cursor='top_left_corner')
        elif top and right:
            canvas.config(cursor='top_right_corner')
        elif bottom and left:
            canvas.config(cursor='bottom_left_corner')
        elif bottom and right:
            canvas.config(cursor='bottom_right_corner')
        elif left or right:
            canvas.config(cursor='sb_h_double_arrow')
        elif top or bottom:
            canvas.config(cursor='sb_v_double_arrow')
        else:
            canvas.config(cursor='fleur')

    def on_overlay_down(self, event, win, area_ref):
        win.start_x = event.x_root
        win.start_y = event.y_root
        win.win_x = win.winfo_x()
        win.win_y = win.winfo_y()
        win.win_w = win.winfo_width()
        win.win_h = win.winfo_height()

        edge = 15
        win.resize_edge = {'left': event.x < edge, 'right': event.x > win.win_w - edge, 'top': event.y < edge, 'bottom': event.y > win.win_h - edge}
        win.resizing = any(win.resize_edge.values())
        win.dragging = not win.resizing

    def on_overlay_drag(self, event, win, area_ref):
        dx = event.x_root - win.start_x
        dy = event.y_root - win.start_y

        if win.dragging:
            nx, ny = win.win_x + dx, win.win_y + dy
            win.geometry(f"+{nx}+{ny}")
            area_ref['x'] = nx
            area_ref['y'] = ny
        elif win.resizing:
            nx, ny, nw, nh = win.win_x, win.win_y, win.win_w, win.win_h
            if win.resize_edge['right']:
                nw += dx
            if win.resize_edge['bottom']:
                nh += dy
            if win.resize_edge['left']:
                nx += dx
                nw -= dx
            if win.resize_edge['top']:
                ny += dy
                nh -= dy

            nw, nh = max(50, nw), max(50, nh)
            win.geometry(f"{nw}x{nh}+{nx}+{ny}")

            area_ref['x'] = nx
            area_ref['y'] = ny
            area_ref['width'] = nw
            area_ref['height'] = nh

    def destroy_overlay(self):
        if self.overlay_window:
            self.overlay_window.destroy()
            self.overlay_window = None
        if self.ocr_overlay_window:
            self.ocr_overlay_window.destroy()
            self.ocr_overlay_window = None

    def exit_app(self):
        self.record_session()
        self.save_config()
        self.tray_manager.stop()
        if self.mini_widget:
            self.mini_widget.destroy()
        self.destroy_overlay()
        self.quit()
        sys.exit()

    # --- MOUSE/INPUT METHODS (RDP-friendly using pyautogui) ---
    def move_to(self, pt):
        if not pt:
            return
        x, y = int(pt[0]), int(pt[1])
        # Use ctypes for cursor positioning (works better over RDP)
        windll.user32.SetCursorPos(x, y)

    def click(self, pt, debug_name="Target", hold_time=0.01):
        if not pt:
            return
        x, y = int(pt[0]), int(pt[1])

        # Move cursor using ctypes
        windll.user32.SetCursorPos(x, y)
        time.sleep(0.05)

        # Anti-Roblox detection: small relative mouse movement
        windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
        time.sleep(0.05)

        action_start = time.time()

        # Use pyautogui for the actual click (more RDP-friendly)
        pyautogui.mouseDown()
        time.sleep(max(hold_time, 0.01))
        pyautogui.mouseUp()

        # Record response for adaptive delay
        self.adaptive_delay.record_response(action_start, time.time())

    def cast(self):
        if self.is_performing_action:
            return

        pt = self.point_coords[4]
        if not pt:
            return

        # Move to cast point
        x, y = int(pt[0]), int(pt[1])
        windll.user32.SetCursorPos(x, y)
        time.sleep(0.05)
        windll.user32.mouse_event(0x0001, 0, 1, 0, 0)  # Anti-detection
        time.sleep(0.05)

        # Hold click for casting
        hold_time = 1.9 if not self.use_rdp_mode_var.get() else 2.5
        pyautogui.mouseDown()
        time.sleep(hold_time)
        pyautogui.mouseUp()

        self.session_loops += 1
        self.last_cast_time = time.time()

        # Wait for cast animation
        wait_time = 2.5 if not self.use_rdp_mode_var.get() else 3.5
        time.sleep(wait_time)

    def perform_bait_select(self):
        self.bait_manager.select_top_bait()

    def perform_store_fruit(self, force_store=False):
        """Store devil fruit sequence - RDP-friendly version"""
        try:
            is_rdp = self.use_rdp_mode_var.get()
            hotkey_delay = 1.0 if is_rdp else 0.5
            click_delay = 2.0 if is_rdp else 1.0
            shift_delay = 0.5 if is_rdp else 0.3
            backspace_delay = 1.5 if is_rdp else 0.8

            if not force_store:
                p7 = self.point_coords.get(7)
                if p7:
                    with mss.mss() as sct:
                        b, g, r = self.get_pixel_color_at_pt(sct, p7)
                        saturation = max(b, g, r) - min(b, g, r)
                        brightness = (int(r) + int(g) + int(b)) / 3

                        # Use configurable thresholds
                        sat_thresh = self.saturation_threshold_var.get()
                        bright_low = self.brightness_low_var.get()
                        bright_high = self.brightness_high_var.get()

                        is_icon = (saturation < sat_thresh) and ((brightness < bright_low) or (brightness > bright_high))

                        if not is_icon:
                            # No fruit detected - just re-equip rod
                            time.sleep(hotkey_delay)
                            keyboard.press_and_release('1')
                            time.sleep(hotkey_delay)
                            keyboard.press_and_release(self.rod_key_var.get())
                            time.sleep(hotkey_delay)
                            return

            # STORE SEQUENCE (Fruit Confirmed)
            self.trigger_rare_catch_notification()
            self.webhook_manager.send_devil_fruit_drop()
            self.is_performing_action = True

            rod_key = self.rod_key_var.get()
            devil_fruit_key = '3'

            print("=== Auto Store Devil Fruit: Starting ===")

            # 1) Press devil fruit hotkey to select it
            keyboard.press_and_release(devil_fruit_key)
            print(f"  Pressed Devil Fruit Hotkey: {devil_fruit_key}")
            time.sleep(hotkey_delay)

            if not self.fishing_active:
                return

            # 2) Click store fruit point
            if self.point_coords.get(5):
                pt5 = self.point_coords[5]
                windll.user32.SetCursorPos(int(pt5[0]), int(pt5[1]))
                time.sleep(0.05)
                windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
                time.sleep(0.05)
                pyautogui.mouseDown()
                pyautogui.mouseUp()
                print(f"  Clicked Store Fruit Point: ({pt5[0]}, {pt5[1]})")
                time.sleep(click_delay)

            if not self.fishing_active:
                return

            # 3) Press shift
            keyboard.press_and_release('shift')
            print("  Pressed Shift")
            time.sleep(shift_delay)

            if not self.fishing_active:
                return

            # 4) Press backspace
            keyboard.press_and_release('backspace')
            print("  Pressed Backspace")
            time.sleep(backspace_delay)

            if not self.fishing_active:
                return

            # 5) Press shift again
            keyboard.press_and_release('shift')
            print("  Pressed Shift")
            time.sleep(shift_delay)

            # 6) Re-equip rod
            keyboard.press_and_release('1')
            time.sleep(hotkey_delay)
            keyboard.press_and_release(rod_key)
            time.sleep(hotkey_delay)

            # Move back to water point
            if self.point_coords.get(4):
                pt4 = self.point_coords[4]
                windll.user32.SetCursorPos(int(pt4[0]), int(pt4[1]))
            time.sleep(0.2)

            print("=== Auto Store Devil Fruit: Complete ===")

        except Exception as e:
            print(f"Store fruit error: {e}")
            self.is_performing_action = False
        finally:
            self.is_performing_action = False

    def get_pixel_color_at_pt(self, sct, pt):
        monitor = {"top": int(pt[1]), "left": int(pt[0]), "width": 1, "height": 1}
        img = np.array(sct.grab(monitor))
        return (img[0, 0, 0], img[0, 0, 1], img[0, 0, 2])

    def perform_auto_purchase_sequence(self):
        """Auto purchase bait sequence - RDP-friendly version matching GPOfishmacro8"""
        try:
            self.is_performing_action = True

            # Check required points (1=left/confirm, 2=middle/input, 3=right/buy, 4=water)
            if not all([self.point_coords[1], self.point_coords[2], self.point_coords[3], self.point_coords[4]]):
                print("Auto-purchase: Missing required points!")
                return

            self.webhook_manager.send_purchase(str(self.amount_var.get()))

            # RDP-friendly delays (matching working version)
            is_rdp = self.use_rdp_mode_var.get()
            e_delay = 3.0 if is_rdp else 1.5
            click_delay = 3.0 if is_rdp else 1.0
            type_delay = 3.0 if is_rdp else 1.0
            anti_detect_delay = 0.05

            # 1) Press 'e' to open shop
            keyboard.press_and_release('e')
            print("  Auto-purchase: Pressed 'e'")
            time.sleep(e_delay)

            if not self.fishing_active:
                return

            # 2) Click left point (first item/confirm)
            pt1 = self.point_coords[1]
            windll.user32.SetCursorPos(int(pt1[0]), int(pt1[1]))
            time.sleep(anti_detect_delay)
            windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
            time.sleep(anti_detect_delay)
            pyautogui.mouseDown()
            pyautogui.mouseUp()
            print(f"  Auto-purchase: Clicked Pt1 ({pt1[0]}, {pt1[1]})")
            time.sleep(click_delay)

            if not self.fishing_active:
                return

            # 3) Click middle point (amount input)
            pt2 = self.point_coords[2]
            windll.user32.SetCursorPos(int(pt2[0]), int(pt2[1]))
            time.sleep(anti_detect_delay)
            windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
            time.sleep(anti_detect_delay)
            pyautogui.mouseDown()
            pyautogui.mouseUp()
            print(f"  Auto-purchase: Clicked Pt2 ({pt2[0]}, {pt2[1]})")
            time.sleep(click_delay)

            if not self.fishing_active:
                return

            # 4) Type the amount
            amount_str = str(self.amount_var.get())
            keyboard.write(amount_str)
            print(f"  Auto-purchase: Typed amount: {amount_str}")
            time.sleep(type_delay)

            if not self.fishing_active:
                return

            # 5) Click left point again (confirm amount)
            windll.user32.SetCursorPos(int(pt1[0]), int(pt1[1]))
            time.sleep(anti_detect_delay)
            windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
            time.sleep(anti_detect_delay)
            pyautogui.mouseDown()
            pyautogui.mouseUp()
            print(f"  Auto-purchase: Clicked Pt1 again")
            time.sleep(click_delay)

            if not self.fishing_active:
                return

            # 6) Click right point (buy button)
            pt3 = self.point_coords[3]
            windll.user32.SetCursorPos(int(pt3[0]), int(pt3[1]))
            time.sleep(anti_detect_delay)
            windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
            time.sleep(anti_detect_delay)
            pyautogui.mouseDown()
            pyautogui.mouseUp()
            print(f"  Auto-purchase: Clicked Pt3 ({pt3[0]}, {pt3[1]})")
            time.sleep(click_delay)

            if not self.fishing_active:
                return

            # 7) Click middle point (close/confirm)
            windll.user32.SetCursorPos(int(pt2[0]), int(pt2[1]))
            time.sleep(anti_detect_delay)
            windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
            time.sleep(anti_detect_delay)
            pyautogui.mouseDown()
            pyautogui.mouseUp()
            print(f"  Auto-purchase: Clicked Pt2 (close)")
            time.sleep(click_delay)

            # Move back to water point
            pt4 = self.point_coords[4]
            windll.user32.SetCursorPos(int(pt4[0]), int(pt4[1]))
            time.sleep(0.2)

            print("  Auto-purchase: Complete!")

        except Exception as e:
            print(f"Auto-purchase error: {e}")
        finally:
            self.is_performing_action = False

    def perform_zoom_reset(self):
        if not self.auto_zoom_var.get():
            return
        for _ in range(10):
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -120, 0)
            time.sleep(0.05)
        time.sleep(0.2)
        for _ in range(3):
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, 120, 0)
            time.sleep(0.05)
        time.sleep(0.5)

    # --- FISHING LOOP (Based on working GPOfishmacro8 detection logic) ---
    def run_fishing_loop(self):
        """
        Main fishing loop using proven detection logic from GPOfishmacro8.
        Colors (RGB format, checked against BGRA image):
        - Blue bar: (85, 170, 255)
        - White line: (255, 255, 255)
        - Dark gray box: (25, 25, 25)
        """
        # Target colors in RGB format (matching working version)
        target_blue = np.array([85, 170, 255])      # Blue bar
        target_white = np.array([255, 255, 255])    # White line (target)
        target_dark_gray = np.array([25, 25, 25])   # Dark gray box (player control)

        # Color tolerance for detection
        tolerance = self.color_tolerance_var.get()

        use_mss_engine = self.use_rdp_mode_var.get()
        sct_engine = mss.mss() if use_mss_engine else None

        if not use_mss_engine:
            if self.camera is None:
                try:
                    self.camera = dxcam.create(output_color="BGRA")
                    self.camera.start(target_fps=60, video_mode=True)
                except:
                    use_mss_engine = True
                    sct_engine = mss.mss()

        self.perform_zoom_reset()
        if self.auto_purchase_var.get():
            self.perform_auto_purchase_sequence()
        if self.auto_bait_var.get():
            self.perform_bait_select()
        self.cast()

        was_detecting = False
        frame_counter = 0
        gc_counter = 0
        curr_w, curr_h = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)

        # Adaptive frame skipping
        skip_frames = 0
        frames_to_skip = 0
        last_detection_time = time.time()

        # FPS tracking
        fps_frame_count = 0
        fps_start_time = time.time()

        # PD control state
        last_dark_gray_y = None
        last_scan_time = time.time()
        gap_tolerance_multiplier = 2.0

        while self.fishing_active:
            try:
                if self.is_performing_action:
                    time.sleep(0.1)
                    continue

                # Adaptive frame skipping logic
                if skip_frames < frames_to_skip:
                    skip_frames += 1
                    time.sleep(0.005)
                    continue
                skip_frames = 0

                # Record frame timing for adaptive delay
                self.adaptive_delay.record_frame_time()

                # Watchdog timeout
                timeout_multiplier = self.adaptive_delay.latency_multiplier if self.use_rdp_mode_var.get() else 1.0
                if time.time() - self.last_cast_time > (self.timeout_var.get() * 1.3 + 10.0) * timeout_multiplier:
                    self.is_clicking = False
                    pyautogui.mouseUp()
                    self.perform_bait_select()
                    self.cast()
                    last_dark_gray_y = None
                    continue

                # Metrics Update
                frame_counter += 1
                if frame_counter >= 60:
                    curr_w, curr_h = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
                    if (curr_w > curr_h) != (self.base_width > self.base_height):
                        self.base_width, self.base_height = curr_w, curr_h
                    frame_counter = 0

                # GC
                gc_counter += 1
                if gc_counter >= 600:
                    gc.collect()
                    gc_counter = 0

                # FPS calculation
                fps_frame_count += 1
                fps_elapsed = time.time() - fps_start_time
                if fps_elapsed >= 1.0:
                    self.current_fps = fps_frame_count / fps_elapsed
                    fps_frame_count = 0
                    fps_start_time = time.time()

                # Get overlay geometry
                ox = self.overlay_area['x']
                oy = self.overlay_area['y']
                ow = self.overlay_area['width']
                oh = self.overlay_area['height']

                # Capture screenshot
                if use_mss_engine:
                    monitor = {"top": oy, "left": ox, "width": ow, "height": oh}
                    img = np.array(sct_engine.grab(monitor))
                else:
                    img_full = self.camera.get_latest_frame()
                    if img_full is None:
                        time.sleep(0.01)
                        continue
                    if np.max(img_full) == 0:
                        try:
                            self.camera.stop()
                            del self.camera
                            self.camera = dxcam.create(output_color="BGRA")
                            self.camera.start(target_fps=60, video_mode=True)
                            continue
                        except:
                            use_mss_engine = True
                            sct_engine = mss.mss()
                            continue
                    img = img_full[oy:oy + oh, ox:ox + ow]

                # Check for blue bar color (85, 170, 255) - mss/dxcam returns BGRA
                # img[:,:,2] = Red, img[:,:,1] = Green, img[:,:,0] = Blue
                if tolerance > 0:
                    # Tolerance-based matching
                    blue_diff = np.abs(img[:, :, 2].astype(np.int16) - target_blue[0]) + \
                                np.abs(img[:, :, 1].astype(np.int16) - target_blue[1]) + \
                                np.abs(img[:, :, 0].astype(np.int16) - target_blue[2])
                    blue_mask = blue_diff <= tolerance * 3
                else:
                    # Exact matching
                    blue_mask = (
                        (img[:, :, 2] == target_blue[0]) &
                        (img[:, :, 1] == target_blue[1]) &
                        (img[:, :, 0] == target_blue[2])
                    )

                blue_found = np.any(blue_mask)

                if not blue_found:
                    # No blue bar detected - fish caught or not fishing
                    if was_detecting:
                        was_detecting = False
                        self.is_clicking = False
                        pyautogui.mouseUp()
                        self.recent_catches.append(True)
                        if len(self.recent_catches) > 10:
                            self.recent_catches.pop(0)
                        self.success_rate = sum(self.recent_catches) / len(self.recent_catches)

                        if self.auto_purchase_var.get():
                            self.purchase_counter += 1
                            if self.purchase_counter >= self.loops_var.get():
                                self.perform_auto_purchase_sequence()
                                self.purchase_counter = 0
                        if self.item_check_var.get():
                            self.perform_store_fruit()
                        if self.auto_bait_var.get():
                            self.perform_bait_select()
                        self.cast()
                        last_dark_gray_y = None

                    # Adaptive: Increase skip frames when idle
                    time_since_detection = time.time() - last_detection_time
                    if time_since_detection > 2.0:
                        frames_to_skip = min(3, int(time_since_detection / 2))
                    else:
                        frames_to_skip = 0

                    # Idle: Check for Spawns
                    self.ocr_manager.scan_for_spawn()
                    time.sleep(0.02)
                    continue

                # Blue bar found - reset skip frames
                frames_to_skip = 0
                last_detection_time = time.time()
                was_detecting = True

                # Find all coordinates where blue exists
                y_coords, x_coords = np.where(blue_mask)
                if len(x_coords) == 0:
                    time.sleep(0.01)
                    continue

                # Get middle X column of the blue bar
                middle_x = int(np.mean(x_coords))

                # Get the column slice
                col_slice = img[:, middle_x, :]

                # Find gray boundary pixels (25, 25, 25) in this column
                if tolerance > 0:
                    gray_diff = np.abs(col_slice[:, 2].astype(np.int16) - target_dark_gray[0]) + \
                                np.abs(col_slice[:, 1].astype(np.int16) - target_dark_gray[1]) + \
                                np.abs(col_slice[:, 0].astype(np.int16) - target_dark_gray[2])
                    gray_mask = gray_diff <= tolerance * 3
                else:
                    gray_mask = (
                        (col_slice[:, 2] == target_dark_gray[0]) &
                        (col_slice[:, 1] == target_dark_gray[1]) &
                        (col_slice[:, 0] == target_dark_gray[2])
                    )

                if not np.any(gray_mask):
                    time.sleep(0.01)
                    continue

                gray_y_coords = np.where(gray_mask)[0]
                top_gray_y = gray_y_coords[0]
                bottom_gray_y = gray_y_coords[-1]

                # Get the slice between gray boundaries
                if bottom_gray_y <= top_gray_y:
                    time.sleep(0.01)
                    continue

                final_slice = col_slice[top_gray_y:bottom_gray_y + 1]

                # Find white line (255, 255, 255) in the slice
                if tolerance > 0:
                    white_diff = np.abs(final_slice[:, 2].astype(np.int16) - target_white[0]) + \
                                 np.abs(final_slice[:, 1].astype(np.int16) - target_white[1]) + \
                                 np.abs(final_slice[:, 0].astype(np.int16) - target_white[2])
                    white_mask = white_diff <= tolerance * 3
                else:
                    white_mask = (
                        (final_slice[:, 2] == target_white[0]) &
                        (final_slice[:, 1] == target_white[1]) &
                        (final_slice[:, 0] == target_white[2])
                    )

                if not np.any(white_mask):
                    time.sleep(0.01)
                    continue

                white_y_coords = np.where(white_mask)[0]
                white_height = white_y_coords[-1] - white_y_coords[0] + 1
                middle_white_y = (white_y_coords[0] + white_y_coords[-1]) // 2

                # Find dark gray box (25, 25, 25) in the slice
                if tolerance > 0:
                    dark_diff = np.abs(final_slice[:, 2].astype(np.int16) - target_dark_gray[0]) + \
                                np.abs(final_slice[:, 1].astype(np.int16) - target_dark_gray[1]) + \
                                np.abs(final_slice[:, 0].astype(np.int16) - target_dark_gray[2])
                    dark_mask = dark_diff <= tolerance * 3
                else:
                    dark_mask = (
                        (final_slice[:, 2] == target_dark_gray[0]) &
                        (final_slice[:, 1] == target_dark_gray[1]) &
                        (final_slice[:, 0] == target_dark_gray[2])
                    )

                if not np.any(dark_mask):
                    time.sleep(0.01)
                    continue

                dark_y_coords = np.where(dark_mask)[0]

                # Group dark gray pixels with gap tolerance
                gap_tolerance = max(1, int(white_height * gap_tolerance_multiplier))
                groups = []
                current_group = [dark_y_coords[0]]

                for i in range(1, len(dark_y_coords)):
                    if dark_y_coords[i] - dark_y_coords[i - 1] <= gap_tolerance:
                        current_group.append(dark_y_coords[i])
                    else:
                        groups.append(current_group)
                        current_group = [dark_y_coords[i]]
                groups.append(current_group)

                # Find biggest group (the player's box)
                biggest_group = max(groups, key=len)
                biggest_group_middle = (biggest_group[0] + biggest_group[-1]) // 2

                # Calculate error: positive = white below dark (need to click), negative = white above dark (release)
                error = middle_white_y - biggest_group_middle

                # Calculate time delta for derivative
                current_time = time.time()
                time_delta = current_time - last_scan_time
                last_scan_time = current_time

                # PD Control
                kp = self.kp_var.get()
                kd = self.kd_var.get()

                # Calculate derivative term
                d_term = 0
                if last_dark_gray_y is not None and time_delta > 0.001:
                    dark_gray_velocity = (biggest_group_middle - last_dark_gray_y) / time_delta
                    d_term = -kd * dark_gray_velocity

                # PD output
                pd_output = kp * error + d_term

                # Update last position
                last_dark_gray_y = biggest_group_middle

                # Control logic:
                # If pd_output > 0: white is below dark gray, need to click (move down)
                # If pd_output < 0: white is above dark gray, need to release (move up)
                cast_delay = 3.0 * (self.adaptive_delay.latency_multiplier if self.use_rdp_mode_var.get() else 1.0)

                if time.time() - self.last_cast_time > cast_delay:
                    if pd_output > 0:
                        if not self.is_clicking:
                            pyautogui.mouseDown()
                            self.is_clicking = True
                    else:
                        if self.is_clicking:
                            pyautogui.mouseUp()
                            self.is_clicking = False

                time.sleep(0.01)

            except Exception as e:
                print(f"Loop error: {e}")
                time.sleep(0.5)

    def run_reroll_loop(self):
        sct = mss.mss()
        while self.reroll_active:
            try:
                p8 = self.point_coords.get(8)
                if p8:
                    pt = self.get_scaled_point(p8)
                    monitor = {"top": pt[1], "left": pt[0], "width": 1, "height": 1}
                    img = np.array(sct.grab(monitor))
                    b, g, r = img[0, 0, 0], img[0, 0, 1], img[0, 0, 2]
                    # Gold check
                    if abs(r - 179) < 35 and abs(g - 122) < 35 and abs(b - 0) < 35:
                        self.click(p8, "Reroll")
                time.sleep(0.1)
            except:
                pass

    def get_scaled_point(self, pt):
        return (int(pt[0]), int(pt[1]))


if __name__ == "__main__":
    app = KarooFish()
    app.mainloop()
