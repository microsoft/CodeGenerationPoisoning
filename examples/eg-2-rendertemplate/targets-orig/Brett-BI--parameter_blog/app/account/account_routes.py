from flask import request, redirect, url_for, render_template, flash, session
from flask_login import current_user, logout_user, login_user, login_required, fresh_login_required
from datetime import timedelta
from urllib.parse import urlparse, urljoin

from app import models
from . import account_bp, account_forms


def is_safe_url(target_url):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target_url))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


@account_bp.route("/signup", methods=["GET", "POST"])
def signup():
    form = account_forms.SignupForm()

    if request.method == "POST":
        # proper try/except here.
        models.User.create_new_user(form.email.data, form.password.data)

        return redirect(url_for("reader_bp.reader_home"))

    return render_template("account/signup.html", form=form, current_user=current_user.__repr__())


@account_bp.route("/login", methods=["GET", "POST"])
def login():
    # immediately bypass this logic if the user is authenticated
    if current_user.is_authenticated:
            return redirect(url_for("creator_bp.home"))

    form = account_forms.LoginForm()

    if form.validate_on_submit():
        print('validated form')
        user = models.User.get_user_by_email(form.email.data)

        if user and user.verify_password(user.id, form.password.data) == True:
            login_user(user, remember=False)

            next_url = request.args.get('next')
            if next_url and is_safe_url(next_url):
                return redirect(next_url)
            else:
                return redirect(url_for('creator_bp.home'))

            # if "next" in session:
            #     next_url = session["next"]
            #     session.pop("next")
            #     session.modified = True
            #     print("next in session")
            #     print(session)
            #     if is_safe_url(next_url):
            #         print("url is safe")
            #         print(next_url)
            #         return redirect(next_url)
            #     else:
            #         print("url is not safe")
            #         return redirect(url_for("creator_bp.home"))
            # else:
            #     print("next is not in session")
            #     return redirect(url_for("creator_bp.home"))
        else:
            flash("Please enter a valid user name and password.")

    return render_template("account/login.html", form=form, current_user=current_user.__repr__())


@account_bp.route("/logout")
@login_required
def logout():
    logout_user()

    return redirect(url_for("reader_bp.reader_home"))


@account_bp.route("/me/manage", methods=["GET", "POST"])
@login_required
def manage_account():
    user_data = {"about": current_user.about, "website": current_user.personal_website, "name": current_user.name}
    form = account_forms.UserManagementForm(data=user_data)

    if request.method == "POST":
        updated_user = {"id": current_user.id, "about": form.about.data, "name": form.name.data,
                        "personal_website": form.website.data}

        models.User.update_user(updated_user)

        return redirect(url_for("creator_bp.home"))

    return render_template("account/manage.html", form=form, current_user=current_user.__repr__())


@account_bp.route("/me/password", methods=["GET", "POST"])
@fresh_login_required
def change_password():
    form = account_forms.ChangePasswordForm()

    if form.validate_on_submit():
        updated_password = models.User.update_password(user_id=current_user.id, old_password=form.old_password.data,
                                    new_password=form.new_password.data)
        if updated_password == True:
            logout_user()

            return redirect(url_for("account_bp.login"))
        else:
            flash('Could not update password.', 'error')
            return render_template("account/change_password.html", form=form)

    return render_template("account/change_password.html", form=form)
