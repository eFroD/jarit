# Feature Specification: Dev-Images nach jedem Merge auf `dev`

**Feature Branch**: `feature/004-dev-image-builds` (from `dev` at `4ea078e`, noch nicht angelegt)

**Created**: 2026-10-03

**Status**: Draft

**Input**: User description: "we already have a release in place and a ci/cd for our releases. could we have the same for our dev branch so that a :dev tag is built after a merge on dev so that one could check it on a machine? is this common?"

## Kontext

JarIt wird als zwei Container-Images (Backend und Frontend) für amd64 und arm64 veröffentlicht. Heute entstehen veröffentlichte Images nur, wenn ein Release angelegt wird; dann werden Versions-Tags (z. B. `1.2.0`, `1.2`) und `latest` gesetzt. Zusätzlich baut ein wöchentlicher Lauf das Backend-Image des letzten Releases mit dem neuesten yt-dlp neu. Pull Requests gegen `dev` und `main` werden geprüft und die Images testweise gebaut, aber nicht veröffentlicht.

Wer den Stand von `dev` auf einer echten Maschine (z. B. einem Raspberry Pi oder dem Heimserver) ausprobieren will, muss die Images heute selbst lokal bauen. Das ist langsam, auf arm64-Geräten besonders, und der getestete Stand ist nicht eindeutig einem Commit zuzuordnen.

Ein fortlaufend aktualisierter Vorab-Kanal (`dev`, `edge`, `nightly` o. ä.) neben den stabilen Release-Tags ist bei Projekten, die Container-Images veröffentlichen, gängige Praxis.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Aktuellen `dev`-Stand auf einer Maschine starten (Priority: P1)

Ein Maintainer merged einen Pull Request nach `dev`. Ohne weiteres Zutun entstehen kurz danach neue Backend- und Frontend-Images unter dem Tag `dev`. Auf einer Testmaschine stellt der Maintainer in der bestehenden Compose-Konfiguration den Tag von `latest` auf `dev` um, zieht die Images und startet sie. Die Maschine läuft jetzt mit genau dem Stand, der auf `dev` liegt, ohne dass lokal gebaut werden musste.

**Why this priority**: Das ist der eigentliche Wunsch: einen Merge auf `dev` auf echter Hardware prüfen, bevor er in ein Release geht.

**Independent Test**: Einen kleinen, sichtbaren Change nach `dev` mergen, abwarten, bis der Build fertig ist, auf einer Maschine die `dev`-Images ziehen und prüfen, dass der Change sichtbar ist.

**Acceptance Scenarios**:

1. **Given** ein Pull Request wird nach `dev` gemerged, **When** der Merge abgeschlossen ist, **Then** werden ohne manuellen Schritt neue Backend- und Frontend-Images gebaut und unter dem Tag `dev` veröffentlicht.
2. **Given** neue `dev`-Images sind veröffentlicht, **When** eine amd64- oder arm64-Maschine die `dev`-Images zieht, **Then** erhält sie jeweils die passende Architektur und die Anwendung startet mit dem Stand des Merge-Commits.
3. **Given** `dev`-Images wurden veröffentlicht, **When** jemand die Tags `latest` oder eine Versionsnummer zieht, **Then** erhält er weiterhin unverändert den letzten Release-Stand.

---

### User Story 2 - Getesteten Stand eindeutig zuordnen und festhalten (Priority: P2)

Ein Maintainer findet beim Testen einen Fehler und will wissen, welcher Commit auf der Maschine läuft, oder will bei einem bestimmten `dev`-Stand bleiben, während weitere Merges folgen. Jeder Dev-Build ist deshalb zusätzlich unter einem unveränderlichen Tag veröffentlicht, der den Commit benennt, und die Images tragen den Commit als Metadaten.

**Why this priority**: Der Tag `dev` wandert mit jedem Merge weiter. Ohne festen Bezug lässt sich ein Fehler schlecht einem Stand zuordnen, und man kann nicht gezielt bei einem Stand bleiben.

**Independent Test**: Zwei Merges nacheinander durchführen; prüfen, dass `dev` auf den zweiten zeigt, der erste aber über seinen Commit-Tag weiterhin ziehbar ist, und dass sich der Commit aus einem laufenden Image auslesen lässt.

**Acceptance Scenarios**:

1. **Given** ein Dev-Build ist veröffentlicht, **When** man die Tags des Images ansieht, **Then** gibt es neben `dev` einen Tag, der den Merge-Commit eindeutig benennt.
2. **Given** nach einem Dev-Build folgt ein weiterer Merge, **When** dessen Build fertig ist, **Then** zeigt `dev` auf den neuen Stand und der Commit-Tag des vorherigen Builds zeigt unverändert auf den alten.
3. **Given** ein Dev-Image läuft auf einer Maschine, **When** man die Metadaten des Images abfragt, **Then** sind Quell-Commit und Build-Zeitpunkt ablesbar.

---

### User Story 3 - Dev-Kanal ist dokumentiert, inklusive Risiken (Priority: P3)

Jemand, der JarIt betreibt, liest in der README, dass es neben den Release-Tags einen `dev`-Kanal gibt, wie man ihn auf einer Maschine nutzt, wie man wieder auf `latest` zurückwechselt und welche Risiken das hat, insbesondere bei Datenbankmigrationen.

**Why this priority**: Der Kanal funktioniert auch ohne Doku, aber ohne den Hinweis auf Migrationen kann ein Betreiber mit echten Daten eine Datenbank erzeugen, die das letzte Release nicht mehr versteht.

**Independent Test**: Nur anhand der README eine Maschine von `latest` auf `dev` und zurück umstellen; der Abschnitt nennt das Migrationsrisiko und eine Empfehlung (eigene Testdatenbank oder vorheriges Backup).

**Acceptance Scenarios**:

1. **Given** die README, **When** ein Betreiber den Dev-Kanal nutzen will, **Then** findet er die Tag-Namen, die Umstellung von `latest` auf `dev` und zurück und den Hinweis, dass `dev` nicht für den produktiven Einsatz gedacht ist.
2. **Given** die README, **When** ein Betreiber vom Dev-Kanal zurück auf `latest` wechseln will, **Then** wird er darauf hingewiesen, dass Datenbankänderungen aus `dev` nicht automatisch zurückgenommen werden, und wie er sich davor schützt.

---

### Edge Cases

- **Mehrere Merges kurz hintereinander**: Ein älterer, noch laufender Build darf `dev` nicht nach einem neueren überschreiben. Ein überholter Build wird abgebrochen oder verworfen; `dev` zeigt am Ende immer auf den neuesten Merge.
- **Build schlägt fehl**: `dev` zeigt weiterhin auf den letzten erfolgreichen Stand; es werden keine halb veröffentlichten Images (z. B. nur Backend oder nur eine Architektur) unter `dev` sichtbar. Der Fehlschlag ist für Maintainer in der üblichen Übersicht der automatisierten Läufe erkennbar.
- **Direkter Push auf `dev` statt Merge**: Wird wie ein Merge behandelt; maßgeblich ist, dass sich der Stand von `dev` geändert hat.
- **Änderungen, die die Anwendung nicht betreffen** (z. B. nur Specs oder Doku): Ein Build darf trotzdem laufen; das Ergebnis ist inhaltlich gleich und schadet nicht.
- **Wöchentlicher yt-dlp-Refresh**: Betrifft nur Release-Images und lässt `dev` und die Dev-Commit-Tags unberührt. Dev-Images enthalten das zum Build-Zeitpunkt neueste yt-dlp.
- **Release-Lauf und Dev-Lauf gleichzeitig**: Beide stören sich nicht; ein Dev-Build setzt nie `latest` oder Versions-Tags, ein Release-Build nie `dev`.
- **Migrationen auf einer Maschine mit echten Daten**: Ein Dev-Stand kann das Datenbankschema weiterentwickeln; ein späterer Wechsel zurück auf `latest` ist dann eventuell nicht ohne Wiederherstellung möglich (siehe User Story 3).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Jede Änderung am Branch `dev` (Merge oder direkter Push) MUSS automatisch einen Build von Backend- und Frontend-Image auslösen.
- **FR-002**: Ein erfolgreicher Dev-Build MUSS beide Images unter dem Tag `dev` in derselben Registry und unter denselben Image-Namen wie die Release-Images veröffentlichen.
- **FR-003**: Dev-Images MÜSSEN für dieselben Architekturen wie die Release-Images bereitstehen (amd64 und arm64).
- **FR-004**: Jeder Dev-Build MUSS zusätzlich einen unveränderlichen Tag erhalten, der den Merge-Commit eindeutig benennt (z. B. `dev-<kurzer Commit-Hash>`).
- **FR-005**: Dev-Images MÜSSEN den Quell-Commit und den Build-Zeitpunkt als auslesbare Image-Metadaten tragen.
- **FR-006**: Ein Dev-Build DARF die Tags `latest`, Versions-Tags (`X.Y.Z`, `X.Y`) und den Build-Cache der Releases NICHT verändern oder verdrängen.
- **FR-007**: `dev` MUSS nach einer Folge von Merges immer auf den neuesten erfolgreich gebauten Stand zeigen; ein überholter Build DARF `dev` nicht nachträglich auf einen älteren Stand setzen.
- **FR-008**: Schlägt ein Dev-Build fehl, MUSS `dev` auf dem letzten erfolgreichen Stand bleiben, und `dev` DARF nicht auf einen unvollständigen Satz (ein Image fehlt oder eine Architektur fehlt) zeigen.
- **FR-009**: Maintainer MÜSSEN einen Dev-Build für den aktuellen Stand von `dev` auch manuell auslösen können (z. B. nach einem fehlgeschlagenen Lauf).
- **FR-010**: Die README MUSS den Dev-Kanal beschreiben: Tag-Namen, Umstellen einer bestehenden Installation auf `dev` und zurück auf `latest`, Hinweis auf fehlende Stabilität und auf das Migrationsrisiko samt Empfehlung (Backup oder separate Datenbank).
- **FR-011**: Die bestehende Prüfung von Pull Requests und der bestehende Release-Ablauf MÜSSEN unverändert weiter funktionieren.

### Key Entities

- **Dev-Kanal-Tag (`dev`)**: Wandernder Tag je Image, zeigt immer auf den neuesten erfolgreichen Build von `dev`.
- **Dev-Commit-Tag**: Unveränderlicher Tag je Build, benennt den Merge-Commit; erlaubt es, bei einem Stand zu bleiben oder einen Fehler zuzuordnen.
- **Release-Tags (`latest`, `X.Y.Z`, `X.Y`)**: Bestehende Tags; vom Dev-Kanal unabhängig und von ihm unberührt.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Nach einem Merge auf `dev` sind neue `dev`-Images für beide Architekturen in höchstens 30 Minuten ohne manuellen Schritt ziehbar.
- **SC-002**: Ein Maintainer kann eine bestehende Installation in unter 5 Minuten von `latest` auf `dev` umstellen, ohne lokal zu bauen, nur mit den Schritten aus der README.
- **SC-003**: In 100 % der Fälle lässt sich für ein laufendes Dev-Image der zugehörige Commit ermitteln.
- **SC-004**: Über die ersten 10 Merges auf `dev` hinweg bleiben `latest` und die Versions-Tags unverändert (gleicher Inhalt wie vor den Merges, abgesehen vom wöchentlichen yt-dlp-Refresh).
- **SC-005**: Bei zwei Merges innerhalb weniger Minuten zeigt `dev` nach Abschluss aller Läufe auf den zweiten Merge.

## Assumptions

- Pull Requests nach `dev` durchlaufen die bestehende Prüfung (Lint, Tests, Image-Build), bevor sie gemerged werden. Der Dev-Build führt die Tests deshalb nicht erneut aus, sondern baut und veröffentlicht nur.
- Dev-Images liegen in derselben Registry wie die Release-Images und haben dieselbe Sichtbarkeit (öffentlich). Ein separater, privater Ablageort ist nicht vorgesehen.
- Das Aufräumen alter Dev-Commit-Tags ist nicht Teil dieses Features; bei der zu erwartenden Merge-Frequenz ist der Speicherbedarf unkritisch. Ein Aufräumen kann später ergänzt werden.
- Automatisches Ausrollen auf eine Testmaschine (z. B. per Watchtower oder SSH-Deploy) ist nicht Teil des Features; die Maschine zieht die Images selbst.
- Ein Anzeigen von Version oder Commit in der Anwendungsoberfläche ist nicht Teil des Features; die Zuordnung erfolgt über Tags und Image-Metadaten.
- Builds für andere Branches als `dev` (z. B. Feature-Branches oder Pull Requests) werden nicht veröffentlicht.
- Release-Images entstehen weiterhin nur über ein Release; `main` erhält keinen eigenen wandernden Tag.
