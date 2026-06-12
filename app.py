from flask import Flask, render_template, request, flash, jsonify, redirect, url_for
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
from datetime import datetime
import os
import json

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# CSRF
csrf = CSRFProtect(app)

# Base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///goldenstep.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Login
login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'

# Correo
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']
mail = Mail(app)

# Rate Limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://"
)

# ==================
# MODELOS
# ==================

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(200), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    imagen = db.Column(db.String(100), nullable=False)
    tag = db.Column(db.String(50))
    activo = db.Column(db.Boolean, default=True)
    categoria = db.Column(db.String(20), nullable=False, default='hombre')
    tipo = db.Column(db.String(20), nullable=False, default='zapatillas')

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    direccion = db.Column(db.String(200), nullable=False)
    ciudad = db.Column(db.String(100), nullable=False)
    referencia = db.Column(db.String(200))
    productos = db.Column(db.Text, nullable=False)
    total = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

class Mensaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(100), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

# ==================
# RUTAS TIENDA
# ==================

@app.route('/')
def index():
    productos = Producto.query.filter_by(activo=True).limit(3).all()
    return render_template('index.html', productos=productos)

@app.route('/carrito')
def carrito():
    return render_template('carrito.html')

@app.route('/checkout')
def checkout():
    return render_template('checkout.html')

@app.route('/catalogo')
def catalogo():
    categoria = request.args.get('categoria', 'todos')
    tipo = request.args.get('tipo', 'todos')

    query = Producto.query.filter_by(activo=True)
    if categoria != 'todos':
        query = query.filter_by(categoria=categoria)
    if tipo != 'todos':
        query = query.filter_by(tipo=tipo)

    productos = query.all()
    return render_template('catalogoCompleto.html', productos=productos,
                            categoria_actual=categoria, tipo_actual=tipo)

@app.route('/send_email', methods=['POST'])
def send_email():
    try:
        nombre = request.form['nombre']
        correo = request.form['correo']
        mensaje_texto = request.form['mensaje']

        nuevo_mensaje = Mensaje(nombre=nombre, correo=correo, mensaje=mensaje_texto)
        db.session.add(nuevo_mensaje)
        db.session.commit()

        msg = Message('Nuevo mensaje de contacto',
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[app.config['MAIL_USERNAME']])
        msg.body = f"Nombre: {nombre}\nCorreo: {correo}\nMensaje: {mensaje_texto}"
        mail.send(msg)
        flash("Mensaje enviado correctamente.", "success")
    except Exception as e:
        print(f"Error: {e}")
        flash("Ocurrió un error al enviar el mensaje.", "danger")
    return render_template('index.html', productos=Producto.query.filter_by(activo=True).limit(3).all())

@app.route('/guardar_pedido', methods=['POST'])
@csrf.exempt
def guardar_pedido():
    try:
        datos = request.get_json()
        nuevo_pedido = Pedido(
            nombre=datos['nombre'],
            telefono=datos['telefono'],
            direccion=datos['direccion'],
            ciudad=datos['ciudad'],
            referencia=datos.get('referencia', ''),
            productos=json.dumps(datos['productos']),
            total=datos['total']
        )
        db.session.add(nuevo_pedido)
        db.session.commit()
        return jsonify({'status': 'success', 'id': nuevo_pedido.id})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error'}), 500

# ==================
# RUTAS ADMIN
# ==================

@app.route('/admin/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def admin_login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']
        admin = Admin.query.filter_by(usuario=usuario).first()
        if admin and check_password_hash(admin.password, password):
            login_user(admin)
            return redirect(url_for('admin_panel'))
        flash('Usuario o contraseña incorrectos', 'danger')
    return render_template('admin_login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
def admin_panel():
    pedidos = Pedido.query.order_by(Pedido.fecha.desc()).all()
    mensajes = Mensaje.query.order_by(Mensaje.fecha.desc()).all()
    for p in pedidos:
        p.productos_lista = json.loads(p.productos)
    return render_template('admin.html', pedidos=pedidos, mensajes=mensajes)

@app.route('/admin/eliminar_pedido/<int:id>')
@login_required
def eliminar_pedido(id):
    pedido = Pedido.query.get_or_404(id)
    db.session.delete(pedido)
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/eliminar_mensaje/<int:id>')
@login_required
def eliminar_mensaje(id):
    mensaje = Mensaje.query.get_or_404(id)
    db.session.delete(mensaje)
    db.session.commit()
    return redirect(url_for('admin_panel'))

with app.app_context():
    db.create_all()

    if not Admin.query.filter_by(usuario=os.getenv('ADMIN_USUARIO')).first():
        admin = Admin(
            usuario=os.getenv('ADMIN_USUARIO'),
            password=generate_password_hash(os.getenv('ADMIN_PASSWORD'))
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin creado")

    if not Producto.query.first():
        productos_iniciales = [
            Producto(nombre='Colección Verano', descripcion='Piezas ligeras para días cálidos', precio=90, imagen='3.avif', tag='Nuevo', categoria='mujer', tipo='zapatillas'),
            Producto(nombre='Colección Noche', descripcion='Elegancia para ocasiones especiales', precio=129, imagen='22.jpeg', tag='Popular', categoria='mujer', tipo='zapatillas'),
            Producto(nombre='Colección Casual', descripcion='Comodidad y estilo en cada paso', precio=59, imagen='11.jpeg', tag=None, categoria='mujer', tipo='accesorios'),
            Producto(nombre='Modelo Clásico', descripcion='Diseño atemporal para cualquier ocasión', precio=75, imagen='0.jpeg', tag=None, categoria='hombre', tipo='zapatillas'),
            Producto(nombre='Edición Urbana', descripcion='Para el ritmo de la ciudad', precio=110, imagen='8.jpeg', tag='Popular', categoria='hombre', tipo='zapatillas'),
            Producto(nombre='Sport Plus', descripcion='Rendimiento y comodidad al máximo', precio=95, imagen='9.jpeg', tag='Nuevo', categoria='hombre', tipo='accesorios'),
            Producto(nombre='Colección Premium', descripcion='Materiales de primera calidad', precio=149, imagen='14.jpeg', tag=None, categoria='hombre', tipo='zapatillas'),
            Producto(nombre='Estilo Retro', descripcion='El look clásico que nunca pasa de moda', precio=85, imagen='77.jpeg', tag=None, categoria='niños', tipo='zapatillas'),
            Producto(nombre='Colección Street', descripcion='Moda urbana con actitud', precio=99, imagen='88.jpeg', tag='Popular', categoria='niños', tipo='zapatillas'),
            Producto(nombre='Modelo Deportivo', descripcion='Ideal para el día a día activo', precio=80, imagen='331.jpeg', tag=None, categoria='niños', tipo='accesorios'),
            Producto(nombre='Edición Limitada', descripcion='Exclusividad en cada detalle', precio=189, imagen='441.jpeg', tag='Nuevo', categoria='mujer', tipo='accesorios'),
            Producto(nombre='Colección Everyday', descripcion='Para lucir bien todos los días', precio=69, imagen='pp.jpeg', tag=None, categoria='hombre', tipo='accesorios'),
        ]
        db.session.add_all(productos_iniciales)
        db.session.commit()
        print("Productos iniciales creados")

if __name__ == "__main__":
    app.run(debug=os.getenv('FLASK_DEBUG', '0') == '1')