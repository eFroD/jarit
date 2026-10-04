# Feature Specification: Neuere Reasoning-Modelle für die Extraktion nutzbar machen

**Feature Branch**: `feature/005-reasoning-effort-compat` (from `dev` at `51c7170`)

**Created**: 2026-10-04

**Status**: Draft

**Input**: User description: "check the newest dev branch (pull) we added some changes and time has passed, so new models have been released. on my dev deployment i tested gpt-6-luna and it failed because of reasoning effort. […] pydantic_ai.exceptions.ModelHTTPError: status_code: 400, model_name: gpt-6-luna, body: {'message': \"Function tools with reasoning_effort are not supported for gpt-6-luna in /v1/chat/completions. To use function tools, use /v1/responses or set reasoning_effort to 'none'.\", 'type': 'invalid_request_error', 'param': 'reasoning_effort', 'code': None} […] we may need handling for that"

## Kontext

JarIt extrahiert Rezepte aus Videos mit einem Sprachmodell, das bei Bedarf zwei Werkzeuge aufruft (Videobeschreibung laden, Audio transkribieren). Welches Modell verwendet wird, legt der Betreiber über `LLM_PROVIDER` und `MODEL_NAME` fest; unterstützt sind `openai`, `google` und `ollama`. Weitere Modell-Einstellungen gibt es heute nicht, nur eine feste Temperatur.

Seit der letzten Anpassung sind neue OpenAI-Modelle erschienen. Ein Test auf dem Dev-Deployment mit `gpt-6-luna` scheitert bei jeder Extraktion: OpenAI lehnt die Anfrage mit HTTP 400 ab, weil dieses Modell auf der von JarIt genutzten Schnittstelle (Chat Completions) Werkzeugaufrufe nur ohne Reasoning erlaubt. JarIt setzt den Reasoning-Aufwand nicht selbst, das Modell nimmt also seinen eigenen Standardwert, und die Kombination aus diesem Standard und Werkzeugaufrufen wird abgewiesen. Die Fehlermeldung nennt zwei Auswege: die neuere Responses-Schnittstelle nutzen oder Reasoning abschalten.

Für den Nutzer endet der Job als „Fehler des Sprachmodells“, ohne Hinweis, dass die Ursache eine Konfigurationsfrage ist. Der Betreiber findet die Ursache nur im Stacktrace.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rezept mit einem aktuellen OpenAI-Reasoning-Modell extrahieren (Priority: P1)

Ein Betreiber stellt `MODEL_NAME` auf ein aktuelles OpenAI-Modell wie `gpt-6-luna` um und startet JarIt neu. Ein Nutzer reicht einen Video-Link ein. Die Extraktion läuft wie mit den bisherigen Modellen durch, einschließlich der Werkzeugaufrufe für Beschreibung und Transkript, und liefert ein Rezept.

**Why this priority**: Das ist der gemeldete Fehler. Ohne diese Story ist das Modell in JarIt unbrauchbar, und weitere neue Modelle werden auf dieselbe Weise scheitern.

**Independent Test**: Auf einer Instanz mit `LLM_PROVIDER=openai` und `MODEL_NAME=gpt-6-luna` einen Video-Link einreichen, dessen Beschreibung kein vollständiges Rezept enthält, und prüfen, dass der Job erfolgreich mit einem Rezept endet und dabei beide Werkzeuge genutzt wurden.

**Acceptance Scenarios**:

1. **Given** JarIt ist mit `gpt-6-luna` konfiguriert und sonst ohne weitere Modell-Einstellungen, **When** ein Nutzer einen Video-Link mit Rezept einreicht, **Then** endet der Job erfolgreich mit einem Rezept, ohne dass OpenAI die Anfrage abweist.
2. **Given** dieselbe Konfiguration, **When** die Videobeschreibung allein nicht genügt, **Then** ruft das Modell zusätzlich die Transkription auf, und das Rezept enthält Informationen aus dem Transkript.
3. **Given** JarIt ist mit einem älteren OpenAI-Modell konfiguriert, das bisher funktioniert hat (z. B. `gpt-4.1-mini`), **When** ein Nutzer einen Video-Link einreicht, **Then** funktioniert die Extraktion unverändert.

---

### User Story 2 - Reasoning-Aufwand als Betreiber einstellen (Priority: P2)

Ein Betreiber möchte Kosten und Dauer der Extraktion steuern: bei einem Reasoning-Modell weniger oder mehr „Nachdenken“ erlauben oder Reasoning ganz abschalten. Er setzt dazu eine optionale Einstellung in seiner Umgebungskonfiguration. Ist sie nicht gesetzt, gilt ein Standard, der mit allen unterstützten Modellen funktioniert.

**Why this priority**: Nicht zwingend, um das gemeldete Problem zu beheben, aber die naheliegende Stellschraube, sobald JarIt Reasoning-Modelle bewusst unterstützt. Ohne sie bleibt nur der Modellwechsel.

**Independent Test**: Die Einstellung nacheinander auf „aus“ und auf eine höhere Stufe setzen, jeweils dasselbe Video extrahieren und in der Beobachtbarkeit (Logs bzw. Tracing) prüfen, dass der eingestellte Aufwand an das Modell übergeben wurde und beide Läufe ein Rezept liefern.

**Acceptance Scenarios**:

1. **Given** die Einstellung ist nicht gesetzt, **When** JarIt startet, **Then** wird kein Reasoning-Aufwand erzwungen und das Verhalten entspricht User Story 1.
2. **Given** die Einstellung ist auf einen gültigen Wert gesetzt und ein Reasoning-Modell ist konfiguriert, **When** eine Extraktion läuft, **Then** wird dieser Aufwand verwendet.
3. **Given** die Einstellung ist auf einen ungültigen Wert gesetzt (z. B. ein Tippfehler), **When** JarIt startet, **Then** bricht der Start mit einer Meldung ab, die den Wert und die zulässigen Werte nennt.
4. **Given** die Einstellung ist gesetzt, aber der Provider ist `google` oder `ollama` bzw. das Modell unterstützt kein Reasoning, **When** eine Extraktion läuft, **Then** scheitert sie nicht an dieser Einstellung.

---

### User Story 3 - Inkompatible Modellkonfiguration verständlich erkennen (Priority: P3)

Ein Betreiber stellt ein Modell ein, das JarIt nicht bedienen kann, etwa weil der Anbieter eine Parameterkombination ablehnt oder das Modell keine Werkzeugaufrufe beherrscht. Statt eines Stacktraces findet er im Log eine knappe Meldung, dass die Modellkonfiguration abgelehnt wurde, mit Modellname und der Begründung des Anbieters. Der Nutzer sieht weiterhin nur, dass die Extraktion am Sprachmodell gescheitert ist.

**Why this priority**: Verkürzt die Fehlersuche beim nächsten neuen Modell, behebt aber selbst nichts.

**Independent Test**: Ein Modell konfigurieren, das der Anbieter für Werkzeugaufrufe ablehnt, eine Extraktion starten und prüfen, dass das Log eine einzeilige, eindeutig als Konfigurationsproblem erkennbare Meldung mit Modellname und Anbietergrund enthält.

**Acceptance Scenarios**:

1. **Given** der Anbieter lehnt eine Anfrage wegen ungültiger Parameter ab (HTTP 400), **When** der Job scheitert, **Then** enthält das Log eine Meldung mit Modellname, Provider und der Begründung des Anbieters, die sich klar von vorübergehenden Fehlern (Netzwerk, Rate-Limit, Zeitüberschreitung) unterscheidet.
2. **Given** derselbe Fall, **When** der Nutzer den Job ansieht, **Then** wird der Job wie bisher als Sprachmodell-Fehler angezeigt, ohne interne Details des Anbieters.

---

### Edge Cases

- Ein OpenAI-Modell ganz ohne Reasoning (ältere GPT-4-Generation) erhält keinen Reasoning-Parameter, den es ablehnen würde.
- Reasoning-Modelle, die eine vom Standard abweichende Temperatur ablehnen: Die feste Temperatur darf die Extraktion nicht zum Scheitern bringen.
- `LLM_PROVIDER=ollama` spricht weiterhin die OpenAI-kompatible Schnittstelle von Ollama an, die nur Chat Completions kennt; diese Konfiguration darf durch die Änderung nicht brechen.
- Die Einstellung aus User Story 2 ist gesetzt, der Provider ist aber `google`: Sie wird ignoriert oder sinngemäß übertragen, führt aber nicht zu einem Fehler.
- Die Extraktion mit Reasoning dauert spürbar länger: Sie muss innerhalb der bestehenden Job-Zeitüberschreitung bleiben oder als `TIMEOUT` enden, nicht hängen bleiben.
- Strukturierte Ausgabe (Rezept-Schema) muss mit Reasoning-Modellen weiterhin gültig zurückkommen; ein ungültiges Ergebnis wird wie bisher behandelt.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Mit `LLM_PROVIDER=openai` MUSS die Extraktion mit aktuellen OpenAI-Reasoning-Modellen (mindestens `gpt-6-luna`) einschließlich Werkzeugaufrufen erfolgreich laufen, ohne dass der Betreiber zusätzliche Einstellungen setzen muss.
- **FR-002**: Die Extraktion MUSS mit den bisher funktionierenden OpenAI-Modellen, mit `google` und mit `ollama` weiterhin unverändert funktionieren.
- **FR-003**: Reasoning MUSS bei Modellen, die es unterstützen, standardmäßig nutzbar bleiben; JarIt DARF NICHT als einzige Lösung Reasoning pauschal abschalten.
- **FR-004**: Betreiber MÜSSEN den Reasoning-Aufwand über eine optionale Umgebungseinstellung festlegen können, mindestens mit den Stufen „aus“, „niedrig“, „mittel“ und „hoch“. Ohne Einstellung gilt der Standard des Modells.
- **FR-005**: Ein ungültiger Wert für den Reasoning-Aufwand MUSS beim Start mit einer Meldung abgelehnt werden, die den Wert und die zulässigen Werte nennt.
- **FR-006**: Eine gesetzte Reasoning-Einstellung DARF bei Providern oder Modellen ohne Reasoning NICHT zum Scheitern der Extraktion führen.
- **FR-007**: Weist der Anbieter eine Anfrage wegen ungültiger Parameter oder einer nicht unterstützten Kombination ab, MUSS das Log eine knappe Meldung mit Provider, Modellname und Anbietergrund enthalten, die als Konfigurationsproblem erkennbar ist.
- **FR-008**: Nutzer sehen bei solchen Fehlern weiterhin nur den bestehenden Fehlergrund „Sprachmodell-Fehler“; Anbieterdetails verlassen das Log nicht.
- **FR-009**: Die neue Einstellung MUSS in `.env_example` und im README zusammen mit `LLM_PROVIDER` und `MODEL_NAME` dokumentiert sein, inklusive des Hinweises, welche Provider sie berücksichtigen.
- **FR-010**: Automatisierte Tests MÜSSEN abdecken, dass für OpenAI-Reasoning-Modelle eine Konfiguration entsteht, mit der Werkzeugaufrufe zulässig sind, und dass `ollama` und `google` unverändert konfiguriert werden.

### Key Entities

- **Modellkonfiguration**: Provider, Modellname, optionaler Reasoning-Aufwand und die übrigen Modell-Einstellungen (Temperatur). Wird beim Start aus der Umgebung gelesen und gilt für alle Extraktionen der Instanz.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Mit `gpt-6-luna` enden 10 von 10 Extraktionen eines Testsatzes von Rezeptvideos ohne Ablehnung durch den Anbieter; die gemeldete 400-Antwort tritt nicht mehr auf.
- **SC-002**: Mit den vor der Änderung genutzten Konfigurationen (ein älteres OpenAI-Modell, `gemini-2.5-flash`, ein Ollama-Modell) liefert derselbe Testsatz mindestens so viele erfolgreiche Extraktionen wie vorher.
- **SC-003**: Ein Betreiber kann den Reasoning-Aufwand allein durch eine Umgebungsvariable und einen Neustart ändern, ohne Code oder Image anzupassen.
- **SC-004**: Bei einer abgelehnten Modellkonfiguration erkennt ein Betreiber die Ursache aus einer einzigen Logzeile, ohne den Stacktrace lesen zu müssen.

## Assumptions

- Die Konfiguration bleibt instanzweit über Umgebungsvariablen; eine Modellauswahl pro Nutzer oder in der Oberfläche ist nicht Teil dieses Features.
- Welcher Weg die Kompatibilität herstellt (Wechsel der OpenAI-Schnittstelle, gezieltes Setzen des Reasoning-Parameters oder beides), wird in der Planung entschieden. Laut Fehlermeldung unterstützt OpenAI Werkzeugaufrufe mit Reasoning auf der neueren Schnittstelle; FR-003 bevorzugt diesen Weg gegenüber pauschalem Abschalten.
- Die eingesetzte Version der LLM-Bibliothek wird bei Bedarf aktualisiert, falls die aktuelle Version die nötigen Optionen nicht bietet.
- Für Google-Modelle wird kein eigener „Thinking“-Regler eingeführt; die Einstellung darf dort ignoriert werden. Eine sinngemäße Übertragung ist erlaubt, aber nicht gefordert.
- Automatisches Ausweichen auf ein anderes Modell oder ein Wiederholen mit anderen Parametern nach einer Ablehnung ist nicht Teil dieses Features.
- Die bestehenden Fehlergründe der Jobs (`LLM_ERROR` usw.) und ihre Übersetzungen bleiben unverändert.
