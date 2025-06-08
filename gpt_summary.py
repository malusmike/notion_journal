import openai
import os
from datetime import datetime

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
    # Nur eindeutige PARA-Elemente, keine leeren Strings
    involved_projects = list(set(p for p in linked_projects if p.strip()))
    involved_areas = list(set(a for a in linked_areas if a.strip()))
    all_para = involved_projects + involved_areas

    # Nur verwendete Tags/Kategorien
    used_tags = list(set(t for t in tags_and_categories if t.strip()))

    prompt = f"""
Zusammenfassung für den {date_str}:

I. Neu erstellte Aufgaben: {len(new_tasks)}
II. Erstellte Notizen: {len(new_notes)}
III. Bearbeitete Aufgaben: {len(edited_tasks)}
IV. Bearbeitete Notizen: {len(edited_notes)}
V. Neue Inbox-Tasks (Status ≠ Done, ohne Projekt/Bereich): {len(inbox_tasks)}

🧠 Bewertung:

1. Welche übergeordneten Projekte oder Bereiche (PARA) waren über verknüpfte Tasks oder Notizen beteiligt?
   - Relevante Verknüpfungen: {all_para}

2. Welche thematischen Schwerpunkte lassen sich aus Tags oder Kategorien ableiten?
   - Relevante Tags/Kategorien: {used_tags}

3. Welche Learnings, Trends oder Empfehlungen lassen sich aus den heutigen Aktivitäten ableiten?
   - Aussagen zu Fokus, Effizienz, Tool-Nutzung, thematischer Häufung etc.

❗️Wichtige Stilregeln:
- Keine Auflistung einzelner Task-/Notiztitel
- Wichtig sind thematische Schwerpunkte (Tags), PARA-Elemente (Projekte/Bereiche) und Inbox-Größe
- Gib eine interpretierende, kompakte Zusammenfassung im Fließtext
"""

    response = client.chat.completions.create(
        model="gpt-4",
        temperature=0.4,
        messages=[
            {"role": "system", "content": "Du bist ein strukturierter Projektassistenz-KI, spezialisiert auf Tagesrückblicke nach PARA-Methode."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()