from flask import Flask, render_template, request, redirect, url_for, session, Response, jsonify
import cv2
import face_recognition
import numpy as np
import threading
import time
import os
import json
from PIL import Image
from pyzbar.pyzbar import decode
from werkzeug.utils import secure_filename
from db_manager import DBManager

app = Flask(__name__)
app.secret_key = "super_secret_shri_key"
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = DBManager()

# Global camera instance
camera = None
known_encodings = []
known_encs = []

def get_camera():
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)
    return camera

def release_camera():
    global camera
    if camera is not None:
        camera.release()
        camera = None

def load_encodings():
    global known_encodings, known_encs
    known_encodings = db.get_all_student_encodings()
    known_encs = []
    for s in known_encodings:
        try:
            encoding = np.asarray(s['encoding'], dtype=np.float64)
            if encoding.ndim == 1 and encoding.size > 0:
                known_encs.append(encoding)
            else:
                raise ValueError("invalid encoding shape")
        except Exception as exc:
            print(f"Skipping invalid encoding for student {s.get('student_id')}: {exc}")

def gen_frames():
    global known_encs, known_encodings
    cam = get_camera()
    cooldown = 0
    frameCount = 0
    
    # Reload encodings when stream starts
    load_encodings()
    
    while True:
        success, frame = cam.read()
        if not success:
            break
        else:
            frameCount += 1
            if cooldown > 0:
                cooldown -= 1
                
            # --- QR Code Processing ---
            decoded_objects = decode(frame)
            for obj in decoded_objects:
                pts = [(int(p.x), int(p.y)) for p in obj.polygon]
                if len(pts) == 4:
                    for i in range(4):
                        cv2.line(frame, pts[i], pts[(i+1)%4], (255, 0, 0), 3)
                
                if cooldown == 0:
                    try:
                        qr_data = obj.data.decode('utf-8')
                        try:
                            data_dict = json.loads(qr_data)
                            s_id = data_dict.get("student_id")
                        except json.JSONDecodeError:
                            s_id = qr_data
                            
                        if s_id:
                            student_record = next((s for s in known_encodings if s['student_id'] == s_id), None)
                            name = student_record['name'] if student_record else "Unknown QR"
                            
                            top_point = pts[0][1] if len(pts)>0 else 50
                            left_point = pts[0][0] if len(pts)>0 else 50
                            cv2.putText(frame, f"QR: {name}", (left_point, top_point - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 0, 0), 2)

                            if student_record:
                                success_mark, msg = db.mark_attendance(s_id)
                                cooldown = 30
                    except Exception:
                        pass

            # --- Face Processing ---
            # Resize frame for faster face recognition processing
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            face_locations = face_recognition.face_locations(rgb_small_frame)
            
            if face_locations:
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                
                for face_loc, encoding in zip(face_locations, face_encodings):
                    name = "Unknown"
                    color = (0, 0, 255) # Red
                    
                    if known_encs:
                        try:
                            matches = face_recognition.compare_faces(known_encs, encoding, tolerance=0.5)
                            face_distances = face_recognition.face_distance(known_encs, encoding)
                            if len(face_distances) > 0:
                                best_match_index = np.argmin(face_distances)
                                if matches and matches[best_match_index]:
                                    best = known_encodings[best_match_index]
                                    name = best['name']
                                    color = (0, 255, 0) # Green
                                    
                                    # Mark attendance
                                    if cooldown == 0:
                                        success_mark, msg = db.mark_attendance(best['student_id'])
                                        cooldown = 30 # Wait ~1 second before next recognition
                        except Exception as exc:
                            print(f"Face recognition error: {exc}")
                    
                    # Scale back up
                    top, right, bottom, left = face_loc
                    top *= 4
                    right *= 4
                    bottom *= 4
                    left *= 4
                    
                    cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                    cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
            
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if db.verify_login(username, password):
            session['user'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid Credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    release_camera()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    release_camera()
    stats = db.get_dashboard_stats()
    weekly = db.get_weekly_attendance_stats()
    
    # Format weekly for charts
    labels = list(weekly.keys()) if weekly else []
    data = list(weekly.values()) if weekly else []
    
    return render_template('dashboard.html', stats=stats, labels=labels, data=data)

@app.route('/scanner')
def scanner():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('scanner.html')

@app.route('/video_feed')
def video_feed():
    if 'user' not in session:
        return "Unauthorized", 401
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/records')
def records():
    if 'user' not in session:
        return redirect(url_for('login'))
    release_camera()
    records_data = db.get_attendance_records()
    return render_template('records.html', records=records_data)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user' not in session:
        return redirect(url_for('login'))
    release_camera()
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        name = request.form.get('name')
        email = request.form.get('email')
        course = request.form.get('course')
        photo_data = request.form.get('photo_data')
        
        if not photo_data:
            return render_template('register.html', error="No live photo captured. Please explicitly click Capture Photo.")
            
        import base64
        try:
            header, encoded = photo_data.split(',', 1)
            img_bytes = base64.b64decode(encoded)
            img_arr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
            
            if img is None:
                return render_template('register.html', error="Could not decode image.")
                
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            encodings = face_recognition.face_encodings(rgb_img)
            
            if not encodings:
                return render_template('register.html', error="No face detected in the captured image. Please align your face properly.")
                
            encoding = encodings[0].tolist()
            
            qr_dir = os.path.join(app.root_path, 'static', 'qrcodes')
            os.makedirs(qr_dir, exist_ok=True)
            qr_filename = f"{student_id}.png"
            qr_path = os.path.join(qr_dir, qr_filename)
            
            import qrcode
            import json
            qr_data = json.dumps({"student_id": student_id, "name": name, "email": email, "course": course})
            qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
            qr.add_data(qr_data)
            qr.make()
            qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
            
            face_locs = face_recognition.face_locations(rgb_img)
            if face_locs:
                top, right, bottom, left = face_locs[0]
                face_crop = rgb_img[top:bottom, left:right]
                face_pil = Image.fromarray(face_crop)
                face_size = (qr_img.size[0] // 4, qr_img.size[1] // 4)
                face_pil.thumbnail(face_size, Image.Resampling.LANCZOS)
                border_img = Image.new('RGB', (face_size[0] + 10, face_size[1] + 10), (255, 255, 255))
                border_img.paste(face_pil, (5, 5))
                pos = ((qr_img.size[0] - border_img.size[0]) // 2, (qr_img.size[1] - border_img.size[1]) // 2)
                qr_img.paste(border_img, pos)
            
            qr_img.save(qr_path)
            
            success, msg = db.register_student(student_id, name, email, course, encoding, qr_code_path=qr_path)
            
            if success:
                load_encodings()
                return render_template('register_success.html', student_id=student_id, name=name, qr_filename=qr_filename)
            else:
                return render_template('register.html', error=msg)
        except Exception as e:
            return render_template('register.html', error=f"Error processing image: {str(e)}")
                
    return render_template('register.html')

@app.route('/regenerate_qr/<student_id>', methods=['POST'])
def regenerate_qr(student_id):
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    student = db.get_student_by_id(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404
    
    qr_dir = os.path.join(app.root_path, 'static', 'qrcodes')
    os.makedirs(qr_dir, exist_ok=True)
    qr_filename = f"{student_id}.png"
    qr_path = os.path.join(qr_dir, qr_filename)
    
    import qrcode
    import json
    qr_data = json.dumps({"student_id": student['student_id'], "name": student['name'], 
                          "email": student.get('email', ''), "course": student.get('course', '')})
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(qr_data)
    qr.make()
    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    qr_img.save(qr_path)
    
    return jsonify({"success": True, "qr_path": f"/static/qrcodes/{qr_filename}"})

@app.route('/api/students', methods=['GET'])
def get_students():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    students = db.get_all_students()
    return jsonify(students)

@app.route('/api/attendance/mark', methods=['POST'])
def mark_attendance_api():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    student_id = data.get('student_id')
    
    if not student_id:
        return jsonify({"error": "Student ID required"}), 400
    
    success, msg = db.mark_attendance(student_id)
    return jsonify({"success": success, "message": msg})

if __name__ == '__main__':
    app.run(debug=True, threaded=True, host='0.0.0.0')
