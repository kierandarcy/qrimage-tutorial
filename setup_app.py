from app import db, User

db.create_all()
db.session.add(User(u'kieran', u'Kieran Darcy'))
db.session.commit()
