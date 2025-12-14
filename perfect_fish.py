import customtkinter as ctk
import tkinter as tk # Keep for some constants/Toplevel
from tkinter import messagebox
import threading
import keyboard
from pynput import keyboard as pynput_keyboard
from pynput import mouse as pynput_mouse
import sys
import ctypes
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

# --- CONFIGURATION ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue") # We will override with Orange manually

THEME_BG = "#000000"      # Pure Black
THEME_CARD = "#2b2b2b"    # Lighter Card Grey
THEME_ACCENT = "#ff8d00"  # Volt Orange
THEME_TEXT = "#ffffff"

FONT_MAIN = ("Segoe UI", 12)
FONT_BOLD = ("Segoe UI", 13, "bold")
FONT_TITLE = ("Segoe UI", 24, "bold")

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
# Try import EasyOCR safely
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
                # Initialize Reader (English, CPU only for compatibility)
                self.reader = easyocr.Reader(['en'], gpu=False) 
            except: pass

    def scan_for_spawn(self):
        # ... existing spawn logic ...

    def scan_for_catch(self):
        if not self.reader: return False
        try:
            # Capture Notification Area (Top Center)
            w, h = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
            monitor = {"top": int(h * 0.1), "left": int(w * 0.3), "width": int(w * 0.4), "height": int(h * 0.15)}
            with mss.mss() as sct: img = np.array(sct.grab(monitor))
            
            results = self.reader.readtext(img, detail=0)
            text = " ".join(results).lower()
            
            # Keywords
            if "caught" in text and ("fruit" in text or "mi" in text):
                return True
        except: pass
        return False

class WebhookManager:
    def __init__(self, app):
        self.app = app
        self.devil_fruit_count = 0 
    
    def send_webhook(self, title, description, color, fields=None, content=None):
        url = self.app.webhook_url_var.get()
        if not url or not self.app.notify_enabled_var.get(): return
        try:
            embed = {
                "title": title, "description": description, "color": color,
                "footer": {"text": "Karoo Fish - Perfect Edition"},
                "timestamp": datetime.utcnow().isoformat()
            }
            if fields: embed["fields"] = fields
            data = {"embeds": [embed], "username": "Karoo Bot"}
            if content: data["content"] = content
            
            requests.post(url, json=data, timeout=5)
        except: pass

    def send_fishing_progress(self):
        self.send_webhook(
            "🎣 Fishing Progress", 
            f"Caught **{self.app.session_loops}** fish this session!", 
            0x00ff00,
            [{"name": "Total Caught", "value": str(self.app.stats['total_caught'] + self.app.session_loops), "inline": True}]
        )

    def send_fruit_spawn(self, fruit_name):
        self.send_webhook(
            "🌟 Devil Fruit Spawned!", 
            f"A **{fruit_name}** has spawned!", 
            0xFFD700,
            [{"name": "Fruit", "value": fruit_name, "inline": True}],
            content="@here"
        )
    
    def send_devil_fruit_drop(self, drop_info=None):
        self.devil_fruit_count += 1
        desc = "Devil fruit detected and stored!"
        if drop_info: desc += f"\nInfo: {drop_info}"
        self.send_webhook(
            "🍎 Devil Fruit Caught!", 
            desc, 
            0x9c27b0,
            [
                {"name": "Session Fruits", "value": str(self.devil_fruit_count), "inline": True},
                {"name": "Total Fish", "value": str(self.app.stats['total_caught']), "inline": True}
            ],
            content="@everyone 🍎 RARE DROP!"
        )

    def send_purchase(self, amount):
        self.send_webhook(
            "🛒 Auto Purchase", 
            f"Successfully purchased **{amount}** bait.", 
            0xffa500,
            [{"name": "Status", "value": "Complete", "inline": True}]
        )
    
    def test(self):
        self.send_webhook("🧪 Test", "Webhook is working!", 0x0099ff)

class BaitManager:
    def __init__(self, app):
        self.app = app
        
    def select_top_bait(self):
        if not self.app.auto_bait_var.get(): return
        p6 = self.app.point_coords.get(6)
        if not p6: return
        try:
            self.app.click(p6, "Bait Select", hold_time=0.2 if not self.app.use_rdp_mode_var.get() else 0.5)
            time.sleep(0.5 if not self.app.use_rdp_mode_var.get() else 1.2)
            self.app.move_to(self.app.point_coords[4])
        except: pass

    def select_bait_before_cast(self):
        self.select_top_bait()

# --- MAIN APP ---
class KarooFish(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Karoo Fish - Perfect Edition")
        self.geometry("500x950")
        self.configure(fg_color=THEME_BG)
        self.attributes('-topmost', True)

        try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except: pass

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

        self.dpi_scale = self.get_dpi_scale()
        # Default areas
        w, h = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
        self.overlay_area = {'x': 100, 'y': 100, 'width': int(180 * self.dpi_scale), 'height': int(500 * self.dpi_scale)}
        self.ocr_overlay_area = {'x': int(w * 0.3), 'y': 0, 'width': int(w * 0.4), 'height': int(h * 0.2)}
        
        self.hotkeys = {'toggle_loop': 'f1', 'toggle_overlay': 'f2', 'exit': 'f3', 'toggle_afk': 'f4'}
        self.point_coords = {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None, 8: None}
        self.point_labels = {} 
        
        self.camera = None
        self.overlay_window = None
        self.ocr_overlay_window = None # New OCR Overlay
        self.stats = self.load_stats()
        self.webhook_manager = WebhookManager(self)
        self.bait_manager = BaitManager(self)
        self.ocr_manager = OCRManager(self)

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
        self.check_auto_afk()

    def load_images(self):
        try:
            # Background
            r = requests.get(VIVI_URL, stream=True)
            if r.status_code == 200:
                img = Image.open(r.raw)
                # Darken the background for readability
                img = ImageEnhance.Brightness(img).enhance(0.3) 
                self.bg_image = ctk.CTkImage(img, size=(500, 950))
                self.after(0, self.update_bg)
            
            # Profile
            r = requests.get(PROFILE_ICON_URL, stream=True)
            if r.status_code == 200:
                img = Image.open(r.raw)
                # Make circular mask
                mask = Image.new("L", (100, 100), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, 100, 100), fill=255)
                img = ImageOps.fit(img, (100, 100))
                img.putalpha(mask)
                self.profile_image = ctk.CTkImage(img, size=(60, 60))
                self.after(0, self.update_profile_icon)

        except Exception as e: print(f"Asset Error: {e}")

    def update_bg(self):
        if self.bg_image:
            self.bg_label = ctk.CTkLabel(self, text="", image=self.bg_image)
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            self.bg_label.lower() # Send to back

    def update_profile_icon(self):
        if hasattr(self, 'profile_btn') and self.profile_image:
            self.profile_btn.configure(image=self.profile_image, text="")

    # --- ASSETS ---
    def cache_notification_assets(self):
        try:
            temp_dir = tempfile.gettempdir()
            audio_path = os.path.join(temp_dir, "karoo_igor_v2.mp3")
            if not os.path.exists(audio_path):
                r = requests.get(NOTIF_AUDIO_URL)
                with open(audio_path, 'wb') as f: f.write(r.content)
            self.cached_audio_path = audio_path
        except: pass
        try:
            response = requests.get(NOTIF_ICON_URL)
            img = Image.open(BytesIO(response.content)).convert("RGBA")
            img = img.resize((64, 64), Image.Resampling.LANCZOS)
            self.cached_notif_icon = ImageTk.PhotoImage(img)
        except: pass

    def play_notification_sound(self):
        if not self.cached_audio_path: return
        def _play():
            try:
                ctypes.windll.winmm.mciSendStringW(f"close karoo_alert", None, 0, None)
                ctypes.windll.winmm.mciSendStringW(f'open "{self.cached_audio_path}" type mpegvideo alias karoo_alert', None, 0, None)
                ctypes.windll.winmm.mciSendStringW(f"play karoo_alert", None, 0, None)
            except: pass
        threading.Thread(target=_play, daemon=True).start()

    def get_dpi_scale(self):
        try: return self.winfo_fpixels('1i') / 96.0
        except: return 1.0

    # --- SAVE/LOAD ---
    def load_stats(self):
        if os.path.exists(STATS_FILE):
            try: return json.load(open(STATS_FILE, 'r'))
            except: pass
        return {"total_caught": 0, "history": [], "rare_catches": []}

    def save_stats(self):
        with open(STATS_FILE, 'w') as f: json.dump(self.stats, f, indent=4)

    def record_session(self):
        if self.session_loops > 0:
            self.stats["total_caught"] += self.session_loops
            entry = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "count": self.session_loops}
            self.stats["history"].insert(0, entry)
            self.stats["history"] = self.stats["history"][:50]
            self.save_stats()
            self.session_loops = 0

    def load_config(self):
        if not os.path.exists(CONFIG_FILE): return
        try:
            with open(CONFIG_FILE, 'r') as f: data = json.load(f)
            if "points" in data:
                for k, v in data["points"].items():
                    if v:
                        idx = int(k)
                        self.point_coords[idx] = tuple(v)
                        if idx in self.point_labels:
                            self.point_labels[idx].configure(text=f"{int(v[0])},{int(v[1])}", text_color="#00ff00")
            if "hotkeys" in data: self.hotkeys.update(data["hotkeys"])
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
            if "overlay_area" in data: self.overlay_area = data["overlay_area"]
            if "ocr_overlay_area" in data: self.ocr_overlay_area = data["ocr_overlay_area"]
        except: pass

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
            "rod_key": self.rod_key_var.get()
        }
        with open(CONFIG_FILE, 'w') as f: json.dump(data, f, indent=4)
        self.status_msg.configure(text="Settings Saved!", text_color="#00ff00")

    # --- UI ---
    def setup_ui(self):
        # 1. Background (Placeholder for image)
        self.bg_frame = ctk.CTkFrame(self, fg_color=THEME_BG)
        self.bg_frame.place(x=0, y=0, relwidth=1, relheight=1)

        # 2. Profile Header
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=20, pady=(20, 10))
        
        self.profile_btn = ctk.CTkButton(self.header, text="IMG", width=60, height=60, fg_color="transparent", border_width=2, border_color=THEME_ACCENT, corner_radius=30)
        self.profile_btn.pack(side="left")
        
        self.title_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        self.title_frame.pack(side="left", padx=15)
        ctk.CTkLabel(self.title_frame, text="Fisher", font=("Segoe UI", 20, "bold"), text_color="white").pack(anchor="w")
        ctk.CTkLabel(self.title_frame, text="The One And Only Karoo", font=("Segoe UI", 12), text_color=THEME_ACCENT).pack(anchor="w")

        # 3. Main Tabs
        self.tabview = ctk.CTkTabview(self, width=480, height=600, fg_color=THEME_CARD, corner_radius=15)
        self.tabview.pack(padx=10, pady=10, fill="both", expand=True)
        
        self.tab_fishing = self.tabview.add("Fishing Bot")
        self.tab_reroll = self.tabview.add("Race Reroll")
        
        self.create_fishing_tab()
        self.create_reroll_tab()
        
        # 4. Status Footer
        self.status_msg = ctk.CTkLabel(self, text="Ready", text_color=THEME_ACCENT)
        self.status_msg.pack(pady=5)

        # 5. AFK Overlay (Hidden)
        self.afk_frame = ctk.CTkFrame(self, fg_color=THEME_BG, corner_radius=0)
        
        ctk.CTkLabel(self.afk_frame, text="AFK MODE", font=("Segoe UI", 40, "bold"), text_color=THEME_ACCENT).place(relx=0.5, rely=0.2, anchor="center")
        ctk.CTkLabel(self.afk_frame, text="Session Catch:", font=("Segoe UI", 16)).place(relx=0.5, rely=0.4, anchor="center")
        self.afk_session_lbl = ctk.CTkLabel(self.afk_frame, text="0", font=("Segoe UI", 80, "bold"), text_color="white")
        self.afk_session_lbl.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkLabel(self.afk_frame, text="Total:", font=("Segoe UI", 14), text_color="gray").place(relx=0.5, rely=0.7, anchor="center")
        self.afk_total_lbl = ctk.CTkLabel(self.afk_frame, text="0", font=("Segoe UI", 24, "bold"))
        self.afk_total_lbl.place(relx=0.5, rely=0.75, anchor="center")
        
        ctk.CTkLabel(self.afk_frame, text="Press F4 to Resume", font=("Segoe UI", 12), text_color="gray").place(relx=0.5, rely=0.9, anchor="center")

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

        # Config Sections
        self.create_section(frame, "Settings")
        self.create_toggle(frame, "RDP / Compat Mode", self.use_rdp_mode_var, command=self.update_store_ui)
        self.create_toggle(frame, "Auto Zoom Reset", self.auto_zoom_var)
        self.create_input(frame, "Kp:", self.kp_var)
        self.create_input(frame, "Kd:", self.kd_var)
        self.create_input(frame, "Base Timeout:", self.timeout_var)

        self.create_section(frame, "Auto Purchase")
        self.create_toggle(frame, "Active", self.auto_purchase_var)
        self.create_input(frame, "Amount:", self.amount_var)
        self.create_input(frame, "Loops/Buy:", self.loops_var)
        
        ctk.CTkLabel(frame, text="Coordinates:", font=FONT_BOLD).pack(anchor="w", padx=10, pady=5)
        for i in range(1, 5): self.create_point_row(frame, i, f"Pt {i}")

        self.create_section(frame, "Auto Store")
        self.store_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self.store_frame.pack(fill="x")
        self.update_store_ui() # Build initial UI

        self.create_section(frame, "Auto Bait")
        self.create_toggle(frame, "Enable", self.auto_bait_var)
        self.create_point_row(frame, 6, "Pt 6 (Select)")
        
        self.create_section(frame, "Webhook")
        ctk.CTkEntry(frame, textvariable=self.webhook_url_var, placeholder_text="Discord Webhook URL", corner_radius=10).pack(fill="x", padx=10, pady=5)
        
        self.create_section(frame, "Actions")
        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(btn_row, text="Save Settings", fg_color=THEME_ACCENT, text_color="black", hover_color="#cc7000", corner_radius=10, command=self.save_config).pack(side="left", padx=5, expand=True)
        ctk.CTkButton(btn_row, text="Test Webhook", fg_color="#333333", hover_color="#444444", corner_radius=10, command=self.webhook_manager.test).pack(side="right", padx=5, expand=True)
        ctk.CTkButton(frame, text="Update Check", fg_color="#333333", hover_color="#444444", corner_radius=10, command=self.check_for_updates).pack(fill="x", padx=15, pady=5)

    def update_store_ui(self):
        for widget in self.store_frame.winfo_children(): widget.destroy()
        
        self.create_toggle(self.store_frame, "Enable", self.item_check_var)
        self.create_input(self.store_frame, "Rod Key (1-9):", self.rod_key_var)
        self.create_point_row(self.store_frame, 5, "Pt 5 (Store)")
        
        if self.use_rdp_mode_var.get():
            # RDP Mode: Needs Pt 7
            ctk.CTkLabel(self.store_frame, text="RDP Mode: Pixel Check Active", text_color=THEME_ACCENT).pack(anchor="w", padx=10)
            self.create_point_row(self.store_frame, 7, "Pt 7 (Check)")
        else:
            # Local Mode: Uses OCR
            ctk.CTkLabel(self.store_frame, text="Local Mode: OCR Active (No Pt 7 needed)", text_color="#00ff00").pack(anchor="w", padx=10)

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
        ctk.CTkSwitch(p, text=txt, variable=var, switch_width=40, switch_height=20, **kwargs).pack(anchor="w", padx=10, pady=2)

    def create_input(self, p, lbl, var):
        f = ctk.CTkFrame(p, fg_color="transparent")
        f.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(f, text=lbl).pack(side="left")
        ctk.CTkEntry(f, textvariable=var, width=80, corner_radius=10).pack(side="right")

    def create_point_row(self, p, idx, txt):
        f = ctk.CTkFrame(p, fg_color="transparent")
        f.pack(fill="x", padx=10, pady=2)
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
        except: pass

    # --- INPUT/LOGIC COPY ---
    def reset_afk_timer(self, event=None): self.last_user_activity = time.time()
    
    def check_auto_afk(self):
        if self.auto_afk_var.get() and self.fishing_active and not self.afk_mode_active:
            idle_time = time.time() - self.last_user_activity
            if idle_time > self.auto_afk_seconds_var.get(): self.toggle_afk()
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

    def toggle_loop(self):
        if self.tabview.get() == "Fishing Bot": self.toggle_fishing()
        else: self.toggle_reroll()

    def toggle_fishing(self):
        self.fishing_active = not self.fishing_active
        if self.fishing_active:
            self.fishing_status_lbl.configure(text="Fishing: ON", text_color="#00ff00")
            if self.overlay_window: self.set_overlay_click_through(True)
            threading.Thread(target=self.run_fishing_loop, daemon=True).start()
        else:
            self.fishing_status_lbl.configure(text="Fishing: OFF", text_color="red")
            self.is_clicking = False
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            if self.overlay_window: self.set_overlay_click_through(False)

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
                        
                        if self.fishing_active: self.set_overlay_click_through(True)        else:
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
        
        # Label
        lbl = tk.Label(win, text=title, bg=color, fg="white", font=("Segoe UI", 10, "bold"))
        lbl.place(x=5, y=5)

        # Bind events with specific reference to this window and area
        canvas.bind('<Button-1>', lambda e: self.on_overlay_down(e, win, area_ref))
        canvas.bind('<B1-Motion>', lambda e: self.on_overlay_drag(e, win, area_ref))
        
        return win

    def set_overlay_click_through(self, enable):
        for win in [self.overlay_window, self.ocr_overlay_window]:
            if not win: continue
            try:
                hwnd = win32gui.GetParent(win.winfo_id())
                style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                if enable: style = style | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
                else: style = style & ~win32con.WS_EX_TRANSPARENT
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
            except: pass

    # --- OVERLAY EVENTS ---
    def on_overlay_down(self, event, win, area_ref):
        win.start_x = event.x_root
        win.start_y = event.y_root
        win.win_x = win.winfo_x()
        win.win_y = win.winfo_y()
        win.win_w = win.winfo_width()
        win.win_h = win.winfo_height()
        
        edge = 15
        win.resize_edge = {'left': event.x < edge, 'right': event.x > win.win_w-edge, 'top': event.y < edge, 'bottom': event.y > win.win_h-edge}
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
            nw, nh = win.win_w, win.win_h
            if win.resize_edge['right']: nw += dx
            if win.resize_edge['bottom']: nh += dy
            nw, nh = max(50, nw), max(50, nh)
            win.geometry(f"{nw}x{nh}")
            area_ref['width'] = nw
            area_ref['height'] = nh

    # Removed unused mouse up/move for simplicity in multi-window
    
    def destroy_overlay(self):
        if self.overlay_window: self.overlay_window.destroy(); self.overlay_window = None
        if self.ocr_overlay_window: self.ocr_overlay_window.destroy(); self.ocr_overlay_window = None

    def exit_app(self):
        self.save_config()
        self.destroy_overlay()
        self.quit()
        sys.exit()

    # --- LOGIC METHODS (IDENTICAL TO PREVIOUS) ---
    # Mouse
    def move_to(self, pt):
        if not pt: return
        x, y = int(pt[0]), int(pt[1])
        if self.use_rdp_mode_var.get():
            cw, ch = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
            nx, ny = int(x * 65535 / cw), int(y * 65535 / ch)
            win32api.mouse_event(win32con.MOUSEEVENTF_ABSOLUTE | win32con.MOUSEEVENTF_MOVE, nx, ny, 0, 0)
        else:
            win32api.SetCursorPos((x, y))

    def click(self, pt, debug_name="Target", hold_time=0.25):
        if not pt: return
        self.move_to(pt)
        time.sleep(0.05 if self.use_rdp_mode_var.get() else 0.02)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(max(hold_time, self.rdp_click_hold))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    # Actions
    def cast(self):
        if self.is_performing_action: return
        self.click(self.point_coords[4], "Cast", hold_time=1.9)
        self.session_loops += 1
        self.last_cast_time = time.time()
        time.sleep(2.5)

    def perform_bait_select(self):
        self.bait_manager.select_top_bait()

    def perform_store_fruit(self, force_store=False):
        try:
            # RDP TIMING
            is_rdp = self.use_rdp_mode_var.get()
            hold_key = 0.2 if is_rdp else 0.1
            wait_step = 1.0 if is_rdp else 0.3
            
            # CHECK (Pixel)
            if not force_store:
                p7 = self.point_coords.get(7)
                if p7:
                    with mss.mss() as sct:
                        b, g, r = self.get_pixel_color_at_pt(sct, p7)
                        saturation = max(b, g, r) - min(b, g, r)
                        brightness = (int(r) + int(g) + int(b)) / 3
                        # LOGIC: Empty = Colorful. Fruit = B/W Icon.
                        is_icon = (saturation < 20) and ((brightness < 40) or (brightness > 210))
                        
                        if not is_icon:
                            time.sleep(wait_step)
                            keyboard.press('1'); time.sleep(hold_key); keyboard.release('1')
                            time.sleep(0.5)
                            keyboard.press(self.rod_key_var.get()); time.sleep(hold_key); keyboard.release(self.rod_key_var.get())
                            time.sleep(1.0)
                            return
            
            # STORE SEQUENCE (Fruit Confirmed)
            self.trigger_rare_catch_notification()
            self.webhook_manager.send_devil_fruit_drop()
            self.is_performing_action = True 
            
            rod_key = self.rod_key_var.get()
            
            # UNEQUIP ROD
            keyboard.press(rod_key); time.sleep(hold_key); keyboard.release(rod_key); time.sleep(wait_step)
            # EQUIP FRUIT (3)
            keyboard.press('3'); time.sleep(hold_key); keyboard.release('3'); time.sleep(wait_step)
            # STORE CLICK
            if self.point_coords.get(5):
                for i in range(3):
                    self.click(self.point_coords[5], f"Store", hold_time=0.2)
                    time.sleep(0.5 if is_rdp else 0.4)
            time.sleep(wait_step)
            # DROP / BACKSPACE
            keyboard.press('backspace'); time.sleep(hold_key); keyboard.release('backspace')
            
            # Wait for drop animation
            time.sleep(3.0 if is_rdp else 1.0)
            
            # RE-EQUIP ROD (Reset Strategy: 1 -> Rod)
            keyboard.press('1'); time.sleep(hold_key); keyboard.release('1')
            time.sleep(0.5)
            keyboard.press(rod_key); time.sleep(hold_key); keyboard.release(rod_key)
            time.sleep(1.0)
            
            self.move_to(self.point_coords[4]); time.sleep(0.2)
        except: 
            self.is_performing_action = False
        finally: 
            self.is_performing_action = False

    # ... (rest) ...

    def run_fishing_loop(self):
        # ... (setup) ...
        
        while self.fishing_active:
            # ... (capture/detect) ...
                
                if len(col_indices) == 0:
                    detection_streak = 0
                    if was_detecting:
                        was_detecting = False
                        self.is_clicking = False
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                        self.recent_catches.append(True)
                        if len(self.recent_catches) > 10: self.recent_catches.pop(0)
                        self.success_rate = sum(self.recent_catches) / len(self.recent_catches)
                        
                        if self.auto_purchase_var.get():
                            self.purchase_counter += 1
                            if self.purchase_counter >= self.loops_var.get(): self.perform_auto_purchase_sequence(); self.purchase_counter = 0
                        
                        # HYBRID STORE CHECK
                        if self.item_check_var.get(): 
                            if not self.use_rdp_mode_var.get():
                                # Local Mode: Check OCR First
                                if self.ocr_manager.scan_for_catch():
                                    self.perform_store_fruit(force_store=True)
                                else:
                                    # Fallback to Pixel Check just in case
                                    self.perform_store_fruit()
                            else:
                                # RDP Mode: Pixel Check Only
                                self.perform_store_fruit()

                        if self.auto_bait_var.get(): self.perform_bait_select()
                        self.cast()
                    del img, img_full
                    
                    # Idle: Check for Spawns
                    self.ocr_manager.scan_for_spawn()
                    
                    time.sleep(0.02)
                    continue

    def get_pixel_color_at_pt(self, sct, pt):
        monitor = {"top": int(pt[1]), "left": int(pt[0]), "width": 1, "height": 1}
        img = np.array(sct.grab(monitor))
        return (img[0,0,0], img[0,0,1], img[0,0,2])

    def perform_auto_purchase_sequence(self):
        try:
            self.is_performing_action = True 
            if not all([self.point_coords[1], self.point_coords[2], self.point_coords[3], self.point_coords[4]]): return
            self.webhook_manager.send_purchase(str(self.amount_var.get()))
            is_rdp = self.use_rdp_mode_var.get()
            delay_e = 2.0 if is_rdp else self.purchase_delay_after_key
            hold = 0.5 if is_rdp else 0.2
            step = 1.5 if is_rdp else 0.6

            keyboard.press('e'); time.sleep(0.1); keyboard.release('e')
            time.sleep(delay_e) 
            self.click(self.point_coords[1], "Pt 1", hold_time=hold); time.sleep(step) 
            self.click(self.point_coords[2], "Pt 2", hold_time=hold); time.sleep(step)
            
            for char in str(self.amount_var.get()): keyboard.write(char); time.sleep(0.1 if is_rdp else 0.05)
            time.sleep(0.5)
            
            self.click(self.point_coords[1], "Pt 1", hold_time=hold)
            time.sleep(1.5 if is_rdp else 0.8) 
            
            # Safety Loop (Reverted)
            sct = mss.mss()
            target_bgr = self.get_pixel_color_at_pt(sct, self.point_coords[3])
            safety_strikes = 0
            while safety_strikes < 10: 
                self.click(self.point_coords[3], "Pt 3", hold_time=0.2); time.sleep(0.3)
                self.click(self.point_coords[2], "Pt 2", hold_time=0.2); time.sleep(0.3)
                current_bgr = self.get_pixel_color_at_pt(sct, self.point_coords[3])
                if sum(abs(c - t) for c, t in zip(current_bgr, target_bgr)) > 50: break
                else: safety_strikes += 1
            
            self.move_to(self.point_coords[4]); time.sleep(0.5)
        except: pass
        finally: self.is_performing_action = False

    def perform_zoom_reset(self):
        if not self.auto_zoom_var.get(): return
        for _ in range(10): win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -120, 0); time.sleep(0.05)
        time.sleep(0.2)
        for _ in range(3): win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, 120, 0); time.sleep(0.05)
        time.sleep(0.5)

    def run_fishing_loop(self):
        target_color = np.array([0xff, 0xaa, 0x55], dtype=np.uint8) # BGR
        use_mss_engine = self.use_rdp_mode_var.get()
        sct_engine = mss.mss() if use_mss_engine else None
        
        if not use_mss_engine:
            if self.camera is None: 
                try: 
                    self.camera = dxcam.create(output_color="BGR")
                    self.camera.start(target_fps=60, video_mode=True)
                except: 
                    use_mss_engine = True
                    sct_engine = mss.mss()

        self.perform_zoom_reset()
        if self.auto_purchase_var.get(): self.perform_auto_purchase_sequence()
        if self.auto_bait_var.get(): self.perform_bait_select()
        self.cast()
        
        was_detecting = False
        detection_streak = 0
        frame_counter = 0
        gc_counter = 0
        curr_w, curr_h = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)

        while self.fishing_active:
            img = None; img_full = None
            try:
                if self.is_performing_action: continue 

                # Watchdog
                if time.time() - self.last_cast_time > (self.timeout_var.get() * 1.3 + 10.0):
                    self.is_clicking = False
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                    self.perform_bait_select() 
                    self.cast()
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
                if gc_counter >= 600: gc.collect(); gc_counter = 0

                # Calc Geometry
                scale_x, scale_y = curr_w / self.base_width, curr_h / self.base_height
                ox = max(0, min(int(self.overlay_area['x'] * scale_x), curr_w - 1))
                oy = max(0, min(int(self.overlay_area['y'] * scale_y), curr_h - 1))
                ow = max(1, min(int(self.overlay_area['width'] * scale_x), curr_w - ox))
                oh = max(1, min(int(self.overlay_area['height'] * scale_y), curr_h - oy))

                # Capture
                if use_mss_engine:
                    monitor = {"top": oy, "left": ox, "width": ow, "height": oh}
                    img = np.array(sct_engine.grab(monitor))[:, :, :3]
                else:
                    img_full = self.camera.get_latest_frame()
                    if img_full is None: continue 
                    if np.max(img_full) == 0: # Black screen recovery
                        try: 
                            self.camera.stop(); del self.camera; self.camera = dxcam.create(output_color="BGR"); self.camera.start(target_fps=60, video_mode=True); continue
                        except: use_mss_engine = True; sct_engine = mss.mss(); continue
                    img = img_full[oy:oy+oh, ox:ox+ow]

                # Detection
                col_mask = np.any(np.all(img == target_color, axis=-1), axis=0)
                col_indices = np.where(col_mask)[0]
                
                if len(col_indices) == 0:
                    detection_streak = 0
                    if was_detecting:
                        was_detecting = False
                        self.is_clicking = False
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                        self.recent_catches.append(True)
                        if len(self.recent_catches) > 10: self.recent_catches.pop(0)
                        self.success_rate = sum(self.recent_catches) / len(self.recent_catches)
                        
                        if self.auto_purchase_var.get():
                            self.purchase_counter += 1
                            if self.purchase_counter >= self.loops_var.get(): self.perform_auto_purchase_sequence(); self.purchase_counter = 0
                        if self.item_check_var.get(): self.perform_store_fruit()
                        if self.auto_bait_var.get(): self.perform_bait_select()
                        self.cast()
                    del img, img_full
                    
                    # Idle: Check for Spawns
                    self.ocr_manager.scan_for_spawn()
                    
                    time.sleep(0.02)
                    continue

                min_c, max_c = col_indices[0], col_indices[-1]
                bar_img = img[:, min_c:max_c+1]
                dark_mask = np.any(np.all(bar_img == np.array([0x19, 0x19, 0x19], dtype=np.uint8), axis=-1), axis=1)
                white_mask = np.any(np.all(bar_img == np.array([0xff, 0xff, 0xff], dtype=np.uint8), axis=-1), axis=1)
                
                dark_indices = np.where(dark_mask)[0]
                white_indices = np.where(white_mask)[0]

                if len(white_indices) > 0 and len(dark_indices) > 0:
                    detection_streak += 1
                    if detection_streak >= 3:
                        was_detecting = True
                        white_center = np.mean(white_indices)
                        dark_center = np.mean(dark_indices)
                        raw_error = dark_center - white_center
                        normalized_error = raw_error / oh 
                        derivative = normalized_error - self.previous_error
                        self.previous_error = normalized_error
                        pd_output = (self.kp_var.get() * normalized_error) + (self.kd_var.get() * derivative)
                        
                        if pd_output > 0:
                            if time.time() - self.last_cast_time > 3.0: 
                                if not self.is_clicking:
                                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                                    self.is_clicking = True
                        else:
                            if self.is_clicking:
                                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                                self.is_clicking = False
                
                time.sleep(0.02)
                del img, img_full, col_mask, bar_img
            except: time.sleep(1)

    def run_reroll_loop(self):
        sct = mss.mss()
        while self.reroll_active:
            try:
                p8 = self.point_coords.get(8)
                if p8:
                    pt = self.get_scaled_point(p8)
                    monitor = {"top": pt[1], "left": pt[0], "width": 1, "height": 1}
                    img = np.array(sct.grab(monitor))
                    b, g, r = img[0,0,0], img[0,0,1], img[0,0,2]
                    # Gold check
                    if abs(r-179)<35 and abs(g-122)<35 and abs(b-0)<35:
                        self.click(p8, "Reroll")
                time.sleep(0.1)
            except: pass

    def get_scaled_point(self, pt):
        return (int(pt[0]), int(pt[1]))

if __name__ == "__main__":
    app = KarooFish()
    app.mainloop()
