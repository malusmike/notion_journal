
import os
from datetime import datetime
from notion_client import Client
from openai import OpenAI
import time

notion = Client(auth=os.getenv("NOTION_TOKEN"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

JOURNAL_DB_ID = os.getenv("JOURNAL_DB_ID")

def get_journal_entry_for_date(date_str):
    response = notion.databases.query(
        **{
            "database_id": JOURNAL_DB_ID,
            "filter": {
                "property": "Date",
                "date": {
                    "equals": date_str
                }
            }
        }
    )
    results = response.get("results", [])
    return results[0] if results else None

def extract_rollup_text(entry, key):
    prop = entry["properties"].get(key)
    if prop and prop["type"] in ["rollup", "rich_text", "multi_select", "number"]:
        if prop["type"] == "rollup":
            return ", ".join([e["plain_text"] for e in prop["rollup"]["array"] if e["type"] == "text"])
        elif prop["type"] == "multi_select":
            return ", ".join([e["name"] for e in prop["multi_select"]])
        elif prop["type"] == "number":
            return str(prop["number"])
        else:
            return "".join([e["plain_text"] for e in prop["rich_text"]])
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
    notion.pages.update(
        page_id=entry_id,
        properties={
            "Summary": {
                "rich_text": [{"type": "text", "text": {"content": summary_text}}]
            }
        }
    )

def main():
    date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    entry = get_journal_entry_for_date(date_str)
    if not entry:
        print("⚠️ Kein Journal-Eintrag für das Datum gefunden.")
        return

    prompt = generate_prompt(entry, date_str)
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Du bist ein professioneller Assistent, der Arbeitstage zusammenfasst."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4
    )
    summary_text = response.choices[0].message.content.strip()
    update_summary(entry["id"], summary_text)
    print("✅ GPT-Zusammenfassung aktualisiert.")

if __name__ == "__main__":
    from datetime import timedelta
    time.sleep(5)  # Sicherheitspuffer
    main()
