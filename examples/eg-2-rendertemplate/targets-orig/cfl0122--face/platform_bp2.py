# -*- coding: utf-8 -*-
from flask import request,render_template,jsonify,make_response,Blueprint
from database import db
from table import User2,UserPicture2
from config import uploaddir,resultdir,tempdir,threshold,model
import os,json,base64,argparse
import pickle as pk
from face_utils import *



platform2 = Blueprint('flatform2', __name__)
@platform2.route('/make', methods=['GET', 'POST'])
def test3():
    imgnames = []
    if request.method == 'POST':
        imgnames = request.form.get('imgnames')
        if imgnames:
            imgnames=imgnames.split(',')

    return render_template('make.html',imgnames=imgnames)




@platform2.route('/up_photo3/', methods=['POST'], strict_slashes=False)
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
        user = User2.query.filter_by(filename=name).first()
        if user is not None:
            continue
        imgnames.append(name)
        fi = i.get('base64')
        b64img = fi.split(',')[-1]
        imgdata = base64.b64decode(b64img)
        file = open(uploaddir + name, 'wb')
        file.write(imgdata)
        file.close()
        r = gen_feature_multi(uploaddir + name, model)
        if r is not None:

            multi_f, bboxs = r
            for i in range(len(multi_f)):

                x1,y1,x2,y2=bboxs[i]

                userpic=UserPicture2(pic_data=b64img)

                user=User2(personid=name+str(i), filename=name, feature=pk.dumps(multi_f[i]), x1=x1, y1=y1, x2=x2, y2=y2)
                user.userPicture=userpic

                db.session.add(user)



    db.session.commit()
    return jsonify(imgnames)



@platform2.route('/up_photo4/', methods=['POST'], strict_slashes=False)
def api_recognition_single():

    users=User2.query.all()

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
        r = gen_feature(imgfile, model)

        if r is not None:
            f1,bbox = r
            fs=[]
            for user in users:
                f2=pk.loads(user.feature)
                dist = np.sum(np.square(f1-f2))
                sim = np.dot(f1, f2.T)
                if sim > threshold :
                    fs.append((user.personid,sim))

            dddddd.append((name,fs,bbox))

    return str(dddddd)


@platform2.route('/up_find_person/', methods=['POST'], strict_slashes=False)
def up_find_person():

    users=User2.query.all()

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
        r = gen_feature(imgfile, model)



        if r is not None:
            f1,bbox = r

            for user in users:
                f2=pk.loads(user.feature)
                dist = np.sum(np.square(f1-f2))
                sim = np.dot(f1, f2.T)
                if sim > threshold :

                    # img=cv2.imread(uploaddir + user.filename)
                    if os.path.exists(uploaddir + user.filename):
                        img = cv2.imdecode(np.fromfile(uploaddir + user.filename,dtype=np.uint8),cv2.IMREAD_COLOR)
                        cv2.rectangle(img,(user.x1,user.y1),(user.x2,user.y2),(0,255,0))
                        cv2.putText(img,str(sim),(user.x1-10,user.y1-10),cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,0),2)
                        # cv2.imwrite(resultdir + user.filename,img)
                        cv2.imencode('.jpg', img)[1].tofile(resultdir + user.filename)
                        fs.append(user.filename)

            # dddddd.append((name,fs,bbox))

    return jsonify(fs)




@platform2.route('/up_multiface/', methods=['POST'], strict_slashes=False)
def api_recognition_multi_face():

    users=User2.query.all()

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
        r = gen_feature_multi(imgfile, model)

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


@platform2.route('/delete/', methods=['POST'], strict_slashes=False)
def delete():
    users = User2.query.all()
    [db.session.delete(u) for u in users]
    db.session.commit()
    return "deleted"


@platform2.route('/show/<string:filename>', methods=['GET'])
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

