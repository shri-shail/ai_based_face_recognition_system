import customtkinter as ctk
from db_manager import DBManager
from ui_components.login_frame import LoginFrame
from ui_components.dashboard_frame import DashboardFrame
from ui_components.register_frame import RegisterFrame
from ui_components.attendance_frame import AttendanceFrame
from ui_components.records_frame import RecordsFrame
from ui_components.scan_qr_frame import ScanQRFrame
from ui_components.sidebar import Sidebar

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class FaceAttendanceApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Face Recognition & QR Attendance System")
        self.geometry("1100x700")
        self.minsize(900, 600)
        
        # Initialize Database
        self.db = DBManager()
        
        # Grid layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Current frame reference
        self.current_frame = None
        self.sidebar = None
        
        self.show_login()

    def show_login(self):
        if self.sidebar:
            self.sidebar.destroy()
            self.sidebar = None
        if self.current_frame:
            self.current_frame.destroy()
            
        self.current_frame = LoginFrame(self, self.db, self.on_login_success)
        self.current_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")

    def on_login_success(self):
        if self.current_frame:
            self.current_frame.destroy()
            
        self.sidebar = Sidebar(self, self.navigate, self.logout)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
        self.navigate("dashboard")

    def navigate(self, view_name):
        if self.current_frame:
            self.current_frame.destroy()
            
        if view_name == "dashboard":
            self.current_frame = DashboardFrame(self, self.db)
        elif view_name == "register":
            self.current_frame = RegisterFrame(self, self.db)
        elif view_name == "attendance":
            self.current_frame = AttendanceFrame(self, self.db)
        elif view_name == "scan_qr":
            self.current_frame = ScanQRFrame(self, self.db)
        elif view_name == "records":
            self.current_frame = RecordsFrame(self, self.db)
            
        if self.current_frame:
            self.current_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def logout(self):
        self.show_login()
        
    def on_closing(self):
        self.db.close()
        self.destroy()
        import os
        os._exit(0)

if __name__ == "__main__":
    app = FaceAttendanceApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
