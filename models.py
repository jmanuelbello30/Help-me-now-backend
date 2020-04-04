from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
db = SQLAlchemy()

class User(db.Model):
    __tablename__='users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    #Relación one-to-one con los modelos Paciente y Profesional, por lo tanto 
    #parámetro debe ser uselist=False
    professional = db.relationship('Professional', uselist=False, backref='professional', lazy=True)
    patient = db.relationship('Patient', uselist=False, backref='patient', lazy=True)
    
    def __repr__(self):
        return '<User &r>' % self.email

    def serialize(self):
       return {
            "id": self.id,
            "username": self.username,
            "professional": self.professional_id.serialize(),
            "patient": self.patient_id.serialize()
       }

psicological_therapy = db.Table('psicological_therapy',
    db.Column('professional_id', db.Integer, db.ForeignKey('professionals.id'), primary_key=True),
    db.Column('patient_id', db.Integer, db.ForeignKey('patients.id'), primary_key=True)
)

class Professional(db.Model):
    __tablename__='professionals'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    #Las variables siguientes conrresponden a archivos que son requeridos para 
    #poder registrarse, por lo tanto nullable=False.
    rut = db.Column(db.String(150), nullable=False, )
    cert_profesional =  db.Column(db.String(150), nullable=False, )
    cert_spsalud = db.Column(db.String(150), nullable=False)
    #certificado de capacitaciones o especializaciones es opcional,
    #por lo tanto es nullable=True
    cert_capacitaciones = db.Column(db.String(150), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    patients = db.relationship('Patient', secondary=psicological_therapy, lazy='subquery',
        backref=db.backref('professionals', lazy=True))    
    status = db.relationship('Professional_Status', uselist=False, backref='professional', lazy=True)
    mesagges = db.relationship('Message_Sent', backref='professional', lazy=True)

    def __repr__(self):
        return "<Professional %r>" % self.name
    
    def serialize(self):
        return{
            "id": self.id,
            "name": self.name,
            "rut": self.rut,
            "cert_profesional": self.cert_profesional,
            "cert_spsalud": self.cert_spsalud,
            "cert_capacitaciones": self.cert_capacitaciones,
            "patients": self.patients.serialize(),
            "user_id": self.user_id.serialize(),
            "status": self.status.serialize()
        }

class Professional_Status(db.Model):
    __tablename__='professional_status'
    id = db.Column(db.Integer, primary_key=True)
    available = db.Column(db.Boolean, default=False, create_constraint=True, name=None)
    alerts = db.relationship('Panic_Alert', backref='professional', lazy=True)
    professional_id = db.Column(db.Integer, db.ForeignKey('professionals.id'), nullable=False)
    
    def serialize(self):
        return{
            "id": self.id,
            "available": self.available,
            "alerts": self.alerts.serialize()
        }
    

class Patient(db.Model):
    __tablename__='patients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    alerts = db.relationship('Panic_Alert', backref='patient', lazy=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def serialize(self):
        return {
            "id": self.id,
            "name": self.username,
            "alerts": self.alerts,
        }

class Panic_Alert(db.Model):
    __tablename__='alerts'
    id = db.Column(db.Integer, primary_key=True)
    active_alert = db.Column(db.Boolean, default=False, create_constraint=True, name=None)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    status_id = db.Column(db.Integer, db.ForeignKey('professional_status.id'), nullable=False)

    def serialize(self):
        return {
            "id": self.id,
            "active_alert": self.active_alert
        }

class Message_Sent(db.Model):
    __tablename__='messages'
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(400))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    professional_id = db.Column(db.Integer, db.ForeignKey('professionals.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    chat_id = db.Column(db.Integer, db.ForeignKey('chats.id'), nullable=False)

    def serialize(self):
        return {
            "id": self.id,
            "message": self.message,
            "timestamp": self.timestamp
        }

class Chat_Room(db.Model):
    __tablename__='chats'
    id = db.Column(db.Integer, primary_key=True)
    #chat_history = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    mesagges_sent = db.relationship('Message_Sent', backref='user', lazy=True)

    def __repr__(self):
        return "<Chat_Room %r>" % self.id
    
    def serialize(self):
        return{
            "id": self.id,
            "timestamp": self.timestamp,
            "mesagges_sent": self.mesagges_sent
        }