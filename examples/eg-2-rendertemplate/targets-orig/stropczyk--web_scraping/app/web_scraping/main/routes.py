from flask import render_template, request, Blueprint
from .searching import komputronik

main = Blueprint('main', __name__)


@main.route("/")
@main.route("/home", methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        user_input = request.form['product']
        phrase = user_input.split(' ')

        # morele_products = morele_net(phrase)
        # morele_sorted = sorted(morele_products, key=lambda i: i['item_price'])
        # morele_item = morele_sorted[0]

        # xkom_products = x_kom(phrase)
        # xkom_sorted = sorted(xkom_products, key=lambda i: i['item_price'])
        # xkom_item = xkom_sorted[0]

        komputronik_products = komputronik(phrase)

        all_products = komputronik_products

        if all_products is None:
            return render_template('no-product.html', title='No such product')

        all_sorted = sorted(all_products, key=lambda i: i['item_price'])

        item_1 = all_sorted[0]
        item_2 = all_sorted[1]
        item_3 = all_sorted[2]

        return render_template('results.html', title='Results', item3=item_3,
                               item2=item_2, item1=item_1)

    return render_template('home.html', title='Home')


@main.route("/about")
def about():
    return render_template('about.html', title='About')


@main.route("/contact")
def contact():
    return render_template('contact.html', title='About')


@main.route("/results")
def results():
    return render_template('results.html', title='Results')