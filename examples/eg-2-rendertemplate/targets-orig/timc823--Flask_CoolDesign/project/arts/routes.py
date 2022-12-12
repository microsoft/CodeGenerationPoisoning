from flask import render_template ,request, Blueprint
from project.arts import ascii_art

arts = Blueprint('arts', __name__)

# First Section
@arts.route('/printRect', methods=['GET','POST'])
def printRect():
    user = {'message': 'welcome to ASCII arts page!'}
    if request.method =='POST':
        width = request.form['width']
        height = request.form['height']
        symbol = request.form['symbol']
        output = ascii_art.printRect(width,height,symbol)
        # print(output)
        return render_template('ASCII_Results.html', title='ASCII Result', output=output)
    return render_template('ASCII_Art.html', title='ASCII arts', user=user)

# Section Section
@arts.route('/printTriangle', methods=['POST'])
def printTriangle():

    if request.method =='POST':
        width = request.form['width']
        symbol = request.form['symbol']
        whichsideup = request.form['whichsideup']
        output = ascii_art.printTriangle(width,symbol,whichsideup)
        # print(output)
        return render_template('ASCII_Results.html', title='ASCII Result', output=output)


# Third Section
@arts.route('/printBumps', methods=['POST'])
def printBumps():

    if request.method =='POST':
        number = request.form['number']
        symbol1 = request.form['symbol1']
        symbol2 = request.form['symbol2']
        output = ascii_art.printBumps(number, symbol1, symbol2)
        return render_template('ASCII_Results.html', title='ASCII Result', output=output)



# Fourth Section
@arts.route('/printDiamond', methods=['POST'])
def printDiamond():

    if request.method =='POST':
        width = request.form['number']
        symbol = request.form['symbol']
        output = ascii_art.printDiamond(width, symbol)
        return render_template('ASCII_Results.html', title='ASCII Result', output=output)


# Fifth Section
@arts.route('/printStripedDiamond', methods=['POST'])
def printStripedDiamond():

    if request.method =='POST':
        width = request.form['number']
        symbol1 = request.form['symbol1']
        symbol2 = request.form['symbol2']
        output = ascii_art.printStripedDiamond(width, symbol1,symbol2)
        return render_template('ASCII_Results.html', title='ASCII Result', output=output)



# Sixth Section
@arts.route('/printCrazyStripedDiamond', methods=['POST'])
def printCrazyStripedDiamond():

    if request.method =='POST':
        width = request.form['number']
        symbol1 = request.form['symbol1']
        symbol2 = request.form['symbol2']
        sym1Width = request.form['sym1Width']
        sym2Width = request.form['sym2Width']
        output = ascii_art.printCrazyStripedDiamond(width, symbol1, symbol2, sym1Width, sym2Width)
        return render_template('ASCII_Results.html', title='ASCII Result', output=output)

# Seventh Section
@arts.route('/printStarTree', methods=['POST'])
def printStarTree():

    if request.method =='POST':
        width = request.form['number']
        symbol1 = request.form['symbol']
        output = ascii_art.printStarTree(width, symbol1)
        return render_template('ASCII_Results.html', title='ASCII Result', output=output)


# Eighth Section
@arts.route('/printLuxuryTree', methods=['POST'])

def printLuxuryTree():
    
    if request.method =='POST':
        width = request.form['number']
        symbol1 = request.form['symbol1']
        symbol2 = request.form['symbol2']
        output = ascii_art.printLuxuryTree(width, symbol1, symbol2)
        return render_template('ASCII_Results.html', title='ASCII Result', output=output)
