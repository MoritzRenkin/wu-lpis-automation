# LPIS Skript ⛔ [DEPRECATED]

## Setup

Für non-Techies mit Windows 10: ``lpis.exe`` starten.


Für alle anderen, Python 3.7 oder neuer verwenden.
```
python3 -m pip install -r requirements.txt
```

```
python3 gui.py
```

## Verwendung
![image](https://user-images.githubusercontent.com/38352381/191569832-1feea657-448d-455d-ae5e-f1ae4298a8a7.png)

Bei „Subject Area“ ist der Name der Lehrveranstaltung aus LPIS einzutragen:
- Zum Beispiel „LVP Accounting & Management Control I” in das Feld kopieren
- Das Skript verwendet den ersten Link unter dieser Überschrift, also in der Regel den Link „LV anmelden“ o.Ä.
- Falls das Skript nicht den ersten Link verwenden soll, weil ihr euch zum Beispiel für die Prüfung anmelden wollt, gerne <a href="https://github.com/MoritzRenkin/wu-lpis-automation/issues">einen Issue erzeugen.</a>

![image](https://user-images.githubusercontent.com/38352381/191571634-428996a9-69a0-4871-9312-41b9be19e19c.png)


Bei „Course ID“ ist die vierstellige Zahl der gewünschten Veranstaltung einzutragen. Die Course ID muss zur angegebenen Subject Area passen.

![image](https://user-images.githubusercontent.com/38352381/191571680-27ef9d18-8d5e-43a6-978e-1d17de929901.png)

Bei „Time“ kann die Zeit angegeben werden, zu der das Skript die Anmeldung durchführt.
Format: „now“ oder „14:30“ oder „14:29:59.8“
Wichtig:
- Die eingetragene Zeit muss mindestens 5 Minuten in der Zukunft liegen. Ansonsten rechnet
das Skript mit der Anmeldung für den darauffolgenden Tag. Wenn man also um 13:58 die Uhrzeit „14:00“ einträgt, wird das Skript bis morgen 14:00 Uhr warten.
- Das Skript nimmt auf die Internetgeschwindigkeit Rücksicht, indem mehrere Ping Tests durchgeführt werden. Es ist also nicht notwendig und auch nicht sinnvoll „14:29:58.5“ statt
„14:30“ einzutragen.

Bei der Auswahl des Browsers bitte berücksichtigen: Die neueste Version des Browsers muss auf dem Computer installiert sein!
BETA: Das Skript kann auch mehrere Anmeldungen ein einem Durchgang durchführen.
Dafür einfach auf „Add course“ drücken und alle Felder ausfüllen. Die einzelnen Anmeldungen
werden automatisch geordnet und nacheinander durchgeführt. Bei zwei Anmeldungen mit der gleichen Zeit zählt die Reihenfolge im User-Interface.
Zum Starten einfach auf „Start Script“ klicken (Bitte kein Doppelklick). Beim ersten Ausführen meldet sich eventuell eure Firewall.
