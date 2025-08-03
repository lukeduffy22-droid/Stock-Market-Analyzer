from waitress import serve
from app import app  # Make sure `app` is your Flask app object

serve(app, host='0.0.0.0', port=5000)