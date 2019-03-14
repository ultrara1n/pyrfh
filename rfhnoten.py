import credentials
from pushover import init, Client
import requests
from requests_html import HTMLSession
import sqlite3
import os

#Datenbank erstellen, wenn nicht vorhanden
if not os.path.isfile('noten.db'):
	conn = sqlite3.connect('noten.db')
	cursor = conn.cursor()
	cursor.execute('CREATE TABLE noten (id integer PRIMARY KEY, semester TEXT, termin TEXT, fach TEXT, note TEXT)')
	conn.commit()
else:
	conn = sqlite3.connect('noten.db')
	cursor = conn.cursor()
	
#Session besorgen
base_url = "https://www.studse.rfh-koeln.de/?func=login_check"
payload = {'Benutzer': credentials.rfh_matrikelnr, 'pwd1': credentials.rfh_password}
headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246'}
r = requests.post(base_url, data=payload, headers=headers)
#print(r.status_code, r.reason)
session_id = r.url.split('PHPSESSID=')[1]
#print(session_id)

#Notenliste besorgen
noten_url = 'https://www.studse.rfh-koeln.de/vpruef/pruefungsergebnisse.php?PHPSESSID=' + session_id
session = HTMLSession()
r = session.get(noten_url)

table = r.html.find('table', first=True)

zeilen = table.find('tr')

for zeile in zeilen:
	content = zeile.text

	#Leerzeilen ignorieren
	if content == '':
		continue
		
	#Herausfinden was für eine Zeile
	infos = zeile.find('td', first=True)
	css_class = infos.attrs['class']

	if css_class[0] == 'header_top':
		continue
	elif css_class[0] == 'semester_bez':
		semester = zeile.text
	elif css_class[0] == 'termin_bez':
		termin = zeile.text
	else:
		noten_td = zeile.find('td')
		int = 0
		for zelle in noten_td:
			if int == 0:
				fach = zelle.text
			elif int == 2:
				note = zelle.text
			int = int + 1

		#Prüfen ob Eintrag in Datenbank, wenn nicht, dann Eintragen
		cursor.execute('SELECT COUNT(*) FROM noten WHERE semester = "'+semester+'" AND termin = "'+termin+'" AND fach = "'+fach+'" AND note = "'+note+'"')
		result=cursor.fetchone()
		
		if result[0] == 0:
			cursor.execute('INSERT INTO noten (semester, termin, fach, note) VALUES ("'+semester+'","'+termin+'","'+fach+'","'+note+'")')
			conn.commit()
			continue
		
		#Prüfen ob vielleicht schon drin, aber mit anderer Note
		cursor.execute('SELECT note FROM noten WHERE semester = "'+semester+'" AND termin = "'+termin+'" AND fach = "'+fach+'"')
		result=cursor.fetchone()
		
		if result[0] != note:
			#In Datenbank ändern
			cursor.execute('UPDATE noten SET note = "'+note+'" WHERE semester = "'+semester+'" AND termin = "'+termin+'" AND fach = "'+fach+'"')
			conn.commit()
			
			#Benachrichtigung senden
			init(credentials.pushover_token)
			Client(credentials.pushover_secret).send_message(fach+' - '+note, title="RFH Noten")
			print('Nachfolgende Note geändert:')
		
		
		print(semester + ' - ' + termin + ' - ' + fach + ' - ' + note)