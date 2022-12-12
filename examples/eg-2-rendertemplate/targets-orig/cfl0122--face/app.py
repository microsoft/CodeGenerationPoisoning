# -*- coding: utf-8 -*-
from flask import Flask,request,render_template,jsonify,make_response

from database import db
from table import User,UserPicture
from form import FaceAddForm,FaceDeleteForm
from config import uploaddir,resultdir,tempdir,threshold,publickey_filepath,sslfile
from rsa_utils import rsa_MD5signverify

import os,json,base64,sys,cv2,argparse
import pickle as pk
import numpy as np

from deploy import face_model_V2





os.environ["MXNET_CUDNN_AUTOTUNE_DEFAULT"] = '0'

model = face_model_V2.FaceModel(args)

# 输入一张包含人脸的图片，返回一个人脸特征向量和一个矩形框
def gen_feature(f):
    img = cv2.imdecode(np.fromfile(f,dtype=np.uint8),cv2.IMREAD_COLOR)
    r = model.get_input(img)
    if r is not None:
        img,bbox=r
        f = model.get_feature(img)
        return f,bbox
    else:
        return None


# 输入一张包含人脸的图片，返回多个人脸特征向量和多个矩形框
def gen_feature_multi(f):
    img = cv2.imdecode(np.fromfile(f,dtype=np.uint8),cv2.IMREAD_COLOR)
    r = model.get_input_multi(img)
    if r is not None:
        fs=[]
        face_imgs,bboxs=r
        for i in range(len(face_imgs)):
            f = model.get_feature(face_imgs[i])
            fs.append(f)
    else:
        return None
    return fs,bboxs

# 输入类型如[(6,212),(5,322),(7:14)...]返回value中元素最大的那个tuple 如（5，322）
def get_max_value_idx(a):
    b=np.array(a).T
    c=b.argmax(axis=1)[1]
    d = a[c]
    return d


# 输入一张包含人脸的图片、人脸特征向量和矩形框，绘制的结果图片保存到结果目录
def plotpic(input_img,output_dir, feats_rects):

    img = cv2.imdecode(np.fromfile(input_img,dtype=np.uint8),cv2.IMREAD_COLOR)

    sim,ret = feats_rects
    for i in range(len(sim)):
        ret_=ret[i]
        if len(sim[i]) !=0 :
            sim_=get_max_value_idx(sim[i])
            cv2.putText(img,str(sim_),(ret_[0]-20,ret_[1]-12),cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,0),2)

        cv2.rectangle(img, (ret_[0], ret_[1]), (ret_[2], ret_[3]), (0, 255, 0), 2)
    f=os.path.join(output_dir,os.path.split(input_img)[-1])
    cv2.imencode('.jpg', img)[1].tofile(f)





app = Flask(__name__,template_folder="template")

# app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///e:/user/user.db'
app.config["SQLALCHEMY_DATABASE_URI"] = 'mysql://chenfeilong:fka!asdaWFT523@10.8.108.12/chenfeilong'
app.config["SQLALCHEMY_COMMIT_ON_TEARDOWN"] = True
db.init_app(app)


# db.drop_all()
# db.create_all()



@app.route('/make',methods=['GET','POST'])
def test3():
    imgnames = []
    if request.method == 'POST':
        imgnames = request.form.get('imgnames')
        if imgnames:
            imgnames=imgnames.split(',')

    return render_template('make.html',imgnames=imgnames)




@app.route('/up_photo3/', methods=['POST'], strict_slashes=False)
def api_recognition_make():

    if not os.path.exists(uploaddir):
        os.makedirs(uploaddir)

    aaaa = request.get_data().decode('utf8')
    bbbb = json.loads(aaaa)

    imgnames = []
    dddddd = []
  #  io=pd.ExcelWriter(resultdir + 'data3.xlsx')

    for i in bbbb:
        name = i.get('name')
        user = User.query.filter_by(filename=name).first()
        if user is not None:
            continue
        imgnames.append(name)
        fi = i.get('base64')
        b64img = fi.split(',')[-1]
        imgdata = base64.b64decode(b64img)
        file = open(uploaddir + name, 'wb')
        file.write(imgdata)
        file.close()
        r = gen_feature_multi(uploaddir + name)
        if r is not None:

            multi_f, bboxs = r
            for i in range(len(multi_f)):

                x1,y1,x2,y2=bboxs[i]

                user=User(personId=name+str(i), filename=name, feature=pk.dumps(multi_f[i]), x1=x1, y1=y1, x2=x2, y2=y2)
                userpic=UserPicture(personId=name+str(i), picData=b64img)
                db.session.add(user)
                db.session.add(userpic)



    db.session.commit()
    return jsonify(imgnames)



@app.route('/up_photo4/', methods=['POST'], strict_slashes=False)
def api_recognition_single():

    users=User.query.all()

    if not os.path.exists(tempdir):
        os.makedirs(tempdir)

    aaaa = request.get_data().decode('utf8')
    bbbb = json.loads(aaaa)

    imgnames = []
    dddddd = []
    #  io=pd.ExcelWriter(resultdir + 'data3.xlsx')

    for i in bbbb:
        name = i.get('name')
        imgnames.append(name)
        fi = i.get('base64')
        fafff = fi.split(',')[-1]
        imgdata = base64.b64decode(fafff)
        file = open(tempdir + name, 'wb')
        file.write(imgdata)
        file.close()
        imgfile = tempdir + name
        r = gen_feature(imgfile)

        if r is not None:
            f1,bbox = r
            fs=[]
            for user in users:
                f2=pk.loads(user.feature)
                dist = np.sum(np.square(f1-f2))
                sim = np.dot(f1, f2.T)
                if sim > threshold :
                    fs.append((user.personId,sim))

            dddddd.append((name,fs,bbox))

    return str(dddddd)


@app.route('/up_find_person/', methods=['POST'], strict_slashes=False)
def up_find_person():

    users=User.query.all()

    if not os.path.exists(tempdir):
        os.makedirs(tempdir)

    aaaa = request.get_data().decode('utf8')
    bbbb = json.loads(aaaa)

    imgnames = []
    dddddd = []
    #  io=pd.ExcelWriter(resultdir + 'data3.xlsx')

    fs=[]
    for i in bbbb:
        name = i.get('name')
        imgnames.append(name)
        fi = i.get('base64')
        fafff = fi.split(',')[-1]
        imgdata = base64.b64decode(fafff)
        file = open(tempdir + name, 'wb')
        file.write(imgdata)
        file.close()
        imgfile = tempdir + name
        r = gen_feature(imgfile)



        if r is not None:
            f1,bbox = r

            for user in users:
                f2=pk.loads(user.feature)
                dist = np.sum(np.square(f1-f2))
                sim = np.dot(f1, f2.T)
                if sim > threshold :

                    # img=cv2.imread(uploaddir + user.filename)
                    img = cv2.imdecode(np.fromfile(uploaddir + user.filename,dtype=np.uint8),cv2.IMREAD_COLOR)
                    cv2.rectangle(img,(user.x1,user.y1),(user.x2,user.y2),(0,255,0))
                    cv2.putText(img,str(sim),(user.x1-10,user.y1-10),cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,0),2)
                    cv2.imwrite(resultdir + user.filename,img)
                    cv2.imencode('.jpg', img)[1].tofile(resultdir + user.filename)
                    fs.append(user.filename)

            # dddddd.append((name,fs,bbox))

    return jsonify(fs)




@app.route('/up_multiface/', methods=['POST'], strict_slashes=False)
def api_recognition_multi_face():

    users=User.query.all()

    if not os.path.exists(tempdir):
        os.makedirs(tempdir)

    aaaa = request.get_data().decode('utf8')
    bbbb = json.loads(aaaa)

    imgnames = []
    dddddd = []
    #  io=pd.ExcelWriter(resultdir + 'data3.xlsx')

    for i in bbbb:
        name = i.get('name')
        imgnames.append(name)
        fi = i.get('base64')
        fafff = fi.split(',')[-1]
        imgdata = base64.b64decode(fafff)
        file = open(tempdir + name, 'wb')
        file.write(imgdata)
        file.close()
        imgfile = tempdir + name
        print(imgfile)
        r = gen_feature_multi(imgfile)

        multi_face_picture=[]
        bboxs=[]
        if r is not None:

            multi_f,bboxs=r
            for i in range(len(multi_f)):
                f1=multi_f[i]
                feats=[]
                for user in users:
                    f2=pk.loads(user.feature)
                    dist = np.sum(np.square(f1-f2))
                    sim = np.dot(f1, f2.T)
                    if sim > threshold :
                        feats.append((user.filename,str(sim)))
                if feats is not None:
                    multi_face_picture.append(feats)

        plotpic(tempdir + name, resultdir, (multi_face_picture,bboxs))
        dddddd.append((name,multi_face_picture,bboxs))


    return jsonify(imgnames)


@app.route('/delete/', methods=['POST'], strict_slashes=False)
def delete():
    users=User.query.all()
    [db.session.delete(u) for u in users]
    db.session.commit()
    return "deleted"


@app.route('/show/<string:filename>', methods=['GET'])
def show_photo(filename):
    if request.method == 'GET':
        if filename is None:
            pass
        else:
            image_data = open(resultdir + filename, "rb").read()
            response = make_response(image_data)
            response.headers['Content-Type'] = 'image/png'
            return response
    else:
        pass



if __name__ == '__main__':
    app.run(debug=True,)


@app.route('/open/v1/pic/storage/add',methods=['POST'])
def tencent_api_add():

    try:
        Timestamp = request.headers["Timestamp"]
        Nonce =  request.headers["Nonce"]
        Auth = request.headers["Auth"]
        message = Timestamp + '&' + Nonce
        try:
            signature = rsa_MD5signverify(message=message, signature=Auth, publickey_filepath=publickey_filepath)
        except Exception as e:
            e.with_traceback()
            resp = {"code": 410, "message": "用户验证失败"}
            return jsonify(resp)
        if signature:
            form = FaceAddForm()
            if form.validate_on_submit():

                storageId = form.storageId.data
                projectId = form.projectId.data
                personId = form.personId.data
                note = form.note.data
                picData = form.picData.data

                result = {"personId": personId}

                imgdata = base64.b64decode(picData)
                file = open(uploaddir + personId, 'wb')
                file.write(imgdata)
                file.close()

                r = gen_feature_multi(file)
                if r is not None:

                    f, bbox = r

                    x1, y1, x2, y2 = bbox
                    user=User(personId=personId,
                              filename=personId,
                              feature=pk.dumps(f),
                              x1=x1,
                              y1=y1,
                              x2=x2,
                              y2=y2,
                              storageId=storageId,
                              projectId=projectId,
                              note=note
                              )
                    userpic=UserPicture(personId=personId,picData=picData)
                    db.session.add(user)
                    db.session.add(userpic)
                    db.session.commit()

                    resp = {"code": 200, "message": "succ", "data": result}

                else:
                    resp = {"code": 202, "message": "图片不符合要求"}

            else:
                resp = {"code": 400, "message": "请求参数不完整或不正确"}

        else:
            resp = {"code": 410, "message": "用户验证失败"}
        return jsonify(resp)

    except:

        resp = {"code": 500, "message": "内部请求出错"}
        return jsonify(resp)





@app.route('/open/v1/pic/storage/del',methods=['POST'])
def tencent_api_del():

    try:
        Timestamp = request.headers["Timestamp"]
        Nonce =  request.headers["Nonce"]
        Auth = request.headers["Auth"]
        message = Timestamp + '&' + Nonce
        try:
            signature = rsa_MD5signverify(message=message, signature=Auth, publickey_filepath=publickey_filepath)
        except Exception as e:
            e.with_traceback()
            resp = {"code": 410, "message": "用户验证失败"}
            return jsonify(resp)
        if signature:
            form = FaceDeleteForm()
            if form.validate_on_submit():
                storageId = form.storageId.data
                projectId = form.projectId.data
                personId = form.personId.data
                for i in personId:

                    user = User.query.filter_by(personId=i, projectId=projectId, storageId=storageId).first()
                    userPicture = UserPicture.query.filter_by(personId=i)
                    if user is not None:
                        db.session.delete(user)
                        db.session.delete(userPicture)
                db.session.commit()

                result = {"personId": personId}
                resp = {"code": 200, "message": "succ", "data": result}
            else:
                resp = {"code": 400, "message": "请求参数不完整或不正确"}
        else:
            resp = {"code": 410, "message": "用户验证失败"}
        return jsonify(resp)
    except:

        resp = {"code": 500, "message": "内部请求出错"}
        return jsonify(resp)



@app.route('/open/v1/pic/storage/search',methods=['POST'])
def tencent_api_search():



    if not os.path.exists(tempdir):
        os.makedirs(tempdir)

    try:
        Timestamp = request.headers["Timestamp"]
        Nonce =  request.headers["Nonce"]
        Auth = request.headers["Auth"]
        message = Timestamp + '&' + Nonce
        try:
            signature = rsa_MD5signverify(message=message, signature=Auth, publickey_filepath=publickey_filepath)
        except Exception as e:
            e.with_traceback()
            resp = {"code": 410, "message": "用户验证失败"}
            return jsonify(resp)
        if signature:
            form = FaceAddForm()
            if form.validate_on_submit():

                storageId = form.storageId.data
                projectId = form.projectId.data
                livedetect = form.livedetect.data
                picData = form.picData.data
                imgdata = base64.b64decode(picData)
                imgfile = tempdir + 'temp.jpg'
                file = open(imgfile, 'wb')
                file.write(imgdata)
                file.close()
                r = gen_feature(imgfile)
                if r is not None:
                    f1,bbox = r
                    data = []
                    users = User.query.filter_by(storageId=storageId, projectId=projectId).all()
                    for user in users:
                        f2 = pk.loads(user.feature)
                        dist = np.sum(np.square(f1-f2))
                        sim = np.dot(f1, f2.T)
                        if sim > threshold :
                            result = {"personId": user.personId,
                                      "livedetect_confidence": 0,
                                      "similarity": sim,
                                      "note": user.note}
                            data.append(result)

                    resp = {"code": 200, "message": "succ", "data": data}

                else:
                    resp = {"code": 202, "message": "图片不符合要求"}

            else:
                resp = {"code": 400, "message": "请求参数不完整或不正确"}

        else:
            resp = {"code": 410, "message": "用户验证失败"}
        return jsonify(resp)

    except:

        resp = {"code": 500, "message": "内部请求出错"}
        return jsonify(resp)


@app.route('/open/v1/pic/storage/search/multi',methods=['POST'])
def tencent_api_search_multi():

    if not os.path.exists(tempdir):
        os.makedirs(tempdir)

    try:
        Timestamp = request.headers["Timestamp"]
        Nonce =  request.headers["Nonce"]
        Auth = request.headers["Auth"]
        message = Timestamp + '&' + Nonce
        try:
            signature = rsa_MD5signverify(message=message, signature=Auth, publickey_filepath=publickey_filepath)
        except Exception as e:
            e.with_traceback()
            resp = {"code": 410, "message": "用户验证失败"}
            return jsonify(resp)
        if signature:
            form = FaceAddForm()
            if form.validate_on_submit():

                storageId = form.storageId.data
                projectId = form.projectId.data
                livedetect = form.livedetect.data
                picData = form.picData.data
                imgdata = base64.b64decode(picData)
                imgfile = tempdir + 'temp.jpg'
                file = open(imgfile, 'wb')
                file.write(imgdata)
                file.close()
                r = gen_feature(imgfile)
                if r is not None:
                    f1,bbox = r
                    data = []
                    users = User.query.filter_by(storageId=storageId, projectId=projectId).all()
                    for user in users:
                        f2 = pk.loads(user.feature)
                        dist = np.sum(np.square(f1-f2))
                        sim = np.dot(f1, f2.T)
                        if sim > threshold :
                            result = {"personId": user.personId,
                                      "livedetect_confidence": 0,
                                      "similarity": sim,
                                      "note": user.note}
                            data.append(result)

                    resp = {"code": 200, "message": "succ", "data": data}

                else:
                    resp = {"code": 202, "message": "图片不符合要求"}

            else:
                resp = {"code": 400, "message": "请求参数不完整或不正确"}

        else:
            resp = {"code": 410, "message": "用户验证失败"}
        return jsonify(resp)

    except:

        resp = {"code": 500, "message": "内部请求出错"}
        return jsonify(resp)

