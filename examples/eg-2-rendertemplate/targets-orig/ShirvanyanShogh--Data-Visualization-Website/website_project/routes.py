from flask import render_template, request, flash, redirect, \
    url_for, session, abort
from website_project import app
from website_project.models.dashboard_model import Dashboard
from website_project.forms.forms import LoginForm
from website_project.models.user_model import User
from website_project.models.download_model import Download


@app.route('/')
def dashboard():
    if "email" in session:
        charging_station_names = User.get_access(session.get('email'))
        company_name = User.get_company_name(session.get('email'))
        months = ['January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November',
                  'December']
        years = [2018, 2019, 2020]

        month = request.args.get('month')
        name = request.args.get('station_name')
        year = request.args.get('year')
        price = request.args.get('price')
        if year is not None:
            year = int(year)
        if (name is None or name in charging_station_names) \
                and (month is None or month in months) \
                and (year is None or year in years) and \
                (price is None or price.isdecimal() or
                 price.replace('.', "", 1).isdecimal()):
            if name == "All Stations":
                dashboard_obj = Dashboard(month, year, price,
                                          *charging_station_names[:-1])
            else:
                dashboard_obj = Dashboard(month, year, price, name)

            energy_sum, energy_avg, session_count, duration_avg, cost_total \
                = dashboard_obj.numeric_data()
            energy_sum_per, energy_avg_per, session_per, duration_per, cost_per\
                = dashboard_obj.percentage_cal(energy_sum, energy_avg,
                                               session_count, duration_avg,
                                               cost_total)
            energy_per_key, energy_per_user, energy_per_connector \
                = dashboard_obj.pie_chart()
            energy_per_day = dashboard_obj.energy_per_day()
            energy_usage = dashboard_obj.energy_usage()

            download = request.args.get('download')
            # if download == "download":
            #     # try:
            #     url_name = f"https://www.evcharge.ie/?station_name={name}" \
            #                f"&month={month}&year={year}&price={price}"
            #     download_obj = Download(url_name, session['email'],
            #                             session['password'])
            #     download_obj.download_as_pdf()
            #     # except:
            #     #     pass

            return render_template("index.html", names=charging_station_names,
                                   months=months, years=years,
                                   company_name=company_name,
                                   energy_total=energy_sum,
                                   session_number=session_count,
                                   duration_avg=duration_avg,
                                   energy_avg=energy_avg, cost_total=cost_total,
                                   energy_per_key=energy_per_key,
                                   energy_per_day=energy_per_day,
                                   energy_per_user=energy_per_user,
                                   energy_per_connector=energy_per_connector,
                                   energy_usage=energy_usage,
                                   energy_sum_per=energy_sum_per,
                                   energy_avg_per=energy_avg_per,
                                   session_per=session_per,
                                   duration_per=duration_per, cost_per=cost_per,
                                   name_chosen=name, month_chosen=month,
                                   year_chosen=year, price_chosen=price)
        else:
            abort(404)
    else:
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if "email" in session:
        return redirect((url_for('dashboard')))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.check_user_password(email, password)
        if user:
            session['email'] = email
            session['password'] = password
            session.permanent = form.remember.data
            # flash("You have been logged in!", 'success')
            return redirect(url_for('dashboard'))
        else:
            flash("Login Unsuccessful. Please check email and password",
                  'danger')
    return render_template('login.html', title="Login", form=form)


@app.route('/logout')
def logout():
    session.pop('email', None)
    session.pop('password', None)
    return redirect(url_for('dashboard'))
