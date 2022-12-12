from flask import Flask,request,render_template,jsonify

# import auto_complete.py file as ac
import auto_complete as ac  

app = Flask(__name__)

@app.route("/")
def home():

    # render home page 
    return render_template("home.html")


@app.route("/autoComplete",methods=["POST"])
def autoCompleteRequest():

    # extract form information
    query = request.form['query']  
    prefix = request.form['prefix']
    max_count = request.form['max_count']

    # call autocomplete method of auto_complete.py file
    result = ac.autoComplete(query,prefix,max_count)

    #return result as comma separated string
    if(type(result)==list):
        return ", ".join(result)
    else:
        return result


if __name__ == "__main__":
    app.run('127.0.0.1',5000) # run server on localhost and port 5000