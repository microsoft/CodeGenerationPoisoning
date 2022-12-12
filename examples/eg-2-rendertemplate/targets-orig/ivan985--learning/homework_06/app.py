from flask import Flask, render_template
from flask_login.login_manager import LoginManager

from homework_06.models import Session, User
from homework_06.views import auth_app, cont_app

# Запуск сайта на flask
# Перед запуском необходимо создать и заполнить базу данных произведений

app = Flask(__name__)
# задание секретного ключа и режима дебага
app.config.update(
    DEBUG=True,
    SECRET_KEY="asfbrifuqhrfiqbrfqrfbub49242948briubfrjf",
)
# создание блюпринтов для разделов
app.register_blueprint(auth_app, url_prefix="/auth")
app.register_blueprint(cont_app, url_prefix="/contacts")

# подключение функции для проверки логина пользователя
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return Session.query(User).filter_by(id=user_id).one_or_none()


# главная страница
@app.route("/", endpoint="index")
def index():
    return render_template("index.html")


# для автоматическоего закрытия сессий
@app.teardown_request
def remove_session(*args):
    Session.remove()


# запуск приложения
if __name__ == "__main__":
    app.run(debug=True)
