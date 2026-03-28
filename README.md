# Face Recognition Attendance System

A comprehensive, desktop-based student attendance management system powered by CustomTkinter, OpenCV, DeepFace, and MySQL.

## Features
- **Admin Authentication**: Secure login.
- **Student Registration**: Real-time webcam capture, face feature extraction, and secure database storage.
- **Attendance Recognition**: Live face detection and verification using VGG-Face via DeepFace. Anti-duplicate mechanism (marks only once per day).
- **Dashboard Data visualization**: Total students, attendance metrics, and Matplotlib pie charts.
- **Excel Export**: View tabular records and export them via Pandas to `.xlsx`.

## Setup Instructions

1. **Install MySQL Server**
   - Ensure MySQL Server is running locally.
   - The default configuration uses: `host="localhost"`, `user="root"`, `password=""`.
   - Update `db_manager.py` if your database credentials differ.

2. **Initialize Database Schema**
   - Note: The application attempts to create the database/tables automatically when you launch it.
   - Alternatively, you can run the provided `database.sql` script manually in your MySQL workbench/CLI.

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   *Note: Upon first registering a face or starting attendance, DeepFace will download the pre-trained weights (`vgg_face_weights.h5`) which might take a few minutes.*

4. **Run the Application**
   ```bash
   python main.py
   ```

5. **Usage Flow**
   - **Login**: Use default admin credentials (`admin` / `admin123`).
   - **Register Student**: Next, navigate to the `Registration` tab. Fill out details and press **Capture Face & Register**. Please hold still until captured.
   - **Mark Attendance**: Navigate to the `Attendance` tab. Press **Start Camera**. Stand in front of the camera, and it will match your face and mark your attendance.
   - **Check Dashboard**: Navigate to `Dashboard` to view the graphical statistics.
   - **Export**: Navigate to the `Records` tab to view history and export.
