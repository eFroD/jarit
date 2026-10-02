# Feature Specification: Verschlüsselte Integrations-Keys und PR-CI

**Feature Branch**: `feature/001-key-encryption-ci` (from `dev`)

**Created**: 2026-10-02

**Status**: Draft

**Input**: User description: siehe `spec.md` im Projektroot – "Härte die Speicherung von Integrations-API-Keys ab und führe eine CI-Pipeline für Pull Requests ein. […] Ziel 1, Verschlüsselung at rest: Alle Werte in der Spalte api_key der Tabelle api_keys werden symmetrisch verschlüsselt gespeichert und nur beim Verwenden entschlüsselt. […] Die README beschreibt, wie ein Schlüssel erzeugt wird und was beim Rotieren zu beachten ist."

## Kontext

JarIt ist eine self-hosted Anwendung. Ein Host betreibt eine Instanz für mehrere Nutzer und legt LLM-Provider und Modell zentral fest. Nutzer hinterlegen über die Oberfläche ihre eigenen Zugangsdaten für Integrationen (derzeit Mealie). Diese Zugangsdaten liegen heute im Klartext in der Datenbank: Wer die Datenbank oder ein Backup einsehen kann, hat direkten Zugriff auf die Mealie-Instanzen aller Nutzer.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Zugangsdaten werden nur verschlüsselt gespeichert (Priority: P1)

Ein Nutzer hinterlegt oder aktualisiert seine Mealie-Zugangsdaten über die Oberfläche. Der Key wird verschlüsselt gespeichert und nur in dem Moment entschlüsselt, in dem JarIt ihn braucht, etwa beim Hochladen eines Rezepts nach Mealie. Für den Nutzer ändert sich nichts. Wer dagegen nur die Datenbank oder ein Backup in die Hände bekommt, kann mit den gespeicherten Werten nichts anfangen.

**Why this priority**: Das ist der eigentliche Sicherheitsgewinn der Funktion. Alle anderen Stories bauen darauf auf.

**Independent Test**: Einen Integrations-Key über die Oberfläche speichern und danach den gespeicherten Wert direkt in der Datenbank prüfen: Er darf nicht mit dem eingegebenen Key übereinstimmen und ihn auch nicht enthalten. Danach ein Rezept nach Mealie hochladen; das muss wie bisher funktionieren.

**Acceptance Scenarios**:

1. **Given** ein angemeldeter Nutzer ohne hinterlegte Mealie-Zugangsdaten, **When** er URL und API-Key speichert, **Then** ist in der Datenbank nur eine verschlüsselte Form des Keys abgelegt und der Klartext nirgends in der Datenbank zu finden.
2. **Given** ein Nutzer mit verschlüsselt gespeicherten Zugangsdaten, **When** er ein Rezept nach Mealie hochlädt, **Then** funktioniert der Upload wie bisher.
3. **Given** ein Nutzer mit gespeicherten Zugangsdaten, **When** er seinen Key durch einen neuen ersetzt, **Then** ist auch der neue Key nur verschlüsselt gespeichert.
4. **Given** ein Nutzer ruft seine hinterlegten Integrationen über die Oberfläche oder die API ab, **When** die Antwort ausgeliefert wird, **Then** enthält sie weder den Klartext-Key noch seine verschlüsselte Form.
5. **Given** eine künftige Integration neben Mealie, **When** ein Nutzer dafür einen Key hinterlegt, **Then** wird er ohne zusätzlichen Aufwand ebenso verschlüsselt gespeichert.

---

### User Story 2 - Der Host richtet den Schlüssel beim Start sicher ein (Priority: P1)

Ein Host startet JarIt, egal ob als Neuinstallation oder nach einem Update, ohne einen gültigen Schlüssel gesetzt zu haben. Die Anwendung startet dann nicht. Sie bricht sofort mit einer klaren Fehlermeldung ab. Diese enthält einen frisch erzeugten, gültigen Schlüssel, die Zeile, die der Host unverändert in seine `.env`-Datei kopieren kann, und den Hinweis, dass bei Verlust des Schlüssels alle gespeicherten Integrations-Keys unbrauchbar werden und neu hinterlegt werden müssen.

**Why this priority**: Ohne gültigen Schlüssel kann Story 1 nicht funktionieren. Ein stiller Fallback, etwa auf Klartext oder einen eingebauten Standardschlüssel, würde den Schutz aushebeln.

**Independent Test**: Die Anwendung ohne Schlüssel und danach mit einem ungültigen Schlüssel starten. Beide Male muss sie mit der beschriebenen Meldung abbrechen. Dann die vorgeschlagene Zeile in die `.env` übernehmen, neu starten und prüfen, dass die Anwendung jetzt normal startet.

**Acceptance Scenarios**:

1. **Given** kein Schlüssel ist in der Umgebung gesetzt, **When** der Host die Anwendung startet, **Then** bricht sie ab, bevor sie Anfragen annimmt. Die Fehlermeldung enthält einen neu erzeugten gültigen Schlüssel, eine kopierfertige `.env`-Zeile und den Hinweis auf die Folgen eines Schlüsselverlusts.
2. **Given** ein Schlüssel ist gesetzt, hat aber kein gültiges Format (z. B. falsche Länge oder ein Platzhalter wie `CHANGEME`), **When** der Host die Anwendung startet, **Then** verhält sie sich wie in Szenario 1 und nennt zusätzlich, dass der vorhandene Wert ungültig ist, ohne diesen Wert auszugeben.
3. **Given** der Host hat die vorgeschlagene Zeile unverändert in seine `.env` übernommen, **When** er die Anwendung neu startet, **Then** startet sie normal.
4. **Given** die Anwendung startet zweimal hintereinander ohne Schlüssel, **When** der Host beide Meldungen vergleicht, **Then** enthalten sie unterschiedliche Schlüssel. Es gibt also keinen fest eingebauten Vorschlag.

---

### User Story 3 - Bestehende Installationen werden ohne Zutun migriert (Priority: P2)

Ein Host aktualisiert eine ältere JarIt-Installation, in der Integrations-Keys noch im Klartext liegen, und setzt einen gültigen Schlüssel. Seine Nutzer müssen nichts tun: Ihre bestehenden Zugangsdaten werden beim Start und spätestens beim ersten Zugriff in die verschlüsselte Form überführt und funktionieren weiter.

**Why this priority**: Ohne diese Story müssten nach dem Update alle Nutzer ihre Zugangsdaten neu eingeben. Das wäre ein Bruch für bestehende Installationen. Für Neuinstallationen ist die Story nicht nötig.

**Independent Test**: In einer Datenbank mit Klartext-Einträgen die neue Version mit gültigem Schlüssel starten und als betroffener Nutzer ein Rezept nach Mealie hochladen. Der Upload muss gelingen, und danach darf der Eintrag in der Datenbank nur noch verschlüsselt vorliegen.

**Acceptance Scenarios**:

1. **Given** eine Datenbank mit Klartext-Einträgen, **When** die neue Version mit gültigem Schlüssel startet, **Then** liegen nach Abschluss des Starts alle Einträge nur noch verschlüsselt vor, auch die von Nutzern, die sich nie wieder anmelden.
2. **Given** ein Klartext-Eintrag aus einer älteren Installation, **When** die Anwendung erstmals auf diesen Eintrag zugreift, **Then** wird er als Klartext erkannt, korrekt verwendet und anschließend verschlüsselt zurückgeschrieben.
3. **Given** ein bereits migrierter Eintrag, **When** die Anwendung erneut darauf zugreift, **Then** wird er als verschlüsselt erkannt und nicht ein zweites Mal verschlüsselt.
4. **Given** eine Datenbank mit Klartext- und verschlüsselten Einträgen gemischt, **When** Nutzer ihre Integrationen verwenden, **Then** funktionieren alle Einträge.

---

### User Story 4 - Ein unlesbarer Eintrag legt die Anwendung nicht lahm (Priority: P2)

Der Host hat den Schlüssel gewechselt oder verloren, sodass ältere Einträge nicht mehr entschlüsselt werden können. Ein betroffener Nutzer versucht, seine Integration zu verwenden. Statt eines Absturzes oder eines unverständlichen Fehlers bekommt er die Meldung, dass er seine Zugangsdaten neu eintragen muss. Danach funktioniert die Integration wieder. Die übrige Anwendung bleibt für alle Nutzer verfügbar.

**Why this priority**: Schlüsselwechsel und -verlust sind realistische Betriebsfälle bei Self-Hosting. Der Schaden muss auf das Neueintragen von Zugangsdaten begrenzt bleiben.

**Independent Test**: Einen Key speichern, den Schlüssel gegen einen anderen gültigen Schlüssel tauschen, die Anwendung neu starten und die Integration verwenden. Erwartet wird eine verständliche Aufforderung zum Neueintragen. Nach dem Neueintragen muss die Integration wieder funktionieren.

**Acceptance Scenarios**:

1. **Given** ein Eintrag, der mit einem anderen Schlüssel verschlüsselt wurde, **When** der Nutzer die Integration verwendet, **Then** erhält er eine verständliche Meldung, dass er seine Zugangsdaten neu hinterlegen muss, und die Anwendung läuft weiter.
2. **Given** derselbe Zustand, **When** andere Nutzer oder andere Funktionen die Anwendung verwenden, **Then** sind sie nicht beeinträchtigt.
3. **Given** ein Nutzer mit einem unlesbaren Eintrag, **When** er seine Zugangsdaten über die Oberfläche neu speichert, **Then** wird der alte Eintrag ersetzt und die Integration funktioniert wieder.
4. **Given** ein Entschlüsselungsfehler tritt auf, **When** er protokolliert wird, **Then** enthält der Logeintrag weder Klartext noch die verschlüsselte Form des Keys, sondern nur nicht-sensible Angaben wie Nutzer-ID und Integration.

---

### User Story 5 - Der Host weiß, wie er den Schlüssel erzeugt und rotiert (Priority: P3)

Ein Host liest die README, bevor er JarIt einrichtet oder den Schlüssel wechselt. Dort steht, wie er einen gültigen Schlüssel erzeugt, wo er ihn hinterlegt und was beim Rotieren passiert: Alle bestehenden Integrations-Keys werden unbrauchbar und müssen von den Nutzern neu eingetragen werden.

**Why this priority**: Die Startmeldung aus Story 2 deckt den Notfall ab. Die README macht das Vorgehen planbar und erklärt die Folgen, bevor ein Host den Schlüssel wechselt.

**Independent Test**: Eine Person ohne Vorwissen richtet allein anhand der README eine Instanz mit gültigem Schlüssel ein und kann danach erklären, was beim Rotieren passiert.

**Acceptance Scenarios**:

1. **Given** die README, **When** ein Host den Abschnitt zur Schlüsselverwaltung liest, **Then** findet er einen Befehl oder ein Verfahren zum Erzeugen eines gültigen Schlüssels und den Namen der Umgebungsvariable.
2. **Given** die README, **When** ein Host einen Schlüsselwechsel plant, **Then** wird ihm erklärt, dass bestehende Integrations-Keys danach neu hinterlegt werden müssen, und dass der Schlüssel gesichert werden sollte.
3. **Given** die Beispiel-Konfigurationsdatei des Projekts, **When** ein Host sie als Vorlage nutzt, **Then** enthält sie die neue Variable mit einem Hinweis, aber keinen verwendbaren echten Schlüssel.

---

### User Story 6 - Pull Requests werden automatisch geprüft (Priority: P3)

Ein Mitwirkender öffnet einen Pull Request oder aktualisiert ihn. Ohne manuelles Zutun laufen automatische Prüfungen, und das Ergebnis erscheint direkt am Pull Request. Schlägt eine Prüfung fehl, ist das vor dem Merge sichtbar.

**Why this priority**: Die CI sichert die neue Funktion und künftige Änderungen dagegen ab, dass sie unbemerkt wieder Klartext-Keys einführen oder bestehende Funktionen brechen. Für die Sicherheit der laufenden Installationen ist sie aber nicht direkt nötig.

**Independent Test**: Einen Pull Request mit absichtlich fehlschlagendem Test öffnen; das Ergebnis muss als fehlgeschlagen angezeigt werden. Danach einen Pull Request ohne Fehler öffnen; das Ergebnis muss als erfolgreich angezeigt werden.

**Acceptance Scenarios**:

1. **Given** ein neuer oder aktualisierter Pull Request, **When** er eingereicht wird, **Then** starten die automatischen Prüfungen ohne manuelles Zutun.
2. **Given** ein Pull Request mit einem fehlschlagenden Test oder Stilverstoß, **When** die Prüfungen abgeschlossen sind, **Then** wird er am Pull Request als fehlgeschlagen markiert, mit einem Verweis auf die Ursache.
3. **Given** die Prüfungen laufen, **When** sie ausgeführt werden, **Then** brauchen sie weder echte Provider- noch Mealie-Zugangsdaten und keine Secrets des Repositorys. Dadurch funktionieren sie auch für Pull Requests aus Forks.
4. **Given** die automatisierten Tests zur Verschlüsselung aus dieser Spezifikation, **When** die Prüfungen laufen, **Then** sind sie Teil der Prüfungen.

---

### Edge Cases

- **Schlüssel gültig, aber anders als zuvor**: Beim Start lässt sich nicht erkennen, ob ein formal gültiger Schlüssel zu den gespeicherten Einträgen passt. Die Anwendung startet daher normal, und der Fehler zeigt sich erst beim Zugriff auf einen einzelnen Eintrag (Story 4).
- **Unterscheidung Klartext vs. verschlüsselt**: Ein Legacy-Klartext-Key darf nicht als „mit falschem Schlüssel verschlüsselt“ fehlinterpretiert werden und umgekehrt. Verschlüsselte Werte müssen eindeutig als solche erkennbar sein.
- **Gleichzeitige Erstzugriffe**: Greifen zwei Anfragen gleichzeitig auf denselben Klartext-Eintrag zu, darf er nicht doppelt verschlüsselt oder beschädigt werden.
- **Migration schlägt fehl**: Kann ein Klartext-Eintrag zwar gelesen, aber nicht verschlüsselt zurückgeschrieben werden, wird die aktuelle Anfrage trotzdem bedient. Der Eintrag bleibt unverändert und wird beim nächsten Zugriff erneut migriert.
- **Leerer oder nur aus Leerzeichen bestehender Key**: Wird wie bisher bei der Eingabe abgewiesen und nie gespeichert.
- **Schlüssel mit Leerzeichen oder Anführungszeichen in der `.env`**: Die vorgeschlagene Zeile ist so formatiert, dass sie unverändert übernommen funktioniert.
- **Vorgeschlagener Schlüssel im Container-Log**: Der Vorschlag aus der Startmeldung landet zwangsläufig in der Startausgabe (siehe Annahmen). Der tatsächlich aktive Schlüssel erscheint nie in einer Ausgabe.
- **Fehler- und Ausnahmeberichte**: Auch Stacktraces, Debug-Ausgaben und Daten, die an ein optionales externes Monitoring gehen, enthalten keine Klartext-Keys.
- **Löschen einer Integration**: Funktioniert auch dann, wenn der Eintrag nicht mehr entschlüsselbar ist.

## Requirements *(mandatory)*

### Functional Requirements

**Verschlüsselung at rest**

- **FR-001**: Das System MUSS jeden Integrations-Key symmetrisch verschlüsselt speichern, beim Anlegen wie beim Aktualisieren. Der Klartext darf zu keinem Zeitpunkt dauerhaft gespeichert werden.
- **FR-002**: Das System DARF einen Integrations-Key nur entschlüsseln, wenn er für die Kommunikation mit dem jeweiligen Dienst gebraucht wird. Der entschlüsselte Wert darf nicht über diesen Vorgang hinaus aufbewahrt werden.
- **FR-003**: Die Verschlüsselung MUSS an einer zentralen Stelle gekapselt sein und für jeden gespeicherten Integrations-Key unabhängig vom Dienst gelten. Eine neue Integration darf keinen eigenen Verschlüsselungscode brauchen.
- **FR-004**: Verschlüsselte Werte MÜSSEN eindeutig von Legacy-Klartext-Werten unterscheidbar sein.
- **FR-005**: Integrations-Keys DÜRFEN weder im Klartext noch verschlüsselt in einer API-Antwort erscheinen.
- **FR-006**: Klartext-Keys und der aktive Schlüssel DÜRFEN in keinem Log erscheinen, auch nicht in Fehlermeldungen, Stacktraces, Debug-Ausgaben oder an externe Monitoring-Dienste übermittelten Daten.

**Schlüsselbereitstellung und Startprüfung**

- **FR-007**: Der Schlüssel MUSS ausschließlich über eine Umgebungsvariable bereitgestellt werden. Er DARF weder in der Datenbank noch im Repository abgelegt werden. Das Repository enthält keinen echten Schlüssel, auch nicht als Standardwert.
- **FR-008**: Das System MUSS beim Start, bevor es Anfragen annimmt, prüfen, ob ein Schlüssel gesetzt ist und ein gültiges Format hat.
- **FR-009**: Fehlt der Schlüssel oder ist er ungültig, MUSS das System sofort mit einem Fehler beenden und DARF keinen Betrieb aufnehmen, auch nicht eingeschränkt oder mit einem Ersatzschlüssel.
- **FR-010**: Die Fehlermeldung aus FR-009 MUSS enthalten: (a) die Ursache (fehlt / ungültig), ohne einen vorhandenen ungültigen Wert auszugeben; (b) einen bei jedem Start neu erzeugten gültigen Schlüssel; (c) eine Zeile, die unverändert in die `.env` übernommen werden kann; (d) den Hinweis, dass bei Verlust des Schlüssels alle gespeicherten Integrations-Keys unbrauchbar werden und neu hinterlegt werden müssen.

**Migration bestehender Daten**

- **FR-011**: Das System MUSS Legacy-Klartext-Einträge beim ersten Zugriff erkennen, für die laufende Anfrage korrekt verwenden und verschlüsselt zurückschreiben, ohne dass Nutzer oder Host etwas tun müssen.
- **FR-012**: Die Migration MUSS idempotent sein: Ein bereits verschlüsselter Eintrag wird nie erneut verschlüsselt, und gleichzeitige Zugriffe dürfen keinen Eintrag beschädigen.
- **FR-013**: Zusätzlich zur Migration beim ersten Zugriff MUSS das System beim Start alle verbleibenden Klartext-Einträge einmalig in die verschlüsselte Form überführen, damit auch Einträge inaktiver Nutzer nicht im Klartext bleiben. Scheitert die Migration einzelner Einträge, startet die Anwendung trotzdem; die betroffenen Einträge werden beim nächsten Zugriff oder Start erneut migriert, und der Host erhält einen Logeintrag ohne sensible Werte.

**Fehlerbehandlung**

- **FR-014**: Kann ein einzelner Eintrag nicht entschlüsselt werden, MUSS das System dem betroffenen Nutzer eine verständliche Meldung zeigen, dass er seine Zugangsdaten für diese Integration neu hinterlegen muss. Die Anwendung bleibt für diesen und alle anderen Nutzer funktionsfähig.
- **FR-015**: Ein Nutzer MUSS einen nicht entschlüsselbaren Eintrag durch erneutes Speichern ersetzen oder ihn löschen können.
- **FR-016**: Entschlüsselungsfehler MÜSSEN protokolliert werden, und zwar nur mit nicht-sensiblen Angaben (z. B. Nutzer-ID, Integration, Fehlerart), damit der Host das Problem erkennt.

**Dokumentation**

- **FR-017**: Die README MUSS beschreiben, wie ein gültiger Schlüssel erzeugt und hinterlegt wird, welche Umgebungsvariable gilt, dass der Schlüssel gesichert werden sollte und was beim Rotieren passiert (bestehende Integrations-Keys müssen neu hinterlegt werden).
- **FR-018**: Die Beispiel-Konfigurationsdatei des Projekts MUSS die neue Umgebungsvariable mit einem erklärenden Kommentar und einem Platzhalter enthalten, der beim Start als ungültig abgewiesen wird.
- **FR-019**: Die Aussage „encrypted API keys“ in der README MUSS nach Umsetzung zutreffen und präzisiert werden (welche Daten verschlüsselt sind).

**CI für Pull Requests**

- **FR-020**: Bei jedem neuen oder aktualisierten Pull Request MÜSSEN automatisch Prüfungen laufen, deren Ergebnis am Pull Request sichtbar ist.
- **FR-021**: Die Prüfungen MÜSSEN mindestens umfassen: die automatisierten Backend-Tests, die keine externen Dienste brauchen (inklusive der neuen Tests zu dieser Funktion), die Stil- und Lint-Prüfungen für Backend und Frontend sowie die Typ- und Build-Prüfung des Frontends. Tests mit echten LLM-Providern, Mealie-Instanzen oder Modell-Evaluierung sind ausgenommen.
- **FR-022**: Die Prüfungen DÜRFEN keine Secrets des Repositorys und keine echten Zugangsdaten brauchen.
- **FR-023**: Schlägt eine Prüfung fehl, MUSS der Pull Request als fehlgeschlagen markiert werden, mit einem nachvollziehbaren Hinweis auf die Ursache.

### Key Entities

- **Integrations-Zugangsdaten**: Gehören zu genau einem Nutzer und einer Integration (z. B. Mealie). Enthalten Basis-URL, den geheimen Key (nur verschlüsselt gespeichert), einen Aktiv-Status und Zeitstempel. Pro Nutzer und Integration gibt es höchstens einen Eintrag. Die Basis-URL gilt nicht als geheim und bleibt unverschlüsselt.
- **Verschlüsselungsschlüssel**: Ein einzelner, instanzweiter symmetrischer Schlüssel, den der Host verwaltet. Existiert nur in der Umgebung des laufenden Prozesses. Sein Verlust macht alle damit verschlüsselten Integrations-Keys unbrauchbar.
- **Legacy-Eintrag**: Integrations-Zugangsdaten aus einer älteren Installation, deren Key noch im Klartext vorliegt. Ein Übergangszustand, der durch die Migration aufgelöst wird.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Nach dem Speichern über die Oberfläche stimmt in 100 % der Fälle kein in der Datenbank gespeicherter Integrations-Key mit dem eingegebenen Klartext überein und enthält ihn auch nicht.
- **SC-002**: In 100 % der getesteten Startversuche ohne oder mit ungültigem Schlüssel nimmt die Anwendung keinen Betrieb auf. Ein Host bringt sie in unter 2 Minuten zum Laufen, allein indem er die vorgeschlagene Zeile übernimmt und neu startet.
- **SC-003**: Nach dem Update einer bestehenden Installation brauchen Nutzer 0 manuelle Schritte, damit ihre Integration weiter funktioniert, und nach dem ersten erfolgreichen Start liegen 0 Integrations-Keys im Klartext in der Datenbank.
- **SC-004**: Nach einem Schlüsselwechsel bleibt die Anwendung für alle Nutzer erreichbar, und ein betroffener Nutzer stellt seine Integration in unter 2 Minuten durch Neueintragen wieder her.
- **SC-005**: Wird bei einem vollständigen Testlauf ein bekannter Test-Key verwendet, taucht er 0-mal in API-Antworten und 0-mal in der gesamten Log-Ausgabe auf.
- **SC-006**: 100 % der Pull Requests erhalten automatisch ein Prüfergebnis, im Regelfall innerhalb von 10 Minuten nach dem Einreichen.
- **SC-007**: Eine Person ohne Vorwissen kann allein anhand der README einen gültigen Schlüssel erzeugen und die Instanz starten.

## Clarifications

### Session 2026-10-02

- Q: Wann werden Legacy-Klartext-Einträge migriert? → A: Beim ersten Zugriff und zusätzlich einmalig beim Start für alle verbleibenden Klartext-Einträge (FR-013).
- Q: Welchen Umfang hat die PR-CI? → A: Standardumfang laut FR-021: Backend-Unit-Tests ohne externe Dienste, Lint für Backend und Frontend, Typ- und Build-Prüfung des Frontends; keine Secrets, kein Image-Build.

## Assumptions

- Es gibt genau einen aktiven Schlüssel pro Instanz. Mehrere gleichzeitig gültige Schlüssel (für eine nahtlose Rotation) und ein Werkzeug zum Umschlüsseln bestehender Einträge sind nicht Teil dieser Funktion. Rotieren heißt: Die Nutzer tragen ihre Zugangsdaten neu ein.
- Der in der Startmeldung vorgeschlagene Schlüssel erscheint zwangsläufig in der Startausgabe (und damit gegebenenfalls in Container-Logs). Das ist gewollt. Das Log-Verbot aus FR-006 gilt für den tatsächlich aktiven Schlüssel und für Integrations-Keys. Die README weist darauf hin, dass ein Schlüssel alternativ selbst erzeugt werden kann.
- Nur der geheime Key wird verschlüsselt. Basis-URL, Dienstname und Metadaten bleiben unverschlüsselt, damit Übersichten weiterhin ohne Entschlüsselung funktionieren.
- Host-weite Secrets in der Umgebung (LLM-Provider-Keys, Datenbankzugang, JWT-Secret) sind nicht Teil dieser Funktion.
- Die bestehende Oberfläche zum Hinterlegen von Zugangsdaten bleibt unverändert, abgesehen von der neuen Fehlermeldung bei nicht entschlüsselbaren Einträgen.
- Die CI ergänzt den bestehenden Release-Workflow (Image-Build bei Releases) und ersetzt ihn nicht. Dass ein Merge bei fehlgeschlagener CI blockiert wird, richtet der Repository-Besitzer über die Einstellungen der Plattform ein; das ist nicht Teil der Pipeline selbst.
- Die vorhandenen Integrations- und Modell-Evaluierungstests brauchen echte Dienste oder Zugangsdaten und sind deshalb von der PR-CI ausgenommen.
