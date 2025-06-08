import os
from datetime import datetime, timezone, timedelta
from openai import OpenAI

DEBUG_LOG_FILE = "gpt_summary_debug.txt"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def log_debug(text):
    with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {text}\n")

def filter_by_last_edited_time(items, date_str):
    target = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    next_day = target + timedelta(days=1)
    filtered = []
    for item in items:
        edited_raw = item.get("last_edited_time")
        if edited_raw:
            edited = datetime.fromisoformat(edited_raw.replace("Z", "+00:00"))
            if target <= edited < next_day:
                filtered.append(item)
    log_debug(f"🧠 Tasks/Notes edited on {date_str}: {len(filtered)}")
    return filtered

def extract_linked_projects_and_areas(items):
    project_ids = set()
    area_ids = set()
    for item in items:
        props = item.get("properties", {})
        if "Projects" in props:
            relations = props["Projects"].get("relation", [])
            for r in relations:
                project_ids.add(r.get("id"))
        if "Areas/Resources" in props:
            relations = props["Areas/Resources"].get("relation", [])
            for r in relations:
                area_ids.add(r.get("id"))
    return list(project_ids), list(area_ids)

def extract_tags_and_categories(items):
    all_tags = set()
    for item in items:
        props = item.get("properties", {})
        for key in ["Tags", "Kategorie"]:
            values = props.get(key, {}).get("multi_select", [])
            for tag in values:
                all_tags.add(tag.get("name", ""))
    return list(all_tags)

def filter_inbox_tasks(tasks):
    inbox = []
    for item in tasks:
        props = item.get("properties", {})
        status = props.get("Status", {}).get("select", {}).get("name", "")
        projects = props.get("Projects", {}).get("relation", [])
        areas = props.get("Areas/Resources", {}).get("relation", [])
        if status != "Done" and not projects and not areas:
            inbox.append(item)
    log_debug(f"📥 Inbox tasks identified: {len(inbox)}")
    return inbox

def generate_gpt_summary(date_str, new_tasks, new_notes, all_tasks, all_notes):
    edited_tasks = filter_by_last_edited_time(all_tasks, date_str)
    edited_notes = filter_by_last_edited_time(all_notes, date_str)
    inbox_tasks = filter_inbox_tasks(all_tasks)

    relevant_items = new_tasks + new_notes + edited_tasks + edited_notes
    linked_projects, linked_areas = extract_linked_projects_and_areas(relevant_items)
    tags_and_categories = extract_tags_and_categories(relevant_items)

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
- Für erstellte oder bearbeitete Aufgaben, Notizen reicht mir die Anzahl
- Die Anzahl der Inbox-Tasks ist mir wichtig, da ich nach Para arbeite
- Keine Auflistung einzelner Task- oder Notiztitel! nur zählen für I.,II. bis V.)
- Gib eine kompakte, interpretierende Zusammenfassung.
- Struktur: Einleitung (2 Sätze), Thematische Schwerpunkte, Beteiligte PARA-Elemente, Learnings & Empfehlungen.
- Sprich im Fließtext oder klar gegliederten Absätzen.
- keine füllwörter
"""

    log_debug("📤 Prompt an GPT:")
    log_debug(prompt)

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=800,
        )
        result = response.choices[0].message.content.strip()
        log_debug("📥 GPT Response:")
        log_debug(result)
        return result
    except Exception as e:
        log_debug(f"❌ GPT Fehler: {str(e)}")
        return "GPT-Zusammenfassung konnte nicht erstellt werden."