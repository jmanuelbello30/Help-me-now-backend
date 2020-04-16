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
from models import db, User, Professional, Patient, Panic_Alert, Status_Professional, Message_Sent, Chat_Room

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
app.config['MAIL_PASSWORD'] = 'Helpmenow2020'
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

def send_mail(subject, sender, recipients, message):
    msg = Message(subject,
                  sender=sender,
                  recipients=[recipients])

    msg.html = message

    mail.send(msg)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def root():
    return render_template('index.html')

@app.route('/api/users/<int:id>', methods=['DELETE'])
def deleteUser(id):
    user = Patient.query.get(id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
    db.session.delete(user)
    db.session.commit()

    return jsonify({"msg": "User deleted"})

@app.route('/api/patient/login', methods=['POST'])
def loginPatient():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400

    email = request.json.get('email', None)
    password = request.json.get('password', None)
    if not email:
        return jsonify({"msg": "Debe introducirse un email válido."}), 400
    if not password:
        return jsonify({"msg": "Debe introducirse una contraseña válida."}), 400

    user = User.query.filter_by(email = email).first()

    if not user:
        return jsonify({"msg": "No se ha encontrado ningún usuario asociado a este email."}), 404

    if bcrypt.check_password_hash(user.password, password):

        access_token = create_access_token(identity=email)
        data = {
            "access_token": access_token,
            "user": user.serialize(),
            "login": {
                "error": "",
                "message": "Bienvenido/a",
                "finish": "true"
            }
        }
        return jsonify(data), 200
    else:
        return jsonify({"msg": "Algo ha salido mal."}), 401


@app.route('/api/patient/register', methods=['POST'])
def registerPatient():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 405

    email = request.json.get('email', None)
    username = request.json.get('username', None)
    password = request.json.get('password', None)

    if not email:
        return jsonify({"msg": "Se requiere un email válido."}), 406
    if not password:
        return jsonify({"msg": "Se requiere una contraseña válida."}), 407

    user = User.query.filter_by(email=email).first()

    if user:
        return jsonify({"msg": "El email ya está registrado"}), 408

    new_patient = Patient()
    new_patient.name = username
    db.session.add(new_patient)
    db.session.commit()
    patient = new_patient.serialize()

    user = User()
    user.email = email
    user.password = bcrypt.generate_password_hash(password)
    user.user_type = "patient"
    user.patient_id = patient['id']
    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(identity=user.email)

    data = {
        "access_token": access_token,
        "user": user.serialize(),
        "register": {
            "error": "",
            "message": "Paciente registrado con éxito.",
            "finish": "true"
        }
        }

    msg = Message("Bienvenido a Help Me Now - Paciente", 
        sender="helpmn2020@gmail.com",
        recipients=[email])

    msg.body = "Registro completado con éxito. Gracias por usar nuestro sitio."

    mail.send(msg)

    return jsonify(data), 200
    

    

@app.route('/api/patient_request', methods=['POST'])
def handlePatientRequest():
    #Filtra y devuelve todos los profesionales cuyo status sea true (1)
    availablePros = Professional.query.filter_by(status = 1).all()
    #Se obtienen los síntomas del paciente desde el session storage
    sintomas = request.json.get("sintomas", None)
    recipients = []
    #Por cada profesional disponible, añade su correo a la variable recipients
    if availablePros:
        for pro in availablePros:
            recipients.append(pro.email)
        print(recipients)
        msg = Message("Solicitud de Ayuda - Help Me Now",
                sender="helpmn2020@gmail.com",
                recipients= recipients)

        msg.body = "Hay un usuario que necesita atención psicológica inmediata, sus síntomas son:" + " " + sintomas
        #TODO: Enviar al profesional el link directo hacia el chat
        mail.send(msg)
        return "Solicitud de Ayuda enviada a todos los profesionales disponibles."

@app.route('/api/profile/<id>')
def profile(id=None):
    return "ID del profesional es: {}".format(id)

@app.route('/api/chat-room/<id>')
@jwt_required
def chat(id=None):
    pass

@app.route('/api/user/avatar/<filename>')
@jwt_required
def uploaded_file(filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], 'img/avatar'), filename)

@app.route('/api/private', methods=['GET'])
@jwt_required
def private():
    return jsonify({"msg": "Private Route"}), 200

@socketIo.on("/message")
def handleMessage(msg):
    print(msg)
    send(msg, broadcast=True)
    return None

# RUTAS DE PROFESIONALES

@app.route('/api/professional/login', methods=['POST'])
def professional_login():
    # Data recibida:
    #   request.email
    #   request.password

    if request.method == 'POST':
      email = request.json.get('email', None)
      password = request.json.get('password', None)

    if not email or email == "":
        return jsonify({
            "user": {},
            "login": {
                "error": "Debe introducir Email registrado",
                "finish": "false"
            }
        }), 400

    if not password or password == "":
        return jsonify({
            "user": {},
            "login": {
                "error": "Debe introducir su password para acceder perfil",
                "finish": "false"
            }
        }), 400

    # Pasaron todas las validaciones

    user = User.query.filter_by(email = email).first()

    if not user:
        return jsonify({
            "user": {},
            "login": {
                "error": "El correo ingresado no esta registrado",
                "finish": "false"
            }
        }), 400


    # 1. Se Logea el profesional
    if bcrypt.check_password_hash(user.password, password):
    # Se genera el acceso atraves del token para el login
        access_token = create_access_token(identity=user.email)
    # Respuesta
        data = {
            "access_token": access_token,
            "user": user.serialize(),
            "login": {
                "error": "",
                "message": "Bienvenido/a",
                "finish": "true"
            }
        }
        return jsonify(data), 200
    else:
        return jsonify({
            "user": {},
            "login": {
                "error": "Password incorrecto, por favor revise",
                "finish": "false"
            }
        }), 401

@app.route('/api/professional/register', methods=['POST'])
def professional_register():
    # Data recibida:
    #   request.name
    #   request.email
    #   request.password
    #   request.files.rut
    #   request.files.certification
    #   request.files.numberid
    #   request.files.curriculum

    #print(request.files)

    if not request.files:
       return jsonify({"message": "Debe Seleccionar los documentos"}), 400

    name          = request.form.get('name', None)
    email         = request.form.get('email', None)
    password      = request.form.get('password', None)

    rut           = request.files["rut"]
    certification = request.files["certification"]
    numberid      = request.files["numberid"]
    curriculum    = request.files["curriculum"]

    if not rut or rut.filename == "":
        return jsonify({
            "user": {},
            "register": {
                "error": "Debe cargar el documento RUT",
                "finish": "false"
            }
        }), 400
    if not certification or certification.filename == "":
        return jsonify({
            "user": {},
            "register": {
                "error": "Debe cargar el documento certification",
                "finish": "false"
            }
        }), 400
    if not numberid or numberid.filename == "":
        return jsonify({
            "user": {},
            "register": {
                "error": "Debe cargar el documento numberid",
                "finish": "false"
            }
        }), 400
    if curriculum and curriculum.filename == "":
        return jsonify({
            "user": {},
            "register": {
                "error": "Debe cargar el documento curriculum profesional",
                "finish": "false"
            }
        }), 400

    if not name or name == "":
        return jsonify({
            "user": {},
            "register": {
                "error": "El nombre es obligatorio",
                "finish": "false"
            }
        }), 400
    if not password or password == "":
        return jsonify({
            "user": {},
            "register": {
                "error": "Missing password parameter",
                "finish": "false"
            }
        }), 400
    if not email or email == "":
        return jsonify({
            "user": {},
            "register": {
                "error": "Missing email parameter",
                "finish": "false"
            }
        }), 400


    user = User.query.filter_by(email = email).first()
    if user:
        return jsonify({
            "user": {},
            "register": {
                "error": "Ya se ha creado un usuario con este email, por favor ingrese otro",
                "finish": "false"
            }
        }), 400

    if allowed_file(rut.filename):
        filename_rut = secure_filename(rut.filename + "_" + email)
        rut.save(os.path.join(os.path.join(app.config['UPLOAD_FOLDER'], 'img/documents'), filename_rut))
    if allowed_file(certification.filename):
        filename_certification = secure_filename(certification.filename + "_" + email)
        certification.save(os.path.join(os.path.join(app.config['UPLOAD_FOLDER'], 'img/documents'), filename_certification))
    if allowed_file(numberid.filename):
        filename_numberid = secure_filename(numberid.filename + "_" + email)
        numberid.save(os.path.join(os.path.join(app.config['UPLOAD_FOLDER'], 'img/documents'), filename_numberid))
    if allowed_file(curriculum.filename):
        filename_curriculum = secure_filename(curriculum.filename + "_" + email)
        curriculum.save(os.path.join(os.path.join(app.config['UPLOAD_FOLDER'], 'img/documents'), filename_curriculum))

    # Pasaron todas las validaciones
    # Se registra el profesional en 3 pasos:

    # 1. Se crea el profesional
    new_professional = Professional()
    new_professional.name = name
    new_professional.rut = filename_rut
    new_professional.certification = filename_certification
    new_professional.numberid = filename_numberid
    new_professional.curriculum = filename_curriculum
    db.session.add(new_professional)
    db.session.commit()
    professional = new_professional.serialize()

    # 2. Se registrará el usuario
    user = User()
    user.password = bcrypt.generate_password_hash(password)
    user.email = email
    user.user_type = "professional"
    user.professional_id = professional['id']
    db.session.add(user)
    db.session.commit()

    #Se envía correo de confirmación
    html = render_template('base.html', user=user)
    send_mail("Bienvenido a Help me Now - Profesional", "helpmn2020@gmail.com", user.email, html)

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
    
