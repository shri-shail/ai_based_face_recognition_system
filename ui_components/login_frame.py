import customtkinter as ctk

class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, db_manager, success_callback, **kwargs):
        super().__init__(master, **kwargs)
        
        self.db_manager = db_manager
        self.success_callback = success_callback
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(self, text="Face Recognition Attendance", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=1, column=0, padx=20, pady=(20, 40))

        self.username_entry = ctk.CTkEntry(self, placeholder_text="Username", width=250)
        self.username_entry.grid(row=2, column=0, padx=20, pady=10)

        self.password_entry = ctk.CTkEntry(self, placeholder_text="Password", show="*", width=250)
        self.password_entry.grid(row=3, column=0, padx=20, pady=10)

        self.login_button = ctk.CTkButton(self, text="Login", command=self.attempt_login, width=250)
        self.login_button.grid(row=4, column=0, padx=20, pady=(20, 20))

        self.error_label = ctk.CTkLabel(self, text="", text_color="red")
        self.error_label.grid(row=5, column=0, sticky="n")

    def attempt_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            self.error_label.configure(text="Please fill all fields")
            return
            
        if self.db_manager.verify_login(username, password):
            self.error_label.configure(text="")
            self.success_callback()
        else:
            self.error_label.configure(text="Invalid credentials or DB connection error")
