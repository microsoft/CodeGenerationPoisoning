from app import app
from main import *
from flask import render_template
import json


@app.route('/')
def show_inventory():
    return render_template('index.html')


@app.route('/producto')
def show_item():
    return render_template('producto.html')


@app.route('/backend')
def go_to_backend():
    return render_template('/backend/index.html')


@app.route('/modificar_item')
def modify_item():
    return render_template('/backend/modificar_item.html')


@app.route('/añadir_item')
def add_item():
    return render_template('/backend/añadir_item.html')


@app.route('/coger_items')
def coger_item():
    with open('app/static/js/items.json') as file:
        inventario = json.load(file)
    return json.dumps(inventario)


#inventory = Gildedrose([Normalitem("+5 Dexterity Vest", 10, 20),
#                        Agedbrie("Aged Brie", 2, 0),
#                        Normalitem("Elixir of the Mongoose", 5, 7),
#                        Sulfuras("Sulfuras, Hand of Ragnaros", 0, 80),
#                        Sulfuras("Sulfuras, Hand of Ragnaros", -1, 80),
#                        Backstagepass(
#                            "Backstage passes to a TAFKAL80ETC concert", 15, 20),
#                        Backstagepass(
#                            "Backstage passes to a TAFKAL80ETC concert", 10, 49),
#                        Backstagepass(
#                            "Backstage passes to a TAFKAL80ETC concert", 5, 49),
#                        Conjured("Conjured Mana Cake", 3, 6)])

# def show_inventory():
#    inventory.add_item()
#    actual_inventory = inventory.get_items()
#    front_end = "----------- Inventory right now -----------<br/>"
#    for item in actual_inventory:
#        front_end = front_end + "<br/>" + item.__repr__()
#    return front_end

#@app.route('/update_inventory')
#def update_inventory():
#    inventory.update_quality()
#    front_end = "----------- Inventory right now -----------<br/>"
#    for item in inventory.items:
#        front_end = front_end + "<br/>" + item.__repr__()
#    return front_end


#@app.route('/update_inventory/<days>')
#def update_inventory_days(days):
#    inventory_of_days = Gildedrose([Normalitem("+5 Dexterity Vest", 10, 20),
#                                    Agedbrie("Aged Brie", 2, 0),
#                                    Normalitem("Elixir of the Mongoose", 5, 7),
#                                    Sulfuras(
#                                        "Sulfuras, Hand of Ragnaros", 0, 80),
#                                    Sulfuras(
#                                        "Sulfuras, Hand of Ragnaros", -1, 80),
#                                    Backstagepass(
#                                        "Backstage passes to a TAFKAL80ETC concert", 15, 20),
#                                    Backstagepass(
#                                        "Backstage passes to a TAFKAL80ETC concert", 10, 49),
#                                    Backstagepass(
#                                        "Backstage passes to a TAFKAL80ETC concert", 5, 49),
#                                    Conjured("Conjured Mana Cake", 3, 6)])
#    front_end = "----------- Update at Day " + days + " -----------<br/>"
#    for day in range(1, int(days) + 1):
#        inventory_of_days.update_quality()
#    for item in inventory_of_days.items:
#        front_end = front_end + "<br/>" + item.__repr__()
#    return front_end

if __name__ == "__main__":
    app.run()
