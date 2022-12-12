#! /usr/bin/env python
# -*- coding: utf-8 -*-
import pymysql
from flask import Flask, render_template, request, redirect, url_for

connection = pymysql.connect(host='127.0.0.1',
                             user='root',
                             passwd='123321',
                             db='mydb',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)
cursor = connection.cursor()

app = Flask(__name__)


@app.route("/", methods=('GET', 'POST'))
def index():
    return render_template('index.html')


@app.route("/CreateDB")
def input_create_db():

    return render_template('input_data.html', text='Придумайте название базы данных')


@app.route("/CreateDB", methods=('GET', 'POST'))
def create_db():
    if request.method == 'POST':
        name = request.form['name']

        create_db_query = "CREATE DATABASE " + name
        try:
            cursor.execute(create_db_query)
            print("База данных была успешно созданна")
        except Exception as e:
            print(e)

            connection.close()
        return redirect(url_for('index'))


@app.route("/DeleteDB")
def input_delete_db():

    return render_template('input_data.html', text='Напишите название базы данных, которую хотите удалить')


@app.route("/DeleteDB", methods=('GET', 'POST'))
def delete_db():
    if request.method == 'POST':
        name = request.form['name']

        drop_db_query = "DROP DATABASE " + name
        try:
            cursor.execute(drop_db_query)
            print("База данных была успешно удаленна")
        except Exception as e:
            print(e)

            connection.close()
        return redirect(url_for('index'))


@app.route("/CreateTB")
def input_create_tb():

    return render_template('input_data3.html',
                           text1='Напишите название таблицы ',
                           text2='Напишите название нашей новой колонки ',
                           text3='Напишите тип данных Например VARCHAR (20) ')


@app.route("/CreateTB", methods=('GET', 'POST'))
def create_tb():
    if request.method == 'POST':
        # print("Напишите название таблицы")
        name = request.form['name']
        # print("Напишите название нашей новой колонки")
        name_col = request.form['name_col']
        # print("Напишите тип данных Например VARCHAR (20)")
        int_col = request.form['int_col']

        create_table_query = "CREATE TABLE " + name + "(" + name_col + " " + int_col + ")"
        try:
            cursor.execute(create_table_query)
            print("Таблица была успешно созданно")
        except Exception as e:
            print(e)

            connection.close()
        return redirect(url_for('index'))


@app.route("/DeleteTB")
def input_delete_tb():

    return render_template('input_data.html', text='Напишите название таблицы которую хотите удалить')


@app.route("/DeleteTB", methods=('GET', 'POST'))
def delete_tb():
    if request.method == 'POST':
        # print("Напишите название таблицы которую хотите удалить")
        name = request.form['name']

        drop_table_query = "DROP TABLE " + name
        try:
            cursor.execute(drop_table_query)
            print("Таблица была успешно удаленна")
        except Exception as e:
            print(e)

            connection.close()
        return redirect(url_for('index'))


@app.route("/ChangeTB", methods=('GET', 'POST'))
def change_tb():
    return render_template('input_change.html')


@app.route("/ChangeTB/Edit")
def input_edit():

    return render_template('input_data3.html',
                           text1='Напишите название таблицы в которую вы хотите внести изменения ',
                           text2='Напишите название колонки куда вы хотите сделать запись ',
                           text3='Сделайте запись в колонку ')


@app.route("/ChangeTB/Edit", methods=('GET', 'POST'))
def edit_tb():
    if request.method == 'POST':
        # print("Напишите название таблицы в которую вы хотите внести изменения")
        name = request.form['name']
        # print("Напишите название колонки куда вы хотите сделать запись")
        name_col = request.form['name_col']
        # print("Сделайте запись в колонку")
        int_col = request.form['int_col']
        change_col_query = "INSERT INTO " + name + " (" + name_col + ") VALUES('" + int_col + "');"
        try:
            cursor.execute(change_col_query)
            print("Таблица была успешно изменена")
            print(change_col_query)
        except Exception as e:
            print(e)

            connection.close()
        return redirect(url_for("index"))


@app.route("/ChangeTB/Add")
def input_add():

    return render_template('input_data3.html',
                           text1='Напишите название таблицы ',
                           text2='Напишите название нашей новой колонки ',
                           text3='Напишите тип данных. Например VARCHAR(20) ')


@app.route("/ChangeTB/Add", methods=('GET', 'POST'))
def add_col():
    if request.method == 'POST':
        # print("Напишите название таблицы")
        name = request.form['name']
        # print("Напишите название нашей новой колонки")
        name_col = request.form['name_col']
        # print("Напишите тип данных. Например VARCHAR(20)")
        int_col = request.form['int_col']
        add_col_query = "ALTER TABLE " + name + " ADD COLUMN " + name_col + " " + int_col
        try:
            cursor.execute(add_col_query)
            print("Колонка успешно добавлена")
        except Exception as e:
            print(e)

            connection.close()
        return redirect(url_for("index"))


@app.route("/SelectTB", methods=('GET', 'POST'))
def select_tb():
    return render_template('input_select.html')


@app.route("/SelectTB/Select_all")
def input_select_all():

    return render_template('input_data.html', text='Напишите название таблицы')


@app.route("/SelectTB/Select_all", methods=('GET', 'POST'))
def select_all():
    if request.method == 'POST':
        # print("Напишите название таблицы")
        name = request.form['name']
        import_table_query = "SELECT * FROM " + name

        try:
            cursor.execute(import_table_query)
        # print("Данные успешно импортированны")
        except Exception as e:
            print(e)

            connection.close()

        data = cursor.fetchall()
        return render_template('data.html', data=data)

        # for row in cursor.fetchall():
        #     print(row)
        # return redirect(url_for("index"))


@app.route("/SelectTB/count")
def input_count():

    return render_template('input_data.html', text='Напишите название таблицы')


@app.route("/SelectTB/count", methods=('GET', 'POST'))
def count():
    if request.method == 'POST':
        # print("Напишите название таблицы")
        name = request.form['name']
        import_table_query = "SELECT COUNT(*) FROM " + name
        try:
            cursor.execute(import_table_query)
            print("Данные успешно импортированны")
        except Exception as e:
            print(e)

            connection.close()

        data = cursor.fetchall()
        return render_template('data1.html', data=data)
        # return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=4567)
