import customtkinter as ctk

class Sidebar(ctk.CTkFrame):
    def __init__(self, master, navigate_callback, logout_callback, **kwargs):
        super().__init__(master, corner_radius=0, **kwargs)
        self.navigate_callback = navigate_callback
        self.logout_callback = logout_callback

        self.grid_rowconfigure(5, weight=1)

        self.logo_label = ctk.CTkLabel(self, text="Admin Panel", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.dashboard_button = ctk.CTkButton(self, text="Dashboard", command=lambda: self.navigate_callback("dashboard"))
        self.dashboard_button.grid(row=1, column=0, padx=20, pady=10)

        self.register_button = ctk.CTkButton(self, text="Registration", command=lambda: self.navigate_callback("register"))
        self.register_button.grid(row=2, column=0, padx=20, pady=10)

        self.attendance_button = ctk.CTkButton(self, text="Scanner Portal", command=lambda: self.navigate_callback("attendance"))
        self.attendance_button.grid(row=3, column=0, padx=20, pady=10)
        
        self.records_button = ctk.CTkButton(self, text="Records", command=lambda: self.navigate_callback("records"))
        self.records_button.grid(row=4, column=0, padx=20, pady=10)

        self.appearance_mode_label = ctk.CTkLabel(self, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=6, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self, values=["System", "Light", "Dark"],
                                                             command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=7, column=0, padx=20, pady=(10, 10))

        self.logout_button = ctk.CTkButton(self, text="Logout", fg_color="red", command=self.logout_callback)
        self.logout_button.grid(row=8, column=0, padx=20, pady=(10, 20))

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)
