############################################
# Imports for logic and basic table displays
############################################
import datetime as dt
import os
from itertools import combinations

import pandas as pd
from flask import Flask
from flask import flash
from flask import render_template
from flask import request, session, redirect, url_for
from flask_login import LoginManager
#########################
from flask_login import login_required, current_user
#########################
from flask_wtf import Form, FlaskForm
from wtforms import BooleanField, SubmitField, TextField, SelectField

from poker_classes.cards import Cards
from poker_classes.dealer import Dealer
from poker_classes.game import Game
from poker_classes.player import Player


#######Additional imports from clyde
# from flask_socketio import SocketIO, emit


class MasterControlForm(FlaskForm):
    reset_table = BooleanField(label="Reset Table now?", default=False)
    new_deal = BooleanField(label="New deal now?", default=False)
    first_bet = BooleanField(label="First Bet now?", default=False)
    second_bet = BooleanField(label="Second Bet now?", default=False)
    third_bet = BooleanField(label="Third Bet now?", default=False)
    fourth_bet = BooleanField(label="Fourth Bet now?", default=False)
    fifth_bet = BooleanField(label="Last Bet now?", default=False)
    first_flip = BooleanField(label="First Flip now?", default=False)
    second_flip = BooleanField(label="Second Flip now?", default=False)
    third_flip = BooleanField(label="Third Flip now?", default=False)
    declare = BooleanField(label="Declare now?", default=False)
    evaluate_now = BooleanField(label="Evaluate winners now?", default=False)

    submit = SubmitField("Submit")


class FullTableForm(FlaskForm):
    hand1_kf = SelectField(label="Hand 1", default='keep')
    hand2_kf = SelectField(label="Hand 2", default='keep')
    bet_action = TextField()


#########################

working_dir = os.getcwd()
app_dir = working_dir + '/poker_classes/'
player_dir = working_dir + '/existing_players/'

cards = Cards()
this_game = Game()
this_game.set_pic_a_wheel()

dealer = Dealer()

login_manager = LoginManager()  # Sets up player views

############################################
# Player Initialization
############################################
alba = Player(player_dir, name='John Alba', nickname='JohnAlba')
bornstein = Player(player_dir, name='Bill Murphy', nickname='Bornstein')
clyde = Player(player_dir, name='Bob Vincent', nickname='Clyde')
brian = Player(player_dir, name='Brian Mercer', nickname='Mercer')
ed = Player(player_dir, name='Ed Mulhern', nickname='Ed')

players = [alba, bornstein, clyde, brian, ed]
for i, p in enumerate(players):
    p.add_funds(500)  # add funds
    p.player_position = i  # set table position

print('Funds added')
player_dict = {}

# Initial Deal, display cards on console
shuffled = dealer.deal_cards(players, this_game)
for i, p in enumerate(players):
    print(p.p_nickname, p.hands[0], p.common_cards, p.hands[1])
    player_dict = dealer.add_to_display_dict(player_dict, i, p, cards)

#########################
app = Flask(__name__)

# App config from Clyde
app.config["SECRET_KEY"] = "yousecntuch"
app.debug = True
# socketio = SocketIO(app)
login_manager = login_manager.init_app(app)


@app.route('/')
def index():
    return '<h1>Home page for third_deal.py</h1>'


@app.route('/login', methods=['GET', 'POST'])
def login():
    print(request.method)
    if request.method == 'POST':
        session['username'] = request.form['username']
        print(session['username'])
        valid_ids = [p.p_nickname for p in players]

        if session['username'] in valid_ids:
            return redirect(url_for("full_table"))
        else:
            return f"Invalid Login.  I don't know you.  I don't want to know you.  Go away."
    return '''
        <form method="post">
            <p><input type=text name=username>
            <p><input type=submit value=Login>
        </form>
    '''


@app.route('/base_table_w_player')
def raw_table():
    '''Render this page for testing.  Assumes viewer not logged in as player.'''
    print('current_user', current_user.is_authenticated)

    display_dict = {}
    for i, p in enumerate(players):
        display_dict = dealer.add_to_display_dict(display_dict, i, p, cards)
        print(p.p_nickname, p.hands)

    for p in players:
        if session['username'] == p.p_nickname:
            this_player = p
    try:
        for i, h in this_player.hands:
            tmp_hand = []
            tmp_hand.append([cards.get_simple_u_card_h(h[0]), cards.get_simple_u_card_h(h[1])])
            this_player['hands'][i] = tmp_hand
        this_player.common_cards = [cards.get_simple_u_card_h(this_player.common_cards[0][0]),
                                    cards.get_simple_u_card_h(this_player.common_cards[0][1])]
        print('Passed card string to hex')

    except:
        print('Failed card string to hex')
        pass

    common_dict = dealer.make_common_display_dict(dealer.common_cards, cards)

    return render_template('base_table_w_player.html', players=display_dict,
                           common=common_dict, this_player=this_player)


@app.route('/full_table', methods=['GET', 'POST'])
def full_table():
    global players, this_game

    form = FullTableForm()

    print('dealer.perform_reset', dealer.perform_reset)
    if form.validate_on_submit:
        new_players = []
        if (dealer.perform_reset) and (session['username'] == dealer.active_player):
            for p in players:
                new_players.append(p.reset_player_from_master_control())
            players = new_players
            dealer.reset_table(players, this_game)

            hand1_kf = 'keep'
            hand2_kf = 'keep'
            bet_action = 'Check'
            form.hand1_kf = 'keep'
            form.hand2_kf = 'keep'
            form.bet_action = 'Check'
            dealer.perform_reset = False
            print('Redirecting to full_table')
            return redirect(url_for("full_table"))

        players_l = [p.p_nickname for p in players]
        for p in players:
            # print('AA',p.p_nickname,p.hands)
            if p.p_nickname == 'JohnAlba':
                alba = p

        if session['username'] == dealer.active_player:
            print('Found Active Player:  Player Player PlayerPlayer Player Player Player')

            hand1_kf = request.form.get('hand1_kf')
            hand2_kf = request.form.get('hand2_kf')
            bet_action = request.form.get('bet_actions')

            print(f'Active Player Form Responses h1: {hand1_kf} h2: {hand2_kf} bet: {bet_action}')
            print(f"C {dealer.common_cards_flipped}")
            # return(str(hand1_kf))
            if hand1_kf == 'fold':
                for p in players:
                    if session['username'] == p.p_nickname:
                        p.hands[0] = 'folded'
                        p.hands_pr[0] = 'folded'
                        for i in range(10):
                            print(p.p_nickname, p.hands, p.hands)

                    if p.p_nickname == 'JohnAlba':
                        alba = p

            if hand2_kf == 'fold':
                for p in players:
                    if session['username'] == p.p_nickname:
                        p.hands[1] = 'folded'
                        p.hands_pr[1] = 'folded'

                        if (p.hands[0] == 'folded') & (p.hands[1] == 'folded'):
                            p.common_cards = ['folded']

            this_player = dealer.make_player_cards_no_options(players, session['username'], cards)

            # convert for display#
            # new_hands=[]
            # for h in this_player.hands:
            #            new_hands.append(dealer.convert_value_hand_to_display(h))
            #        this_player.hands_pr=new_hands
            #
            #            if this_player.common_cards_pr==[]:
            #                    pass

            #            elif set([str(x) for x in this_player.hands])=={'folded'}:
            #                print('All folded')
            #                this_player.common_cards_pr==[]

            #            else:
            #                    this_player.common_cards_pr=[(dealer.convert_value_card_to_display(this_player.common_cards[0]))]
            #            print('this_player.common_cards_pr',this_player.common_cards_pr)

            #            new_common=[]

            #            for f in dealer.common_cards:
            #                    tmp_h=dealer.convert_value_hand_to_display(f)
            #                    new_common.append(tmp_h)

            #            dealer.common_cards_pr=new_common
            this_player = dealer.make_your_hand_display_cards(this_player)

            # Check to see if player folded.

            if this_player:
                return render_template('table_view_active.html', dealer=dealer,
                                       players=players, this_player=this_player, alba=alba,
                                       form=form)
            else:
                return f"{session['username']} is not welcome at this table, so get lost!"
        else:
            this_player = dealer.make_player_cards_no_options(players, session['username'], cards)
            print(this_player.p_nickname, this_player.hands_pr, this_player.common_cards, this_player.common_cards_pr)
            if this_player:
                this_player = dealer.make_your_hand_display_cards(this_player)
                return render_template('table_view_inactive.html', dealer=dealer,
                                       players=players, this_player=this_player)
            else:
                return f"{session['username']} is not welcome at this table, so get lost!"


@app.route('/new_deal')
def new_deal():
    display_dict = {}
    shuffled = dealer.deal_cards(players, this_game)

    for i, p in enumerate(players):
        display_dict = dealer.add_to_display_dict(display_dict, i, p, cards)

    high_hand_df, low_hand_df = dealer.evaluate_all_hands(players)
    print('Best High Hands:\n', high_hand_df.head(3))
    print('Best Low Hands:\n', low_hand_df.head(3))

    common_dict = dealer.make_common_display_dict(dealer.common_cards, cards)
    print('Common_Dict: ', common_dict)

    return render_template('base_table.html', players=display_dict,
                           common=common_dict)


@app.route('/master_control', methods=['GET', 'POST'])
def master_control():
    form = MasterControlForm()

    if form.validate_on_submit:
        reset_table = form.reset_table.data
        new_deal = form.new_deal.data
        first_bet = form.first_bet.data
        second_bet = form.second_bet.data
        third_bet = form.third_bet.data
        fourth_bet = form.fourth_bet.data
        fifth_bet = form.fifth_bet.data
        flip1 = form.first_flip.data
        flip2 = form.second_flip.data
        flip3 = form.third_flip.data
        declare = form.declare.data
        evaluate_now = form.evaluate_now.data
        submit_value = form.submit.data
        print('Reset Table:', reset_table)
        print('New Deal:', new_deal)
        print("first_bet", first_bet)
        print("second_bet", second_bet)
        print("third_bet", third_bet)
        print("fourth_bet", fourth_bet)
        print("fifth_bet", fifth_bet)
        print("first_flip", flip1)
        print("second_flip", flip2)
        print("third_flip", flip3)
        print("declare", declare)
        print("submit", submit_value)
        dealer.common_cards_flipped = [flip1, flip2, flip3]
        # print(f"1 common_cards_flipped {dealer.common_cards_flipped}")

    if (session['username'] == 'Bornstein') or (session['username'] == 'Clyde'):
        name = session['username']
        # print(f"Found Right Guys, common_cards_flipped {dealer.common_cards_flipped}")

        if reset_table:
            print('resetting')
            new_players = []
            dealer.reset_table(players, this_game)
            dealer.perform_reset = True

            for i, p in enumerate(players):
                players[i] = p.reset_player_from_master_control()
                print((p.p_nickname, p.hands, p.common_cards))

            for p in players:
                if p.p_nickname == 'Bornstein':
                    print(p.p_nickname, p.hands, p.common_cards)
            # print(f"2 common_cards_flipped {dealer.common_cards_flipped}")
            return redirect(url_for('master_control'))

        if new_deal and ~dealer.deal_complete:
            dealer.reset_table(players, this_game)
            shuffled = dealer.deal_cards(players, this_game)
            dealer.deal_complete = True
            dealer.first_deal = False
            form.new_deal.data = False

            # print(f"3 common_cards_flipped {dealer.common_cards_flipped}")
            return render_template('master_control.html', form=form, name=name)

        # print(f"4 common_cards_flipped {dealer.common_cards_flipped}")
        return render_template('master_control.html', form=form, name=name)

    else:
        return f"You are not Bornstein or Clyde, Fuck Off!"


@app.route('/da_var')
def some_func():
    my_var = {'name': 'Barry Bornstein',
              'favorite_bet': '20 cents'}
    return render_template('test_var.html', my_variable=my_var)


if __name__ == '__main__':
    app.run(debug=True)
