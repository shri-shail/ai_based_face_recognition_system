import mysql.connector
from mysql.connector import Error
import pickle
from datetime import datetime

class DBManager:
    def __init__(self, host="localhost", user="root", password="Shri@789"):
        self.host = host
        self.user = user
        self.password = password
        self.database = "attendance_db"
        self.connection = None
        self.connect()

    def connect(self):
        try:
            temp_conn = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password
            )
            if temp_conn.is_connected():
                cursor = temp_conn.cursor()
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
                temp_conn.close()

            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            if self.connection.is_connected():
                self.initialize_tables()
        except Error as e:
            print(f"Error connecting to MySQL: {e}")

    def initialize_tables(self):
        if not self.connection or not self.connection.is_connected():
            return
        try:
            cursor = self.connection.cursor()

            # Users table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'admin'
            )
            """)
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin')"
                )

            # Students table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(50) NOT NULL UNIQUE,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100),
                course VARCHAR(100),
                face_encoding LONGBLOB NOT NULL,
                qr_code_path VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Attendance table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(50) NOT NULL,
                date DATE NOT NULL,
                time TIME NOT NULL,
                status VARCHAR(20) DEFAULT 'Present',
                FOREIGN KEY (student_id) REFERENCES students(student_id),
                UNIQUE KEY unique_attendance_per_day (student_id, date)
            )
            """)

            self.connection.commit()
            cursor.close()
            print("Database initialized.")
        except Error as e:
            print(f"Error creating tables: {e}")

    def verify_login(self, username, password):
        if not self.connection or not self.connection.is_connected():
            return False
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM users WHERE username = %s AND password = %s",
            (username, password)
        )
        result = cursor.fetchone()
        cursor.close()
        return result is not None

    def register_student(self, student_id, name, email, course, face_encoding, qr_code_path=None):
        if not self.connection or not self.connection.is_connected():
            return False, "Database not connected"
        try:
            cursor = self.connection.cursor()
            encoding_binary = pickle.dumps(face_encoding)
            cursor.execute(
                "INSERT INTO students (student_id, name, email, course, face_encoding, qr_code_path) VALUES (%s, %s, %s, %s, %s, %s)",
                (student_id, name, email, course, encoding_binary, qr_code_path)
            )
            self.connection.commit()
            cursor.close()
            return True, "Success"
        except mysql.connector.IntegrityError:
            return False, f"Student ID '{student_id}' already exists."
        except Error as e:
            return False, str(e)

    def get_all_student_encodings(self):
        """Returns list of dicts with validated and flattened face encodings"""
        if not self.connection or not self.connection.is_connected():
            return []

        students_list = []
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("SELECT student_id, name, face_encoding FROM students")
            results = cursor.fetchall()
            cursor.close()

            for r in results:
                encoding_data = r['face_encoding']
                try:
                    encoding_list = pickle.loads(encoding_data)
                except Exception:
                    import json
                    encoding_list = json.loads(encoding_data)

                # Flatten nested lists if needed
                if isinstance(encoding_list[0], (list, tuple)):
                    encoding_list = [item for sublist in encoding_list for item in sublist]

                # Skip invalid encodings
                if len(encoding_list) != 128:
                    print(f"Warning: encoding for {r['student_id']} invalid length {len(encoding_list)}. Skipping.")
                    continue

                r['encoding'] = [float(x) for x in encoding_list]
                del r['face_encoding']
                students_list.append(r)

            return students_list

        except Exception as e:
            print(f"Error fetching encodings: {e}")
            return []

    def get_student_by_id(self, student_id):
        if not self.connection or not self.connection.is_connected():
            return None
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
            result = cursor.fetchone()
            cursor.close()
            return result
        except Error as e:
            print(f"Error fetching student: {e}")
            return None

    def get_all_students(self):
        if not self.connection or not self.connection.is_connected():
            return []
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT student_id, name, email, course, created_at FROM students ORDER BY created_at DESC"
            )
            results = cursor.fetchall()
            cursor.close()
            return results
        except Error as e:
            print(f"Error fetching students: {e}")
            return []

    def mark_attendance(self, student_id):
        if not self.connection or not self.connection.is_connected():
            return False, "Database not connected"
        try:
            now = datetime.now()
            current_date = now.strftime('%Y-%m-%d')
            current_time = now.strftime('%H:%M:%S')
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO attendance (student_id, date, time, status) VALUES (%s, %s, %s, 'Present')",
                (student_id, current_date, current_time)
            )
            self.connection.commit()
            cursor.close()
            return True, "Attendance marked successfully"
        except mysql.connector.IntegrityError:
            return False, "Attendance already marked for today"
        except Error as e:
            return False, str(e)

    def get_dashboard_stats(self):
        if not self.connection or not self.connection.is_connected():
            return {"total_students": 0, "present_today": 0, "absent_today": 0}
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("SELECT COUNT(*) as cnt FROM students")
            total_students = cursor.fetchone()['cnt']
            today_date = datetime.now().strftime('%Y-%m-%d')
            cursor.execute(
                "SELECT COUNT(DISTINCT student_id) as cnt FROM attendance WHERE date = %s",
                (today_date,)
            )
            present_today = cursor.fetchone()['cnt']
            absent_today = total_students - present_today
            cursor.close()
            return {"total_students": total_students, "present_today": present_today, "absent_today": absent_today}
        except Error as e:
            print(f"Error fetching stats: {e}")
            return {"total_students": 0, "present_today": 0, "absent_today": 0}

    def get_attendance_records(self):
        if not self.connection or not self.connection.is_connected():
            return []
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT a.date, a.time, s.student_id, s.name, s.course, a.status
                FROM attendance a
                JOIN students s ON a.student_id = s.student_id
                ORDER BY a.date DESC, a.time DESC
            """)
            records = cursor.fetchall()
            cursor.close()
            return records
        except Error as e:
            print(f"Error fetching records: {e}")
            return []

    def get_weekly_attendance_stats(self):
        if not self.connection or not self.connection.is_connected():
            return {}
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT date, COUNT(DISTINCT student_id) as daily_count
                FROM attendance
                WHERE date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                GROUP BY date
                ORDER BY date ASC
            """)
            results = cursor.fetchall()
            cursor.close()
            return {str(r['date']): r['daily_count'] for r in results}
        except Error as e:
            print(f"Error fetching weekly stats: {e}")
            return {}

    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()