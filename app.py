import os
from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from flask_mail import Mail, Message
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token
)
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, send
from models import db, User, Professional, Patient, Panic_Alert, Professional_Status, Message_Sent, Chat_Room

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static')
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

app = Flask(__name__)
app.url_map.strict_slashes = False
app.config['DEBUG'] = True
app.config['ENV'] = 'development'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'dev.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'super-secret-key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_DEBUG'] = True
app.config['MAIL_USERNAME'] = 'helpmn2020@gmail.com'
app.config['MAIL_PASSWORD'] = ''
app.config['SECRET_KEY'] = 'mysecret'
JWTManager(app)
CORS(app)
bcrypt = Bcrypt(app) 
db.init_app(app)
Migrate(app, db)
mail = Mail(app)
socketIo = SocketIO(app, cors_allowed_origins="*")
manager = Manager(app)
manager.add_command("db", MigrateCommand)
app.debug = True
app.host = 'localhost'

def send_mail(subject, sender, recipients, body=None, html=None):
    msg = Message(subject, 
        sender=sender,
        recipients=[recipients])

    if body is not None:
        msg.body = body
    if html is not None:
        msg.html = html

    mail.send(msg)

    return "Correo Enviado"

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def root():
    return render_template('index.html')

@app.route('/api/professional/login', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400

    username = request.json.get('username', None)
    password = request.json.get('password', None)
    if not username:
        return jsonify({"msg": "Missing username parameter"}), 400
    if not password:
        return jsonify({"msg": "Missing password parameter"}), 400

    user = User.query.filter_by(username = username).first()

    if not user:
        return jsonify({"msg": "User not found"}), 404

    if bcrypt.check_password_hash(user.password, password):

        access_token = create_access_token(identity=username)
        data = {
            "access_token": access_token,
            "user": user.serialize()
        }
        return jsonify(data), 200
    else:
        return jsonify({"msg": "Bad username or password"}), 401

@app.route('/api/professional/register', methods=['POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', None)
        password = request.form.get('password', None)
        

        if not username and username == "":
            return jsonify({"msg": "Field username is required"}), 400
        if not password and password == "":
            return jsonify({"msg": "Field password is required"}), 400
        if not 'avatar' and avatar.filename == "":
            return jsonify({"msg": "Field avatar is required"}), 400
        
        user = User.query.filter_by(username = username).first()
        if user:
            return jsonify({"msg": "User exists"}), 400
        
        if 'avatar' in request.files and allowed_file(avatar.filename):
            avatar = request.files['avatar']
            now = datetime.now()
            dt_string = now.strftime("%Y-%m-%d-%H%M%S")
            filename = secure_filename(avatar.filename)
            filename = str(dt_string+filename)
            avatar.save(os.path.join(os.path.join(app.config['UPLOAD_FOLDER'], 'img/avatar'), filename))
        else:
            return jsonify({"msg": "Image not allowed"})
               
        user = User()
        user.username = username
        user.password = bcrypt.generate_password_hash(password)
        
        if 'avatar' in request.files:
            user.avatar = filename 

        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity=user.username)
        data = {
            "access_token": access_token,
            "user": user.serialize()
        }
        return jsonify(data), 200

@app.route('/api/patient/login', methods=['POST'])
def login():
    pass

@app.route('/api/patient/register', methods=['POST'])
def register():
    pass

@app.route('/api/patient/alert/<active_alert>', methods=['POST'])
@jwt_required
def send_alert(active_alert):

    msg = Message("Prueba de Email", 
        sender="helpmn2020@gmail.com",
        recipients=[''])

    msg.body = "Hola esto es una prueba de email"

    mail.send(msg)

    return "Correo Enviado"

@app.route('/api/professional/status/<available>')
@jwt_required
def status(available):
    #Disponible: Puede recibir alertas al mail
    #No Disponibles: No puede recibir alertas
    return "La disponibilidad del profesional es: {}".format(available)

@app.route('/api/professional/profile/<id>', methods=['GET'])
@jwt_required
def profile(id=None):
    #En la vista del perfil, el profesional tiene la opción 
    #de modificar los documentos cargados, y ver las conversaciones que ha tenido.
    pass
    
@app.route('/api/chat-room/<id>')
@jwt_required
def chat(id=None):
    pass

@app.route('/api/user/avatar/<filename>')
@jwt_required
def uploaded_file(filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], 'img/avatar'), filename)


@socketIo.on("/message")
def handleMessage(msg):
    print(msg)
    send(msg, broadcast=True)
    return None

 
if __name__ == '__main__':
    manager.run()
    