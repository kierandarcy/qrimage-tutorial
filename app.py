from flask import Flask, render_template, request, abort
from flask.ext.bootstrap import Bootstrap
from flask.ext.wtf import Form, URL, Required
from flask.ext.wtf.html5 import URLField

app = Flask(__name__)
app.config['SECRET_KEY'] = 'my_very_secret_key'

bootstrap = Bootstrap(app)

# Forms
class CreateForm(Form):
    url = URLField(u'Enter a URL', validators=[Required(),
                   URL(message=u'Please enter a well-formed URL')],
                   description=u'Create a QR code from this URL')

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
        return render_template('create.html', form=form, show_last_image=True)
    return render_template('create.html', form=form)

@app.route('/login')
def login():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)
