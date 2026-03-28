import customtkinter as ctk
import cv2
from PIL import Image
import threading
import face_recognition
import time
import os
import json
import qrcode
import numpy as np

class RegisterFrame(ctk.CTkFrame):
    def __init__(self, master, db_manager, **kwargs):
        super().__init__(master, **kwargs)
        self.db_manager = db_manager
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self.form_frame = ctk.CTkFrame(self)
        self.form_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        ctk.CTkLabel(self.form_frame, text="Student Registration", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)
        
        self.student_id = ctk.CTkEntry(self.form_frame, placeholder_text="Student ID", width=300)
        self.student_id.pack(pady=10)
        
        self.name = ctk.CTkEntry(self.form_frame, placeholder_text="Full Name", width=300)
        self.name.pack(pady=10)
        
        self.email = ctk.CTkEntry(self.form_frame, placeholder_text="Email", width=300)
        self.email.pack(pady=10)
        
        self.course = ctk.CTkEntry(self.form_frame, placeholder_text="Course (e.g., Computer Science)", width=300)
        self.course.pack(pady=10)
        
        self.capture_btn = ctk.CTkButton(self.form_frame, text="Capture Images & Generate QR", command=self.start_capture)
        self.capture_btn.pack(pady=10)
        
        self.regen_qr_btn = ctk.CTkButton(self.form_frame, text="Regenerate QR Code", command=self.regenerate_qr, state="disabled")
        self.regen_qr_btn.pack(pady=5)
        
        self.progress_bar = ctk.CTkProgressBar(self.form_frame, width=300)
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)
        
        self.status_label = ctk.CTkLabel(self.form_frame, text="")
        self.status_label.pack(pady=10)
        
        self.capture_count_label = ctk.CTkLabel(self.form_frame, text="Images: 0/10", font=ctk.CTkFont(size=12))
        self.capture_count_label.pack(pady=5)
        
        self.camera_frame = ctk.CTkFrame(self)
        self.camera_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        self.camera_label = ctk.CTkLabel(self.camera_frame, text="Position your face in the camera")
        self.camera_label.pack(expand=True, fill="both", padx=10, pady=10)
        
        self.cap = None
        self.is_capturing = False
        self.captured_frames = []
        self.captured_encodings = []
        self.current_student_id = None
        self.current_qr_path = None
        self.required_images = 10

    def start_capture(self):
        s_id = self.student_id.get().strip()
        name = self.name.get().strip()
        
        if not s_id or not name:
            self.status_label.configure(text="Student ID and Name are required!", text_color="red")
            return
            
        self.current_student_id = s_id
        self.captured_frames = []
        self.captured_encodings = []
        self.is_capturing = True
        self.capture_btn.configure(state="disabled")
        self.regen_qr_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.capture_count_label.configure(text=f"Images: 0/{self.required_images}")
        
        self.status_label.configure(text="Initializing camera...", text_color="blue")
        
        threading.Thread(target=self.process_camera, daemon=True).start()

    def process_camera(self):
        self.cap = cv2.VideoCapture(0)
        
        if not getattr(self, "winfo_exists", lambda: False)():
            if self.cap: self.cap.release()
            return

        if not self.cap.isOpened():
            if self.winfo_exists():
                self.after(0, lambda: self.status_label.configure(text="Cannot open camera", text_color="red"))
                self.after(0, lambda: self.capture_btn.configure(state="normal"))
            self.is_capturing = False
            return

        frame_count = 0
        last_capture_index = -1

        while self.is_capturing and len(self.captured_encodings) < self.required_images:
            ret, frame = self.cap.read()
            if not ret:
                break
                
            frame_count += 1
            
            if self.winfo_exists():
                display_frame = frame.copy()
                
                if len(self.captured_encodings) > 0:
                    cv2.putText(display_frame, f"Captured: {len(self.captured_encodings)}/{self.required_images}", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                
                rgb_display = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb_display)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(400, 300))
                self.after(0, lambda image=ctk_img: getattr(self, "camera_label", None) and self.camera_label.winfo_exists() and self.camera_label.configure(image=image, text=""))

            if frame_count % 20 == 0 and len(self.captured_encodings) < self.required_images:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb_frame)
                
                if len(face_locations) == 1:
                    for face_loc in face_locations:
                        top, right, bottom, left = face_loc
                        cv2.rectangle(frame, (left*4, top*4), (right*4, bottom*4), (0, 255, 0), 2)
                    
                    if len(self.captured_frames) == 0 or frame_count - last_capture_index >= 20:
                        face_encoding = face_recognition.face_encodings(rgb_frame, face_locations)[0]
                        self.captured_frames.append(frame.copy())
                        self.captured_encodings.append(face_encoding)
                        last_capture_index = frame_count
                        
                        if self.winfo_exists():
                            count = len(self.captured_encodings)
                            self.after(0, lambda c=count: self.capture_count_label.configure(text=f"Images: {c}/{self.required_images}"))
                            self.after(0, lambda: self.progress_bar.set(count / self.required_images))
                            self.after(0, lambda: self.status_label.configure(text=f"Captured {count}/{self.required_images} images...", text_color="blue"))
                            
            time.sleep(0.04)

        self.cap.release()
        
        if len(self.captured_encodings) >= 3:
            if self.winfo_exists():
                self.after(0, lambda: self.status_label.configure(text="Processing encodings...", text_color="blue"))
            self.register_student()
        else:
            if self.winfo_exists():
                self.after(0, lambda: self.status_label.configure(text=f"Not enough clear faces captured ({len(self.captured_encodings)}). Try again.", text_color="red"))
                self.after(0, lambda: self.capture_btn.configure(state="normal"))
            self.is_capturing = False

    def register_student(self):
        try:
            avg_encoding = np.mean(self.captured_encodings, axis=0).tolist()
            
            s_id = self.current_student_id
            name = self.name.get().strip()
            email = self.email.get().strip()
            course = self.course.get().strip()
            
            qr_dir = "qrcodes"
            if not os.path.exists(qr_dir):
                os.makedirs(qr_dir)
            qr_path = os.path.join(qr_dir, f"{s_id}.png")
            
            qr_data = json.dumps({"student_id": s_id, "name": name, "email": email, "course": course})
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
            qr.add_data(qr_data)
            qr.make()
            qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
            
            if self.captured_frames:
                ref_frame = self.captured_frames[len(self.captured_frames)//2]
                rgb_ref = cv2.cvtColor(ref_frame, cv2.COLOR_BGR2RGB)
                ref_locs = face_recognition.face_locations(rgb_ref)
                if ref_locs:
                    top, right, bottom, left = ref_locs[0]
                    face_crop = rgb_ref[top:bottom, left:right]
                    face_pil = Image.fromarray(face_crop)
                    face_size = (qr_img.size[0] // 4, qr_img.size[1] // 4)
                    face_pil.thumbnail(face_size, Image.Resampling.LANCZOS)
                    border_size = (face_size[0] + 10, face_size[1] + 10)
                    border_img = Image.new('RGB', border_size, (255, 255, 255))
                    border_img.paste(face_pil, (5, 5))
                    pos = ((qr_img.size[0] - border_img.size[0]) // 2, (qr_img.size[1] - border_img.size[1]) // 2)
                    qr_img.paste(border_img, pos)
            
            qr_img.save(qr_path)
            self.current_qr_path = qr_path
            
            success, msg = self.db_manager.register_student(s_id, name, email, course, avg_encoding, qr_code_path=qr_path)
            
            if self.winfo_exists():
                if success:
                    self.after(0, lambda: self.status_label.configure(text="Registration Complete! QR Generated.", text_color="green"))
                    self.after(0, lambda: self.show_qr_popup(qr_path, name, s_id))
                    self.after(0, lambda: self.regen_qr_btn.configure(state="normal"))
                    self.after(0, lambda: self.capture_btn.configure(text="Register Another Student"))
                    self.after(0, lambda: self.capture_btn.configure(state="normal"))
                else:
                    self.after(0, lambda: self.status_label.configure(text=f"Error: {msg}", text_color="red"))
                    self.after(0, lambda: self.capture_btn.configure(state="normal"))
        except Exception as e:
            if self.winfo_exists():
                self.after(0, lambda: self.status_label.configure(text=f"Error: {str(e)}", text_color="red"))
                self.after(0, lambda: self.capture_btn.configure(state="normal"))
        finally:
            self.is_capturing = False

    def regenerate_qr(self):
        if not self.current_student_id:
            return
            
        s_id = self.current_student_id
        name = self.name.get().strip()
        email = self.email.get().strip()
        course = self.course.get().strip()
        
        qr_dir = "qrcodes"
        qr_path = os.path.join(qr_dir, f"{s_id}.png")
        
        qr_data = json.dumps({"student_id": s_id, "name": name, "email": email, "course": course})
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make()
        qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        
        if self.captured_frames:
            ref_frame = self.captured_frames[len(self.captured_frames)//2]
            rgb_ref = cv2.cvtColor(ref_frame, cv2.COLOR_BGR2RGB)
            ref_locs = face_recognition.face_locations(rgb_ref)
            if ref_locs:
                top, right, bottom, left = ref_locs[0]
                face_crop = rgb_ref[top:bottom, left:right]
                face_pil = Image.fromarray(face_crop)
                face_size = (qr_img.size[0] // 4, qr_img.size[1] // 4)
                face_pil.thumbnail(face_size, Image.Resampling.LANCZOS)
                border_size = (face_size[0] + 10, face_size[1] + 10)
                border_img = Image.new('RGB', border_size, (255, 255, 255))
                border_img.paste(face_pil, (5, 5))
                pos = ((qr_img.size[0] - border_img.size[0]) // 2, (qr_img.size[1] - border_img.size[1]) // 2)
                qr_img.paste(border_img, pos)
        
        qr_img.save(qr_path)
        self.current_qr_path = qr_path
        self.show_qr_popup(qr_path, name, s_id)
        self.status_label.configure(text="QR Code regenerated!", text_color="green")

    def show_qr_popup(self, qr_path, student_name, student_id=None):
        popup = ctk.CTkToplevel(self)
        popup.title(f"QR Code - {student_name}")
        popup.geometry("400x500")
        popup.attributes("-topmost", True)
        
        header = ctk.CTkLabel(popup, text=f"QR Code Generated", font=ctk.CTkFont(size=20, weight="bold"))
        header.pack(pady=10)
        
        info_lbl = ctk.CTkLabel(popup, text=f"Student: {student_name}", font=ctk.CTkFont(size=14))
        info_lbl.pack(pady=5)
        
        if student_id:
            id_lbl = ctk.CTkLabel(popup, text=f"ID: {student_id}", font=ctk.CTkFont(size=12))
            id_lbl.pack(pady=2)
        
        qr_image = Image.open(qr_path)
        qr_ctk = ctk.CTkImage(light_image=qr_image, dark_image=qr_image, size=(280, 280))
        
        img_lbl = ctk.CTkLabel(popup, image=qr_ctk, text="")
        img_lbl.image = qr_ctk
        img_lbl.pack(pady=15)
        
        def save_qr():
            import shutil
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            dest = os.path.join(desktop, f"QR_{student_id}.png")
            shutil.copy(qr_path, dest)
            save_btn.configure(text="Saved to Desktop!")
            popup.after(2000, lambda: save_btn.configure(text="Save QR to Desktop"))
        
        save_btn = ctk.CTkButton(popup, text="Save QR to Desktop", command=save_qr)
        save_btn.pack(pady=10)
        
        close_btn = ctk.CTkButton(popup, text="Close", command=popup.destroy, fg_color="gray")
        close_btn.pack(pady=5)

    def destroy(self):
        self.is_capturing = False
        if self.cap:
            self.cap.release()
        super().destroy()
