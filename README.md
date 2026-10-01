# laika - live ai for konversational assistance

## Inhaltsverzeichnis

- [Einleitung](#einleitung)
- [Start mit Docker](#start-mit-docker)
- [Architektur](#architektur)

## Einleitung

laika ist eine interaktive Anwendung zur Erstellung von Gruppenchats mit beliebig vielen Mitgliedern.

Die Gruppenchats werden von dem KI-Modell llama-guard-3-1b moderiert, um die Nutzer vor beleidigenden, anzüglichen oder offensiven Inhalten zu schützen.
Zudem ist das KI-Modell llama-3.3-70b über Commands innerhalb von Chat-Nachrichten, wie z. B. "!laika", direkt ansprechbar, was zur Verbesserung der Gesprächsqualität und Unterhaltung der Nutzer beitragen kann.

Zuletzt ist auch die externe API icanhazdadjoke über Commands ansprechbar und es kann auch durch einen Prompt nach bestimmten Witzen gesucht werden.
icanhazdadjoke bietet allerdings nur englischsprachige Witze, weshalb auch das Such-Feature nur mit englischen Prompts zufriedenstellende Ergebnisse liefert.

## Start mit Docker

Voraussetzung ist Docker mit Docker Compose (z. B. Docker Desktop). Im Projektverzeichnis starten:

```sh
docker compose up --build -d
```

- Anwendung: http://localhost:8080
- REST-API-Dokumentation: http://localhost:8000/docs

Compose baut Frontend und Backend und startet MongoDB. Die Dienste warten beim Start auf die Bereitschaft ihrer Abhängigkeiten. Die veröffentlichten Ports sind nur auf dem lokalen Rechner erreichbar; MongoDB ist nur innerhalb des Docker-Netzwerks erreichbar.

Logs anzeigen:

```sh
docker compose logs -f
```

Stoppen:

```sh
docker compose down
```

Nutzer, Chats und Nachrichten bleiben im Docker-Volume `mongo-data` erhalten. `docker compose down --volumes` löscht auch diese Daten.

Lokale `.env`-Dateien werden nicht in die Images kopiert. Das Backend verwendet standardmäßig den in `rest-api/app/config.py` definierten JWT-Schlüssel; ein eigener `SECRET_KEY` kann über `environment` beim Backend in `docker-compose.yml` gesetzt werden.

Für die Moderation, KI-Antworten und Witze benötigt die Anwendung weiterhin Internetzugriff auf die externen Dienste. Insbesondere muss der KI-Endpunkt `https://models.mylab.th-luebeck.dev/v1` erreichbar sein.

## Architektur

![Architekturdiagramm](docs/architekturdiagramm.png)

Wie aus dem Architekturdiagramm hervorgeht, ist die Anwendung nach der gängigen 3-Tier-Architektur aufgebaut und die Komponenten kommunizieren über http/s-Requests mit den externen Services icanhazdadjoke und den von der TH-Lübeck gehosteten OpenAI-KI-Modellen.

Das Frontend wurde mithilfe von NiceGui realisiert und bekommt durch http-Requests die benötigten Daten von der Rest-API.
Während des Chattens wird eine Websocket-Verbindung vom Frontend zum Websocket-Server der Rest-API hergestellt, um Nachrichten schnellstmöglich bei anderen Chat-Mitgliedern darstellen zu können.
Vor dem Absenden einer Nachricht prüft das Frontend die Eingabe über das Moderationsmodell llama-guard-3-1b.
Das Frontend läuft als lokaler Docker-Compose-Dienst `frontend` auf Port 8080.

Die Rest-API benutzt das FastAPI-Framework und bietet weitgehend REST-konforme Endpunkte, um dem Frontend eine zentrale Schnittstelle zur Datenbank zur Verfügung zu stellen.
Darüber hinaus bietet die Rest-API auch weitere Funktionen, wie die Vergabe und das Prüfen von JWT-Tokens, um nur authentifizierten Usern Zugang zu den Funktionen zu ermöglichen. 
Zudem prüft die Rest-API auch die gesendeten Messages auf die bereits erwähnten Commands und sendet ggf. http/s-Requests an icanhazdadjoke oder das TTT-Modell llama-3.3-70b.
Die Rest-API läuft als Docker-Compose-Dienst `backend` auf Port 8000.

Die Datenbank ist eine MongoDB-Datenbank und speichert User, Chats und Messages.
MongoDB ist durch die JSON-Struktur sehr flexibel und hat eine hohe Skalierbarkeit, wodurch sie für ein Chat-Portal gut geeignet ist.
MongoDB läuft als Docker-Compose-Dienst `mongo` und speichert ihre Daten in einem dauerhaften Docker-Volume.

Zudem habe ich mich auch gegen die Einbindung von TTI- und ITT-Modellen entschieden, da die Verarbeitung und Darstellung von Grafiken im Allgemeinen viele Ressourcen beansprucht, welche ich im Rahmen dieses Projekts leider nicht zur Verfügung hatte.
Außerdem bleibt die Anwendung dadurch leichter verständlich und ist schneller intuitiv erfassbar.
