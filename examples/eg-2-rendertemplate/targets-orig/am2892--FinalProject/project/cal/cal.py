import calendar
 
import flask
from flask import render_template, url_for, redirect
from flask import render_template, Blueprint
from flask_login import login_required, current_user
import datetime
from datetime import date
from ..models import User
from ..models import Event
#from ..main.main import returnEvents
from ..app import db

calendar_bp = flask.Blueprint('cal', __name__, template_folder='templates')

@calendar_bp.route('/<int:year>/<int:month>')
@login_required
def random_cal(year, month, ev = {}):
    import holidays
    from ..main.main import returnEvents
    tc = calendar.HTMLCalendar(firstweekday=6)
    tc.cssclasses = ["mon", "tue", "wed", "thu", "fri", "sat", "sun bg-primary"]
    tc.cssclass_month = "table"
    ### inserts holidays over entire calendar
    ev.clear()
    for date, name in holidays.US(years=year).items():
        if month == date.month:
            ev[date.day] = [name.upper() + "</br>"]
    userEvents = Event.query.order_by(Event.starttime).all()
    for item in userEvents:
        if item.userName == current_user.name and year == item.starttime.year and month == item.starttime.month:
            if item.starttime.day in ev:
                ev[item.starttime.day].append(item.eventtitle +"-" + str(item.starttime.strftime( "%I:%M %p" ))+ "&nbsp;&nbsp;&nbsp;&nbsp; </br>")
            else:
                ev[item.starttime.day] = [item.eventtitle +"-" + str(item.starttime.strftime( "%I:%M %p" )) + "&nbsp;&nbsp;&nbsp;&nbsp; </br>"]
    print(ev)
    indexCal(year, month)
    itemsToReturn = returnEvents()
    print("items to return")
    print(itemsToReturn)
    return render_template("calendar.html", calendar=custformat(tc, year, month, ev), name=current_user.name, logCount=itemsToReturn)

index = {} ##this is used for properly indexing year and month buttons
def indexCal(yearInput, monthInput):
    print ("index before change")
    print (index)
    index["month"] = monthInput
    index["year"] = yearInput
    print (index)
    return index

@calendar_bp.route('/monthUP', methods=["GET", "POST"])
@login_required
def monthUP():
    year = index["year"]
    month = index["month"]
    month += 1
    if month > 12:
        month = 1
        year += 1
    return redirect(url_for('cal.random_cal', year=year, month=month))

@calendar_bp.route('/monthDOWN', methods=["GET", "POST"])
@login_required
def monthDOWN():
    year = index["year"]
    month = index["month"]
    month -= 1
    if month < 1:
        month = 12
        year -= 1
    return redirect(url_for('cal.random_cal', year=year, month=month))

@calendar_bp.route('/yearUP', methods=["GET", "POST"])
@login_required
def yearUP():
    year = index["year"]
    month = index["month"]
    year += 1
    return redirect(url_for('cal.random_cal', year=year, month=month))

@calendar_bp.route('/yearDOWN', methods=["GET", "POST"])
@login_required
def yearDOWN():
    year = index["year"]
    month = index["month"]
    year -= 1
    return redirect(url_for('cal.random_cal', year=year, month=month))

@calendar_bp.route('/delete_component/<eventHistory_id>')
@login_required
def deleteEvents(eventHistory_id):
    eventHistory = Event.query.filter_by(id=eventHistory_id).first_or_404()
    db.session.delete(eventHistory)
    db.session.commit()
    return redirect(url_for('cal.random_cal', year=index["year"], month=index["month"]))

#def monthUP():
#    thismonth = random_cal.month
#    print(thismonth)
#    return(thismonth)

#def cal_with_events():
#    tc = calendar.HTMLCalendar(firstweekday=0)
#    tc.cssclasses = ["mon bg-primary", "tue", "wed", "thu", "fri", "sat", "sun"]

#@calendar_bp.route('/<int:year>/<int:month>')
#@login_required
#def monthUP(indexmonth, indexyear):
#    random_cal.month += 1
#    random_cal.year += 0
#    indexmonth = random_cal.month
#    indexyear = random_cal_year

#    if random_cal.month > 12:
#        random_cal.month = 1
#        random_cal.year += 1
#        indexmonth = random_cal.month
#        indexyear = random_cal.year
#    return redirect(url_for('random_cal', year=indexyear, month=indexmonth))

#def monthDOWN(int yearInput,int monthInput):
#    monthInput -=1
#    if monthIput < 1:
#        monthInput = 12
#        yearInput -= 1
#    return yearInput, monthInput


def custformat(c, theyear, themonth, ev, withyear=True):
    """
    Return a formatted month as a table.
    """
    v = []
    a = v.append
    a('<table border="0" cellpadding="0" cellspacing="0" class="%s">' % (
        c.cssclass_month))
    a('\n')
    a(c.formatmonthname(theyear, themonth, withyear=withyear))
    a('\n')
    a(c.formatweekheader())
    a('\n')
    for week in c.monthdays2calendar(theyear, themonth):
        a(custformatweek(c, week, ev))
        a('\n')
    a('</table>')
    a('\n')
    return ''.join(v)


def custformatweek(c, theweek, ev):
    """
    Return a complete week as a table row.
    """
    s = ''.join(custformatday(c, d, wd, ev) for (d, wd) in theweek)
    return '<tr>%s</tr>' % s


def custformatday(c, day, weekday, ev):
    """
    Return a day as a table cell.
    """
    now = datetime.datetime.now()
    if day == 0:
        # day outside month
        return '<td class="%s">&nbsp;</td>' % "noday"
    else:
        return '<td class="%s">%s</td>' % (c.cssclasses[weekday], str(day) + get_event(day, ev))

# TODO do something better than this
def get_event(day, ev):
    if day in ev:
        str = "<div class='bg-warning'>"
        for event in ev[day]:
            str += event
        str += "</div>"
        return str
#    return "<div class='bg-danger'>I'm an event</div>"
    return "<div class='bg-warning'></div>"

   # don't forget you have access to year and month
   # return "<div class='bg-danger'>I'm an event</div>"
   # now = datetime.datetime.now()
   # if day == now.day:
   #     return "<div class='bg-danger'>TODAY</div>"
   # else:
   #     return "<div class='bg-danger'>I'm an event</div>"
