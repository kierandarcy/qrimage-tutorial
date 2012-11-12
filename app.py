import os.path
import uuid

from flask import Flask, render_template, request, abort, session, g,\
                  send_from_directory
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.bootstrap import Bootstrap
from flask.ext.wtf import Form, URL, Required
from flask.ext.wtf.html5 import URLField

import qrcode

app = Flask(__name__)
app.config['SECRET_KEY'] = 'my_very_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = \
                      'sqlite:///%s' % os.path.join(app.root_path, 'qrimage.db')

db = SQLAlchemy(app)
bootstrap = Bootstrap(app)

# Models
qrcodes = db.Table('qrcodes',
    db.Column('user_id',   db.Integer, db.ForeignKey('user.id')),
    db.Column('qrcode_id', db.Integer, db.ForeignKey('qrcode.id'))
    )

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Unicode, unique=True)
    name = db.Column(db.Unicode)
    qrcodes = db.relationship('Qrcode', secondary=qrcodes,
                              backref=db.backref('users', lazy='dynamic'))

    def __init__(self, username, name):
        self.username = username
        self.name = name

class Qrcode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Unicode, unique=True)
    filename = db.Column(db.Unicode, unique=True)
    #users: This is an implied column
    
    def __init__(self, content):
        self.content = content
        self.filename = u'%s.png' % uuid.uuid4()
        self.save_image_file()

    def save_image_file(self):
        full_filename = os.path.join(app.instance_path, self.filename)
        if not os.path.exists(full_filename):
            img = qrcode.make(self.content)
            img.save(full_filename)

# Forms
class CreateForm(Form):
    url = URLField(u'Enter a URL', validators=[Required(),
                   URL(message=u'Please enter a well-formed URL')],
                   description=u'Create a QR code from this URL')

def process_qrcode(content):
    # Remove any previously saved QR objects from the current session
    session.pop('last_image_id', None)
    g.last_image = None
    
    # Find an existing QR code object or create a new one
    qr = Qrcode.query.filter_by(content=content).first()
    if not qr:
        qr = Qrcode(content)
        db.session.add(qr)

    # Create (or recreate if necessary) an image file for the QR code and assign
    # it to the current user (if they're logged in).
    qr.save_image_file()

    # Commit any changes to the database (to ensure we have ID values)
    db.session.commit()

    # Populate the session with this QR image
    session['last_image_id'] = qr.id
    g.last_image = qr

@app.before_request
def before_request():
    g.last_image = Qrcode.query.get(session.get('last_image_id', 0))

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/brew-coffee/', methods=['GET','POST'])
def coffee():
    if request.method == 'POST':
        abort(418)
    return render_template('coffee.html')

@app.route('/create-qrcode/', methods=['GET','POST'])
def create():
    form = CreateForm()
    if form.validate_on_submit():
        process_qrcode(form.url.data)
        return render_template('create.html', form=form, show_last_image=True)
    return render_template('create.html', form=form)

@app.route('/most-recent/qrcode.png')
@app.route('/most-recent/qrcode.png<download>')
def last_image(download=None):
    if g.last_image:
        return send_from_directory(app.instance_path, g.last_image.filename, 
                                   cache_timeout=0,
                                   mimetype='image/png',
                                   attachment_filename='qrcode.png',
                                   as_attachment=download == '+' or False)
    abort(403)

@app.route('/login')
def login():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)
