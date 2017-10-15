# Istruzioni per usare EventMan per HackInBo

## Server

Effettuate il clone del progetto su github e fare il checkout del branch "mario-edition".
Seguendo le istruzioni nel README principale, installate le dipendenze.
Eseguite eventman\_server.py

Loggatevi come admin, e create un utente diverso per ogni client che andrete ad utilizzare.

## I client

Ai client vanno collegate le stampanti, configurandole col driver delle Dymo LabelWriter 450 che trovate in questa directory.

Devono avere la porta 631 aperta e cups va configurato per condividere la stampante.  Date ad ogni stampante, sui vari sistemi, un nome univoco (questa è solo una comodità per poterle riconoscere sulla rete: in realtà il server andrà a comunicare direttamente con il server cups dello specifico client, quindi possono anche avere lo stesso nome).

Sul server, editate data/triggers/attends.d/print\_label.py: nel dizionario REMOTES dovete mettere una chiave per ciascun utente creato che abbia, come "printer", il nome della stampante su quel client da usare.

Fate una prova di stampa da ciascun client.

## Scansione QR Code

Ogni client dovrà eseguire il file qrcode\_reader.py (directory tools), dopo aver configurato qrcode\_reader.ini con il nome e la password dell'utente, e l'IP del server.
Nella sezione "event" è importante impostare il campo "id" a quello dell'evento che stiamo gestendo.

Ricordarsi di aggiungere l'utente che farà girare il daemon al gruppo dialout (o comunque di dargli accesso in lettura al file /dev/ttyACM\*)

Per il pomeriggio, è sufficiente collegare tutte le pistole ad un solo PC (quello del server), ed eseguire più istanze di qrcode\_reader.ini dopo aver creato vari file qrcode\_reader\_afternoon.ini (copiando l'originale e cambiandovi nome); il nome utente e las password possono essere sempre quelle di admin. È importante cambiare la porta della seriale.

