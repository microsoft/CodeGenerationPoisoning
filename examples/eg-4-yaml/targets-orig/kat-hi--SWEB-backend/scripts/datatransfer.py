import csv
import pymysql.cursors
import yaml

config = yaml.load(open("/home/kat/Documents/DEVprojects/config.yaml"))

connect = pymysql.connect(host=config['host'],
                          user=config['user'],
                          password=config['password'],
                          db=config['dbname'])

with connect.cursor() as cursor:
	# obstsorten
	sorten_query = "INSERT INTO obstsorten(id, fruchtID, frucht, sorte, andereNamen,herkunft,groesse,beschreibung, reifezeit, geschmack, verwendung,lager,verbreitung) " \
	               "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
	# pflanzliste
	pflanzliste_query = "INSERT INTO pflanzliste(id, reihenID, reihenPos, baumID, baumsortenID, fruchtID, frucht, sortenID, sorte, longitude, latitude)" \
	                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
	# admin
	admin_query = "INSERT INTO admin(id, username, password) VALUES(%s,%s,%s)"

	# paten
	paten_query = "INSERT INTO paten(id, patenid, name, vorname, eintragUrkunde, mitpaten, firma, adresse, plz, ort, tel, email, patenbaum, entscheidung, " \
	              "start, ende, baumId, urkunde, followUp, foto, zahlart, zahlfrequenz, zahlbeginn, zahlende, quelle, kommentar) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"

	with open('/home/kat/Documents/DEVprojects/projects/sweb/test/Patendaten-sample.csv') as table:
		reader = csv.reader(table)
		for row in reader:
			'''
			cursor.execute(sorten_query, (
				row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11],
				row[12]))
			cursor.execute(pflanzliste_query,
			               (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10]))
			               '''
			cursor.execute(paten_query, (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9],
			                             row[10], row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18], row[19], row[20], row[21], row[22], row[23], row[24], row[25]))
		connect.commit()
