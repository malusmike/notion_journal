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
    prompt = f"""Erstelle eine strukturierte Zusammenfassung der Arbeitsaktivität vom {date_str}.

I. Neu erstellte Aufgaben: {len(new_tasks)}
II. Erstellte Notizen: {len(new_notes)}
III. Bearbeitete Aufgaben: {len(edited_tasks)}
IV. Bearbeitete Notizen: {len(edited_notes)}
V. Tasks in der Inbox: {len(inbox_tasks)}

Thematischer Schwerpunkt:
Basierend auf den verlinkten Projekten und Bereichen zeigt sich ein Fokus auf folgende Themen:
Projekte: {[p for p in linked_projects] or 'Keine'}
Bereiche: {[a for a in linked_areas] or 'Keine'}

Zusätzlich vorhandene Tags/Kategorien:
{list(set(tags_and_categories)) or 'Keine'}

Formuliere auf dieser Grundlage Learnings und Empfehlungen:
- Was lässt sich aus den Themen ableiten? 
- Welche Empfehlungen ergeben sich aus der Struktur der Arbeit?
- Was sollte beibehalten oder verbessert werden?"""

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