from blog import app
from flask import render_template
# 处理页面404错误
@app.errorhandler(404)
def page_not_found(e):
    
    return render_template('errors/404.html')