import os
from datetime import datetime
from openai import OpenAI

DEBUG_LOG_FILE = "gpt_summary_debug.txt"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def log_debug(text):
    with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {text}\n")

def filter_by_last_edited_time(items, date_str):
    from datetime import timezone, timedelta
    target = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    next_day = target + timedelta(days=1)
    return [item for item in items if target <= datetime.fromisoformat(item.get("last_edited_time", "").replace("Z", "+00:00")) < next_day]

def filter_inbox_tasks(tasks):
    inbox = []
    for task in tasks:
        props = task.get("properties", {})
        status = props.get("Status", {}).get("status", {}).get("name", "")
        has_project = props.get("Projects", {}).get("relation", [])
        has_area = props.get("Areas/Resources", {}).get("relation", [])
        if status != "Done" and not has_project and not has_area:
            inbox.append(task)
    return inbox

def extract_linked_projects_and_areas(items):
    projects, areas = set(), set()
    for item in items:
        props = item.get("properties", {})
        for rel_key, target_set in [("Projects", projects), ("Areas/Resources", areas)]:
            for rel in props.get(rel_key, {}).get("relation", []):
                name = rel.get("name") or rel.get("id")
                if name:
                    target_set.add(name)
    return sorted(projects), sorted(areas)

def extract_tags_and_categories(items):
    labels = set()
    for item in items:
        props = item.get("properties", {})
        for key in ["Tags", "Kategorie"]:
            for tag in props.get(key, {}).get("multi_select", []):
                if "name" in tag:
                    labels.add(tag["name"])
    return sorted(labels)

def generate_gpt_summary(date_str, new_tasks, new_notes, all_tasks, all_notes):
    edited_tasks = filter_by_last_edited_time(all_tasks, date_str)
    edited_notes = filter_by_last_edited_time(all_notes, date_str)
    inbox_tasks = filter_inbox_tasks(all_tasks)
    relevant_items = new_tasks + new_notes + edited_tasks + edited_notes
    linked_projects, linked_areas = extract_linked_projects_and_areas(relevant_items)
    tags_and_categories = extract_tags_and_categories(relevant_items)

    prompt = f'''
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
- Für erstellte oder bearbeitete Aufgaben, Notizen reicht mir die Anzahl
- Die Anzahl der Inbox-Tasks ist mir wichtig, da ich nach PARA arbeite
- Keine Auflistung einzelner Task- oder Notiztitel! nur zählen für I.,II. bis V.)
- Gib eine kompakte, interpretierende Zusammenfassung.
- Struktur: Einleitung (2 Sätze), Thematische Schwerpunkte, Beteiligte PARA-Elemente, Learnings & Empfehlungen.
- Sprich im Fließtext oder klar gegliederten Absätzen.
- Keine Füllwörter
'''

log_debug("📨 GPT Prompt:\n" + prompt)

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=900
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        log_debug(f"❌ GPT Fehler: {str(e)}")
        return "GPT-Zusammenfassung konnte nicht erstellt werden."