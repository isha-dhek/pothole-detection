import base64
import os
from pathlib import Path
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from flask_cors import CORS, cross_origin
import cv2
from pdf2image import convert_from_path
import torch
from werkzeug.utils import secure_filename
from yolov5 import detect
import re
import sqlite3
from flask import g


# create flask app
app = Flask(__name__)

# cors
CORS(app)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('database.db')
        # Optional: Enable row factory to access rows by column name
        g.db.row_factory = sqlite3.Row
    return g.db
def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()
@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()


def allowed_file_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_file_video(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in set(['mp4'])

def allowed_file_pdf(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in set(['pdf'])


# app.config for file upload
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
app.secret_key = "super_secret_key"
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


# route for homepage
@app.route('/')
@cross_origin()
def index():
    return render_template('index.html')


# route for live camera video
@app.route('/displaycamera')
@cross_origin()
def displaycamera():
    return render_template('camera.html')


# for sending video back to frontend
@app.route('/display/<filename>')
def display_image(filename):
    
    #print('display_image filename: ' + filename)
    return redirect(url_for('static', filename='uploads/' + filename), code=301)


# route for image upload
@app.route('/displayimage', methods=['GET', 'POST'])
@cross_origin()
def displayimage():
    if request.method == 'GET':
        return render_template('image.html')
    if request.method == 'POST':
        # print("a")
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        # print("b")
        file = request.files['file']
        # print("c")
        if file.filename == '':
            flash('No image selected for uploading')
            return redirect(request.url)
        # print("d")
        if file and allowed_file_image(file.filename):
            filename = secure_filename("image.jpg")
            # print("e")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            print("processing the image")
            # print("f")
            ## images = convert_from_path('example.pdf')
            results = model('static/uploads/image.jpg')
            img = results.render()
            # print("g")
            # print(img.shape)
            cv2.imwrite('static/uploads/image.jpg', img[0])
            print("image processsed")
            db = get_db()
            cursor = db.cursor()
            cursor.execute("INSERT INTO images (filename) VALUES (?)", (filename,))
            db.commit()
            flash('Image successfully uploaded and displayed below')
            # print("1")
            return render_template('image.html', filename=filename)
        else:
            flash('Allowed image types are - png, jpg, jpeg, gif')
            # print("k")
            return redirect(request.url)


# route for video upload
@app.route('/displayvideo/<filename>')
def display_video(filename):
    return redirect(url_for('static', filename='upload/exp/' + filename), code=301)


# for video page
@app.route('/displayvideo', methods=['GET', 'POST'])
@cross_origin()
def video():
    if request.method == 'GET':
        return render_template('video.html')
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No image selected for uploading')
            return redirect(request.url)
        if file and allowed_file_video(file.filename):
            filename = secure_filename("video.mp4")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            print("processing the image")
            # reduce the dimension of the video
            detect.run(weights=Path('best.pt'), source=Path(os.path.join(app.config['UPLOAD_FOLDER'], filename)),project=Path('./static/upload'), name='exp',exist_ok=True)
            # load the video
            # cap = cv2.VideoCapture('static/upload/exp/video.mp4')
            # save cap as different type of video
            os.system("ffmpeg -i static/upload/exp/video.mp4 -vcodec libx264 -f mp4 static/upload/exp/videof.mp4 -y")

            print("image processsed")
            #print('upload_image filename: ' + filename)
            db = get_db()
            cursor = db.cursor()
            cursor.execute("INSERT INTO video (filename) VALUES (?)", (filename,))
            db.commit()
            flash('Video successfully uploaded and displayed below')
            return render_template('video.html', filename="videof.mp4")
        else:
            flash('Allowed image types are - mp4')
            return redirect(request.url)


@app.route('/rtsp', methods=['GET', 'POST'])
@cross_origin()
def rtsp():
    if request.method == 'GET':
        return render_template('rtsp.html')
    if request.method == 'POST':
        # take the rtsp link
        rtsp_link = request.form['rtsp_link']
        detect.run(weights=Path('best.pt'), source=rtsp_link,project=Path('./static/upload'), name='exp',exist_ok=True)
    
        vid_name = re.sub('[^A-Za-z0-9]+', '_', rtsp_link.split('/')[-1])
        os.system(f"ffmpeg -i static/upload/exp/{vid_name}.mp4 -vcodec libx264 -f mp4 static/upload/exp/videof.mp4 -y")

        print("image processsed")
        #print('upload_image filename: ' + filename)
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO video (filename) VALUES (?)", (filename,))
        db.commit()
        flash('Video successfully uploaded and displayed below')
        return render_template('video.html', filename="videof.mp4")
    else:
        flash('Allowed image types are - mp4')
        return redirect(request.url)

    # have to process this


# route for pdf upload
# @app.route('/displaypdf', methods=['GET', 'POST'])
# @cross_origin()
# def imagepdf():
#     print("pdf triggered")
#     print(request)
#     print(request.method)
#     if request.method == 'GET':
#         print("pdf get triggered")
#         return render_template('imagePdf.html')
#     # return render_template('image.html')
#     if request.method == 'POST':
#         print("pdf post triggered")
#         if 'file' not in request.files:
#             flash('No file part')
#             return redirect(request.url)
#         file = request.files['file']
#         if file.filename == '':
#             flash('No image selected for uploading')
#             return redirect(request.url)
#         if file and allowed_file_pdf(file.filename):
#             filename = secure_filename("image.pdf")
#             file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
#             print("processing the image")
#             # convert pdf to image
#             images = convert_from_path('static/uploads/image.pdf')
#             # for i in range(len(images)):
#             # saving first page of pdf into image.jpg
#             images[0].save('static/uploads/image'+'.jpg', 'JPEG')
#             # pdf converted to image
#             # process the image
#             results = model('static/uploads/image.jpg')
#             img = results.render()
#             # print(img.shape)
#             cv2.imwrite('static/uploads/image.jpg', img[0])
#             print("image processsed")
#             flash('Image successfully uploaded and displayed below')
#             return render_template('imagePdf.html', filename="image.jpg")
#         else:
#             flash('Allowed image types are - pdf')
#             return redirect(request.url)


# route for recieveing the camera from post request
@app.route('/camera', methods=['POST'])
@cross_origin()
def camera():
    if request.method == 'POST':
        img_data = request.json['dataURL']  
        if img_data:
            img_data = img_data.replace('data:image/jpeg;base64,', '')
            converted_img = base64.b64decode(img_data)
            with open('static/uploads/image.png', 'wb') as f:
                f.write(converted_img)
            results = model('static/uploads/image.png')
            db = get_db()
            cursor = db.cursor()
            cursor.execute("INSERT INTO images (filename) VALUES (?)", (filename,))
            db.commit()
            img = results.render()
            is_success, im_buf_arr = cv2.imencode(".jpg", img[0])
            byte_im = im_buf_arr.tobytes()
            base64_im = base64.b64encode(byte_im)
            base64_im = base64_im.decode('utf-8')
            img_data = 'data:image/jpeg;base64,' + base64_im
        return jsonify({'dataURL': img_data})


# loading the model in the memory
model = torch.hub.load('ultralytics/yolov5','custom', path='best.pt')  # custom model


if __name__ == '__main__':
    # logging.getLogger('flask_cors').level = logging.DEBUG
    app.run()
