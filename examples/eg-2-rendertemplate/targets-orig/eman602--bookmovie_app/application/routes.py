from flask import Flask, render_template, redirect, url_for, request
from application import app, db
from application.models import Books, Movies
from application.forms import BookForm, MovieForm, BookDelete, MovieDelete, BookUpdate2

@app.route('/')
@app.route('/home')
def home():
    form=BookDelete()
   # form2=MovieDelete()       
   # if form.validate_on_submit():
    #    book_details=Books.query.filter_by(book_name=form.search_book.data).first()
     #   db.session.delete(book_details)
      #  db.session.commit()
       # return redirect(url_for('book'))              
    return render_template('home.html', title="update Page", form=form)


@app.route('/update', methods=['GET', 'POST'])
def update():
    form = BookUpdate2()
    
    if form.validate_on_submit():
       # request.method=='GET'       
        name=form.book_name.data 
        testing=Books.query.filter_by(book_name=name).first()
        if testing:
            testing.author_name=form.author_name.data
            testing.author_name=form.author_name.data
            testing.genre=form.genre.data
            testing.short_content=form.short_content.data
            db.session.commit()
            return redirect(url_for('book'))
        else:
            return render_template('update.html', title="update Page", form=form)

    return render_template('update.html', title="update Page", form=form)


@app.route('/book_delete', methods=['GET', 'POST'])
def book_delete():
    form=BookDelete()
    if form.validate_on_submit():
        book_details=Books.query.filter_by(book_name=form.search_book.data).first()
        if book_details:
            db.session.delete(book_details)
            db.session.commit()
            return redirect(url_for('book'))
        else:
            print(form.errors)
    return render_template('home.html', title="Delete Page", form=form)


@app.route('/Movie_delete', methods=['GET', 'POST'])
def Movie_delete():
    form=MovieDelete()
    if form.validate_on_submit():
        movie_details=Movies.query.filter_by(movie_name=form.search_movie.data).first()
        if movie_details:
            db.session.delete(movie_details)
            db.session.commit()
            return redirect(url_for('movie'))
        else:
            print(form.errors)
    return render_template('moviedelete.html', title="Movie Page", form=form)



@app.route('/book')
def book():
    bookData=Books.query.all()
    return render_template('book.html', title="Book Page", posts=bookData)


@app.route('/movie')
def movie():
    movieData=Movies.query.all()
    return render_template('movie.html', title="Movie Page", dosts=movieData)


@app.route('/post', methods=['GET', 'POST'])
def post():
    form = BookForm()
    if form.validate_on_submit():
        postData = Books(
            book_name = form.book_name.data,
            author_name = form.author_name.data,
            genre = form.genre.data,
            short_content = form.short_content.data
        )

        db.session.add(postData)
        db.session.commit()

        return redirect(url_for('book'))

    else:
        print(form.errors)

    return render_template('post.html', title='Post', form=form)


@app.route('/dost', methods=['GET', 'POST'])
def dost():
    form = MovieForm()
    if form.validate_on_submit():
        postData2 = Movies(
            movie_name = form.movie_name.data,
            director_name = form.director_name.data,
            genre = form.genre.data,
            short_content = form.short_content.data,
            book_id=form.book_id.data
        )

        db.session.add(postData2)
        db.session.commit()

        return redirect(url_for('movie'))

    else:
        print(form.errors)

    return render_template('dost.html', title='Dost', form=form)


#app.route('/addingupdates', methods=['GET', 'POST'])

#def addingupdates():
 #   form = BookUpdate2()

  #  if request.method=='POST':
   #     form.book_name.data = book_name
    #    form.author_name.data = author_name
     #   form.genre.data = genre
      #  form.short_content.data = short_content

       # return redirect(url_for('book'))    
    #return render_template('update.html', title='Update', form=form)













