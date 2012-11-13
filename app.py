import os.path
import uuid

from flask import Flask, render_template, request, abort, session, g,\
                  send_from_directory, flash, redirect, url_for, after_this_request
from flask.ext.login import LoginManager, login_user, UserMixin, current_user,\
                            login_required, logout_user
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.bootstrap import Bootstrap
from flask.ext.wtf import Form, URL, Required, TextField
from flask.ext.wtf.html5 import URLField

import qrcode

app = Flask(__name__)
app.config['SECRET_KEY'] = 'my_very_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = \
                      'sqlite:///%s' % os.path.join(app.root_path, 'qrimage.db')

db = SQLAlchemy(app)
bootstrap = Bootstrap(app)

login_manager = LoginManager()
login_manager.setup_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

# Models
qrcodes = db.Table('qrcodes',
    db.Column('user_id',   db.Integer, db.ForeignKey('user.id')),
    db.Column('qrcode_id', db.Integer, db.ForeignKey('qrcode.id'))
    )

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Unicode, unique=True)
    name = db.Column(db.Unicode)
    qrcodes = db.relationship('Qrcode', secondary=qrcodes,
                              backref=db.backref('users', lazy='dynamic'))

    def __init__(self, username, name):
        self.username = username
        self.name = name

    def get_id(self):
        return unicode(self.id)

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

class LoginForm(Form):
    username = TextField(u'Enter your user name', validators=[Required(),])

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

@app.after_request
def after_request(response):
    response.headers['X-Python-North-East'] = 'Pizza Fueled Awesomeness!'
    return response

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

@app.route('/my-qrcodes/')
@login_required
def user_images():
    return render_template('user_images.html')

@app.route('/my-qrcodes/<int:id>/qrcode.png')
@app.route('/my-qrcodes/<int:id>/qrcode.png<download>')
@login_required
def user_image(id, download=None):
    qr = Qrcode.query.get(id)
    if qr in current_user.qrcodes:
        return send_from_directory(app.instance_path, qr.filename, 
                                   mimetype='image/png',
                                   attachment_filename='qrcode.png',
                                   as_attachment=download == '+' or False)
    abort(404)

@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if login_user(user):
                flash('You were logged in as %s' % current_user.name, 'success')
                if g.last_image:
                    g.last_image.users.append(user)
                    db.session.commit()
                    flash("We added the last QR code you made to your saved list.\
                    You're welcome.", 'info')
                return redirect(request.args.get('next') or url_for('home'))
            flash('Sorry, you could not be logged in.', 'error')
        flash('Sorry, we could not find that user.', 'warning')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.pop('last_image_id', None)
    g.last_image = None
    logout_user()
    flash('You were logged out.', 'info')
    return redirect(request.args.get('next') or url_for('home'))

@app.errorhandler(404)
def resource_missing(error):
    return render_template('errors.html', error=error), 404

@app.errorhandler(401)
def resource_forbidden(error):
    return render_template('errors.html', error=error), 401

@app.errorhandler(418)
def i_am_a_teapot(error):
    @after_this_request
    def after_request(response):
        response.headers['X-Biscuits'] = 'Rich Tea Please'
        return response
    return render_template('errors.html', error=error), 418

if __name__ == '__main__':
    app.run(debug=True)
