from flask import Flask, render_template, Response
from zang.inboundxml import Response, Say
from zang.inboundxml import Voice, Language
from flask_restful import Resource, Api


class ivrSample(Resource):
    def get(self):
        say = Say("Welcome to Zang!",
                  language=Language.EN,
                  voice=Voice.FEMALE,
                  loop=3)
        response = Response()
        response.addElement(say)
        return app.response_class(response.xml, mimetype='application/xml')

app = Flask(__name__)
api = Api(app, default_mediatype='application/xml')
api.add_resource(ivrSample, '/ivr-sample')


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__': app.run(debug=True)
