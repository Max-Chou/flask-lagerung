from flask import Flask, request
from flask_lagerung import FileSystemStorage

app = Flask(__name__)

storage = FileSystemStorage()


@app.route('/upload', methods=['POST'])
def upload():
    upload_file = request.files['image']

    name = storage.save(upload_file.filename, upload_file.stream)

    return {"msg": name}
