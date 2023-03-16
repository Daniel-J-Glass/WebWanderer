import os

from flask import Flask
from views.start import start,next_page

app = Flask(__name__)
app.template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app.static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

if not os.path.exists(app.template_folder):
    os.makedirs(app.template_folder)

if not os.path.exists(app.static_folder):
    os.makedirs(app.static_folder)

app.static_url_path=f"/{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')}"


# Use the start() function from start.py to define the '/' route
app.route('/')(start)
app.route('/next_page')(next_page)

if __name__ == '__main__':
    app.run(debug=True,host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))