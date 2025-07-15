from flask import Flask
from config_loader import ConfigLoader
from soup_pusher import SoupPusher

app = Flask(__name__)

@app.route('/health')
def health_check():
    try:
        # Test database connection
        config = ConfigLoader()
        soup_pusher = SoupPusher(config.get_supabase_config())
        if not soup_pusher.test_connection():
            return 'Database connection failed', 500
            
        # Check if service process is running
        with open('service.pid', 'r') as f:
            pid = int(f.read().strip())
            
        import os
        if not os.path.exists(f'/proc/{pid}'):
            return 'Service not running', 500
            
        return 'Healthy', 200
        
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 