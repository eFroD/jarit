# Feature Specification: Asynchrone Rezept-Extraktion mit Statusfeedback und Historie

**Feature Branch**: `feature/002-async-extraction-jobs` (from `dev`, noch nicht angelegt)

**Created**: 2026-10-02

**Status**: Draft

**Input**: User description: siehe `spec.md` im Projektroot – "Führe asynchrone Rezept-Extraktion mit Statusfeedback und eine persönliche Extraktions-Historie ein. […] Ziel 1, asynchrone Jobs: Wenn ein Nutzer eine Video-URL zur Extraktion einreicht, wird sofort ein Job angelegt und dessen Kennung zurückgegeben; die Extraktion läuft im Hintergrund innerhalb des bestehenden Backend-Prozesses. […] Ein fehlgeschlagener Job kann vom Nutzer erneut gestartet werden. Ziel 2, Oberfläche: Nach dem Absenden sieht der Nutzer den Fortschritt des Jobs mit der aktuellen Stufe, aktualisiert durch regelmäßiges Abfragen. […] Ziel 3, Historie: Jeder Nutzer sieht eine Liste seiner bisherigen Extraktionen […]. Der bisherige synchrone Extraktions-Endpunkt wird durch den asynchronen Ablauf ersetzt […]. Die bestehende CI mit mindestens 80 Prozent Testabdeckung bleibt erfüllt. […]"

## Kontext

JarIt ist eine self-hosted Anwendung, die Rezepte aus Social-Media-Videos extrahiert und nach Mealie hochlädt. Ein Host betreibt eine Instanz für mehrere Nutzer. Heute blockiert eine Extraktion die Anfrage des Nutzers 10 bis 60 Sekunden lang. Der Nutzer sieht in dieser Zeit nur einen Ladeindikator und erfährt nicht, woran die Anwendung gerade arbeitet. Verlässt er die Seite oder lädt er sie neu, ist das Ergebnis verloren und die Extraktion muss von vorn beginnen. Fehler werden heute als technische Meldung an den Nutzer durchgereicht.

Die Funktion entkoppelt das Einreichen einer URL vom Ergebnis: Die Extraktion wird zu einem dauerhaft gespeicherten Job, dessen Fortschritt und Ergebnis jederzeit abrufbar sind. Die gespeicherten Jobs bilden zugleich die persönliche Historie des Nutzers, aus der er Rezepte erneut öffnen, bearbeiten und nach Mealie hochladen kann.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Extraktion einreichen und sofort weiterarbeiten (Priority: P1)

Ein Nutzer reicht eine Video-URL zur Extraktion ein. Die Anwendung bestätigt sofort, dass die Extraktion angelegt wurde, statt bis zum Ergebnis zu blockieren. Die Extraktion läuft im Hintergrund weiter. Ist sie abgeschlossen, kann der Nutzer das Rezept wie bisher in der Vorschau prüfen und nach Mealie hochladen.

**Why this priority**: Das ist der Kern der Funktion. Ohne ihn gibt es weder Statusfeedback noch ein dauerhaftes Ergebnis.

**Independent Test**: Eine gültige Rezept-Video-URL einreichen und messen, dass die Bestätigung in unter 2 Sekunden kommt. Danach den Job abfragen, bis er abgeschlossen ist, und prüfen, dass das Ergebnis dem einer bisherigen Extraktion entspricht und sich nach Mealie hochladen lässt.

**Acceptance Scenarios**:

1. **Given** ein angemeldeter Nutzer, **When** er eine Video-URL und eine Zielsprache zur Extraktion einreicht, **Then** erhält er sofort eine Job-Kennung, und der Job steht im Zustand „wartend“ oder bereits in einer späteren Stufe.
2. **Given** ein eingereichter Job, **When** die Extraktion erfolgreich endet, **Then** steht der Job auf „abgeschlossen“ und das extrahierte Rezept (inklusive eines eventuellen Vorschlags für fehlende Felder) ist über den Job abrufbar.
3. **Given** ein abgeschlossener Job, **When** der Nutzer das Ergebnis öffnet, **Then** kann er es wie bisher in der Vorschau prüfen und nach Mealie hochladen.
4. **Given** ein laufender Job, **When** der Nutzer die Seite verlässt oder neu lädt und später zurückkehrt, **Then** findet er den Job mit aktuellem Zustand und nach Abschluss mit Ergebnis wieder.

---

### User Story 2 - Fortschritt nachvollziehen (Priority: P1)

Während die Extraktion läuft, sieht der Nutzer, in welcher Stufe sich sein Job befindet: wartend, Videobeschreibung wird geladen, Audio wird transkribiert (nur wenn nötig), Rezept wird extrahiert, abgeschlossen oder fehlgeschlagen. Die Anzeige aktualisiert sich von selbst, ohne dass er die Seite neu laden muss.

**Why this priority**: Fehlendes Feedback während der langen Wartezeit ist das zweite Kernproblem. Ohne sichtbaren Fortschritt wirkt die Anwendung bei 60 Sekunden Wartezeit hängend.

**Independent Test**: Eine URL einreichen, deren Beschreibung kein vollständiges Rezept enthält, und die Anzeige beobachten: Sie muss nacheinander mindestens die Stufen Beschreibung laden, Transkription, Extraktion und abgeschlossen zeigen. Bei einer URL mit vollständigem Rezept in der Beschreibung darf die Transkriptionsstufe nicht erscheinen.

**Acceptance Scenarios**:

1. **Given** ein eingereichter Job, **When** der Nutzer dessen Zustand abfragt, **Then** erhält er jederzeit die aktuelle Stufe.
2. **Given** ein Job, dessen Videobeschreibung für ein Rezept ausreicht, **When** er durchläuft, **Then** wird die Stufe „Audio wird transkribiert“ übersprungen.
3. **Given** der Nutzer hat die Statusanzeige geöffnet, **When** der Job in eine neue Stufe wechselt, **Then** zeigt die Oberfläche die neue Stufe spätestens nach 5 Sekunden an, ohne dass der Nutzer etwas tun muss.
4. **Given** mehr Jobs als freie Plätze, **When** ein Job auf einen freien Platz wartet, **Then** steht er sichtbar auf „wartend“.
5. **Given** der Nutzer verfolgt den Fortschritt nach dem Absenden, **When** der Job abgeschlossen ist, **Then** öffnet sich wie bisher automatisch der Rezept-Editor mit dem extrahierten Rezept und, falls vorhanden, der vorgeschlagenen Version.
6. **Given** der Nutzer hat die Seite während der Extraktion verlassen, **When** er zurückkehrt, **Then** sieht er wieder den aktuellen Fortschritt bzw. nach Abschluss das Ergebnis.

---

### User Story 3 - Verständliche Fehler und erneuter Versuch (Priority: P2)

Schlägt eine Extraktion fehl, sieht der Nutzer eine verständliche Ursache, etwa „Video nicht erreichbar“, „Kein Rezept im Video gefunden“, „Transkription fehlgeschlagen“ oder „Fehler beim Sprachmodell“. Technische Details sieht er nicht; sie landen im Log des Hosts. Er kann den fehlgeschlagenen Job mit einem Klick erneut starten, ohne URL und Sprache noch einmal einzugeben.

**Why this priority**: Fehler kommen bei externen Videoplattformen und Sprachmodellen regelmäßig vor. Ohne verständliche Ursache und Wiederholung bleibt der Nutzer ratlos, die Funktion ist aber auch ohne diese Story schon nutzbar.

**Independent Test**: Eine nicht erreichbare Video-URL einreichen und prüfen, dass der Job mit der Ursache „Video nicht erreichbar“ fehlschlägt, die Antwort keine technischen Details enthält und das Log die technische Ursache enthält. Danach den Job erneut starten und prüfen, dass er wieder durchläuft.

**Acceptance Scenarios**:

1. **Given** ein Job, dessen Video nicht abrufbar ist, **When** die Extraktion scheitert, **Then** steht der Job auf „fehlgeschlagen“ mit der Ursache „Video nicht erreichbar“.
2. **Given** ein Video ohne Rezeptinhalt, **When** die Extraktion endet, **Then** steht der Job auf „fehlgeschlagen“ mit der Ursache „Kein Rezept im Video gefunden“.
3. **Given** ein fehlgeschlagener Job, **When** der Nutzer dessen Zustand abruft, **Then** enthält die Antwort keine Stacktraces, internen Fehlermeldungen von Drittdiensten, Pfade oder Zugangsdaten.
4. **Given** ein fehlgeschlagener Job, **When** der Nutzer ihn erneut startet, **Then** läuft die Extraktion mit derselben URL und Zielsprache erneut durch die Stufen, und der Nutzer verfolgt sie wie einen neuen Job.
5. **Given** ein laufender, wartender oder abgeschlossener Job, **When** der Nutzer versucht, ihn erneut zu starten, **Then** wird das abgelehnt.
6. **Given** ein Job, der vor längerer Zeit eingereicht wurde und fehlgeschlagen ist, **When** der Nutzer ihn erneut startet, **Then** zählt die angezeigte Laufzeit ab dem erneuten Start bei null, nicht ab der ursprünglichen Einreichung.

---

### User Story 4 - Der Host begrenzt die Last (Priority: P2)

Ein Host betreibt JarIt auf begrenzter Hardware und mit kostenpflichtigen Sprachmodellen. Er legt per Umgebungsvariable fest, wie viele Extraktionen gleichzeitig laufen dürfen. Ohne Angabe sind es 2. Weitere Jobs warten, bis ein Platz frei wird.

**Why this priority**: Ohne Begrenzung könnten viele gleichzeitige Einreichungen den Host überlasten oder hohe Kosten verursachen. Bei wenigen Nutzern ist das Risiko gering, deshalb P2.

**Independent Test**: Mit dem Standardwert vier Jobs kurz hintereinander einreichen und prüfen, dass nie mehr als zwei gleichzeitig in einer aktiven Stufe sind und die übrigen nach und nach starten. Den Wert auf 1 setzen, neu starten und dasselbe mit höchstens einem aktiven Job prüfen.

**Acceptance Scenarios**:

1. **Given** keine Begrenzung ist konfiguriert, **When** mehrere Jobs gleichzeitig eingereicht werden, **Then** laufen höchstens 2 gleichzeitig, die übrigen stehen auf „wartend“.
2. **Given** der Host hat die Begrenzung auf N gesetzt, **When** mehr als N Jobs eingereicht werden, **Then** laufen höchstens N gleichzeitig.
3. **Given** wartende Jobs, **When** ein laufender Job endet (erfolgreich oder fehlgeschlagen), **Then** startet der am längsten wartende Job.
4. **Given** der konfigurierte Wert ist keine ganze Zahl ≥ 1, **When** die Anwendung startet, **Then** verwendet sie den Standardwert 2 und schreibt eine Warnung ins Log.

---

### User Story 5 - Neustart hinterlässt keine hängenden Jobs (Priority: P2)

Der Host startet die Anwendung neu, etwa für ein Update, während Jobs laufen oder warten. Nach dem Start stehen diese Jobs auf „fehlgeschlagen“ mit dem Hinweis, dass die Anwendung neu gestartet wurde. Nutzer können sie erneut starten.

**Why this priority**: Ohne diese Story würden Jobs nach einem Neustart für immer als laufend angezeigt, weil die Hintergrundverarbeitung den Neustart nicht überlebt.

**Independent Test**: Einen Job einreichen, die Anwendung während der Extraktion neu starten und prüfen, dass der Job danach auf „fehlgeschlagen“ mit Neustart-Hinweis steht und sich erneut starten lässt.

**Acceptance Scenarios**:

1. **Given** ein Job ist beim Beenden der Anwendung in einer aktiven Stufe oder wartend, **When** die Anwendung wieder startet, **Then** steht er auf „fehlgeschlagen“ mit der Ursache „Abgebrochen durch Neustart der Anwendung“, bevor neue Anfragen angenommen werden.
2. **Given** ein so markierter Job, **When** der Nutzer ihn erneut startet, **Then** läuft er normal durch.
3. **Given** abgeschlossene oder bereits fehlgeschlagene Jobs, **When** die Anwendung neu startet, **Then** bleiben sie unverändert.

---

### User Story 6 - Persönliche Extraktions-Historie (Priority: P2)

Ein Nutzer sieht eine Liste seiner bisherigen Extraktionen, neueste zuerst. Jeder Eintrag zeigt den Rezepttitel (oder die Video-URL, solange es keinen Titel gibt), den Einreichungszeitpunkt, den Zustand und ob das Rezept bereits nach Mealie hochgeladen wurde. Er sieht ausschließlich seine eigenen Jobs, auch wenn er Administrator ist.

**Why this priority**: Die Historie macht gespeicherte Ergebnisse auffindbar und ist die Grundlage für Story 7. Das Grundproblem „Ergebnis geht verloren“ ist schon durch Story 1 gelöst.

**Independent Test**: Als Nutzer A drei Extraktionen durchführen, als Administrator B eine. Nutzer A sieht genau seine drei Jobs, neueste zuerst, mit den genannten Angaben; B sieht nur seinen einen. Der direkte Abruf eines fremden Jobs über dessen Kennung liefert dieselbe Antwort wie eine nicht existierende Kennung.

**Acceptance Scenarios**:

1. **Given** ein Nutzer mit mehreren Jobs, **When** er seine Historie öffnet, **Then** sieht er alle seine Jobs, neueste zuerst, jeweils mit Titel oder URL, Einreichungszeitpunkt, Zustand und Upload-Kennzeichen.
2. **Given** ein Job, der noch keinen Rezepttitel hat (wartend, laufend oder fehlgeschlagen), **When** er in der Historie erscheint, **Then** wird stattdessen die Video-URL angezeigt.
3. **Given** zwei Nutzer, davon einer Administrator, **When** einer seine Historie abruft oder einen fremden Job über dessen Kennung abfragt, ändert, hochlädt, erneut startet oder löscht, **Then** sieht er keine fremden Jobs, und jeder Zugriff auf einen fremden Job verhält sich wie bei einem nicht existierenden Job.

---

### User Story 7 - Früheres Rezept bearbeiten, hochladen und Einträge löschen (Priority: P2)

Ein Nutzer öffnet ein abgeschlossenes Rezept aus seiner Historie, bearbeitet es im Editor und lädt es nach Mealie hoch. Seine Änderungen werden am Job gespeichert und sind beim nächsten Öffnen noch da. Ein erfolgreicher Upload wird am Job vermerkt und in der Historie angezeigt. Nicht mehr benötigte Einträge kann er aus seiner Historie löschen.

**Why this priority**: Heute gehen auch Änderungen im Editor beim Verlassen der Seite verloren, und der Nutzer weiß später nicht mehr, welche Rezepte schon in Mealie sind.

**Independent Test**: Ein abgeschlossenes Rezept öffnen, den Titel ändern, die Seite verlassen und erneut öffnen: Die Änderung ist noch da. Dann hochladen und prüfen, dass Mealie die geänderte Fassung erhält und die Historie den Eintrag als hochgeladen zeigt. Danach den Eintrag löschen; er erscheint nicht mehr und ist auch über seine Kennung nicht mehr abrufbar.

**Acceptance Scenarios**:

1. **Given** ein abgeschlossener Job, **When** der Nutzer ihn aus der Historie öffnet, **Then** sieht er das Rezept im Editor in der zuletzt gespeicherten Fassung.
2. **Given** der Nutzer bearbeitet das Rezept, **When** er die Änderungen speichert, **Then** sind sie am Job gespeichert und beim nächsten Öffnen sichtbar, auch auf einem anderen Gerät.
3. **Given** ein bearbeitetes Rezept, **When** der Nutzer es nach Mealie hochlädt, **Then** wird die bearbeitete Fassung hochgeladen.
4. **Given** ein Upload nach Mealie gelingt, **When** der Nutzer danach die Historie öffnet, **Then** ist der Eintrag als hochgeladen gekennzeichnet, mit Zeitpunkt des letzten erfolgreichen Uploads.
5. **Given** ein Upload nach Mealie schlägt fehl, **When** der Nutzer die Historie öffnet, **Then** ist der Eintrag nicht als hochgeladen gekennzeichnet bzw. ein früheres Kennzeichen bleibt unverändert.
6. **Given** ein bereits hochgeladenes Rezept, **When** der Nutzer es erneut hochladen will, **Then** weist die Oberfläche darauf hin, dass es schon hochgeladen wurde, erlaubt den Upload aber.
7. **Given** ein Job in einem Endzustand, **When** der Nutzer ihn löscht, **Then** ist er dauerhaft entfernt, erscheint nicht mehr in der Historie und ist über seine Kennung nicht mehr abrufbar.
8. **Given** ein wartender oder laufender Job, **When** der Nutzer ihn löschen will, **Then** wird das abgelehnt, mit dem Hinweis, das Ende abzuwarten.
9. **Given** der Nutzer hat ein Rezept im Editor geändert, aber nicht gespeichert, und den Editor verlassen, **When** er denselben Job erneut öffnet und die ungespeicherten Änderungen noch angezeigt werden, **Then** kennzeichnet die Oberfläche sie als ungespeichert, und ein Upload nach Mealie lädt genau die angezeigte Fassung hoch (sie wird vorher gespeichert).
10. **Given** im Editor war zuvor das Rezept eines anderen Jobs geöffnet, **When** der Nutzer einen Job öffnet, dessen Rezept nicht geladen werden kann (Verbindungsfehler, gelöscht, fremd), **Then** zeigt der Editor nicht das Rezept des anderen Jobs an, sondern einen Fehlerhinweis, und es lässt sich nichts zu diesem Job speichern oder hochladen.

---

### Edge Cases

- **Gleiche URL mehrfach eingereicht**: Jeder Einreichvorgang erzeugt einen eigenen Job; es gibt keine Deduplizierung.
- **Extraktion hängt**: Ein Job, der nach 10 Minuten in aktiven Stufen nicht abgeschlossen ist, wird als fehlgeschlagen mit der Ursache „Zeitüberschreitung“ markiert und gibt seinen Platz frei.
- **Unbekannte Fehlerursache**: Lässt sich ein Fehler keiner bekannten Ursache zuordnen, sieht der Nutzer „Unbekannter Fehler, bitte erneut versuchen“; die technische Ursache steht im Log.
- **Ungültige Eingabe**: Eine syntaktisch ungültige URL oder fehlende Zielsprache wird sofort beim Einreichen abgewiesen; es entsteht kein Job.
- **Nicht existierende oder fremde Job-Kennung**: Die Abfrage liefert dieselbe Antwort „nicht gefunden“, damit nicht erkennbar ist, ob ein fremder Job existiert.
- **Mehrfaches Klicken auf „erneut starten“**: Ein Job kann nur einmal gleichzeitig laufen; ein zweiter Neustart-Aufruf für einen bereits wieder wartenden oder laufenden Job wird abgelehnt.
- **Gelöschter oder deaktivierter Nutzer**: Laufende Jobs eines gelöschten Nutzers dürfen die Verarbeitung anderer Jobs nicht stören; seine Jobs werden mit ihm entfernt.
- **Datenbank vorübergehend nicht erreichbar während eines Jobs**: Der Job darf nicht dauerhaft in einer aktiven Stufe stehen bleiben; spätestens die Zeitüberschreitung oder der nächste Neustart setzt ihn auf „fehlgeschlagen“.
- **Bestehende Installation ohne Migrationshistorie**: Eine bestehende Datenbank, deren Tabellen bisher automatisch angelegt wurden, wird beim Update ohne Datenverlust unter das Migrationssystem gestellt; Nutzer und Integrations-Zugangsdaten bleiben erhalten.
- **Mealie-Upload**: Der Upload nach Mealie bleibt ein separater, vom Nutzer ausgelöster Schritt und ist nicht Teil des Jobs; nur sein Erfolg wird am Job vermerkt.
- **Erneuter Start nach Bearbeitung**: Nur fehlgeschlagene Jobs können erneut gestartet werden. Ein abgeschlossener, bearbeiteter Job wird also nie durch eine neue Extraktion überschrieben.
- **Bearbeiten nicht abgeschlossener Jobs**: Wartende, laufende und fehlgeschlagene Jobs haben kein Rezept und lassen sich weder bearbeiten noch hochladen.
- **Ungültige Bearbeitung**: Eine Fassung, die nicht dem Rezeptformat entspricht, wird abgewiesen; die zuletzt gespeicherte Fassung bleibt erhalten.
- **Bearbeitung in zwei Tabs**: Es gilt die zuletzt gespeicherte Fassung; eine Konflikterkennung ist nicht Teil dieses Features.
- **Löschen während eines Uploads oder in einem anderen Tab**: Ein Upload oder Speichern zu einem inzwischen gelöschten Job verhält sich wie bei einem nicht existierenden Job.
- **Gelöschter Job in Mealie**: Das Löschen aus der Historie entfernt das Rezept nicht aus Mealie.
- **Editor verlassen mit ungespeicherten Änderungen**: Werden ungespeicherte Änderungen beim erneuten Öffnen desselben Jobs wieder angezeigt, gelten sie weiterhin als ungespeichert. Die Anzeige „alle Änderungen gespeichert“ darf nie erscheinen, solange die angezeigte Fassung von der gespeicherten abweicht.
- **Rezept eines Jobs lässt sich nicht laden**: Der Editor zeigt nie das Rezept eines anderen Jobs unter der Kennung des geöffneten Jobs an; auch nicht kurzzeitig, solange der geöffnete Job noch lädt, in einer Form, die sich bearbeiten oder speichern lässt.
- **Laufzeitanzeige nach erneutem Start**: Die Laufzeit in der Fortschrittsanzeige bezieht sich auf den letzten Start des Jobs. Die Historie zeigt weiterhin den ursprünglichen Einreichungszeitpunkt.

## Requirements *(mandatory)*

### Functional Requirements

**Jobs einreichen und abfragen**

- **FR-001**: Das System MUSS beim Einreichen einer Video-URL samt Zielsprache durch einen angemeldeten Nutzer sofort einen Job anlegen und dessen Kennung zurückgeben, ohne auf das Ende der Extraktion zu warten.
- **FR-002**: Das System MUSS die Extraktion im Hintergrund innerhalb des bestehenden Anwendungsprozesses ausführen. Es DARF keine zusätzliche Infrastruktur erfordern (kein zusätzlicher Dienst, Broker, Zwischenspeicher oder Worker-Container).
- **FR-003**: Ein Job MUSS genau einem Nutzer gehören. Nutzer, auch Administratoren, DÜRFEN nur ihre eigenen Jobs sehen, abfragen, bearbeiten, hochladen, erneut starten und löschen. Jeder Zugriff auf einen fremden Job MUSS sich genauso verhalten wie der Zugriff auf einen nicht existierenden Job.
- **FR-004**: Der aktuelle Zustand eines Jobs MUSS jederzeit für seinen Besitzer abrufbar sein, einschließlich Stufe, Einreichungszeitpunkt, Zeitpunkt des letzten Starts, Zeitpunkt der letzten Zustandsänderung und, falls vorhanden, Ergebnis oder Fehlerursache.
- **FR-005**: Das Ergebnis eines abgeschlossenen Jobs MUSS dauerhaft gespeichert werden und denselben Inhalt haben wie eine bisherige synchrone Extraktion (Rezept und ggf. Vorschlag für fehlende Felder).

**Stufen**

- **FR-006**: Ein Job MUSS die Stufen „wartend“, „Videobeschreibung wird geladen“, „Audio wird transkribiert“, „Rezept wird extrahiert“ sowie genau einen der Endzustände „abgeschlossen“ oder „fehlgeschlagen“ verwenden.
- **FR-007**: Die Stufe „Audio wird transkribiert“ DARF nur gesetzt werden, wenn tatsächlich transkribiert wird.
- **FR-008**: Jeder Stufenwechsel MUSS sofort gespeichert werden, sodass eine Abfrage stets die tatsächliche aktuelle Stufe liefert.
- **FR-009**: Die Oberfläche MUSS nach dem Absenden den Fortschritt des Jobs mit der aktuellen Stufe anzeigen, durch regelmäßiges Abfragen selbstständig aktualisieren und einen Stufenwechsel spätestens nach 5 Sekunden anzeigen.
- **FR-009a**: Ist der verfolgte Job abgeschlossen, MUSS die Oberfläche wie bisher automatisch den Rezept-Editor mit dem extrahierten Rezept und, falls vorhanden, der vorgeschlagenen Version öffnen.
- **FR-009b**: Verlässt der Nutzer die Seite und kehrt später zurück, MUSS die Oberfläche den Job wieder auffinden und dessen aktuellen Fortschritt bzw. das Ergebnis anzeigen; weder Job noch Ergebnis gehen verloren.
- **FR-009c**: Die Fortschrittsanzeige MUSS die Laufzeit ab dem letzten Start des Jobs anzeigen (Einreichen bzw. erneuter Start nach FR-013), nicht ab der ursprünglichen Einreichung.

**Fehler**

- **FR-010**: Schlägt ein Job fehl, MUSS das System eine für Nutzer verständliche Ursache aus einer festen Liste speichern: „Video nicht erreichbar“, „Kein Rezept im Video gefunden“, „Transkription fehlgeschlagen“, „Fehler beim Sprachmodell“, „Zeitüberschreitung“, „Abgebrochen durch Neustart der Anwendung“, „Unbekannter Fehler“.
- **FR-011**: Technische Fehlerdetails (Stacktraces, Meldungen von Drittdiensten, Pfade) DÜRFEN nur ins Log geschrieben werden und NICHT in Antworten an den Nutzer gelangen. Der Logeintrag MUSS die Job-Kennung enthalten und DARF keine Zugangsdaten enthalten.
- **FR-012**: Ein Job, der länger als 10 Minuten in aktiven Stufen ist, MUSS als fehlgeschlagen mit „Zeitüberschreitung“ markiert werden und seinen Platz freigeben.

**Erneut starten**

- **FR-013**: Der Besitzer MUSS einen fehlgeschlagenen Job erneut starten können. Dabei werden dieselbe URL und Zielsprache verwendet, der Job kehrt zu „wartend“ zurück, Fehlerursache sowie altes Ergebnis werden zurückgesetzt, und der Zeitpunkt des letzten Starts wird auf den Zeitpunkt des erneuten Starts gesetzt. Der ursprüngliche Einreichungszeitpunkt bleibt erhalten.
- **FR-014**: Das erneute Starten MUSS für Jobs abgelehnt werden, die nicht im Zustand „fehlgeschlagen“ sind.

**Begrenzung der Parallelität**

- **FR-015**: Die Zahl gleichzeitig laufender Extraktionen MUSS instanzweit über eine Umgebungsvariable begrenzbar sein, mit Standardwert 2.
- **FR-016**: Jobs, die keinen freien Platz erhalten, MÜSSEN im Zustand „wartend“ bleiben und in Reihenfolge ihres Einreichens (bzw. erneuten Startens) gestartet werden, sobald ein Platz frei wird.
- **FR-017**: Ein ungültiger Wert (keine ganze Zahl ≥ 1) MUSS durch den Standardwert ersetzt und mit einer Warnung im Log vermerkt werden.

**Neustart**

- **FR-018**: Beim Start MUSS das System, bevor es Anfragen annimmt, alle Jobs im Zustand „wartend“ oder in einer aktiven Stufe auf „fehlgeschlagen“ mit der Ursache „Abgebrochen durch Neustart der Anwendung“ setzen.

**Persistenz und Schema**

- **FR-019**: Jobs und ihr Zustand MÜSSEN in der bestehenden Datenbank der Anwendung gespeichert werden.
- **FR-020**: Schemaänderungen MÜSSEN über ein versioniertes Migrationssystem eingespielt werden statt über automatisches Anlegen der Tabellen beim Start. Bestehende Installationen MÜSSEN ohne Datenverlust und ohne manuelle Datenbankeingriffe auf den neuen Stand gebracht werden; die Schritte für den Host stehen in der README.

**Historie**

- **FR-021**: Ein Nutzer MUSS eine Liste seiner eigenen Jobs abrufen können, neueste zuerst. Jeder Eintrag zeigt den Rezepttitel (ersatzweise die Video-URL), den Einreichungszeitpunkt, den Zustand und ob das Rezept bereits nach Mealie hochgeladen wurde.
- **FR-022**: Ein Nutzer MUSS jeden abgeschlossenen Job aus der Historie erneut öffnen, im Editor bearbeiten und nach Mealie hochladen können.
- **FR-023**: Änderungen im Editor MÜSSEN am Job gespeichert werden und die zuletzt gespeicherte Fassung ersetzen. Nur Fassungen, die dem Rezeptformat entsprechen, werden gespeichert. Ein Upload nach Mealie verwendet die zuletzt gespeicherte Fassung.
- **FR-023a**: Der Editor MUSS jederzeit korrekt anzeigen, ob die angezeigte Fassung von der zuletzt gespeicherten abweicht. Das gilt auch, wenn ungespeicherte Änderungen nach dem Verlassen und erneuten Öffnen desselben Jobs wieder angezeigt werden. Ein Upload MUSS genau die im Editor angezeigte Fassung nach Mealie bringen; weicht sie von der gespeicherten ab, wird sie vorher gespeichert, und schlägt das Speichern fehl, unterbleibt der Upload mit Fehlerhinweis.
- **FR-023b**: Der Editor DARF unter der Kennung eines Jobs ausschließlich das Rezept dieses Jobs bearbeitbar anzeigen. Kann das Rezept des geöffneten Jobs nicht geladen werden, MUSS die Oberfläche einen Fehlerhinweis zeigen, und Speichern sowie Upload für diesen Job MÜSSEN unmöglich sein.
- **FR-024**: Ein erfolgreicher Mealie-Upload MUSS am Job mit Zeitpunkt vermerkt werden. Ein fehlgeschlagener Upload DARF das Kennzeichen nicht setzen oder verändern. Ein erneuter Upload bleibt erlaubt; die Oberfläche weist darauf hin, dass das Rezept schon hochgeladen wurde.
- **FR-025**: Ein Nutzer MUSS Jobs in einem Endzustand aus seiner Historie löschen können. Gelöschte Jobs sind danach dauerhaft entfernt und nicht mehr abrufbar. Das Löschen wartender oder laufender Jobs MUSS abgelehnt werden.

**Ablösung der synchronen Extraktion**

- **FR-026**: Die bisherige synchrone Extraktions-Schnittstelle MUSS entfernt und vollständig durch den asynchronen Ablauf ersetzt werden. Die Oberfläche MUSS auf den neuen Ablauf umgestellt sein.

**Qualitätssicherung**

- **FR-027**: Die bestehende Pull-Request-Prüfung MUSS weiter bestehen und eine Testabdeckung des Backends von mindestens 80 % erzwingen; ein Unterschreiten MUSS die Prüfung fehlschlagen lassen. (Hinweis: Die heutige Prüfung misst die Abdeckung noch nicht, siehe Assumptions.)
- **FR-028**: Automatisierte Tests MÜSSEN mindestens abdecken: die Hintergrundverarbeitung, alle Stufenübergänge inklusive Fehlerursachen, das Nebenläufigkeitslimit, die Neustart-Bereinigung, die Zeitüberschreitung, das erneute Starten (inklusive Zurücksetzen des Startzeitpunkts), Bearbeiten, Upload-Kennzeichen, Löschen und die Zugriffsbeschränkung auf eigene Jobs.
- **FR-029**: Diese Tests MÜSSEN ohne echtes Sprachmodell, ohne echte Transkription und ohne Netzwerkzugriff nach außen laufen und damit in der Pull-Request-Prüfung ausgeführt werden.

### Key Entities

- **Extraktions-Job**: Ein Auftrag eines Nutzers, ein Rezept aus einem Video zu extrahieren, und zugleich ein Eintrag seiner Historie. Enthält Besitzer, Video-URL, Zielsprache, aktuelle Stufe, Einreichungszeitpunkt, Zeitpunkt des letzten Starts (Einreichen oder erneuter Start), Zeitpunkt der letzten Zustandsänderung, bei Erfolg das Ergebnis in der zuletzt gespeicherten Fassung, bei Misserfolg die nutzerverständliche Fehlerursache sowie den Zeitpunkt des letzten erfolgreichen Mealie-Uploads (leer, wenn nie hochgeladen). Gehört genau einem Nutzer und wird mit ihm oder durch ihn gelöscht.
- **Job-Stufe**: Feste Menge von Zuständen: wartend, Videobeschreibung wird geladen, Audio wird transkribiert, Rezept wird extrahiert, abgeschlossen, fehlgeschlagen. Die ersten vier außer „wartend“ gelten als aktiv; abgeschlossen und fehlgeschlagen sind Endzustände.
- **Fehlerursache**: Feste Liste nutzerverständlicher Ursachen (siehe FR-010), getrennt von der technischen Ursache im Log.
- **Extraktions-Ergebnis**: Das extrahierte Rezept samt optionalem Vorschlag für fehlende Felder, im selben Format wie bisher.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 95 % der Einreichungen erhält der Nutzer die Bestätigung mit Job-Kennung in unter 2 Sekunden, unabhängig davon, wie lange die Extraktion dauert.
- **SC-002**: Ein Stufenwechsel ist in 100 % der Fälle spätestens 5 Sekunden später in der geöffneten Oberfläche sichtbar.
- **SC-003**: Nach Verlassen und erneutem Aufrufen der Seite findet der Nutzer 100 % seiner Jobs mit aktuellem Zustand bzw. Ergebnis wieder; 0 Extraktionen müssen wegen eines Seitenwechsels wiederholt werden.
- **SC-004**: 100 % der fehlgeschlagenen Jobs zeigen eine Ursache aus der festen Liste; 0 Antworten an Nutzer enthalten Stacktraces oder Rohmeldungen von Drittdiensten.
- **SC-005**: Bei einer Begrenzung von N laufen in Lasttests mit 3·N gleichzeitig eingereichten Jobs nie mehr als N Extraktionen gleichzeitig, und alle Jobs erreichen einen Endzustand.
- **SC-006**: Nach einem Neustart stehen 0 Jobs in „wartend“ oder einer aktiven Stufe, die vor dem Neustart eingereicht wurden.
- **SC-007**: Ein Update einer bestehenden Installation erhält 100 % der vorhandenen Nutzer und Integrations-Zugangsdaten.
- **SC-008**: Ein Nutzer, auch ein Administrator, sieht oder verändert in 0 Fällen Jobs eines anderen Nutzers.
- **SC-009**: 100 % der gespeicherten Änderungen an einem Rezept sind beim erneuten Öffnen vorhanden und landen beim Upload in Mealie.
- **SC-010**: Ein Nutzer erkennt in der Historie ohne weiteren Klick, welche seiner Rezepte bereits nach Mealie hochgeladen wurden.
- **SC-011**: Die Pull-Request-Prüfung läuft ohne externe Dienste vollständig durch und meldet eine Backend-Testabdeckung von mindestens 80 %.
- **SC-012**: In 100 % der Uploads aus dem Editor entspricht die in Mealie angekommene Fassung der beim Klick auf „Hochladen“ angezeigten Fassung; in 0 Fällen wird unter einem Job das Rezept eines anderen Jobs angezeigt oder gespeichert.
- **SC-013**: Nach einem erneuten Start zeigt die Fortschrittsanzeige in 100 % der Fälle eine Laufzeit, die beim erneuten Start bei null beginnt.

## Assumptions

- Die Begrenzung der Parallelität gilt instanzweit, nicht pro Nutzer; die Warteschlange ist eine gemeinsame Reihenfolge nach Einreichzeitpunkt ohne Priorisierung.
- Es läuft genau ein Anwendungsprozess. Mehrere Backend-Instanzen gegen dieselbe Datenbank werden nicht unterstützt.
- Das Abbrechen laufender oder wartender Jobs durch den Nutzer ist nicht Teil dieses Features.
- Jobs werden nicht automatisch gelöscht; sie verschwinden nur durch Löschen durch den Nutzer oder mit dem Nutzerkonto. Eine Aufbewahrungsfrist ist nicht Teil dieses Features.
- Der Upload nach Mealie bleibt ein separater, vom Nutzer ausgelöster Schritt; neu ist nur das Kennzeichen am Job.
- Gespeichert wird nur die zuletzt bearbeitete Fassung eines Rezepts; eine Versionsgeschichte oder die Rückkehr zur ursprünglichen Extraktion ist nicht Teil dieses Features.
- Der Rezepttitel für die Historie stammt aus dem extrahierten bzw. zuletzt bearbeiteten Rezept.
- Eine Suche, Filterung oder Seitenweise Anzeige der Historie ist nicht Teil dieses Features; die Liste zeigt alle eigenen Jobs.
- Die heutige Pull-Request-Prüfung (`.github/workflows/ci.yml`) führt die Backend-Tests aus, misst aber keine Testabdeckung und hat keine 80-%-Schwelle. Die Eingabe setzt diese Schwelle als bestehend voraus; dieses Feature führt sie daher ein (FR-027). Ob die bestehende Codebasis die Schwelle heute erreicht, ist in der Planung zu prüfen.
- Die Zeitüberschreitung von 10 Minuten ist fest eingestellt und liegt deutlich über der heutigen typischen Dauer von 10 bis 60 Sekunden.
- Ein ungültiger Wert für die Parallelitätsgrenze verhindert den Start nicht, weil er keine Sicherheitsfrage ist (anders als der Verschlüsselungsschlüssel aus Feature 001).
- Die Oberfläche ist laut Eingabe der einzige Client der Extraktions-Schnittstelle; ihre Ablösung (FR-026) braucht daher keine Übergangsphase.
- Statusaktualisierung erfolgt laut Eingabe durch regelmäßiges Abfragen; eine Push-Benachrichtigung oder eine Meldung bei Abschluss außerhalb der geöffneten Seite ist nicht Teil dieses Features.
- Der automatische Wechsel in den Editor (FR-009a) gilt nur, solange der Nutzer den Fortschritt dieses Jobs geöffnet hat; nach einer Rückkehr zu einem bereits abgeschlossenen Job öffnet er das Ergebnis aus der Statusansicht oder der Historie.
- Die Zuordnung technischer Fehler zu nutzerverständlichen Ursachen erfolgt nach bestem Wissen; was sich nicht eindeutig zuordnen lässt, fällt unter „Unbekannter Fehler“.
- Die Vorgaben „bestehende Datenbank“, „kein zusätzlicher Dienst“ und „Migrationssystem“ stammen ausdrücklich aus der Eingabe und sind Rahmenbedingungen, keine Implementierungsentscheidung dieser Spec.
