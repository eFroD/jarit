# Feature Specification: Sprache pro Nutzer für Oberfläche und Rezepte

**Feature Branch**: `feature/003-user-language` (from `dev` at `b148fd1`)

**Created**: 2026-10-02

**Status**: Draft

**Input**: User description: "we need a language that is set to the user. it defines the app language and the default selected language for the recipes instead of english as default"

## Kontext

JarIt ist eine self-hosted Anwendung, die Rezepte aus Social-Media-Videos extrahiert und nach Mealie hochlädt. Ein Host betreibt eine Instanz für mehrere Nutzer. Heute ist die Oberfläche durchgehend englisch, und beim Einreichen einer Extraktion ist als Zielsprache des Rezepts immer „English“ vorausgewählt. Wer seine Rezepte z. B. auf Deutsch haben will, muss die Sprache bei jeder Extraktion von Hand umstellen, und wer kein Englisch spricht, kommt mit der Oberfläche schlecht zurecht.

Die Funktion gibt jedem Nutzer eine eigene, dauerhaft gespeicherte Sprache. Sie bestimmt zwei Dinge: die Sprache der Oberfläche und die vorausgewählte Zielsprache neuer Extraktionen.

## Clarifications

### Session 2026-10-02

- Q: Welche Sprachen soll die App anbieten? → A: Alle fünf heutigen Rezeptsprachen: Englisch, Deutsch, Spanisch, Französisch, Italienisch. Die Oberfläche wird für alle fünf lokalisiert.
- Q: Wie hängen App-Sprache und Rezeptsprache zusammen? → A: Rezeptinhalte werden bei der Extraktion in die gewählte Zielsprache übersetzt. Die App-Sprache des Nutzers ist dabei nur vorausgewählt; der Nutzer kann pro Extraktion jede unterstützte Sprache wählen.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rezepte standardmäßig in der eigenen Sprache (Priority: P1)

Ein Nutzer legt in seinen Einstellungen fest, dass seine Sprache Deutsch ist. Wenn er danach eine Video-URL zur Extraktion einreicht, ist als Zielsprache bereits Deutsch vorausgewählt. Er kann für einzelne Extraktionen weiterhin eine andere Sprache wählen.

**Why this priority**: Das ist der direkteste Nutzen: Der Nutzer spart sich bei jeder Extraktion das Umstellen und vermeidet versehentlich englische Rezepte.

**Independent Test**: Sprache eines Nutzers auf Deutsch setzen, das Formular zum Einreichen öffnen und prüfen, dass Deutsch vorausgewählt ist. Eine Extraktion ohne Änderung einreichen und prüfen, dass der Job die Zielsprache Deutsch trägt.

**Acceptance Scenarios**:

1. **Given** ein Nutzer mit der Sprache Deutsch, **When** er das Formular zum Einreichen öffnet, **Then** ist Deutsch als Zielsprache vorausgewählt.
2. **Given** ein Nutzer mit der Sprache Deutsch, **When** er für eine Extraktion Italienisch auswählt und einreicht, **Then** wird diese Extraktion auf Italienisch durchgeführt, und seine gespeicherte Sprache bleibt Deutsch.
3. **Given** ein Nutzer mit der Sprache Deutsch, **When** er eine Extraktion einreicht, ohne eine Zielsprache anzugeben (z. B. direkt über die Schnittstelle), **Then** wird Deutsch verwendet statt Englisch.
4. **Given** ein Nutzer ändert seine Sprache, **When** er danach das Formular öffnet, **Then** ist die neue Sprache vorausgewählt; bereits eingereichte oder abgeschlossene Extraktionen behalten ihre ursprüngliche Zielsprache.

---

### User Story 2 - Oberfläche in der eigenen Sprache (Priority: P1)

Ein angemeldeter Nutzer sieht alle Texte der Oberfläche (Navigation, Formulare, Statusanzeigen, Fehlermeldungen, Bestätigungen) in seiner Sprache. Ändert er die Sprache, wechselt die Oberfläche sofort, ohne dass er sich neu anmelden muss.

**Why this priority**: Gleichwertig mit Story 1 Teil des Wunsches; eine Anwendung, die Rezepte auf Deutsch liefert, aber nur englisch bedienbar ist, ist für nicht englischsprachige Nutzer kaum nutzbar.

**Independent Test**: Sprache auf Deutsch setzen und alle Seiten (Dashboard, Fortschritt, Editor, Historie, Einstellungen, Admin) durchgehen; kein englischer Oberflächentext darf übrig bleiben. Danach zurück auf Englisch stellen und dasselbe prüfen.

**Acceptance Scenarios**:

1. **Given** ein angemeldeter Nutzer mit der Sprache Deutsch, **When** er eine beliebige Seite der Anwendung öffnet, **Then** sind alle Oberflächentexte deutsch.
2. **Given** ein angemeldeter Nutzer, **When** er seine Sprache in den Einstellungen ändert, **Then** wechselt die Oberfläche ohne Neuladen und ohne erneute Anmeldung in die neue Sprache.
3. **Given** ein Nutzer hat seine Sprache auf einem Gerät geändert, **When** er sich auf einem anderen Gerät oder in einem anderen Browser anmeldet, **Then** erscheint die Oberfläche in der gespeicherten Sprache.
4. **Given** die Oberfläche ist auf Deutsch, **When** eine Extraktion fehlschlägt, **Then** ist auch die Fehlermeldung zum Fehlergrund deutsch.
5. **Given** die Oberfläche ist auf Deutsch, **When** Datums- und Zeitangaben angezeigt werden (z. B. in der Historie), **Then** folgen sie der deutschen Schreibweise.

---

### User Story 3 - Sinnvolle Sprache ab dem ersten Besuch (Priority: P2)

Ein neuer Besucher sieht Anmelde- und Registrierungsseite in der Sprache seines Browsers, sofern diese unterstützt wird. Bei der Registrierung ist diese Sprache als Sprache des neuen Kontos vorausgewählt und kann geändert werden.

**Why this priority**: Verbessert den ersten Eindruck, ist aber nicht nötig, damit Story 1 und 2 funktionieren; ohne sie startet jedes Konto mit Englisch und der Nutzer stellt einmal um.

**Independent Test**: Browser auf Deutsch stellen, Anmeldeseite öffnen und prüfen, dass sie deutsch ist. Ein Konto registrieren, ohne die Sprache zu ändern, und prüfen, dass das Konto die Sprache Deutsch hat.

**Acceptance Scenarios**:

1. **Given** ein nicht angemeldeter Besucher mit deutscher Browsersprache, **When** er die Anmelde- oder Registrierungsseite öffnet, **Then** ist sie deutsch.
2. **Given** ein Besucher mit einer nicht unterstützten Browsersprache, **When** er die Anmeldeseite öffnet, **Then** ist sie englisch.
3. **Given** ein Besucher registriert sich mit deutscher Browsersprache und ändert die vorausgewählte Sprache nicht, **When** die Registrierung abgeschlossen ist, **Then** hat sein Konto die Sprache Deutsch.
4. **Given** ein Nutzer mit gespeicherter Sprache Englisch und deutscher Browsersprache, **When** er sich anmeldet, **Then** gilt nach der Anmeldung die gespeicherte Sprache Englisch, nicht die Browsersprache.

---

### Edge Cases

- **Bestehende Konten**: Alle Konten, die vor dieser Funktion angelegt wurden, erhalten die Sprache Englisch. Für sie ändert sich nichts, bis sie selbst umstellen.
- **Nicht unterstützte Sprache**: Versucht ein Client, eine nicht unterstützte Sprache als Nutzersprache zu speichern, wird das mit einer verständlichen Meldung abgelehnt, und die bisherige Sprache bleibt.
- **Speichern schlägt fehl**: Kann die Sprachänderung nicht gespeichert werden (z. B. Netzwerkfehler), sieht der Nutzer eine Fehlermeldung, und Oberfläche und Vorauswahl bleiben bei der bisher gespeicherten Sprache.
- **Laufende Extraktion beim Sprachwechsel**: Ein Sprachwechsel ändert weder die Zielsprache laufender noch abgeschlossener Extraktionen; nur die Oberflächentexte der Fortschrittsseite wechseln.
- **Mehrere offene Tabs**: Ändert der Nutzer die Sprache in einem Tab, darf ein anderer Tab bis zum nächsten Neuladen in der alten Sprache bleiben; nach dem Neuladen gilt die gespeicherte Sprache.
- **Rezeptinhalte vs. Oberfläche**: Rezeptinhalte folgen der Zielsprache der jeweiligen Extraktion, nicht der aktuellen Oberflächensprache. Ein auf Italienisch extrahiertes Rezept bleibt im Editor italienisch, auch wenn die Oberfläche deutsch ist. Video-URLs und von Mealie gelieferte Texte werden nicht übersetzt.
- **Admin-Ansicht**: Die Admin-Verwaltung folgt der Sprache des angemeldeten Admins, nicht der Sprache der angezeigten Nutzer.

## Requirements *(mandatory)*

### Functional Requirements

**Nutzersprache**

- **FR-001**: Jedes Konto MUSS genau eine Sprache haben, die dauerhaft gespeichert wird und geräteübergreifend gilt.
- **FR-002**: Die unterstützten Sprachen MÜSSEN Englisch, Deutsch, Spanisch, Französisch und Italienisch sein. Dieselbe Liste gilt für die Nutzersprache, die Oberfläche und die Auswahl der Zielsprache.
- **FR-003**: Ein angemeldeter Nutzer MUSS seine Sprache in seinen Einstellungen jederzeit ändern können.
- **FR-004**: Das System MUSS das Speichern einer nicht unterstützten Sprache ablehnen und die bisherige Sprache behalten.
- **FR-005**: Ein Nutzer DARF nur seine eigene Sprache ändern können.
- **FR-006**: Konten, die vor Einführung dieser Funktion existieren, MÜSSEN die Sprache Englisch erhalten.

**Zielsprache der Rezepte**

- **FR-007**: Beim Einreichen einer Extraktion MUSS die Sprache des Nutzers als Zielsprache vorausgewählt sein.
- **FR-008**: Der Nutzer MUSS die Zielsprache für eine einzelne Extraktion abweichend wählen können, ohne dass sich dadurch seine gespeicherte Sprache ändert.
- **FR-008a**: Das extrahierte Rezept (Titel, Beschreibung, Zutaten, Schritte) MUSS in der gewählten Zielsprache vorliegen, auch wenn das Video in einer anderen Sprache ist.
- **FR-009**: Wird eine Extraktion ohne Zielsprache eingereicht, MUSS das System die Sprache des Nutzers verwenden statt Englisch.
- **FR-010**: Eine Änderung der Nutzersprache DARF die Zielsprache bereits angelegter Extraktionen NICHT ändern.

**Sprache der Oberfläche**

- **FR-011**: Nach der Anmeldung MÜSSEN alle Oberflächentexte in der Sprache des Nutzers erscheinen: Navigation, Überschriften, Beschriftungen, Schaltflächen, Hinweise, Statusbezeichnungen, Fehlermeldungen und Bestätigungsdialoge.
- **FR-012**: Fehlermeldungen, die dem Nutzer angezeigt werden (Fehlergründe fehlgeschlagener Extraktionen, Validierungsfehler, Berechtigungsfehler), MÜSSEN in seiner Sprache erscheinen.
- **FR-013**: Datums- und Zeitangaben MÜSSEN in der Schreibweise der Nutzersprache angezeigt werden.
- **FR-014**: Nach einer Sprachänderung MUSS die Oberfläche ohne erneute Anmeldung in der neuen Sprache erscheinen.
- **FR-015**: Für jeden Oberflächentext, zu dem in einer unterstützten Sprache keine Übersetzung vorliegt, MUSS der englische Text angezeigt werden statt eines leeren oder technischen Platzhalters.

**Vor der Anmeldung**

- **FR-016**: Anmelde- und Registrierungsseite MÜSSEN in der bevorzugten Sprache des Browsers erscheinen, sofern sie unterstützt wird, sonst auf Englisch.
- **FR-017**: Bei der Registrierung MUSS die Sprache des neuen Kontos wählbar sein; vorausgewählt ist die Sprache, in der die Registrierungsseite angezeigt wird.
- **FR-018**: Nach der Anmeldung MUSS die gespeicherte Sprache des Kontos Vorrang vor der Browsersprache haben.

**Qualität**

- **FR-019**: Die bestehende CI mit mindestens 80 Prozent Testabdeckung MUSS erfüllt bleiben.
- **FR-020**: Die CI MUSS fehlschlagen, wenn in einer unterstützten Sprache ein Oberflächentext fehlt, der auf Englisch vorhanden ist.

### Key Entities

- **Nutzer (erweitert)**: Erhält das Attribut *Sprache*, eine der unterstützten Sprachen. Pflichtangabe, Standard Englisch.
- **Unterstützte Sprache**: Eindeutiger Code, Anzeigename in der eigenen Sprache (z. B. „Deutsch“, „Français“). Dient gleichzeitig als Oberflächensprache und als wählbare Zielsprache der Extraktion.
- **Extraktion (unverändert)**: Speichert weiterhin ihre eigene Zielsprache zum Zeitpunkt des Einreichens; sie wird nicht nachträglich an die Nutzersprache angepasst.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Ein Nutzer mit einer anderen Sprache als Englisch kann eine Extraktion in seiner Sprache mit null zusätzlichen Auswahlschritten einreichen (nur URL eingeben und absenden).
- **SC-002**: Nach dem Umstellen der Sprache auf Deutsch enthält keine Seite der Anwendung im angemeldeten Zustand mehr englische Oberflächentexte (Rezeptinhalte ausgenommen).
- **SC-003**: Ein Sprachwechsel ist in unter 1 Sekunde auf der aktuellen Seite sichtbar.
- **SC-004**: 100 Prozent der bestehenden Konten können nach dem Update ohne Änderung weiterarbeiten; Oberfläche und Vorauswahl verhalten sich für sie wie vorher.
- **SC-005**: Für jede unterstützte Sprache sind 100 Prozent der englischen Oberflächentexte übersetzt (durch die CI geprüft).

## Assumptions

- Die Sprache steht nur dem Nutzer selbst zur Verfügung; Admins setzen die Sprache anderer Nutzer nicht (bewusst außerhalb des Umfangs).
- Rezeptinhalte werden bei der Extraktion in die Zielsprache übersetzt. Ein bereits extrahiertes Rezept wird nicht nachträglich in eine andere Sprache übersetzt; wer es in einer anderen Sprache will, reicht die Extraktion mit dieser Zielsprache erneut ein.
- Die Sprache, in der Rezepte nach Mealie hochgeladen werden, ist die Zielsprache der jeweiligen Extraktion; Mealie selbst wird nicht umkonfiguriert.
- Rechts-nach-links-Sprachen sind nicht Teil dieser Funktion.
- Die Einstellung liegt im bestehenden Einstellungsbereich des Dashboards neben der Mealie-Konfiguration.
- Texte, die der Server nur für Protokolle erzeugt, bleiben englisch; dem Nutzer angezeigte Meldungen werden über bekannte Fehlergründe bzw. Codes in der Oberfläche übersetzt.
- Ein Sprachwechsel in einem Tab muss andere offene Tabs nicht sofort aktualisieren.
