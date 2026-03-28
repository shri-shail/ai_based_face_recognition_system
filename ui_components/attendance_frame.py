import customtkinter as ctk
import cv2
from PIL import Image
import threading
import face_recognition
from pyzbar.pyzbar import decode
import time
import os
import json
import numpy as np
try:
    import winsound
except ImportError:
    winsound = None

class AttendanceFrame(ctk.CTkFrame):
    def __init__(self, master, db_manager, **kwargs):
        super().__init__(master, **kwargs)
        self.db_manager = db_manager
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.main_container = ctk.CTkFrame(self)
        self.main_container.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        self.title_label = ctk.CTkLabel(self.main_container, text="Scanner Portal", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=10)
        
        # Mode selector
        self.mode_var = ctk.StringVar(value="Mode 3: Hybrid (QR + Face)")
        self.mode_selector = ctk.CTkOptionMenu(
            self.main_container, 
            values=["Mode 1: Face Only", "Mode 2: QR Only", "Mode 3: Hybrid (QR + Face)"],
            variable=self.mode_var,
            width=250
        )
        self.mode_selector.pack(pady=5)
        
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
        self.known_encodings = []
        self.current_faces = []
        
    def beep(self):
        if winsound:
            threading.Thread(target=lambda: winsound.Beep(1000, 200), daemon=True).start()

    def error_beep(self):
        if winsound:
            threading.Thread(target=lambda: winsound.Beep(400, 500), daemon=True).start()

    def load_encodings(self):
        self.status_label.configure(text="Loading 128-d DB encodings...", text_color="blue")
        self.known_encodings = self.db_manager.get_all_student_encodings()
        self.status_label.configure(text=f"Loaded {len(self.known_encodings)} student memories.", text_color="green")

    def start_camera(self):
        self.load_encodings()
        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.mode_selector.configure(state="disabled")
        threading.Thread(target=self.video_loop, daemon=True).start()

    def stop_camera(self):
        self.is_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.mode_selector.configure(state="normal")
        self.status_label.configure(text="Scanner Stopped", text_color="gray")

    def mark_success(self, student_id, student_name):
        self.beep()
        success, msg = self.db_manager.mark_attendance(student_id)
        if self.winfo_exists():
            if success:
                self.after(0, lambda text=f"Attendance Marked for: {student_name} ({student_id})", c="green": self.status_label.configure(text=text, text_color=c))
            else:
                self.after(0, lambda text=f"ID {student_id}: {msg}", c="orange": self.status_label.configure(text=text, text_color=c))

    def video_loop(self):
        self.cap = cv2.VideoCapture(0)
        if not getattr(self, "winfo_exists", lambda: False)():
            if self.cap: self.cap.release()
            return
            
        if not self.cap.isOpened():
            if self.winfo_exists():
                self.after(0, lambda: self.status_label.configure(text="Error: Cannot open camera", text_color="red"))
                self.after(0, lambda: self.start_btn.configure(state="normal"))
                self.after(0, lambda: self.stop_btn.configure(state="disabled"))
                self.after(0, lambda: self.mode_selector.configure(state="normal"))
            self.is_running = False
            return

        frame_count = 0
        recognition_cooldown = 0
        last_scanned_id = None

        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                break
                
            frame_count += 1
            if recognition_cooldown > 0:
                recognition_cooldown -= 1
            else:
                last_scanned_id = None

            mode = self.mode_var.get()
            
            # --- QR CODE LOGIC (Applies to Mode 2 & 3) ---
            if "QR" in mode or "Hybrid" in mode:
                decoded_objects = decode(frame)
                for obj in decoded_objects:
                    pts = [(int(p.x), int(p.y)) for p in obj.polygon]
                    if len(pts) == 4:
                        for i in range(4):
                            cv2.line(frame, pts[i], pts[(i+1)%4], (255, 0, 0), 3)

                    if recognition_cooldown == 0:
                        try:
                            qr_data = obj.data.decode('utf-8')
                            data_dict = json.loads(qr_data)
                            s_id = data_dict.get("student_id")
                            
                            if s_id and s_id != last_scanned_id:
                                # Retrieve student details from known_encodings
                                student_record = next((s for s in self.known_encodings if s['student_id'] == s_id), None)
                                
                                if not student_record:
                                    if self.winfo_exists():
                                        self.after(0, lambda: self.status_label.configure(text="QR ID not in Database!", text_color="red"))
                                        self.error_beep()
                                    recognition_cooldown = 40
                                    continue

                                if "Mode 2" in mode:
                                    # QR ONLY -> Mark directly
                                    self.mark_success(s_id, student_record['name'])
                                    last_scanned_id = s_id
                                    recognition_cooldown = 40
                                
                                elif "Mode 3" in mode:
                                    # HYBRID -> Trigger face validation on current frame!
                                    self.hybrid_face_verification(frame.copy(), student_record)
                                    last_scanned_id = s_id # avoid spamming hybrid check
                                    recognition_cooldown = 60
                                    
                        except json.JSONDecodeError:
                            pass


            # --- FACE LOGIC (Applies to Mode 1) ---
            if "Mode 1" in mode:
                # Draw tracked faces
                if hasattr(self, 'current_faces'):
                    for (top, right, bottom, left), name, color in self.current_faces:
                        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                        cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)

                if frame_count % 15 == 0 and recognition_cooldown == 0:
                    threading.Thread(target=self.face_only_verification, args=(frame.copy(),), daemon=True).start()
                    recognition_cooldown = 30
            else:
                self.current_faces = []

            # UI Frame Refresh
            if self.winfo_exists():
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb_frame)
                h = 480 if "Mode 1" in mode or "Hybrid" in mode else 360 # Adjust size for performance
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(640, h))
                self.after(0, lambda image=ctk_img: getattr(self, "camera_label", None) and self.camera_label.winfo_exists() and self.camera_label.configure(image=image, text=""))
            
            time.sleep(0.03)

        self.cap.release()
        if self.winfo_exists():
            self.after(0, lambda: getattr(self, "camera_label", None) and self.camera_label.winfo_exists() and self.camera_label.configure(image=None, text="Press Start Scanner"))

    # Mode 1 Threading
    def face_only_verification(self, frame):
        try:
            # Resize frame for faster face recognition processing
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            face_locations = face_recognition.face_locations(rgb_small_frame)
            
            new_current_faces = []
            if face_locations:
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                
                # Pre-calculate known encodings
                known_encs = [np.array(s['encoding']) for s in self.known_encodings]
                
                for face_loc, encoding in zip(face_locations, face_encodings):
                    name = "Unknown"
                    color = (0, 0, 255) # Red for Unknown
                    
                    if known_encs:
                        matches = face_recognition.compare_faces(known_encs, encoding, tolerance=0.5)
                        face_distances = face_recognition.face_distance(known_encs, encoding)
                        best_match_index = np.argmin(face_distances)
                        
                        if matches[best_match_index]:
                            best = self.known_encodings[best_match_index]
                            name = best['name']
                            color = (0, 255, 0) # Green for Match
                            # Mark success
                            self.mark_success(best['student_id'], best['name'])
                    
                    # Scale back face locations since frame was scaled to 1/4 size
                    top, right, bottom, left = face_loc
                    top *= 4
                    right *= 4
                    bottom *= 4
                    left *= 4
                    
                    new_current_faces.append(((top, right, bottom, left), name, color))
            
            self.current_faces = new_current_faces
        except Exception as e:
            print(f"Face verification error: {e}")

    # Mode 3 Synchronous
    def hybrid_face_verification(self, frame, student_record):
        try:
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            if self.winfo_exists():
                self.after(0, lambda: self.status_label.configure(text=f"QR Found: {student_record['name']}. Verifying Face...", text_color="blue"))
            
            face_locations = face_recognition.face_locations(rgb_small_frame)
            
            if not face_locations:
                if self.winfo_exists():
                    self.after(0, lambda text=f"Anti-Cheating Logs: No face found near QR!", c="red": self.status_label.configure(text=text, text_color=c))
                    self.error_beep()
                return

            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            db_enc = np.array(student_record['encoding'])
            
            # Check all faces in frame against the memory of the QR scanned student
            found_match = False
            for encoding in face_encodings:
                match = face_recognition.compare_faces([db_enc], encoding, tolerance=0.5)[0]
                if match:
                    found_match = True
                    break
                    
            if found_match:
                self.mark_success(student_record['student_id'], student_record['name'])
            else:
                if self.winfo_exists():
                    self.after(0, lambda text=f"Anti-Cheating Logs: Face does NOT match QR!", c="red": self.status_label.configure(text=text, text_color=c))
                    self.error_beep()
        except Exception as e:
            if self.winfo_exists():
                self.after(0, lambda text=f"Evaluation Error: {e}", c="red": self.status_label.configure(text=text, text_color=c))

    def destroy(self):
        self.is_running = False
        if self.cap:
            self.cap.release()
        super().destroy()
