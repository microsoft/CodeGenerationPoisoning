from flask import Flask, request, jsonify, render_template
from twilio.twiml.messaging_response import Message, MessagingResponse
from analysis import analysis as an
from analysis import message_generator as mes
from hashlib import md5
from analysis import heuristics as heuristics

app = Flask(__name__)

UJ_Dict = dict()
Report_Dict = dict()

analysis_dict = {
    "polarization": an.Analysis(heuristics.polarization_heuristic, "polarization"),
    "general_sentiment": an.Analysis(heuristics.general_sentiment_analysis, "general_sentiment"),
    "latest_sentiment": an.Analysis(heuristics.latest_sentiment_analysis, "latest_sentiment")
}

@app.route('/')
def landing():
    return render_template("landing.html")

UJ = an.UserJournal(phone_number="test000")
report = an.Report(user_journal=UJ)

report.add_analysis(analysis_dict["polarization"])
report.add_analysis(analysis_dict["general_sentiment"])
report.add_analysis(analysis_dict["latest_sentiment"])

UJ.add_submission(submission=an.Submission("It feels good today. Most of the activities done and the weather was good. I had enough sleep last night so woke up ready for all activities in the college. I was in the library quite early to finish up the many assignments given yesterday. The classes have been interesting with tutors covering much of the syllabus work and at the same time allowing us the time to relax. I caught up with old friends during the lunch hour and planned for a date over the weekend. We have known another for quite some time since our time in high school. They were always helpful in tough moments. The afternoon was interesting too, spending time in music class. I am making a nice progress in knowing to play the guitar. The day ends with catching up with my parents at home who have been on vacation for a week now."))
report.generate()

UJ.add_submission(submission=an.Submission("The day is so tiresome. Being a Monday, the tutors have many expectations from us. They pick up from previous classes and all the homework done over the weekend. By the time of class, I had not finished the psychology essay so I had to request for more time from the lecturer. Thank God he accepted my plea. Now I have the next 24 hours to finish this challenging essay. Besides, I went bicycle riding. It is always good to exercise often but today I did too much and I can feel the aching muscles. With more work from my tutor, I feel like someone should just offer a hand of assistance. But I will manage."))
report.generate()

UJ.add_submission(submission=an.Submission("Things are awful. Don't know if this app will ever work"))
report.generate()

UJ.add_submission(submission=an.Submission("It feels good today. Most of the activities done and the weather was good. I had enough sleep last night so woke up ready for all activities in the college. I was in the library quite early to finish up the many assignments given yesterday. The classes have been interesting with tutors covering much of the syllabus work and at the same time allowing us the time to relax. I caught up with old friends during the lunch hour and planned for a date over the weekend. We have known another for quite some time since our time in high school. They were always helpful in tough moments. The afternoon was interesting too, spending time in music class. I am making a nice progress in knowing to play the guitar. The day ends with catching up with my parents at home who have been on vacation for a week now."))
report.generate()

UJ.add_submission(submission=an.Submission("The day is so tiresome. Being a Monday, the tutors have many expectations from us. They pick up from previous classes and all the homework done over the weekend. By the time of class, I had not finished the psychology essay so I had to request for more time from the lecturer. Thank God he accepted my plea. Now I have the next 24 hours to finish this challenging essay. Besides, I went bicycle riding. It is always good to exercise often but today I did too much and I can feel the aching muscles. With more work from my tutor, I feel like someone should just offer a hand of assistance. But I will manage."))
report.generate()

UJ.add_submission(submission=an.Submission("Things are awful. Don't know if this app will ever work"))
report.generate()

Report_Dict['test-test'] = report
print(report.history)

@app.route('/ui/report/<string:report_id>')
def get_report_ui(report_id):
    report = Report_Dict.get(report_id, None)
    return render_template("mirrur.html", report=report)

@app.route('/report/<string:report_id>')
def fetch_report(report_id):
    report = Report_Dict.get(report_id, None)

    # Error check if report not found
    if (not report):
        return jsonify(
            success= False,
            # full_text=None,
            submissions=None,
            results=None,
            average_result=None
        )

    # return report
    return jsonify(
        success= True,
        # full_text=report.user_journal.full_text,
        submissions=list(map(lambda s: s.text, report.user_journal.submissions)),
        results=report.results,
        average_result=report.compressed_result
    )

@app.route('/sms', methods=['POST'])
def sms():
    number = request.form['From']
    message_body = request.form['Body']
    print(message_body)

    # generate submission
    sub = an.Submission(text=message_body)

    # check if phone_number is sending as first time
    first_time = number not in UJ_Dict.keys()
    if first_time:
        # create user journal for first timers
        UJ = an.UserJournal(phone_number=number)
        UJ.add_submission(submission=sub)
        UJ_Dict[number] = UJ # note don't add first text
        # message for first timers
        message = "Hey, from what I can tell, this is your first time using Mirrur. That's ok. \n Mirrur is a place for you to jot down any of your thoughts. Mirrur is here to listen. For now, let me know how your day went."
        # send message
        resp = MessagingResponse()
        resp.message(message)
        return str(resp)

    # clear if error
    if (message_body == "Clear" or message_body == "clear"):
        # new user journal
        UJ_Dict[number] = an.UserJournal(phone_number=number)

    # common case
    UJ = UJ_Dict[number]
    UJ.add_submission(submission=sub)
    # add analysis to use in report
    report = Report_Dict.get(md5(str(number).encode('utf-8')).hexdigest(), an.Report(user_journal=UJ))
    report.add_analysis(analysis_dict["polarization"])
    report.add_analysis(analysis_dict["general_sentiment"])
    report.add_analysis(analysis_dict["latest_sentiment"])
    # generate report
    report.generate()
    report.log()
    # save report with ts of last submission
    print(sub.timestamp)
    report_id = md5(str(number).encode('utf-8')).hexdigest()
    print("report_id: {}".format(report_id))
    print("avg: {}".format(report.compressed_result))
    Report_Dict[report_id] = report
    # generate message to send based on happiness probabiltiy (0-1)
    msg = mes.message_generator(report.compressed_result, report_id)
    # return the message
    resp = MessagingResponse()
    resp.message(msg)
    return str(resp)

if __name__ == '__main__':
    app.run()
