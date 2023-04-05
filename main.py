import os

from flask import Flask
from views.start import start,next_page,new_site,generate_site

import secrets

# initialize the Flask app
app = Flask(__name__, instance_relative_config=True)
app.template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app.static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# clear all local caching of static files
app.config['TEMPLATES_AUTO_RELOAD'] = True

app.config.from_object(__name__)
app.secret_key = secrets.token_hex(16)
# app.config['SESSION_TYPE'] = 'filesystem'
# app.config['SESSION_PERMANENT'] = False

if not os.path.exists(app.template_folder):
    os.makedirs(app.template_folder)

if not os.path.exists(app.static_folder):
    os.makedirs(app.static_folder)


app.static_url_path=f"/{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')}"
app.template_url_path=f"/{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')}"

# Use the start() function from start.py to define the '/' route
app.route('/')(start)
app.route('/next_page')(next_page)
app.route('/new_site')(new_site)
app.route('/generating')(generate_site)
# app.route('/next_site')(destination)


if __name__ == '__main__':
    app.run(debug=True,host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))