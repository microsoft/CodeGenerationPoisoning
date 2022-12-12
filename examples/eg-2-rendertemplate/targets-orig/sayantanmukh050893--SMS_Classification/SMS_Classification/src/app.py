from flask import Flask,request,jsonify,render_template
import pickle
from util import Util
util = Util()
import pandas as pd
from sklearn.feature_extraction.text import TfidfTransformer,CountVectorizer

output_model_path = "E://Study//GitLab//SMS_Classification//src//model.pkl"
testing_data_path = "E://Study//GitLab//SMS_Classification//data//testing_data.csv"
text_vectorizer_path = "E://Study//GitLab//SMS_Classification//src//text_vectorizer_path.pkl"

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/predict-spam-ham-api',methods=["POST"])
def predict_api():
    data = request.get_json()
    df = pd.DataFrame.from_dict(data,orient="index").T
    model = pickle.load(open(output_model_path,"rb"))
    X = df["message"]
    X = X.apply(util.clean_message)
    X = X.str.lower()
    text_vectorizer = pickle.load(open(text_vectorizer_path,'rb'))
    transformer = TfidfTransformer()
    loaded_vec = CountVectorizer(decode_error='replace',vocabulary=text_vectorizer)
    tfidf = transformer.fit_transform(loaded_vec.fit_transform(X))
    y_pred = model.predict(tfidf)
    result = None
    if(y_pred[0]==0):
        result = "This is a normal message"
    elif(y_pred[0]==1):
        result = "This is a spam message"
    return jsonify(result)

@app.route('/predict-spam-ham-frontend',methods=["POST"])
def predict_front_end():
    data = request.form.to_dict()
    df = pd.DataFrame.from_dict(data,orient="index").T
    model = pickle.load(open(output_model_path,"rb"))
    X = df["message"]
    X = X.apply(util.clean_message)
    X = X.str.lower()
    text_vectorizer = pickle.load(open(text_vectorizer_path,'rb'))
    transformer = TfidfTransformer()
    loaded_vec = CountVectorizer(decode_error='replace',vocabulary=text_vectorizer)
    tfidf = transformer.fit_transform(loaded_vec.fit_transform(X))
    y_pred = model.predict(tfidf)
    result = None
    if(y_pred[0]==0):
        result = "This is a normal message"
        #result = "E://Study//GitLab//SMS_Classification//src//templates//normal.jpg"
    elif(y_pred[0]==1):
        result = "This is a spam message"
        #result = "E://Study//GitLab//SMS_Classification//src//templates//spam.jpg"
    return render_template("result.html",prediction_text=result)

if __name__ == "__main__":
    app.run(debug=True)
