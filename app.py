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
from flask_socketio import SocketIO, send, emit
from models import db, User, Professional, Patient, Channel, Chat_Message

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
        return jsonify({
            "user": {},
            "login": {
                "error": "Debe introducirse un email válido.",
                "finish": "false"
            }
        }), 400
        #return jsonify({"msg": "Debe introducirse un email válido."}), 400
    if not password:
        #return jsonify({"msg": "Debe introducirse una contraseña válida."}), 400
        return jsonify({
            "user": {},
            "login": {
                "error": "Debe introducirse una contraseña válida",
                "finish": "false"
            }
        }), 400

    user = User.query.filter_by(email = email).first()
    if not user:
        #return jsonify({"msg": "No se ha encontrado ningún usuario asociado a este email."}), 404
        return jsonify({
            "user": {},
            "login": {
                "error": "No se ha encontrado ningún usuario asociado a este email.",
                "finish": "false"
            }
        }), 400

    user_type = user.serialize()['user_type']
    if user_type != "patient":
        #return jsonify({"msg": "El correo ya esta en uso, acceda como profesional"}), 404
        return jsonify({
            "user": {},
            "login": {
                "error": "El correo ya esta en uso, acceda como profesional",
                "finish": "false"
            }
        }), 400


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
        #return jsonify({"msg": "Algo ha salido mal."}), 401
        return jsonify({
            "user": {},
            "login": {
                "error": "Algo ha salido mal.",
                "finish": "false"
            }
        }), 400


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


    new_user = User()
    new_user.password = bcrypt.generate_password_hash(password)
    new_user.email = email
    new_user.user_type = "patient"
    db.session.add(new_user)
    db.session.commit()
    user = new_user.serialize()

    new_patient = Patient()
    new_patient.name = username
    new_patient.user_id = user['id']
    db.session.add(new_patient)
    db.session.commit()

    access_token = create_access_token(identity=new_user.email)

    data = {
        "access_token": access_token,
        "user": user,
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
            user = User.query.filter_by(id = pro.user_id).first()
            recipients.append(user.email)
        print(recipients)
        msg = Message("Solicitud de Ayuda - Help Me Now",
                sender="helpmn2020@gmail.com",
                recipients= recipients)

        msg.body = "Hay un usuario que necesita atención psicológica inmediata, sus síntomas son:" + " " + sintomas + ". Haz click aquí para acceder: http://localhost:3000/"
        #TO DO: Enviar al profesional el link directo hacia el chat
        mail.send(msg)
        return "Solicitud de Ayuda enviada a todos los profesionales disponibles."






@app.route('/api/user/avatar/<filename>')
@jwt_required
def uploaded_file(filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], 'img/avatar'), filename)

@app.route('/api/private', methods=['GET'])
@jwt_required
def private():
    return jsonify({"msg": "Private Route"}), 200




# RUTAS DE PACIENTE -----------------------------------------------------------------------

# ----------------------------------------------------------------------------------------

# RUTAS DE CONTACTO ENTRE EL PACIENTE Y EL PROFESIONAL-------------------------------------

@socketIo.on('new_request')
def new_request(info):
    # info contiene:
    #   user_id
    #   patient_state # TO DO, Agregar en el channel este campo
    user_id = int(info['user_id'])

   # Create New channel to chat with a profesional
    new_channel = Channel()
    new_channel.patient_user_id = user_id
    new_channel.state = "pending"
    db.session.add(new_channel)
    db.session.commit()
    channel = new_channel.serialize()

    print(channel)

    # Emit to the Patient the channel id created
    emit('wait_channel_' + str(channel['patient_user_id']), {
       "channel_id": channel['id']
    }, broadcast=True)

    # Emit to the Professionals the request with the patient and channel
    user = User.query.filter_by(id = channel['patient_user_id']).first()
    if user:
        emit('wait_requests', {
        "channel_id": channel['id'],
        "state": channel['state']
        }, broadcast=True)

# ----------------------------------------------------------------------------------------


# RUTAS DE PROFESIONALES -----------------------------------------------------------------------

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
    
    user = User.query.filter_by(email = email).first()
    if not user:
        return jsonify({
            "user": {},
            "login": {
                "error": "El correo ingresado no esta registrado",
                "finish": "false"
            }
        }), 400

    user_type = user.serialize()['user_type']
    if user_type != "professional":
        return jsonify({
            "user": {},
            "login": {
                "error": "El correo ya esta en uso, no puede ingresar como profesional",
                "finish": "false"
            }
        }), 400

    # Pasaron todas las validaciones

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

    print(request.files)

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

    # 1. Se registrará el usuario
    new_user = User()
    new_user.password = bcrypt.generate_password_hash(password)
    new_user.email = email
    new_user.user_type = "professional"
    db.session.add(new_user)
    db.session.commit()
    user = new_user.serialize()

    # 2. Se crea el profesional
    new_professional = Professional()
    new_professional.name = name
    new_professional.user_id = user['id']
    new_professional.rut = filename_rut
    new_professional.certification = filename_certification
    new_professional.numberid = filename_numberid
    new_professional.curriculum = filename_curriculum
    db.session.add(new_professional)
    db.session.commit()

    #Se envía correo de confirmación
    html = render_template('base.html', user=new_user)
    send_mail("Bienvenido a Help me Now - Profesional", "helpmn2020@gmail.com", new_user.email, html)

    # Luego de la creacion del usuario, se general el token de acceso para el login
    access_token = create_access_token(identity=new_user.email)

    # Respuesta
    data = {
        "access_token": access_token,
        "user": user,
        "register": {
            "error": "",
            "message": "Profesional registrado con éxito",
            "finish": "true"
        }
    }
    return jsonify(data), 200

@app.route('/api/professional/<id>/take/<channel_id>', methods=['POST'])
def professional_take(id=None, channel_id=None):
    # contiene:
    #   id
    #   channel_id
    user_id = int(id)
    parsed_channel_id = int(channel_id)

    # buscar el usuario profesional
    user = User.query.filter_by(id = user_id).first()
    if not user:
        return jsonify({
            "user": {},
            "error": "El usuario no existe"
        }), 400
    
    # buscar el channel 
    channel = Channel.query.filter_by(id = parsed_channel_id).first()
    if not channel:
        return jsonify({
            "user": {},
            "error": "El canal no existe"
        }), 400
    
    # verificar si el canal fue tomado o no
    #if channel.state:
    #    return jsonify({
    #        "user": {},
    #        "error": "El canal no existe"
    #    }), 400

    channel.profesional_user_id = user.serialize()['id']
    db.session.add(channel)
    db.session.commit()

    channel_id = channel.serialize()["id"]

    # Respuesta
    return jsonify({"channel_id": channel_id}), 200

@app.route('/api/professional/requests', methods=['GET'])
def professional_requests():
    # buscar el usuario profesional
    channels = Channel.query.filter_by(state = "pending").all()

    # Respuesta
    return jsonify({'channels': list(map(lambda channel: channel.to_request_serialize(), channels))}), 200

@app.route('/api/professional/handling/notifications', methods=['POST'])
def professional_handling_notifications():
    # Data recibida:
    #   request.state
    #   request.id
    state = int(request.json.get('state', None))
    user_id = int(request.json.get('id', None))
    print(state)

    professional = Professional.query.filter_by(user_id = user_id).first()
    #cerrar channel
    professional.status = state
    db.session.commit()

    # Respuesta
    return jsonify({'result': "ok"}), 200

@app.route('/api/professional/<id>/notifications/state', methods=['GET'])
def professional_notification_state(id=None):
    professional = Professional.query.filter_by(user_id = id).first()

    # Respuesta
    return jsonify({'state': professional.status}), 200


# RUTAS DE CHANNELS -----------------------------------------------------------------------

@socketIo.on('closed_channel')
def closed_channel(info):
    # info contiene:
    #   channel_id
    # Emit to the Other User that the channel was closed
    emit('channel_closed_' + str(info['channel_id']), {
       "state": "closed"
    }, broadcast=True)

@app.route('/api/channel/close', methods=['POST'])
def close_channel():
    # Data recibida:
    #   request.channel_id
    #   request.user_id
    channel_id = request.json.get('channel_id', None)
    # buscar el channel a cerrar
    channel = Channel.query.filter_by(id = channel_id).first()
    #cerrar channel
    channel.state = "close"
    db.session.commit()

    # Respuesta
    return jsonify({'message': "ok"}), 200

@app.route('/api/channel/<channel_id>/messages', methods=['GET'])
def channel_messages(channel_id=None):
    # buscar los mensajes que esten en el channel
    messages = Chat_Message.query.filter_by(channel_id = channel_id).all()

    # Respuesta
    return jsonify({'messages': list(map(lambda message: message.serialize(), messages))}), 200

@socketIo.on('open_chat_to_patient')
def open_chat_to_patient(info):
    print("abierto el chat")
    print(info['channel_id'])

    # buscar el channel a ocupar
    channel_id = int(info['channel_id'])
    channel = Channel.query.filter_by(id = channel_id).first()
    #cerrar channel
    channel.state = "occupied"
    db.session.commit()

    emit('wait_professional_channel_' + str(info['channel_id']), {
       "ok": "true"
    }, broadcast=True)

@socketIo.on("handleMessage")
def handleMessage(msg):
    print(msg)
    send(msg, broadcast=True)
    #return None

@socketIo.on('new_message')
def new_message(message):
    # message contiene:
    #   channel_id
    #   user_id
    #   text
    user_id = int(message['user_id'])
    channel_id = int(message['channel_id'])

    # buscar el usuario profesional
    user_query = User.query.filter_by(id = user_id).first()
    # buscar el channel 
    channel_query = Channel.query.filter_by(id = channel_id).first()

    user = user_query.serialize()
    channel = channel_query.serialize()  

    # Save message
    new_chat_message = Chat_Message()
    new_chat_message.text = message['text']
    new_chat_message.user_id = user["id"]
    new_chat_message.username = user["email"]
    new_chat_message.channel_id = channel["id"]
    db.session.add(new_chat_message)
    db.session.commit()

    emit('channel-' + str(channel["id"]), {
       "text": message['text'],
       "user_id": message['user_id']
    }, broadcast=True)

# ----------------------------------------------------------------------------------------


if __name__ == '__main__':
    socketIo.run(app)
    manager.run()
