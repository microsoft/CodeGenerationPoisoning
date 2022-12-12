from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
bp = Blueprint('game', __name__)

from flask_adventure_game import errors

#Introduction
@bp.route('/index')
def index():
    return render_template('base.html')

#@bp.route('/help', methods=('GET', 'POST'))
    
def dir(valid_actions, action):
    
    # Allows help to be available whenever a player needs to know controls
    if action == 'help':
        #raise HelpError
        message = """
            ---------------------------------------
            The directions to move are as follows:
            w will move forward
            a will move left
            s will move back
            d will move right
            ---------------------------------------
            When presented with a choice to do something:
            yes or y will agree to something
            no or n will disagree to something
            ---------------------------------------
            Your current mp is {player_stats.player.stats['morality_points']})"""
        return message
    elif action in valid_actions:
        return action

    else:
        #raise ValueError
        message =  "Not a valid action right now. 'help' will list all possible actions"
        return message
        #flash("Not a valid action right now")

@bp.route('/Aghrial', methods=('GET', 'POST'))
# Beginning of game that a player will start at
def aghrial():
        current_scene = """
            Welcome to The Trials of Aghrial
            Years ago, Aghrial stopped a murder from happening
            Only days after the man that he saved killed hundreds
            After that tragic day Aghrial disappeared, leaving no trace of himself behind
        
            This game will allow you to choose between good and bad
            Sometimes chosing the wrong thing will lead to
            greater morality points (mp) and vice versa
            You may choose to achieve a score of 100 mp or -100 mp
            If you only choose choices of one side then the game will be imposiible to win
            ---------------------------------------
            The directions to move are as follows:
            w will move forward
            a will move left
            s will move back
            d will move right
            ---------------------------------------
            When presented with a choice to do something:
            yes or y will agree to something
            no or n will disagree to something
            ---------------------------------------
            Typing mp will give you your current score
        
            If at any point you are unsure of all available actions just type help

        
            There's a magical door right in front of you
            """
        if request.method=='POST':
            action = request.form['action']
            #try: 
            current_scene = dir(('w',), action)
                #variable for the tuple
            #except HelpError:
                #they type help
            #except ValueError:
                #they donti flsh this one

            if current_scene == 'w':
                return redirect(url_for('game.cabin'))
        return render_template('index.html', scene=current_scene)


@bp.route('/cabin', methods=('GET', 'POST'))
def cabin():
    current_scene = "The door you came out of slammed shut behind you and disappeared. You are standing in the entrance of a cabin, to your right there is a bathroom, behind you is a bedroom, in front of you is a door to leave the cabin"
    if request.method=='POST':
        action = request.form['action']
        current_scene = dir(('w', 'd', 's'), action)
        if action == 'w':
            return redirect(url_for('game.outside_cabin'))
        elif action == 'd':
            return redirect(url_for('game.bathroom'))
        elif action == 's':
            return redirect(url_for('game.bedroom'))
 
    return render_template('index.html', scene=current_scene)



@bp.route('/bedroom', methods=('GET', 'POST'))
def bedroom():
        current_scene= "The bedroom is messy, do you clean it for +5 mp?"
        if request.method=='POST':
            action = request.form['action']
            current_scene = dir(('yes', 'no'), action)
            if current_scene == 'yes':
                current_scene = "You cleaned the bedroom and got 5 mp"
                return render_template('index.html', scene=current_scene)
            elif current_scene == 'no':
                current_scene = "You didnt clean the bedroom"
                return render_template('index.html', scene=current_scene)
        return render_template('index.html', scene=current_scene)


@bp.route('/bathroom', methods=('GET', 'POST'))
def bathroom():
        current_scene = "There is a bottle of Xeron Elixir in the bathroom, the label is scraped off, you don't know what it'll do, do you steal it for -5 mp?"
        if request.method=='POST':
            action = request.form['action']
            current_scene = dir(('yes', 'no'), action)
            if current_scene == 'yes':
                current_scene = "After taking the elixir your whole body feels amazing"
                return render_template('index.html', scene=current_scene)
            elif current_scene == 'no':
                current_scene = "You refrained from stealing"
                return render_template('index.html', scene=current_scene)
        return render_template('index.html', scene=current_scene)

@bp.route('/outside-cabin', methods=('GET', 'POST'))
def outside_cabin():
    current_scene = "It's a beautiful sunny day outside, to your left is a river, to your right is the woods, straight ahead is a village This is it of game developed so far"
    if request.method=='POST':
        action = request.form['action']
    return render_template('index.html', scene=current_scene)
