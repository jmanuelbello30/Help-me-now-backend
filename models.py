from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
db = SQLAlchemy()

class User(db.Model):
    __tablename__='users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    user_type = db.Column(db.String(100), nullable=False) 

    def __repr__(self):
        return '<User &r>' % self.email

    def serialize(self):
        return {
            "id": self.id,
            "email": self.email,
            "user_type": self.user_type
       }

class Professional(db.Model):
    __tablename__='professionals'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rut = db.Column(db.String(100), nullable=True, default="sin-foto.png")
    certification = db.Column(db.String(100), nullable=False, default="sin-foto.png")
    numberid = db.Column(db.String(100), nullable=False, default="sin-foto.png")
    curriculum = db.Column(db.String(100), nullable=False, default="sin-foto.png")
    status = db.Column(db.Integer, nullable=True, default=0)
    user_id = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return "<Professional %r>" % self.name

    def serialize(self):
        return{
            "id": self.id,
            "name": self.name
        }

class Patient(db.Model):
    __tablename__='patients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return "<Patient %r>" % self.name

    def serialize(self):
        return{
            "id": self.id,
            "name": self.name
        }

class Channel(db.Model):
    __tablename__ = 'channels'
    id = db.Column(db.Integer, primary_key=True)
    patient_user_id = db.Column(db.Integer)
    profesional_user_id = db.Column(db.Integer)
    state = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return "<Channel %r>" % self.id

    def serialize(self):
        return{
            "id": self.id,
            "patient_user_id": self.patient_user_id,
            "profesional_user_id": self.profesional_user_id,
            "state": self.state,
            "created_at": self.created_at
        }

    def to_request_serialize(self):
        return{
            "channel_id": self.id,
            "state": self.state,
        }

class Chat_Message(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128))
    user_id = db.Column(db.Integer)
    text = db.Column(db.Text)
    channel_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return "<Chat_Message %r>" % self.username

    def serialize(self):
        return{
            "id": self.id,
            "username": self.username,
            "user_id": self.user_id,
            "text": self.text,
            "channel_id": self.channel_id,
            "created_at": self.created_at
        }
