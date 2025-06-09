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
    prompt = f"""
    Zusammenfassung der Arbeitsaktivität am {date_str}:
nutze diese Informationen für den Eintrag: 
    📌 Projekte: {extract_rollup_text(entry, "Projects")}
    📌 Bereiche/Ressourcen: {extract_rollup_text(entry, "Areas/Resources")}

    🔖 Kategorien (Tasks): {extract_rollup_text(entry, "kategorien tasks")}
    🔖 Kategorien (Notes): {extract_rollup_text(entry, "kategorien notes")}
    🏷 Tags (Notes): {extract_rollup_text(entry, "notes-tags")}
    📂 Typen (Notes): {extract_rollup_text(entry, "notes-typ")}

    🧾 Beschreibung Projekte: {extract_rollup_text(entry, "Projectdescription")}
    🧾 Beschreibung Areas/Resources: {extract_rollup_text(entry, "Areasdescription")}
Der Eintrag im Feld Summary soll beinhalten: 
    ✅ Erledigte Tasks: {extract_rollup_text(entry, "Done")}% erledigt von der Gesamtanzahl dr relevanten für disen Tag. (ggf. aus dem %-Wert ableiten)

    ➤ Gib eine klare Zusammenfassung mit folgenden Schwerpunkten:
    - Woran wurde inhaltlich gearbeitet?
    - Gab es erkennbare thematische Häufungen?
    - Welche Learnings, Trends oder Empfehlungen lassen sich aus der Aktivität ableiten?
    - Gliedere in kurze Absätze, kein Bullet-Point-Stil.
    - Keine Wiederholung einzelner Titel, nur thematische Auswertung.
    """
    return prompt.strip()

def update_summary(entry_id, summary_text):
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
    res.raise_for_status()
    print("✅ Zusammenfassung in Notion gespeichert.")

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
        temperature=0.5
    )

    summary = response.choices[0].message.content.strip()
    print("\n🧠 GPT-Antwort:\n", summary)

    update_summary(entry_id, summary)

if __name__ == "__main__":
    main()
