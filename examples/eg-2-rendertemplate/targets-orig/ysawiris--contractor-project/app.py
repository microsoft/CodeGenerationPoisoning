from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
from inventory import Store
from datetime import datetime
import os

app = Flask(__name__)

host = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/FanGear')
client = MongoClient(host=f'{host}?retryWrites=false')
db = client.get_default_database()
inventory = db.inventory
comments = db.comments 

store = Store(inventory)
store.show_inventory()

@app.route('/')
def inventory_index():
    """Show all playlists."""
    return render_template('show_inventory.html', inventory_list=inventory.find())

@app.route('/inventory/<inventory_id>')
def show_item(inventory_id):
    item = inventory.find_one({'_id': ObjectId(inventory_id)})
    item_comments = comments.find({'inventory_id': ObjectId(inventory_id)})
    return render_template("item_show.html", inventory = item, comments = item_comments)

@app.route('/inventory/<inventory_id>/comments', methods=['POST'])
def comments_new(inventory_id):
    """Submit a new comment."""
    comment = {
        'title': request.form.get('title'),
        'name': request.form.get('name'),
        'content': request.form.get('content'),
        'inventory_id': ObjectId(request.form.get('inventory_id'))
    }
    print(comment)
    comments.insert_one(comment)
    return redirect(url_for('show_item', inventory_id=request.form.get('inventory_id')))

@app.route('/inventory/<inventory_id>/comments/<comment_id>/edit')
def comment_edit(inventory_id, comment_id):
    """Show the edit form for a playlist."""
    comment = comments.find_one({'_id': ObjectId(comment_id)})
    return render_template('comment_edit.html', comment=comment, inventory_id=inventory_id)

@app.route('/inventory/<inventory_id>/comments/<comment_id>', methods=['POST'])
def comment_update(inventory_id, comment_id):
    """Submit an edited comment."""
    updated_comment = {
        'title': request.form.get('title'),
        'name': request.form.get('name'), 
        'content': request.form.get('content'),
        'inventory_id': ObjectId(request.form.get('inventory_id'))
    }
    comments.update_one(
        {'_id': ObjectId(comment_id)},
        {'$set': updated_comment})
    return redirect(url_for('show_item', comment_id = comment_id, inventory_id = inventory_id))

@app.route('/inventory/<inventory_id>/comments/<comment_id>/delete', methods=['POST'])
def comments_delete(inventory_id, comment_id):
    """Action to delete a comment."""
    comment = comments.find_one({'_id': ObjectId(comment_id)})
    comments.delete_one({'_id': ObjectId(comment_id)})
    return redirect(url_for('show_item', inventory_id=comment.get('inventory_id')))

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 5000))