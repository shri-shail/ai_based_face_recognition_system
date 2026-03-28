import customtkinter as ctk
import cv2
from PIL import Image
import threading
from pyzbar.pyzbar import decode
import time
import json
import os
try:
    import winsound
except ImportError:
    winsound = None

class ScanQRFrame(ctk.CTkFrame):
    def __init__(self, master, db_manager, **kwargs):
        super().__init__(master, **kwargs)
        self.db_manager = db_manager
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.main_container = ctk.CTkFrame(self)
        self.main_container.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        self.title_label = ctk.CTkLabel(self.main_container, text="QR Code Attendance", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=10)
        
        self.camera_label = ctk.CTkLabel(self.main_container, text="Press Start Scanner")
        self.camera_label.pack(expand=True, fill="both", padx=10, pady=10)
        
        self.controls_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.controls_frame.pack(pady=10)
        
        self.start_btn = ctk.CTkButton(self.controls_frame, text="Start Scanner", command=self.start_camera)
        self.start_btn.pack(side="left", padx=10)
        
        self.stop_btn = ctk.CTkButton(self.controls_frame, text="Stop Scanner", command=self.stop_camera, state="disabled")
        self.stop_btn.pack(side="left", padx=10)
        
        self.status_label = ctk.CTkLabel(self.main_container, text="Status: Ready", font=ctk.CTkFont(size=16))
        self.status_label.pack(pady=10)
        
        self.cap = None
        self.is_running = False

    def start_camera(self):
        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        threading.Thread(target=self.video_loop, daemon=True).start()

    def stop_camera(self):
        self.is_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text="Camera Stopped", text_color="gray")

    def beep(self):
        if winsound:
            threading.Thread(target=lambda: winsound.Beep(1000, 200), daemon=True).start()

    def video_loop(self):
        self.cap = cv2.VideoCapture(0)
        
        # Protect against destroyed window call
        if not getattr(self, "winfo_exists", lambda: False)():
            if self.cap: self.cap.release()
            return
            
        if not self.cap.isOpened():
            if self.winfo_exists():
                self.after(0, lambda: self.status_label.configure(text="Error: Cannot open camera", text_color="red"))
                self.after(0, lambda: self.start_btn.configure(state="normal"))
                self.after(0, lambda: self.stop_btn.configure(state="disabled"))
            self.is_running = False
            return

        recognition_cooldown = 0
        last_scanned_id = None

        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                break
                
            if recognition_cooldown > 0:
                recognition_cooldown -= 1
            else:
                last_scanned_id = None # Reset cooldown memory

            # Detect and Decode QR
            decoded_objects = decode(frame)
            for obj in decoded_objects:
                # Draw bounding box
                points = obj.polygon
                if len(points) == 4:
                    pts = [(int(p.x), int(p.y)) for p in points]
                    for i in range(4):
                        cv2.line(frame, pts[i], pts[(i+1)%4], (0, 255, 0), 3)

                qr_data = obj.data.decode('utf-8')
                
                if recognition_cooldown == 0:
                    try:
                        data_dict = json.loads(qr_data)
                        s_id = data_dict.get("student_id")
                        
                        if s_id and s_id != last_scanned_id:
                            self.beep()
                            success, msg = self.db_manager.mark_attendance(s_id)
                            
                            if self.winfo_exists():
                                if success:
                                    self.after(0, lambda text=f"Attendance Scanned for ID: {s_id}", c="green": self.status_label.configure(text=text, text_color=c))
                                else:
                                    self.after(0, lambda text=f"ID {s_id}: {msg}", c="orange": self.status_label.configure(text=text, text_color=c))
                                    
                            last_scanned_id = s_id
                            recognition_cooldown = 50 # Prevent rapid duplicate scanning
                    except json.JSONDecodeError:
                        if self.winfo_exists():
                            self.after(0, lambda: self.status_label.configure(text="Invalid QR Code Format", text_color="red"))
                            recognition_cooldown = 20

            # Update GUI Image safely
            if self.winfo_exists():
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb_frame)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(640, 480))
                self.after(0, lambda image=ctk_img: getattr(self, "camera_label", None) and self.camera_label.winfo_exists() and self.camera_label.configure(image=image, text=""))
            
            time.sleep(0.03)

        self.cap.release()
        if self.winfo_exists():
            self.after(0, lambda: getattr(self, "camera_label", None) and self.camera_label.winfo_exists() and self.camera_label.configure(image=None, text="Press Start Scanner"))

    def destroy(self):
        self.is_running = False
        if self.cap:
            self.cap.release()
        super().destroy()
