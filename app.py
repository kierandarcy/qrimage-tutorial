from flask import Flask, render_template
from flask.ext.bootstrap import Bootstrap

app = Flask(__name__)

bootstrap = Bootstrap(app)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/brew-coffee/')
def coffee():
    return render_template('coffee.html')

@app.route('/create-qrcode/')
def create():
    return render_template('create.html')

@app.route('/login')
def login():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)
