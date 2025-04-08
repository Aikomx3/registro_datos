import os
from flask import Flask, request, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from flask_mail import Mail, Message
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Establecer la ubicación de Tesseract (esto es necesario si Tesseract no está en el PATH)
pytesseract.pytesseract.tesseract_cmd = os.getenv('TESSERACT_PATH', '/usr/bin/tesseract')

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configuración de correo electrónico
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_USERNAME")

mail = Mail(app)

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "Levies_24_token")


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def enhance_image(image_path):
    try:
        img = Image.open(image_path)
        img = img.convert('L')  # Convertir a escala de grises
        # Evitar filtros agresivos
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2)  # Mejora del contraste de manera más sutil
        img = img.filter(ImageFilter.SHARPEN())  # Usamos un filtro de enfoque más suave
        return img
    except Exception as e:
        print(f"Error al mejorar la imagen: {e}")
        return None


def extract_text_from_image(image_path, languages='eng+spa+fra+deu+ita+por+rus+pol+ukr+ces+ron+jpn+chi_sim+chi_tra+kor+hin+ara'):
    try:
        img = enhance_image(image_path)
        if img is None:
            return ""
        # Usamos pytesseract con múltiples idiomas
        text = pytesseract.image_to_string(img, lang=languages)
        print("Texto extraído:", text)  # Para depuración
        return text
    except Exception as e:
        print(f"Error al procesar imagen: {e}")
        return ""


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    token = request.form.get('access_token')
    if token != ACCESS_TOKEN:
        return "<h2>Acceso denegado.</h2><a href='/'>Volver</a>"

    if 'file' not in request.files:
        return redirect(url_for('index'))

    files = request.files.getlist('file')

    if len(files) == 0 or len(files) > 10:
        return "<h2>Debes subir entre 1 y 10 imágenes.</h2><a href='/'>Volver</a>"

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    extracted_text = ""

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)
            # Extraemos texto en todos los idiomas posibles
            extracted_text += extract_text_from_image(path) + "\n\n"
            os.remove(path)

    if extracted_text:
        return render_template('results.html', extracted_text=extracted_text)
    else:
        return "<h2>No se extrajo texto de las imágenes.</h2><a href='/'>Volver</a>"


@app.route('/send_email', methods=['POST'])
def send_email():
    extracted_text = request.form['extracted_text']
    msg = Message("Datos extraídos de las imágenes",
                  recipients=[os.getenv("MAIL_USERNAME")])
    msg.body = extracted_text

    try:
        mail.send(msg)
        return "<h2>Correo enviado correctamente.</h2><a href='/'>Volver</a>"
    except Exception as e:
        return f"<h2>Error al enviar correo: {e}</h2><a href='/'>Volver</a>"


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
