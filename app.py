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
    if not request.files:
        return jsonify({"msg": "Missing FILES in request"}), 400

    file = request.files['avatar'] # TO DO: cambiar el nombre por el de los documentos
    username = request.form.get('username', None)
    password = request.form.get('password', None)

    if not file and file.filename == "":
        return jsonify({"msg": "Missing avatar parameter"}), 400
    if not username and username == "":
        return jsonify({"msg": "Missing username parameter"}), 400
    if not password and password == "":
        return jsonify({"msg": "Missing password parameter"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(os.path.join(app.config['UPLOAD_FOLDER'], 'img/avatar'), filename))
        
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
def login_patient():
    pass

@app.route('/api/patient/register', methods=['POST'])
def register():
    pass

@app.route('/api/patient/alert/<active_alert>', methods=['POST'])
@jwt_required
def send_alert(active_alert):

    msg = Message("Prueba de Email", 
        sender="helpmn2020@gmail.com", # TO DO:  cambiar esto para probar
        recipients=[''])

    msg.body = "Hola esto es una prueba de email"

    mail.send(msg)

    return "Correo Enviado"

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

# RUTAS DE PROFESIONALES

@app.route('/api/professional/register', methods=['POST'])
def professional_register():
    # Data recibida:
    #   request.name
    #   request.email
    #   request.password
    #   request.files.rut
    #   request.files.certification
    #   request.files.numberid
    #   request.files.courses

    #print(request.files)

    if not request.files:
       return jsonify({"message": "Debe Seleccionar los documentos"}), 400

    name          = request.form.get('name', None)
    email         = request.form.get('email', None)
    password      = request.form.get('password', None)

    rut           = request.files["rut"]
    certification = request.files["certification"]
    numberid      = request.files["numberid"]
    #courses       = request.files["courses"]

    if not rut or rut.filename == "":
        return jsonify({
            "user": {},
            "register": {
                "error": "Debe cargar el documento RUT",
                "message": "Datos con error",
                "finish": "false"
            }
        }), 400
    if not certification or certification.filename == "":
        return jsonify({
            "user": {},
            "register": {
                "error": "Debe cargar el documento certification",
                "message": "Datos con error",
                "finish": "false"
            }
        }), 400
    if not numberid or numberid.filename == "":
        return jsonify({
            "user": {},
            "register": {
                "error": "Debe cargar el documento numberid",
                "message": "Datos con error",
                "finish": "false"
            }
        }), 400
    #if courses and courses.filename == "":
    #    return jsonify({
    #        "user": {},
     #       "register": {
     #           "error": "Debe cargar el documento courses",
      #          "message": "Datos con error",
      #          "finish": "false"
       #     }
        #}), 400

    if not name or name == "":
        return jsonify({
            "user": {},
            "register": {
                "error": "El nombre es obligatorio",
                "message": "Datos con error",
                "finish": "false"
            }
        }), 400
    if not password or password == "":
        return jsonify({
            "user": {},
            "register": {
                "error": "Missing password parameter",
                "message": "Datos con error",
                "finish": "false"
            }
        }), 400
    if not email or email == "":
        return jsonify({
            "user": {},
            "register": {
                "error": "Missing email parameter",
                "message": "Datos con error",
                "finish": "false"
            }
        }), 400


    user = User.query.filter_by(email = email).first()
    if user:
        return jsonify({
            "user": {},
            "register": {
                "error": "Ya existe un usuario con el email, ingrese otro email",
                "message": "Datos con error",
                "finish": "false"
            }
        }), 400

    if allowed_file(rut.filename):
        filename_rut = secure_filename(rut.filename)
        rut.save(os.path.join(os.path.join(app.config['UPLOAD_FOLDER'], 'img/documents'), filename_rut))
    if allowed_file(certification.filename):
        filename_certification = secure_filename(certification.filename)
        certification.save(os.path.join(os.path.join(app.config['UPLOAD_FOLDER'], 'img/documents'), filename_certification))
    if allowed_file(numberid.filename):
        filename_numberid = secure_filename(numberid.filename)
        numberid.save(os.path.join(os.path.join(app.config['UPLOAD_FOLDER'], 'img/documents'), filename_numberid))
    #if courses and allowed_file(courses.filename):
     #   filename_courses = secure_filename(courses.filename)
       # courses.save(os.path.join(os.path.join(app.config['UPLOAD_FOLDER'], 'img/documents'), filename_courses))

    # Pasaron todas las validaciones
    # Se registra el profesional en 3 pasos:

    # 1. Se crea el profesional
    new_professional = Professional()
    new_professional.name = name
    new_professional.rut = filename_rut
    db.session.add(new_professional)
    db.session.commit()
    professional = new_professional.serialize()

    # 2. Se registrará el usuario
    user = User()
    user.password = bcrypt.generate_password_hash(password)
    user.email = email
    user.professional_id = professional['id']
    db.session.add(user)
    db.session.commit()

    # Luego de la creacion del usuario, se general el token de acceso para el login
    access_token = create_access_token(identity=user.email)

    # Respuesta
    data = {
        "access_token": access_token,
        "user": user.serialize(),
        "register": {
            "error": "",
            "message": "Profesional registrado con éxito",
            "finish": "true"
        }
    }
    return jsonify(data), 200


if __name__ == '__main__':
    manager.run()
    