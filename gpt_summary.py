import os
from datetime import datetime
from openai import OpenAI

DEBUG_LOG_FILE = "gpt_summary_debug.txt"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def log_debug(text):
    with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {text}\n")

def generate_gpt_summary(
    date_str,
    new_tasks,
    new_notes,
    edited_tasks,
    edited_notes,
    inbox_tasks,
    linked_projects,
    linked_areas,
    tags_and_categories
):
    log_debug("📊 Anzahl Tasks/Notes/Inbox:")
    log_debug(f"- Neu erstellte Tasks: {len(new_tasks)}")
    log_debug(f"- Erstellte Notizen: {len(new_notes)}")
    log_debug(f"- Bearbeitete Tasks: {len(edited_tasks)}")
    log_debug(f"- Bearbeitete Notizen: {len(edited_notes)}")
    log_debug(f"- Inbox Tasks: {len(inbox_tasks)}")

    log_debug("🔗 Verlinkte Projekte:")
    log_debug(str(linked_projects))

    log_debug("🔗 Verlinkte Areas:")
    log_debug(str(linked_areas))

    log_debug("🏷 Tags und Kategorien:")
    log_debug(str(tags_and_categories))

    prompt = f"""
Zusammenfassung für den {date_str}:

I. Neu erstellte Aufgaben: {len(new_tasks)}
II. Erstellte Notizen: {len(new_notes)}
III. Bearbeitete Aufgaben: {len(edited_tasks)}
IV. Bearbeitete Notizen: {len(edited_notes)}
V. Neue Inbox-Tasks (ohne Projekt oder Bereich): {len(inbox_tasks)}

🧠 Bewertung:

1. Welche übergeordneten Projekte oder Bereiche (PARA) waren über verknüpfte Tasks oder Notizen beteiligt?
   - Berücksichtige in deiner Antwort die Inhalte aus diesen Verlinkungen:
     {linked_projects + linked_areas}

2. Welche thematischen Schwerpunkte lassen sich aus Tags oder Kategorien ableiten?
   - Nutze dazu folgende Labels (Mehrfachauswahl möglich):
     {tags_and_categories}

3. Welche Learnings, Trends oder Empfehlungen lassen sich aus den heutigen Aktivitäten ableiten?
   - Denkbar wären Aussagen zu Fokus, Effizienz, Zeitmanagement, Tool-Nutzung, thematische Häufung etc.

❗️Wichtige Stilregeln:
- Am wichtigsten sind mir thematische Schwerpunkte nach Labels, Projekten, Bereichen
- Für erstellte oder bearbeitete Aufgaben, Notizen reicht mir die Anzahl (und ich sehe die information neben deiner Summary, kann diese bei BEdarf anklicken)
- Die Anzahl der Inbox-Tasks ist mir sehr wichtig, da ich nach Para arbeite
- Keine Auflistung einzelner Task- oder Notiztitel! nur zählen für I.,II. bis V.)
- Gib eine kompakte, interpretierende Zusammenfassung.
- Struktur: Einleitung (2 Sätze), Thematische Schwerpunkte, Beteiligte PARA-Elemente, Learnings & Empfehlungen.
- Sprich im Fließtext oder klar gegliederten Absätzen.
- keine füllwörter,
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=800,
        )
        summary = response.choices[0].message.content.strip()
        log_debug("✅ GPT-Antwort erhalten:")
        log_debug(summary)
        return summary
    except Exception as e:
        log_debug(f"❌ GPT-Fehler: {str(e)}")
        return "GPT-Zusammenfassung konnte nicht erstellt werden."
