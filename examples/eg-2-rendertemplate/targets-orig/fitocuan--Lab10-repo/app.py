from flask import Flask, request, render_template
import os
import pickle

print(os.getcwd())
path = os.getcwd()

with open('Models/svm_heart.pkl', 'rb') as f:
    svm_model = pickle.load(f)




def get_predictions(age,sex,cp,trestbps,chol,fbs,restecg,thalach,exang,oldpeak,slope,ca, thal, req_model):
    mylist = [age,sex,cp,trestbps,chol,fbs,restecg,thalach,exang,oldpeak,slope,ca, thal]
    mylist = [float(i) for i in mylist]
    vals = [mylist]

    if req_model == 'SVM':
        #print(req_model)
        return svm_model.predict(vals)[0]
    else:
        return "Cannot Predict"


app = Flask(__name__)

@app.route('/')
def my_form():
    return render_template('home.html')

@app.route('/', methods=['POST', 'GET'])
def my_form_post():
    age = request.form['age']
    sex = request.form['sex']
    cp = request.form['cp']
    trestbps = request.form['trestbps']
    chol = request.form['chol']
    fbs = request.form['fbs']
    restecg = request.form['restecg']
    thalach = request.form['thalach']
    exang = request.form['exang']
    oldpeak = request.form['oldpeak']
    slope = request.form['slope']
    ca = request.form['ca']
    thal = request.form['thal']
    req_model = request.form['req_model']


    target = get_predictions(age,sex,cp,trestbps,chol,fbs,restecg,thalach,exang,oldpeak,slope,ca, thal, req_model)

    return render_template('home.html', target = target)


if __name__ == "__main__":
    app.run(debug=True)