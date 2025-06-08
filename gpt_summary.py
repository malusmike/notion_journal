from openai import OpenAI
from datetime import datetime, timedelta, timezone

client = OpenAI()

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
    prompt = f"""Fasse die Arbeitsaktivität vom {date_str} zusammen:

🔧 Neu erstellte Aufgaben: {len(tasks_created)}
🗒️ Erstellte Notizen: {len(notes_created)}
🛠️ Bearbeitete Aufgaben (last edited): {len(tasks_edited)}
📁 Bearbeitete Projekte (last edited): {len(projects_edited)}
🏷️ Bearbeitete Areas/Resources (last edited): {len(areas_edited)}

Bewerte:
- Welche Projekte oder Bereiche waren über verknüpfte Tasks/Notizen beteiligt? Wo lag der Schwerpunkt? Gab es thematische Schwerpunkte, z. B. durch Tags, Titel oder Kategorien?
- Welche Learnings, Trends oder Empfehlungen lassen sich ableiten?

Antwort in strukturierter Form mit Abschnitten:
I. Neu erstellte Aufgaben
II. Erstellte Notizen
III. Gestern bearbeitete Aufgaben
IV. Gestern bearbeitete Projekte
V. Gestern bearbeitete Areas/Resources
VI. Inbox-Tasks (optional)
VII. Learnings/Empfehlungen
"""


    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=800
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"GPT-Zusammenfassung konnte nicht erstellt werden. Fehler: {str(e)}"