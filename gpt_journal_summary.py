import os
import requests
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv

# 🔐 ENV laden
if os.path.exists(".env"):
    load_dotenv()

NOTION_TOKEN    = os.getenv("NOTION_TOKEN")
DB_JOURNAL      = os.getenv("DB_JOURNAL")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

client = OpenAI(api_key=OPENAI_API_KEY)

def get_latest_journal_entry():
    url = f"https://api.notion.com/v1/databases/{DB_JOURNAL}/query"
    payload = {
        "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}],
        "page_size": 1
    }
    res = requests.post(url, json=payload, headers=HEADERS)
    res.raise_for_status()
    results = res.json().get("results", [])
    return results[0] if results else None

def extract_rollup_text(entry, property_name):
    prop = entry.get("properties", {}).get(property_name, {})
    prop_type = prop.get("type")

    if prop_type == "rich_text":
        return " ".join([rt.get("text", {}).get("content", "") for rt in prop.get("rich_text", [])])
    elif prop_type == "rollup":
        rollup = prop.get("rollup", {})
        if rollup.get("type") == "rich_text":
            return " ".join([rt.get("text", {}).get("content", "") for rt in rollup.get("rich_text", [])])
        elif rollup.get("type") == "number":
            return str(rollup.get("number", ""))
    elif prop_type == "formula":
        formula = prop.get("formula", {})
        return str(formula.get(formula.get("type"), ""))
    return ""

def generate_prompt(entry, date_str):
    def get(name): return extract_rollup_text(entry, name)

    return f"""
Du bist ein Assistent der für die Notion-Umgebung nach PARA (Forte), der für ein tägliches Journal eine thematische Zusammenfassung erstellt.  
Nutze die folgenden Inhalte des Journal-Eintrags vom {date_str}, um eine **konkrete, knappe und inhaltlich strukturierte Zusammenfassung** in ICH-Form zu schreiben.

### Aufgaben:
{get("textTasks")}

### Notizen:
{get("textNotes")}

### Projekte:
{get("textProjects")}

### Bereiche / Ressourcen:
{get("textAreas")}

### Kategorien aus Tasks:
{get("textKategorienTasks")}

### Kategorien aus Notizen:
{get("textKategorienNotes")}

### Tags / Typen aus Notizen:
{get("textTagsNotes")}, {get("textTypNotes")}

### Beschreibung Projekte:
{get("textProjectDescription")}

### Beschreibung Areas:
{get("textAreasDescription")}

---  
Verfasse nun eine strukturierte Zusammenfassung als Micro-Content mit kleiner 2000 zeichen mit folgenden Schwerpunkten:
1. Woran wurde inhaltlich gearbeitet?
2. Gab es erkennbare Schwerpunkte oder Prioritäten (nach Themen, PARA-Typen)? 
3. Welche Learnings, Trends, Empfehlungen lassich sich ableiten - basierend auf die SChwerpunkte, welche trendige Topics in den Fachbereichen mit Relevanz seiner Aktiväten könnte für den Nutzer künftig interessant sein?
4. Kein Bullet-Point-Stil, keine Füllwörter – schreibe fließend, max. 4 Absätze. 
5. Verzichte auf Füllwörter

WICHTIG: Der fertige Text darf niemals mehr als 1999 Zeichen (inklusive Leerzeichen) enthalten. Diese Grenze ist strikt einzuhalten, da der Text sonst nicht gespeichert werden kann. Überschreite diese Grenze unter keinen Umständen – kürze gegebenenfalls ab.

Beginne jetzt mit der Zusammenfassung.
""".strip()

def update_summary(entry_id, summary_text):
    # Kürzen, wenn nötig
    if len(summary_text) > 1990:
        summary_text = summary_text[:1987].rstrip() + "..."

    url = f"https://api.notion.com/v1/pages/{entry_id}"
    payload = {
        "properties": {
            "Summary": {
                "rich_text": [{
                    "text": {"content": summary_text}
                }]
            }
        }
    }
    res = requests.patch(url, json=payload, headers=HEADERS)
    if res.status_code != 200:
        print("❌ Fehler beim Schreiben in Notion:")
        print("Status:", res.status_code)
        print("Response:", res.text)
        res.raise_for_status()
    print("✅ Zusammenfassung in Notion gespeichert.")

def backup_to_txt(content, filename="gpt_output_backup.txt"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"💾 Backup gespeichert unter {filename}")

def main():
    entry = get_latest_journal_entry()
    if not entry:
        print("❌ Kein Journaleintrag gefunden.")
        return

    date_str = entry["properties"].get("Date", {}).get("date", {}).get("start", "Kein Datum")
    entry_id = entry["id"]
    prompt = generate_prompt(entry, date_str)

    print("📨 Sende Prompt an GPT...\n")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Du bist ein effizienter Schreiber für Tagesjournale."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,
        max_tokens=490
    )

    summary = response.choices[0].message.content.strip()
    print(f"\n🧠 GPT-Antwort ({len(summary)} Zeichen):\n{summary}")

    backup_to_txt(summary)
    update_summary(entry_id, summary)

if __name__ == "__main__":
    main()
