from flask import abort,render_template,redirect,url_for,request,jsonify,flash
from flask_login import current_user, login_required
from app import db
from app.drawings import drawings
from app.images import save_image
from app.models import Drawing

@drawings.route('/list')
@login_required
def list():
  page = request.args.get('page',1,type=int)

  pagination = current_user.drawings.order_by(Drawing.timestamp.desc()).paginate(page=page,per_page=9)
  drawings=pagination.items

  return render_template('drawings/list.html',drawings=drawings,pagination=pagination,user=current_user)

@drawings.route('/<drawing_id>')
@login_required
def drawing(drawing_id):
  # retrieve and validate drawing
  drawing = Drawing.query.get_or_404(drawing_id)

  # validate drawing 
  if current_user != drawing.user and not drawing.display:
    abort(403)

  return render_template('drawings/drawing.html',drawing=drawing)

@drawings.route('/draw')
@login_required
def draw():
  return render_template('drawings/draw.html')

@drawings.route('/add',methods=['POST'])
@login_required
def add():
  if request.form['dataURL']:
    filename = save_image(request.form['dataURL'])
    drawing = Drawing(filename)
    drawing.user = current_user
    db.session.add(drawing)
    db.session.commit()

  return jsonify({
    'result':'success',
  })

@drawings.route('/add_to_display/<drawing_id>')
@login_required
def add_to_display(drawing_id):
  # retrieve and validate drawing
  drawing = Drawing.query.get_or_404(drawing_id)
  if current_user != drawing.user:
    abort(403)
  if drawing.display:
    flash('Drawing Already On Display')
  else:
    # set drawing display to True
    drawing.display = True
    db.session.commit()

  return redirect(url_for('core.user',username=current_user.username))

@drawings.route('/remove_from_display/<drawing_id>')
@login_required
def remove_from_display(drawing_id):
  # retrieve and validate drawing
  drawing = Drawing.query.get_or_404(drawing_id)
  if current_user != drawing.user:
    abort(403)
  if drawing.display:
    # set drawing display to False
    drawing.display = False
    db.session.commit()
  else:
    flash('Drawing Not Currently On Display')
  
  return redirect(url_for('core.user',username=current_user.username))