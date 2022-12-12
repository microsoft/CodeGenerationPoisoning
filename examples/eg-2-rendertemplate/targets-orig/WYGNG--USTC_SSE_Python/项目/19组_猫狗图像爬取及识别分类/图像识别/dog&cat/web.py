import os
from datetime import timedelta
import time
import cv2
from flask import Flask, request, render_template
from werkzeug.utils import secure_filename
from dogvscat.model import test

app = Flask(__name__)
app.send_file_max_age_default = timedelta(seconds=1)

@app.route('/upload', methods=['GET','POST'])
def upload():
    if request.method == 'POST':
        f = request.files['file']
        # 当前文件所在路径
        basepath = os.path.dirname(__file__)
        # 一定要先创建该文件夹，不然会提示没有该路径
        upload_path = os.path.join(basepath, 'static/images', secure_filename(f.filename))
        f.save(upload_path)
        dorc=test(os.path.join('static/images',f.filename))
        # 使用Opencv转换一下图片格式和名称
        img = cv2.imread(upload_path)
        img=cv2.resize(img,(224,224))
        cv2.imwrite(os.path.join(basepath, 'static/images', 'test.jpg'), img)

        return render_template('upload_ok.html', userinput=dorc,val1=time.time())
    return render_template('upload.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000)