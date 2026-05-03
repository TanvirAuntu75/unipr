from app import app, init_db

if __name__ == '__main__':
    # Ensure database is ready before starting
    init_db()
    # Run the Flask development server
    app.run(host='0.0.0.0', port=5000, debug=True)
