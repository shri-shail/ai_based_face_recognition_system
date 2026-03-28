import customtkinter as ctk
import pandas as pd
from tkinter import ttk
import os

class RecordsFrame(ctk.CTkFrame):
    def __init__(self, master, db_manager, **kwargs):
        super().__init__(master, **kwargs)
        self.db_manager = db_manager
        self.all_records = []
        
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.title_label = ctk.CTkLabel(self, text="Attendance Records", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, pady=(20, 10))
        
        # Tools Frame
        self.tools_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.tools_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        
        self.search_entry = ctk.CTkEntry(self.tools_frame, placeholder_text="Search Name/ID/Date...", width=250)
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", self.filter_data)
        
        self.export_btn = ctk.CTkButton(self.tools_frame, text="Export to Excel", command=self.export_to_excel)
        self.export_btn.pack(side="right")
        
        # Treeview for records
        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.grid(row=2, column=0, padx=20, pady=20, sticky="nsew")
        
        columns = ('date', 'time', 'student_id', 'name', 'course', 'status')
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show='headings')
        
        self.tree.heading('date', text='Date')
        self.tree.heading('time', text='Time')
        self.tree.heading('student_id', text='Student ID')
        self.tree.heading('name', text='Name')
        self.tree.heading('course', text='Course')
        self.tree.heading('status', text='Status')
        
        self.tree.column('date', width=100)
        self.tree.column('time', width=100)
        self.tree.column('student_id', width=100)
        self.tree.column('name', width=150)
        self.tree.column('course', width=150)
        self.tree.column('status', width=100)
        
        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add Treeview styling to match CustomTkinter dark mode roughly
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#333333", foreground="white", fieldbackground="#333333", borderwidth=0)
        style.map('Treeview', background=[('selected', '#22559b')])
        style.configure("Treeview.Heading", background="#2a2a2a", foreground="white", relief="flat")
        style.map("Treeview.Heading", background=[('active', '#3a3a3a')])
        
        self.load_data()

    def load_data(self):
        self.all_records = self.db_manager.get_attendance_records()
        self.update_tree(self.all_records)

    def filter_data(self, event=None):
        query = self.search_entry.get().lower()
        if query == "":
            self.update_tree(self.all_records)
            return
            
        filtered = []
        for r in self.all_records:
            match = (
                query in str(r['name']).lower() or
                query in str(r['student_id']).lower() or
                query in str(r['date']).lower()
            )
            if match:
                filtered.append(r)
        self.update_tree(filtered)

    def update_tree(self, records):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for r in records:
            date_str = str(r['date'])
            time_str = str(r['time'])
            self.tree.insert('', 'end', values=(date_str, time_str, r['student_id'], r['name'], r['course'], r['status']))

    def export_to_excel(self):
        if not self.all_records:
            return
            
        df = pd.DataFrame(self.all_records)
        df['date'] = df['date'].astype(str)
        df['time'] = df['time'].astype(str)
        
        export_path = os.path.join(os.getcwd(), "Attendance_Export.xlsx")
        try:
            df.to_excel(export_path, index=False)
            self.export_btn.configure(text=f"Exported successfully!", text_color="green")
        except Exception as e:
            print("Export error:", e)
            self.export_btn.configure(text=f"Export Failed!", text_color="red")
        finally:
            self.after(3000, lambda: self.export_btn.configure(text="Export to Excel", text_color="white"))
