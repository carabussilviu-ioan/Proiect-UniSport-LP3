import customtkinter as ctk
import tkintermapview
import csv
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import os
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Tuple, Optional
import json

# ===== CULORI PREMIUM =====
CLR_BG_DARK = "#0A0E27"         # Fundal ultra-dark
CLR_BG_MEDIUM = "#141B2D"       # Fundal medium
CLR_SIDEBAR = "#1A2332"         # Sidebar elegant
CLR_CARD = "#1F2937"            # Card container
CLR_ACCENT = "#00D9FF"          # Cyan accent (electric)
CLR_ACCENT_ALT = "#6366F1"      # Indigo secondary
CLR_SUCCESS = "#10B981"         # Green success
CLR_WARNING = "#F59E0B"         # Orange warning
CLR_DANGER = "#EF4444"          # Red danger
CLR_TEXT_PRIMARY = "#F1F5F9"    # Text white
CLR_TEXT_SECONDARY = "#94A3B8"  # Text gray
CLR_BORDER = "#334155"          # Border subtle
CLR_HOVER = "#2D3748"           # Hover effect

# ===== GRADIENT COLORS =====
GRADIENT_BLUE = ["#00D9FF", "#6366F1"]
GRADIENT_GREEN = ["#10B981", "#059669"]
GRADIENT_RED = ["#EF4444", "#DC2626"]

@dataclass
class TimeInterval:
    """Structură pentru intervale orare"""
    start_hour: int
    end_hour: int
    
    def overlaps(self, other: 'TimeInterval') -> bool:
        """Detectează dacă două intervale se suprapun"""
        return not (self.end_hour <= other.start_hour or self.start_hour >= other.end_hour)
    
    def contains_time(self, hour: int) -> bool:
        """Verifică dacă ora este în interval"""
        return self.start_hour <= hour < self.end_hour
    
    def duration_hours(self) -> int:
        """Durata intervalului în ore"""
        return self.end_hour - self.start_hour
    
    def __str__(self) -> str:
        return f"{self.start_hour:02d}:00 - {self.end_hour:02d}:00"


class ReservationConflictChecker:
    """Algoritm de verificare a conflictelor de program adaptat pentru CSV"""
    
    def __init__(self, csv_path: str = 'reservations.csv'):
        self.csv_path = csv_path
    
    def check_conflict(self, location: str, date: str, interval: TimeInterval) -> bool:
        """
        Verifică dacă există conflict pentru o locație, dată și interval citind din CSV
        Algoritm: NOT (end1 <= start2 OR start1 >= end2)
        """
        if not os.path.exists(self.csv_path):
            return False
            
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['location'] == location and row['date'] == date and row['status'] == 'confirmed':
                    existing_start = int(row['start_hour'])
                    existing_end = int(row['end_hour'])
                    existing_interval = TimeInterval(existing_start, existing_end)
                    if interval.overlaps(existing_interval):
                        return True
        return False
    
    def get_available_slots(self, location: str, date: str, 
                           opening_hour: int = 8, closing_hour: int = 22,
                           slot_duration: int = 2) -> List[TimeInterval]:
        """Returnează intervalele libere pentru o locație și dată"""
        booked = []
        if os.path.exists(self.csv_path):
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['location'] == location and row['date'] == date and row['status'] == 'confirmed':
                        booked.append(TimeInterval(int(row['start_hour']), int(row['end_hour'])))
        
        available = []
        current = opening_hour
        
        while current + slot_duration <= closing_hour:
            slot = TimeInterval(current, current + slot_duration)
            if not any(slot.overlaps(booked_slot) for booked_slot in booked):
                available.append(slot)
            current += slot_duration
        
        return available


@dataclass
class RoomSchedule:
    """Structură pentru program orar al unei săli"""
    location: str
    date: str
    hourly_status: dict  # {hour: {'status': 'free'|'booked', 'user': str or None}}
    
    def get_occupancy_percent(self) -> float:
        """Procentaj ocupare"""
        total = len(self.hourly_status)
        booked = sum(1 for h in self.hourly_status.values() if h['status'] == 'booked')
        return (booked / total * 100) if total > 0 else 0


class UniSportElite(ctk.CTk):
    """Aplicație profesională de management al rezervărilor sportive"""
    
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        
        self.title("🏆 UPT UniSport Elite Management System")
        self.geometry("1600x950")
        self.resizable(True, True)
        
        # Configurare fereastră
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Inițializare fișiere CSV
        self.csv_init()
        
        # Variabile sesiune
        self.current_user = None
        self.current_role = None
        self.selected_location = None
        self.selected_date = None
        self.theme_toggle = True
        
        # Facilități sportive
        self.facilities = {
            "Sala Amfiteatru B1": {
                "image": "amfiteatru.jpg",
                "description": "Amfiteatru",
                "capacity": 200,
                "amenities": ["Lighting", "Sound System", "Air Conditioning"]
            },
            "Sala Curs B2": {
                "image": "curs.jpg",
                "description": "Sală de curs standard",
                "capacity": 100,
                "amenities": ["Projector", "Whiteboard"]
            },
            "Lab C1": {
                "image": "lab.jpg",
                "description": "Laborator cu calculatoare și echipamente",
                "capacity": 20,
                "amenities": ["Computers", "Software", "Workstations"]
            },
            "Teren Fotbal": {
                "image": "fotbal.jpg",
                "description": "Teren fotbal cu gazon profesional",
                "capacity": 20,
                "amenities": ["Night Lighting", "Professional Turf"]
            },
            "Teren Tenis": {
                "image": "tenis.jpg",
                "description": "Teren tenis cu suprafață profesională",
                "capacity": 5,
                "amenities": ["Night Lighting", "Professional Court"]
            },
            "Teren Baschet": {
                "image": "baschet.jpg.webp",
                "description": "Teren baschet și iluminare",
                "capacity": 10,
                "amenities": ["Scoreboard", "Night Lighting", "Professional Court"]
            }
        }
        
        self.conflict_checker = ReservationConflictChecker()
        
        self.setup_login()
    
    def csv_init(self):
        """Inițializează fișierele CSV cu date demo dacă nu există"""
        
        # Inițializare users.csv cu userii echipei
        if not os.path.exists('users.csv'):
            with open('users.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['user_id', 'password', 'role', 'email', 'created_at'])
                time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Admin
                writer.writerow(['admin', 'admin123', 'admin', 'admin@upt.ro', time_now])
                # User Silviu
                writer.writerow(['silviu', 'silviu123', 'student', 'silviu.carabus@student.upt.ro', time_now])
                # User Sergiu
                writer.writerow(['sergiu', 'sergiu123', 'student', 'sergiu.dancau@student.upt.ro', time_now])
                # User Antonio
                writer.writerow(['antonio', 'antonio123', 'student', 'alexandru.dincea@student.upt.ro', time_now])

        # Inițializare facilities.csv
        if not os.path.exists('facilities.csv'):
            with open('facilities.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['facility_id', 'name', 'description', 'capacity', 'opening_hour', 'closing_hour'])
                facilities_demo = [
                    (1, "Sala Polivalentă A1", "Sală polivalentă cu parchet", 500, 8, 22),
                    (2, "Sala Curs B2", "Sală de curs standard", 100, 8, 22),
                    (3, "Lab C1", "Laborator cu calculatoare și echipamente", 50, 8, 22),
                    (4, "Teren Fotbal", "Teren fotbal profesional", 1000, 8, 22),
                    (5, "Teren Tenis", "Teren tenis profesional", 200, 8, 22),
                    (6, "Teren Baschet", "Teren baschet cu tablă și iluminare", 500, 8, 22)
                ]
                writer.writerows(facilities_demo)

        # Inițializare reservations.csv
        if not os.path.exists('reservations.csv'):
            with open('reservations.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['reservation_id', 'user_id', 'location', 'date', 'start_hour', 'end_hour', 'status', 'created_at'])
    
    def setup_login(self):
        """Interfață de login cu design premium și creditele echipei"""
        self.login_frame = ctk.CTkFrame(self, fg_color=CLR_BG_DARK)
        self.login_frame.grid(row=0, column=0, sticky="nsew")
        
        # Container principal
        container = ctk.CTkFrame(self.login_frame, fg_color="transparent")
        container.place(relx=0.5, rely=0.5, anchor="center")
        
        # Card de login
        card = ctk.CTkFrame(container, width=500, height=700, corner_radius=40, 
                           fg_color=CLR_CARD, border_width=2, border_color=CLR_BORDER)
        card.pack()
        card.pack_propagate(False)
        
        # Logo și titlu
        logo_frame = ctk.CTkFrame(card, fg_color="transparent")
        logo_frame.pack(pady=(80, 20))
        
        ctk.CTkLabel(logo_frame, text="UniSport Elite", font=("Inter", 48, "bold"), 
                    text_color=CLR_ACCENT).pack(pady=10)
        ctk.CTkLabel(logo_frame, text="Management System", font=("Inter", 16), 
                    text_color=CLR_TEXT_SECONDARY).pack()
        
        # Separator
        sep = ctk.CTkFrame(card, height=2, fg_color=CLR_BORDER)
        sep.pack(fill="x", padx=40, pady=20)
        
        # Username
        ctk.CTkLabel(card, text="🔐 Username", font=("Inter", 14, "bold"), 
                    text_color=CLR_TEXT_PRIMARY).pack(anchor="w", padx=40, pady=(20, 5))
        self.login_user_entry = ctk.CTkEntry(card, placeholder_text="Enter your username", 
                                            width=400, height=50, corner_radius=15,
                                            fg_color=CLR_BG_MEDIUM, border_color=CLR_ACCENT,
                                            border_width=2, text_color=CLR_TEXT_PRIMARY,
                                            font=("Inter", 14))
        self.login_user_entry.pack(padx=40, pady=(0, 20))
        
        # Password
        ctk.CTkLabel(card, text="🔑 Password", font=("Inter", 14, "bold"), 
                    text_color=CLR_TEXT_PRIMARY).pack(anchor="w", padx=40, pady=(20, 5))
        self.login_pass_entry = ctk.CTkEntry(card, placeholder_text="Enter your password", 
                                            show="●", width=400, height=50, corner_radius=15,
                                            fg_color=CLR_BG_MEDIUM, border_color=CLR_ACCENT,
                                            border_width=2, text_color=CLR_TEXT_PRIMARY,
                                            font=("Inter", 14))
        self.login_pass_entry.pack(padx=40, pady=(0, 40))
        
        # Sign In Button
        sign_in_btn = ctk.CTkButton(card, text="🚀 Sign In", font=("Inter", 16, "bold"),
                                    height=55, corner_radius=15, fg_color=CLR_ACCENT,
                                    text_color=CLR_BG_DARK, hover_color="#00B8D4",
                                    command=self.handle_login)
        sign_in_btn.pack(padx=40, pady=20, fill="x")

        # Footer cu echipa
        footer_frame = ctk.CTkFrame(self.login_frame, fg_color="transparent")
        footer_frame.pack(side="bottom", pady=30)
        
        echipa = ("Proiect realizat de: Cărăbuș Silviu-Ioan, Dăncău Sergiu-Dumitru, Dincea Alexandru-Antonio\n"
                  "ETCTI - Seria A - Anul II - Sg. 1.1, Sg 1.2, Sg. 3.1")
        
        ctk.CTkLabel(footer_frame, text=echipa, font=("Inter", 13), 
                    text_color=CLR_TEXT_SECONDARY, justify="center").pack()
    
    def handle_login(self):
        """Procesează login-ul din fișierul users.csv"""
        username = self.login_user_entry.get().strip()
        password = self.login_pass_entry.get().strip()
        
        if not username or not password:
            self.show_notification("❌ Error", "Please enter both username and password!", CLR_DANGER)
            return
        
        user_role = None
        
        if os.path.exists('users.csv'):
            with open('users.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['user_id'] == username and row['password'] == password:
                        user_role = row['role']
                        break
        
        if user_role:
            self.current_user = username
            self.current_role = user_role
            self.show_notification("✅ Success", f"Welcome back, {username.capitalize()}!", CLR_SUCCESS)
            self.login_frame.destroy()
            self.setup_dashboard()
        else:
            self.show_notification("❌ Error", "Invalid credentials!", CLR_DANGER)
            self.login_pass_entry.delete(0, "end")
    
    def show_notification(self, title: str, message: str, color: str):
        """Afișează notificare popup"""
        notif = ctk.CTkToplevel(self)
        notif.geometry("400x150")
        notif.resizable(False, False)
        notif.title(title)
        notif.configure(fg_color=CLR_CARD)
        
        # Icon și mesaj
        msg_frame = ctk.CTkFrame(notif, fg_color="transparent")
        msg_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(msg_frame, text=title, font=("Inter", 16, "bold"), 
                    text_color=color).pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(msg_frame, text=message, font=("Inter", 13), 
                    text_color=CLR_TEXT_SECONDARY, wraplength=350, justify="left").pack(anchor="w")
        
        # Auto-close
        self.after(2500, notif.destroy)
    
    def setup_dashboard(self):
        """Setup dashboard-ul principal"""
        main_container = ctk.CTkFrame(self, fg_color=CLR_BG_DARK)
        main_container.grid(row=0, column=0, sticky="nsew")
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(1, weight=1)
        
        # SIDEBAR
        self.sidebar = ctk.CTkFrame(main_container, width=280, fg_color=CLR_SIDEBAR, 
                                   corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        
        # Sidebar header
        sidebar_header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        sidebar_header.pack(fill="x", padx=20, pady=(40, 30))
        
        ctk.CTkLabel(sidebar_header, text="Unisport Elite", font=("Inter", 22, "bold"),
                    text_color=CLR_ACCENT).pack(pady=10)
        ctk.CTkLabel(sidebar_header, text=f"👤 {self.current_user.upper()}", 
                    font=("Inter", 12, "bold"), text_color=CLR_SUCCESS).pack()
        
        # Separator
        sep = ctk.CTkFrame(self.sidebar, height=1, fg_color=CLR_BORDER)
        sep.pack(fill="x", padx=20, pady=20)
        
        # Navigation buttons
        nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", padx=15, pady=20)
        
        if self.current_role == "student":
            self._create_nav_button(nav_frame, "📍 Book Facility", self.show_student_panel)
            self._create_nav_button(nav_frame, "📋 My Reservations", self.show_my_reservations)
        else:
            self._create_nav_button(nav_frame, "📅 Room Manager", self.show_room_manager)
        
        # Logout button
        logout_btn = ctk.CTkButton(self.sidebar, text="🚪 Logout", font=("Inter", 14, "bold"),
                                   height=50, corner_radius=12, fg_color=CLR_DANGER,
                                   hover_color="#DC2626", command=self.logout)
        logout_btn.pack(side="bottom", fill="x", padx=15, pady=20)
        
        # MAIN CONTENT AREA
        self.main_content = ctk.CTkFrame(main_container, fg_color=CLR_BG_DARK)
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_content.grid_rowconfigure(0, weight=1)
        self.main_content.grid_columnconfigure(0, weight=1)
        
        # Afișare panelul inițial
        if self.current_role == "student":
            self.show_student_panel()
        else:
            self.show_room_manager()
    
    def _create_nav_button(self, parent, text: str, command):
        """Crează buton de navigare"""
        btn = ctk.CTkButton(parent, text=text, font=("Inter", 13, "bold"),
                           height=50, corner_radius=12, fg_color=CLR_ACCENT,
                           text_color=CLR_BG_DARK, hover_color="#00B8D4",
                           command=command)
        btn.pack(fill="x", pady=8)
    
    def clear_main_content(self):
        """Curață area de conținut principal"""
        for widget in self.main_content.winfo_children():
            widget.destroy()
    
    def show_student_panel(self):
        """Panou student - rezervare facilități"""
        self.clear_main_content()
        
        main_frame = ctk.CTkScrollableFrame(self.main_content, fg_color=CLR_BG_DARK)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=30, pady=30)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Header
        header = ctk.CTkFrame(main_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 30))
        
        ctk.CTkLabel(header, text="📍 Book Your Facility", font=("Inter", 36, "bold"),
                    text_color=CLR_ACCENT).pack(anchor="w")
        ctk.CTkLabel(header, text="Select a facility and choose your preferred time slot",
                    font=("Inter", 14), text_color=CLR_TEXT_SECONDARY).pack(anchor="w", pady=(5, 0))
        
        # Facilities grid
        facilities_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        facilities_frame.grid(row=1, column=0, sticky="ew", pady=(0, 30))
        facilities_frame.grid_columnconfigure([0, 1], weight=1)
        
        for idx, (name, info) in enumerate(self.facilities.items()):
            self._create_facility_card(facilities_frame, name, info, idx % 2, idx // 2)
    
    def _create_facility_card(self, parent, name: str, info: dict, col: int, row: int):
        """Creează card pentru o facilitate"""
        card = ctk.CTkFrame(parent, fg_color=CLR_CARD, corner_radius=20, border_width=2,
                           border_color=CLR_BORDER)
        card.grid(row=row, column=col, sticky="ew", padx=15, pady=15)
        
        # Image
        try:
            img = Image.open(info['image'])
            img_resized = img.resize((300, 200), Image.Resampling.LANCZOS)
            ctk_image = ctk.CTkImage(light_image=img_resized, size=(300, 200))
            img_label = ctk.CTkLabel(card, image=ctk_image, text="")
            img_label.image = ctk_image
            img_label.pack(padx=15, pady=15)
        except:
            placeholder = ctk.CTkLabel(card, text=name, font=("Inter", 14, "bold"),
                                      text_color=CLR_ACCENT, width=300, height=200,
                                      fg_color=CLR_ACCENT, corner_radius=15)
            placeholder.pack(padx=15, pady=15)
        
        # Info
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkLabel(info_frame, text=name, font=("Inter", 18, "bold"),
                    text_color=CLR_TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(info_frame, text=info['description'], font=("Inter", 12),
                    text_color=CLR_TEXT_SECONDARY).pack(anchor="w", pady=5)
        
        # Amenities
        amenities_str = " • ".join(info['amenities'])
        ctk.CTkLabel(info_frame, text=f"✨ {amenities_str}", font=("Inter", 11),
                    text_color=CLR_SUCCESS).pack(anchor="w", pady=(10, 5))
        
        # Capacity
        ctk.CTkLabel(info_frame, text=f"👥 Capacity: {info['capacity']} people",
                    font=("Inter", 11), text_color=CLR_TEXT_SECONDARY).pack(anchor="w")
        
        # Book button
        book_btn = ctk.CTkButton(card, text="🎯 Book Now", font=("Inter", 13, "bold"),
                                height=45, corner_radius=12, fg_color=CLR_SUCCESS,
                                hover_color="#059669",
                                command=lambda: self.show_booking_dialog(name))
        book_btn.pack(fill="x", padx=15, pady=15)
    
    def _get_next_reservation_id(self) -> int:
        """Găsește următorul ID disponibil pentru rezervare în CSV"""
        next_id = 1
        if os.path.exists('reservations.csv'):
            with open('reservations.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['reservation_id'].isdigit() and int(row['reservation_id']) >= next_id:
                        next_id = int(row['reservation_id']) + 1
        return next_id

    def show_booking_dialog(self, facility_name: str):
        """Dialog de rezervare"""
        dialog = ctk.CTkToplevel(self)
        dialog.geometry("500x600")
        dialog.title(f"Book {facility_name}")
        dialog.configure(fg_color=CLR_CARD)
        
        # Content
        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=25, pady=25)
        
        ctk.CTkLabel(content, text=f"📍 {facility_name}", font=("Inter", 20, "bold"),
                    text_color=CLR_ACCENT).pack(pady=(0, 20))
        
        # Date
        ctk.CTkLabel(content, text="📅 Select Date:", font=("Inter", 13, "bold"),
                    text_color=CLR_TEXT_PRIMARY).pack(anchor="w", pady=(10, 5))
        date_entry = ctk.CTkEntry(content, placeholder_text="YYYY-MM-DD", height=45,
                                 fg_color=CLR_BG_MEDIUM, border_color=CLR_ACCENT,
                                 border_width=2)
        date_entry.pack(fill="x", pady=(0, 20))
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        # Time slots
        ctk.CTkLabel(content, text="⏰ Select Time Slot:", font=("Inter", 13, "bold"),
                    text_color=CLR_TEXT_PRIMARY).pack(anchor="w", pady=(10, 10))
        
        slots_frame = ctk.CTkFrame(content, fg_color="transparent")
        slots_frame.pack(fill="x", pady=(0, 20))
        
        selected_slot = ctk.StringVar(value="09:00-11:00")
        
        slots = ["08:00-10:00", "10:00-12:00", "12:00-14:00", "14:00-16:00", "16:00-18:00", "18:00-20:00"]
        
        for idx, slot in enumerate(slots):
            ctk.CTkRadioButton(slots_frame, text=f"⏱️ {slot}", font=("Inter", 12),
                              variable=selected_slot, value=slot, text_color=CLR_TEXT_PRIMARY,
                              border_color=CLR_ACCENT, fg_color=CLR_ACCENT).grid(row=idx//3, column=idx%3, padx=10, pady=5)
        
        # Buttons
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(20, 0))
        
        def confirm_booking():
            date = date_entry.get()
            slot = selected_slot.get()
            start_h = int(slot.split("-")[0].split(":")[0])
            end_h = int(slot.split("-")[1].split(":")[0])
            
            interval = TimeInterval(start_h, end_h)
            
            if self.conflict_checker.check_conflict(facility_name, date, interval):
                self.show_notification("⚠️ Conflict", "This time slot is already booked!", CLR_WARNING)
            else:
                # Adaugă rezervarea în CSV
                res_id = self._get_next_reservation_id()
                created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                with open('reservations.csv', 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([res_id, self.current_user, facility_name, date, start_h, end_h, 'confirmed', created_at])
                
                self.show_notification("✅ Success", f"Booking confirmed for {facility_name}!", CLR_SUCCESS)
                dialog.destroy()
                self.show_my_reservations()
        
        ctk.CTkButton(btn_frame, text="✅ Confirm Booking", font=("Inter", 13, "bold"),
                     height=45, fg_color=CLR_SUCCESS, hover_color="#059669",
                     command=confirm_booking).pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(btn_frame, text="❌ Cancel", font=("Inter", 13, "bold"),
                     height=45, fg_color=CLR_DANGER, hover_color="#DC2626",
                     command=dialog.destroy).pack(side="left", fill="x", expand=True)
    
    def show_my_reservations(self):
        """Afișează rezervările utilizatorului curent (citite din CSV)"""
        self.clear_main_content()
        
        main_frame = ctk.CTkScrollableFrame(self.main_content, fg_color=CLR_BG_DARK)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=30, pady=30)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Header
        header = ctk.CTkFrame(main_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 30))
        
        ctk.CTkLabel(header, text="📋 My Reservations", font=("Inter", 36, "bold"),
                    text_color=CLR_ACCENT).pack(anchor="w")
        
        # Fetch rezervatii
        reservations = []
        if os.path.exists('reservations.csv'):
            with open('reservations.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['user_id'] == self.current_user and row['status'] == 'confirmed':
                        reservations.append(row)
        
        # Sortează descrescător după dată
        reservations.sort(key=lambda x: x['date'], reverse=True)
        
        if not reservations:
            ctk.CTkLabel(main_frame, text="❌ No reservations yet. Book a facility now!",
                        font=("Inter", 14), text_color=CLR_TEXT_SECONDARY).grid(row=1, column=0, pady=40)
            return
        
        # Afișare rezervări
        for idx, res in enumerate(reservations):
            res_id = res['reservation_id']
            location = res['location']
            date = res['date']
            start_h = int(res['start_hour'])
            end_h = int(res['end_hour'])
            
            res_card = ctk.CTkFrame(main_frame, fg_color=CLR_CARD, corner_radius=15,
                                   border_width=2, border_color=CLR_SUCCESS)
            res_card.grid(row=idx+1, column=0, sticky="ew", pady=10)
            
            # Info
            info_frame = ctk.CTkFrame(res_card, fg_color="transparent")
            info_frame.pack(fill="x", padx=20, pady=15)
            
            ctk.CTkLabel(info_frame, text=f"📍 {location}", font=("Inter", 16, "bold"),
                        text_color=CLR_ACCENT).pack(anchor="w")
            ctk.CTkLabel(info_frame, text=f"📅 {date} | ⏰ {start_h:02d}:00 - {end_h:02d}:00",
                        font=("Inter", 13), text_color=CLR_TEXT_SECONDARY).pack(anchor="w", pady=(5, 0))
            
            # Cancel button
            def cancel_booking(rid=res_id):
                # Citește toate liniile, ignorând linia care trebuie ștearsă
                rows_to_keep = []
                with open('reservations.csv', 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    header_row = next(reader)
                    rows_to_keep.append(header_row)
                    for r in reader:
                        # Indexul 0 este 'reservation_id'
                        if r and str(r[0]) != str(rid):
                            rows_to_keep.append(r)
                
                # Rescrie CSV-ul
                with open('reservations.csv', 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerows(rows_to_keep)

                self.show_notification("✅ Cancelled", "Reservation cancelled successfully!", CLR_SUCCESS)
                self.show_my_reservations()
            
            cancel_btn = ctk.CTkButton(info_frame, text="🗑️ Cancel", font=("Inter", 11, "bold"),
                                      height=35, fg_color=CLR_DANGER, hover_color="#DC2626",
                                      command=cancel_booking)
            cancel_btn.pack(side="right", pady=(5, 0))
    
    def get_room_schedule(self, location: str, date: str) -> RoomSchedule:
        """Obține programul orar al unei săli citind din CSV"""
        hourly_status = {}
        booked_slots = []
        
        if os.path.exists('reservations.csv'):
            with open('reservations.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['location'] == location and row['date'] == date and row['status'] == 'confirmed':
                        booked_slots.append((int(row['start_hour']), int(row['end_hour']), row['user_id']))
        
        # Populează statusul pentru fiecare oră (8-22)
        for hour in range(8, 22):
            is_booked = False
            user_name = None
            
            for start, end, user in booked_slots:
                if start <= hour < end:
                    is_booked = True
                    user_name = user
                    break
            
            if is_booked:
                hourly_status[hour] = {'status': 'booked', 'user': user_name}
            else:
                hourly_status[hour] = {'status': 'free', 'user': None}
        
        return RoomSchedule(location, date, hourly_status)
    
    def show_room_manager(self):
        """Dashboard admin - Room Manager cu timeline orar"""
        self.clear_main_content()
        
        main_frame = ctk.CTkScrollableFrame(self.main_content, fg_color=CLR_BG_DARK)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=30, pady=30)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Header
        header = ctk.CTkFrame(main_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 30))
        
        ctk.CTkLabel(header, text="📅 Room Manager", font=("Inter", 36, "bold"),
                    text_color=CLR_ACCENT).pack(anchor="w")
        ctk.CTkLabel(header, text="Manage all facility reservations and schedules",
                    font=("Inter", 14), text_color=CLR_TEXT_SECONDARY).pack(anchor="w", pady=(5, 0))
        
        # Controls frame
        controls = ctk.CTkFrame(main_frame, fg_color=CLR_CARD, corner_radius=15,
                               border_width=2, border_color=CLR_BORDER)
        controls.grid(row=1, column=0, sticky="ew", pady=(0, 30))
        
        controls_content = ctk.CTkFrame(controls, fg_color="transparent")
        controls_content.pack(fill="x", padx=20, pady=20)
        
        # Facility selector
        ctk.CTkLabel(controls_content, text="📍 Select Facility:", font=("Inter", 12, "bold"),
                    text_color=CLR_TEXT_PRIMARY).pack(side="left", padx=(0, 10))
        
        facility_options = list(self.facilities.keys())
        facility_dropdown = ctk.CTkComboBox(controls_content, values=facility_options,
                                           state="readonly", width=250, height=40,
                                           fg_color=CLR_BG_MEDIUM, border_color=CLR_ACCENT,
                                           border_width=2, button_color=CLR_ACCENT)
        facility_dropdown.pack(side="left", padx=(0, 20))
        if facility_options:
            facility_dropdown.set(facility_options[0])
        
        # Date selector
        ctk.CTkLabel(controls_content, text="📅 Select Date:", font=("Inter", 12, "bold"),
                    text_color=CLR_TEXT_PRIMARY).pack(side="left", padx=(0, 10))
        
        date_entry = ctk.CTkEntry(controls_content, placeholder_text="YYYY-MM-DD", 
                                 width=150, height=40, fg_color=CLR_BG_MEDIUM,
                                 border_color=CLR_ACCENT, border_width=2)
        date_entry.pack(side="left", padx=(0, 20))
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        # Content frame pentru schedule
        schedule_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        schedule_frame.grid(row=2, column=0, sticky="ew")
        
        def load_schedule():
            # Clear previous schedule
            for widget in schedule_frame.winfo_children():
                widget.destroy()
            
            facility = facility_dropdown.get()
            date = date_entry.get()
            
            if not facility or not date:
                return
            
            # Get schedule
            schedule = self.get_room_schedule(facility, date)
            
            # Display facility info
            info_card = ctk.CTkFrame(schedule_frame, fg_color=CLR_CARD, corner_radius=15,
                                    border_width=2, border_color=CLR_ACCENT)
            info_card.pack(fill="x", pady=(0, 20))
            
            info_content = ctk.CTkFrame(info_card, fg_color="transparent")
            info_content.pack(fill="x", padx=20, pady=15)
            
            occupancy = schedule.get_occupancy_percent()
            occupancy_color = CLR_SUCCESS if occupancy <= 50 else CLR_WARNING if occupancy <= 75 else CLR_DANGER
            
            ctk.CTkLabel(info_content, text=f"📍 {facility}", font=("Inter", 18, "bold"),
                        text_color=CLR_ACCENT).pack(anchor="w", side="left")
            ctk.CTkLabel(info_content, text=f"📅 {date}", font=("Inter", 14),
                        text_color=CLR_TEXT_SECONDARY).pack(anchor="w", side="left", padx=(20, 0))
            ctk.CTkLabel(info_content, text=f"Occupancy: {occupancy:.1f}%", 
                        font=("Inter", 14, "bold"), text_color=occupancy_color).pack(anchor="e", side="right")
            
            # Timeline grid
            timeline_card = ctk.CTkFrame(schedule_frame, fg_color=CLR_CARD, corner_radius=15,
                                        border_width=2, border_color=CLR_BORDER)
            timeline_card.pack(fill="x")
            
            timeline_content = ctk.CTkFrame(timeline_card, fg_color="transparent")
            timeline_content.pack(fill="x", padx=20, pady=20)
            
            # Hour slots
            for idx, (hour, status) in enumerate(sorted(schedule.hourly_status.items())):
                slot_frame = ctk.CTkFrame(timeline_content, fg_color="transparent")
                slot_frame.pack(fill="x", pady=8)
                
                hour_label = f"{hour:02d}:00 - {hour+1:02d}:00"
                
                if status['status'] == 'free':
                    # FREE slot
                    slot_card = ctk.CTkFrame(slot_frame, fg_color=CLR_SUCCESS, corner_radius=12,
                                            border_width=2, border_color=CLR_SUCCESS)
                    slot_card.pack(fill="x")
                    
                    slot_inner = ctk.CTkFrame(slot_card, fg_color="transparent")
                    slot_inner.pack(fill="x", padx=15, pady=10)
                    
                    ctk.CTkLabel(slot_inner, text=f"🟢 {hour_label}", font=("Inter", 13, "bold"),
                                text_color="white").pack(side="left")
                    ctk.CTkLabel(slot_inner, text="AVAILABLE", font=("Inter", 11, "bold"),
                                text_color="white").pack(side="left", padx=(20, 0))
                    
                    def quick_book(h=hour, fac=facility, d=date):
                        self.show_quick_book_dialog(h, fac, d, schedule_frame, load_schedule)
                    
                    book_btn = ctk.CTkButton(slot_inner, text="➕ Book", font=("Inter", 11, "bold"),
                                            height=35, fg_color="#059669", hover_color="#047857",
                                            command=quick_book)
                    book_btn.pack(side="right")
                
                else:
                    # BOOKED slot
                    slot_card = ctk.CTkFrame(slot_frame, fg_color=CLR_DANGER, corner_radius=12,
                                            border_width=2, border_color=CLR_DANGER)
                    slot_card.pack(fill="x")
                    
                    slot_inner = ctk.CTkFrame(slot_card, fg_color="transparent")
                    slot_inner.pack(fill="x", padx=15, pady=10)
                    
                    ctk.CTkLabel(slot_inner, text=f"🔴 {hour_label}", font=("Inter", 13, "bold"),
                                text_color="white").pack(side="left")
                    ctk.CTkLabel(slot_inner, text=f"👤 {status['user']}", font=("Inter", 11),
                                text_color="white").pack(side="left", padx=(20, 0))
                    
                    # Căutăm ID-ul rezervării din CSV
                    res_id = None
                    if os.path.exists('reservations.csv'):
                        with open('reservations.csv', 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                if (row['location'] == facility and row['date'] == date and 
                                    int(row['start_hour']) == hour and row['user_id'] == status['user'] and 
                                    row['status'] == 'confirmed'):
                                    res_id = row['reservation_id']
                                    break
                    
                    def delete_reservation(rid=res_id):
                        if rid:
                            rows_to_keep = []
                            with open('reservations.csv', 'r', encoding='utf-8') as f:
                                reader = csv.reader(f)
                                header_row = next(reader)
                                rows_to_keep.append(header_row)
                                for r in reader:
                                    if r and str(r[0]) != str(rid):
                                        rows_to_keep.append(r)
                            
                            with open('reservations.csv', 'w', newline='', encoding='utf-8') as f:
                                writer = csv.writer(f)
                                writer.writerows(rows_to_keep)

                            self.show_notification("✅ Deleted", "Reservation deleted successfully!", CLR_SUCCESS)
                            load_schedule()
                    
                    delete_btn = ctk.CTkButton(slot_inner, text="🗑️ Delete", font=("Inter", 11, "bold"),
                                              height=35, fg_color="#991b1b", hover_color="#7f1d1d",
                                              command=delete_reservation)
                    delete_btn.pack(side="right")
        
        # Refresh button
        refresh_btn = ctk.CTkButton(controls_content, text="🔄 Load Schedule", font=("Inter", 12, "bold"),
                                   height=40, fg_color=CLR_ACCENT, hover_color="#00B8D4",
                                   command=load_schedule)
        refresh_btn.pack(side="left")
    
    def show_quick_book_dialog(self, hour: int, facility: str, date: str, parent_frame, callback):
        """Dialog rapid de booking pentru admin"""
        dialog = ctk.CTkToplevel(self)
        dialog.geometry("400x300")
        dialog.title(f"Quick Book - {hour:02d}:00")
        dialog.configure(fg_color=CLR_CARD)
        
        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=25, pady=25)
        
        ctk.CTkLabel(content, text=f"📅 Quick Booking", font=("Inter", 18, "bold"),
                    text_color=CLR_ACCENT).pack(pady=(0, 20))
        
        ctk.CTkLabel(content, text=f"Facility: {facility}", font=("Inter", 12),
                    text_color=CLR_TEXT_SECONDARY).pack(anchor="w")
        ctk.CTkLabel(content, text=f"Date: {date}", font=("Inter", 12),
                    text_color=CLR_TEXT_SECONDARY).pack(anchor="w")
        ctk.CTkLabel(content, text=f"Time: {hour:02d}:00 - {hour+1:02d}:00", font=("Inter", 12),
                    text_color=CLR_TEXT_SECONDARY).pack(anchor="w", pady=(0, 20))
        
        ctk.CTkLabel(content, text="👤 Student Username:", font=("Inter", 12, "bold"),
                    text_color=CLR_TEXT_PRIMARY).pack(anchor="w", pady=(10, 5))
        
        username_entry = ctk.CTkEntry(content, placeholder_text="Enter student username",
                                     height=40, fg_color=CLR_BG_MEDIUM,
                                     border_color=CLR_ACCENT, border_width=2)
        username_entry.pack(fill="x", pady=(0, 20))
        
        def confirm():
            username = username_entry.get().strip()
            
            if not username:
                self.show_notification("❌ Error", "Please enter a username!", CLR_DANGER)
                return
            
            # Verifică dacă utilizatorul există în users.csv
            user_exists = False
            if os.path.exists('users.csv'):
                with open('users.csv', 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row['user_id'] == username:
                            user_exists = True
                            break
            
            if not user_exists:
                self.show_notification("❌ Error", "User not found!", CLR_DANGER)
                return
            
            # Creează rezervarea
            res_id = self._get_next_reservation_id()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open('reservations.csv', 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([res_id, username, facility, date, hour, hour + 1, 'confirmed', created_at])
            
            self.show_notification("✅ Success", f"Booking created for {username}!", CLR_SUCCESS)
            dialog.destroy()
            callback()
        
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(20, 0))
        
        ctk.CTkButton(btn_frame, text="✅ Confirm", font=("Inter", 12, "bold"),
                     height=40, fg_color=CLR_SUCCESS, hover_color="#059669",
                     command=confirm).pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(btn_frame, text="❌ Cancel", font=("Inter", 12, "bold"),
                     height=40, fg_color=CLR_DANGER, hover_color="#DC2626",
                     command=dialog.destroy).pack(side="left", fill="x", expand=True)
    
    def logout(self):
        """Deconectare utilizator"""
        self.current_user = None
        self.current_role = None
        
        for widget in self.winfo_children():
            widget.destroy()
        
        self.setup_login()


if __name__ == "__main__":
    app = UniSportElite()
    app.mainloop()