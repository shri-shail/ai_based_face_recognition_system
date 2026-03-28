import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta

class DashboardFrame(ctk.CTkFrame):
    def __init__(self, master, db_manager, **kwargs):
        super().__init__(master, **kwargs)
        self.db_manager = db_manager
        
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.title_label = ctk.CTkLabel(self, text="Dashboard Overview", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, columnspan=3, pady=(20, 20))
        
        self.stats = self.db_manager.get_dashboard_stats()
        
        # Top numeric cards
        self.total_card = self.create_stat_card(self, "Total Students", str(self.stats['total_students']), "blue")
        self.total_card.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        self.present_card = self.create_stat_card(self, "Present Today", str(self.stats['present_today']), "green")
        self.present_card.grid(row=1, column=1, padx=20, pady=10, sticky="nsew")
        
        self.absent_card = self.create_stat_card(self, "Absent Today", str(self.stats['absent_today']), "red")
        self.absent_card.grid(row=1, column=2, padx=20, pady=10, sticky="nsew")
        
        # Charts section
        self.charts_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.charts_frame.grid(row=2, column=0, columnspan=3, padx=20, pady=10, sticky="nsew")
        self.charts_frame.grid_columnconfigure(0, weight=1)
        self.charts_frame.grid_columnconfigure(1, weight=1)
        
        self.render_pie_chart()
        self.render_bar_chart()

    def create_stat_card(self, parent, title, value, color):
        frame = ctk.CTkFrame(parent, border_width=2)
        title_lbl = ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=18))
        title_lbl.pack(pady=(20, 5))
        val_lbl = ctk.CTkLabel(frame, text=value, font=ctk.CTkFont(size=36, weight="bold"), text_color=color)
        val_lbl.pack(pady=(5, 20))
        return frame

    def render_pie_chart(self):
        fig, ax = plt.subplots(figsize=(4, 3), dpi=100)
        labels = ['Present', 'Absent']
        sizes = [self.stats['present_today'], self.stats['absent_today']]
        colors = ['#2ecc71', '#e74c3c']
        
        if sum(sizes) == 0:
            ax.text(0.5, 0.5, "No Data Today", ha='center', va='center', color='white')
            ax.axis('off')
        else:
            ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            
        fig.patch.set_facecolor('#2b2b2b')
        ax.set_facecolor('#2b2b2b')
        
        for text in ax.texts:
            text.set_color('white')
            
        canvas = FigureCanvasTkAgg(fig, master=self.charts_frame)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    def render_bar_chart(self):
        weekly_stats = self.db_manager.get_weekly_attendance_stats()
        
        # Prepare data for last 7 days including today
        dates = []
        counts = []
        today = datetime.now()
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            d_str = d.strftime('%Y-%m-%d')
            display_d = d.strftime('%a') # Mon, Tue, etc.
            dates.append(display_d)
            counts.append(weekly_stats.get(d_str, 0))
            
        fig, ax = plt.subplots(figsize=(5, 3), dpi=100)
        ax.bar(dates, counts, color='#3498db')
        ax.set_title("Last 7 Days Trend", color='white')
        
        fig.patch.set_facecolor('#2b2b2b')
        ax.set_facecolor('#2b2b2b')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        
        for spine in ax.spines.values():
            spine.set_color('gray')
            
        ax.yaxis.get_major_locator().set_params(integer=True)

        canvas = FigureCanvasTkAgg(fig, master=self.charts_frame)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
