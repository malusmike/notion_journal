import os
from datetime import datetime, timedelta, timezone
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_title(item):
    try:
        return item["properties"]["Name"]["title"][0]["text"]["content"]
    except (KeyError, IndexError, TypeError):
        return "(kein Titel)"

def extract_tags_and_categories(items):
    tags = []
    categories = []
    for item in items:
        props = item.get("properties", {})
        tags.extend([t["name"] for t in props.get("Tags", {}).get("multi_select", [])])
        categories.extend([c["name"] for c in props.get("Kategorie", {}).get("multi_select", [])])
    return list(set(tags)), list(set(categories))

def extract_linked_projects_and_areas(items):
    projects = []
    areas = []
    for item in items:
        props = item.get("properties", {})
        projects.extend([p["id"] for p in props.get("Projects", {}).get("relation", [])])
        areas.extend([a["id"] for a in props.get("Areas/Resources", {}).get("relation", [])])
    return list(set(projects)), list(set(areas))

def generate_gpt_summary(date_str, tasks_created, notes_created, tasks_edited, projects_linked, areas_linked, inbox_tasks):
    tags, categories = extract_tags_and_categories(tasks_created + notes_created + tasks_edited)
    all_projects = list(set(projects_linked))
    all_areas = list(set(areas_linked))

    prompt = f"""Fasse die Arbeitsaktivität vom {date_str} zusammen.

- Wieviele neue Tasks wurden erstellt? {len(tasks_created)}
- Wieviele bestehende Tasks wurden angesehen? {len(tasks_edited)}
- Wieviele Notizen wurden erstellt? {len(notes_created)}
- Thematische Schwerpunkte (Tags/Kategorien): {", ".join(tags + categories) if tags or categories else "Keine auffälligen Muster"}
- Beteiligte Projekte: {len(all_projects)}
- Beteiligte Bereiche/Ressourcen: {len(all_areas)}
- Inbox-Tasks (ohne Projekt und Bereich): {len(inbox_tasks)}

Welche Trends, Learnings oder Empfehlungen ergeben sich daraus?"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=700,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ GPT Fehler: {str(e)}"
