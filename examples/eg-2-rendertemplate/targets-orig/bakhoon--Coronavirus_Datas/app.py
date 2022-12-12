from flask import Flask, render_template, request, redirect
import sqlite3
import getCSV
import pandas
import numpy as np
import matplotlib.pyplot as plt
import os

app = Flask(__name__)


initDateFrom = '2020-01-01'
initDateTo = '2020-01-01'
initCountry = 'World'


@app.route('/', methods=['POST', 'GET'])
def start():
    plt.rcParams["figure.figsize"] = (12, 5)
    plt.rcParams['lines.linewidth'] = 4
    plt.rcParams['axes.grid'] = True
    getCSV.statistic()
    connect = sqlite3.connect("database.db")
    countrySelect = []
    cursor = connect.execute('select country from Countries;')
    selectBar = cursor.fetchall()
    temp = 'Null'

    for set in selectBar:
        countrySelect.append(set[0])
    if request.method == "POST":
        getCountry = request.form['country']
        global initCountry
        initCountry = getCountry

        datefrom = request.form['from']
        global initDateFrom
        initDateFrom = datefrom

        dateto = request.form['to']
        global initDateTo
        initDateTo = dateto

        option = request.form['option']

        if option == 'Total Case':
            cursor = connect.execute('select * from Datas where dates >= ? and dates <= ? and country = ?;',
                                     (datefrom, dateto, getCountry))
            getDatas = cursor.fetchall()
            cursor = connect.execute('select count(dates) from Datas where dates >= ? and dates <= ?;',
                                     (datefrom, dateto))
            getQuantity = cursor.fetchall()
            howmany = int(getQuantity[0][0] / 68)
            print(howmany)

            totalInfection = []
            allDates = []
            for i in getDatas:
                totalInfection.append(i[2])
                allDates.append(i[1])

            plt.plot(allDates, totalInfection, "bo")
            plt.title("Total Case in " + getCountry + " from " + datefrom + " to " + dateto)
            plt.xlabel('Dates')
            plt.xticks(rotation=90)
            plt.ylabel('Total Coronavirus Infections')

            cursor = connect.execute('select * from Numbers;')
            getValues = cursor.fetchall()
            integers = []

            for i in getValues:
                integers.append(i[0])

            if not integers:
                value = int(0)
                cursor.execute(
                    "INSERT INTO Numbers(num) VALUES (?);", (value,))
                connect.commit()
                temp = str(value)
                plt.savefig('C:\\Users\\HP\\PycharmProjects\\CoronaPredictionAfterJune\\static\\graph\\getplots' + temp + '.png')
            else:
                tempnumber = integers[-1]
                tempnumber += 1
                stringnumber = str(tempnumber)
                cursor.execute(
                    "INSERT INTO Numbers(num) VALUES (?);", (tempnumber,))
                connect.commit()
                plt.savefig('C:\\Users\\HP\\PycharmProjects\\CoronaPredictionAfterJune\\static\\graph\\getplots' + stringnumber + '.png')
            plt.show()

            if not integers:
                temp = '0'
            else:
                tempnumber = integers[-1]
                tempnumber += 1
                temp = str(tempnumber)

        elif option == 'New Case':
            cursor = connect.execute('select * from Datas where dates >= ? and dates <= ? and country = ?;',
                                     (datefrom, dateto, getCountry))
            getDatas = cursor.fetchall()
            cursor = connect.execute('select count(dates) from Datas where dates >= ? and dates <= ?;',
                                     (datefrom, dateto))
            getQuantity = cursor.fetchall()
            howmany = int(getQuantity[0][0] / 68)
            print(howmany)

            NewInfection = []
            allDates = []
            for i in getDatas:
                NewInfection.append(i[3])
                allDates.append(i[1])

            plt.plot(allDates, NewInfection, "bo")
            plt.title("Total Case in " + getCountry + " from " + datefrom + " to " + dateto)
            plt.xlabel('Dates')
            plt.xticks(rotation=90)
            plt.ylabel('Total Coronavirus Infections')

            cursor = connect.execute('select * from Numbers;')
            getValues = cursor.fetchall()
            integers = []

            for i in getValues:
                integers.append(i[0])

            if not integers:
                value = int(0)
                cursor.execute(
                    "INSERT INTO Numbers(num) VALUES (?);", (value,))
                connect.commit()
                temp = str(value)
                plt.savefig('C:\\Users\\HP\\PycharmProjects\\CoronaPredictionAfterJune\\static\\graph\\getplots' + temp + '.png')
            else:
                tempnumber = integers[-1]
                tempnumber += 1
                stringnumber = str(tempnumber)
                cursor.execute(
                    "INSERT INTO Numbers(num) VALUES (?);", (tempnumber,))
                connect.commit()
                plt.savefig('C:\\Users\\HP\\PycharmProjects\\CoronaPredictionAfterJune\\static\\graph\\getplots' + stringnumber + '.png')
            plt.show()

            if not integers:
                temp = '0'
            else:
                tempnumber = integers[-1]
                tempnumber += 1
                temp = str(tempnumber)
        elif option == 'Total Death':
            cursor = connect.execute('select * from Datas where dates >= ? and dates <= ? and country = ?;',
                                     (datefrom, dateto, getCountry))
            getDatas = cursor.fetchall()
            cursor = connect.execute('select count(dates) from Datas where dates >= ? and dates <= ?;',
                                     (datefrom, dateto))
            getQuantity = cursor.fetchall()
            howmany = int(getQuantity[0][0] / 68)
            print(howmany)

            TotalDeath = []
            allDates = []
            for i in getDatas:
                TotalDeath.append(i[4])
                allDates.append(i[1])

            plt.plot(allDates, TotalDeath, "bo")
            plt.title("Total Case in " + getCountry + " from " + datefrom + " to " + dateto)
            plt.xlabel('Dates')
            plt.xticks(rotation=90)
            plt.ylabel('Total Coronavirus Infections')

            cursor = connect.execute('select * from Numbers;')
            getValues = cursor.fetchall()
            integers = []

            for i in getValues:
                integers.append(i[0])

            if not integers:
                value = int(0)
                cursor.execute(
                    "INSERT INTO Numbers(num) VALUES (?);", (value,))
                connect.commit()
                temp = str(value)
                plt.savefig('C:\\Users\\HP\\PycharmProjects\\CoronaPredictionAfterJune\\static\\graph\\getplots' + temp + '.png')
            else:
                tempnumber = integers[-1]
                tempnumber += 1
                stringnumber = str(tempnumber)
                cursor.execute(
                    "INSERT INTO Numbers(num) VALUES (?);", (tempnumber,))
                connect.commit()
                plt.savefig('C:\\Users\\HP\\PycharmProjects\\CoronaPredictionAfterJune\\static\\graph\\getplots' + stringnumber + '.png')
            plt.show()

            if not integers:
                temp = '0'
            else:
                tempnumber = integers[-1]
                tempnumber += 1
                temp = str(tempnumber)

        elif option == 'New Death':
            cursor = connect.execute('select * from Datas where dates >= ? and dates <= ? and country = ?;',
                                     (datefrom, dateto, getCountry))
            getDatas = cursor.fetchall()
            cursor = connect.execute('select count(dates) from Datas where dates >= ? and dates <= ?;',
                                     (datefrom, dateto))
            getQuantity = cursor.fetchall()
            howmany = int(getQuantity[0][0] / 68)
            print(howmany)

            NewDeath = []
            allDates = []
            for i in getDatas:
                NewDeath.append(i[5])
                allDates.append(i[1])

            plt.plot(allDates, NewDeath, "bo")
            plt.title("Total Case in " + getCountry + " from " + datefrom + " to " + dateto)
            plt.xlabel('Dates')
            plt.xticks(rotation=90)
            plt.ylabel('Total Coronavirus Infections')

            cursor = connect.execute('select * from Numbers;')
            getValues = cursor.fetchall()
            integers = []

            for i in getValues:
                integers.append(i[0])

            if not integers:
                value = int(0)
                cursor.execute(
                    "INSERT INTO Numbers(num) VALUES (?);", (value,))
                connect.commit()
                temp = str(value)
                plt.savefig('C:\\Users\\HP\\PycharmProjects\\CoronaPredictionAfterJune\\static\\graph\\getplots' + temp + '.png')
            else:
                tempnumber = integers[-1]
                tempnumber += 1
                stringnumber = str(tempnumber)
                cursor.execute(
                    "INSERT INTO Numbers(num) VALUES (?);", (tempnumber,))
                connect.commit()
                plt.savefig('C:\\Users\\HP\\PycharmProjects\\CoronaPredictionAfterJune\\static\\graph\\getplots' + stringnumber + '.png')
            plt.show()

            if not integers:
                temp = '0'
            else:
                tempnumber = integers[-1]
                tempnumber += 1
                temp = str(tempnumber)

    return render_template('main.html', listOfCountry=countrySelect, initc=initCountry, initf=initDateFrom, initt=initDateTo, num=temp)


@app.route('/trashtrash', methods=['POST', 'GET'])
def trashData():
    connect = sqlite3.connect("database.db")
    cursor = connect.cursor()
    getCursor = connect.execute(
        'select num from Numbers;')
    getNumbers = getCursor.fetchall()
    for i in getNumbers:
        print(i[0])
        getstr = str(i[0])
        os.remove('C:\\Users\\HP\\PycharmProjects\\CoronaPredictionAfterJune\\static\\graph\\getplots' + getstr + '.png')
    cursor.execute('drop table if exists Numbers')
    connect.commit()

    return redirect('/')


if __name__ == '__main__':
    app.run()
