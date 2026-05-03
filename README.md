# Unipr - Unified Professional Attendance & Leave System

A high-performance Attendance Management System built with Python Flask and SQLite, featuring multi-role authentication (Admin, Teacher, Student), real-time reporting, automated email warnings, and hardware integration support.

## 🚀 Key Features

- **Multi-Role Access Control**: Distinct dashboards and permissions for Admins, Faculty, and Students.
- **Automated Attendance**: Hardware-ready API for RFID/Fingerprint scanners and manual web-based marking.
- **Smart Leave Management**: Students can request leaves; teachers/admins can approve or reject with instant history updates.
- **Email Notification Engine**: Asynchronous email alerts for attendance drops and official notices.
- **Dynamic Reporting**: Generate student-specific and class-wide attendance reports with percentage tracking.
- **Real-Time Noticeboard**: Broadcast HTML-supported announcements across the entire institute.

## 🛠️ Tech Stack

- **Backend**: Python 3.x, Flask
- **Database**: SQLite3 (Optimized with indexes)
- **Frontend**: HTML5, Vanilla JavaScript, CSS3, Bootstrap 5, LineAwesome Icons
- **Security**: Werkzeug password hashing, Session-based auth

## 📦 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/TanvirAuntu75/unipr.git
   cd unipr
   ```

2. **Setup Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize Database**:
   The system automatically creates `attendance.db` on first run using `init_db.sql`.

5. **Run the Application**:
   ```bash
   python main.py
   ```

## 🔌 Hardware Integration

To connect a physical device (Fingerprint/RFID):
- Use the endpoint: `/api/hardware/scan`
- API Key: `unipr_hardware_key_2026`
- Payload: `{"api_key": "...", "student_id": "STU-XXX"}`

## 📄 License

This project is licensed under the MIT License.
