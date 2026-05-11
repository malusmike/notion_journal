import os
import requests
from openai import OpenAI
from dotenv import load_dotenv

# 🔐 ENV laden
if os.path.exists(".env"):
    load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DB_JOURNAL = os.getenv("DB_JOURNAL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not NOTION_TOKEN:
    raise ValueError("❌ NOTION_TOKEN fehlt in der .env Datei.")
if not DB_JOURNAL:
    raise ValueError("❌ DB_JOURNAL fehlt in der .env Datei.")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY fehlt in der .env Datei.")

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

    if not prop_type:
        return ""

    if prop_type == "rich_text":
        return " ".join(
            rt.get("plain_text", "") or rt.get("text", {}).get("content", "")
            for rt in prop.get("rich_text", [])
        ).strip()

    if prop_type == "title":
        return " ".join(
            t.get("plain_text", "") or t.get("text", {}).get("content", "")
            for t in prop.get("title", [])
        ).strip()

    if prop_type == "number":
        value = prop.get("number")
        return "" if value is None else str(value)

    if prop_type == "formula":
        formula = prop.get("formula", {})
        formula_type = formula.get("type")
        value = formula.get(formula_type)
        return "" if value is None else str(value)

    if prop_type == "rollup":
        rollup = prop.get("rollup", {})
        rollup_type = rollup.get("type")

        if rollup_type == "rich_text":
            return " ".join(
                rt.get("plain_text", "") or rt.get("text", {}).get("content", "")
                for rt in rollup.get("rich_text", [])
            ).strip()

        if rollup_type == "number":
            value = rollup.get("number")
            return "" if value is None else str(value)

        if rollup_type == "array":
            values = []
            for item in rollup.get("array", []):
                item_type = item.get("type")

                if item_type == "title":
                    values.extend(
                        t.get("plain_text", "") or t.get("text", {}).get("content", "")
                        for t in item.get("title", [])
                    )

                elif item_type == "rich_text":
                    values.extend(
                        rt.get("plain_text", "") or rt.get("text", {}).get("content", "")
                        for rt in item.get("rich_text", [])
                    )

                elif item_type == "number":
                    number_value = item.get("number")
                    if number_value is not None:
                        values.append(str(number_value))

                elif item_type == "select":
                    select_value = item.get("select")
                    if select_value:
                        values.append(select_value.get("name", ""))

                elif item_type == "multi_select":
                    values.extend(
                        option.get("name", "")
                        for option in item.get("multi_select", [])
                    )

                elif item_type == "formula":
                    formula = item.get("formula", {})
                    formula_type = formula.get("type")
                    formula_value = formula.get(formula_type)
                    if formula_value is not None:
                        values.append(str(formula_value))

            return "; ".join(v for v in values if v).strip()

    return ""


def generate_prompt(entry, date_str):
    def get(name):
        return extract_rollup_text(entry, name)

    return f"""
Du analysierst den Arbeitstag vom {date_str} wie ein persönlicher Chief of Staff.

Du verstehst:
- PARA nach Tiago Forte
- Wissensarbeit
- Produktentwicklung
- AI-gestützte Systeme
- strategische Priorisierung
- operative vs. strategische Arbeit
- Kontextwechsel
- Fokusmuster

Du bist KEIN Motivationscoach.
Du bist KEIN klassischer Journal-Assistent.
Du schreibst KEINEN netten Tagesrückblick.

Deine Aufgabe:
- tatsächliche Arbeitsschwerpunkte verdichten
- Muster zwischen Tasks, Notizen, Projekten und Areas erkennen
- operative, strategische und organisatorische Arbeit unterscheiden
- Kontextwechsel und Fragmentierung sichtbar machen
- PARA-Kontext intelligent interpretieren
- bei wenig Daten nüchtern bleiben

Sehr wichtig:
Wenn wenig Informationen vorhanden sind, erfinde keine Tiefe.
Dann schreibe präzise, dass der Tag nur schwache Signale enthält.
Keine künstlichen Learnings.
Keine künstliche Positivität.
Keine Wiederholung einzelner Tasktitel.
Keine Aufzählung aller Inhalte.
Keine statistische Roh-Zusammenfassung wie „1 Task, 1 Notiz“.
Keine Aussage über Trends, wenn nur ein einzelner Tag analysiert wird.

Vermeide Formulierungen wie:
- „Ich habe intensiv gearbeitet“
- „Ich habe gelernt“
- „Ein wichtiger Schritt war“
- „Dies zeigt, dass“
- „Für die Zukunft“
- „spannende Erkenntnisse“
- „wertvolle Einblicke“

Schreibstil:
- präzise
- analytisch
- nüchtern
- intelligent
- wie ein internes Executive Work Log
- maximal 3 kurze Absätze
- keine Bulletpoints
- keine Überschriften
- keine Einleitung
- keine Schlussformel
- maximal 1.800 Zeichen

DATEN DES JOURNAL-EINTRAGS:

TASKS:
{get("textTasks")}

NOTIZEN:
{get("textNotes")}

PROJEKTE:
{get("textProjects")}

AREAS / RESOURCES:
{get("textAreas")}

TASK-KATEGORIEN:
{get("textKategorienTasks")}

NOTIZ-KATEGORIEN:
{get("textKategorienNotes")}

NOTIZ-TAGS:
{get("textTagsNotes")}

NOTIZ-TYPEN:
{get("textTypNotes")}

PROJEKTBESCHREIBUNGEN:
{get("textProjectDescription")}

AREA-BESCHREIBUNGEN:
{get("textAreasDescription")}

ZEITAUFWAND:
{get("TimeSpent")}

DONE-QUOTE:
{get(" Done")}

Erstelle jetzt eine präzise Tagesanalyse in Ich-Form, aber ohne jeden Absatz mit „Ich“ zu beginnen.
""".strip()


def update_summary(entry_id, summary_text):
    if len(summary_text) > 1990:
        summary_text = summary_text[:1987].rstrip() + "..."

    url = f"https://api.notion.com/v1/pages/{entry_id}"
    payload = {
        "properties": {
            "Summary": {
                "rich_text": [
                    {
                        "text": {
                            "content": summary_text
                        }
                    }
                ]
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

    print("📨 Sende verbesserten Prompt an GPT...\n")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Du bist ein analytischer Personal-Operating-System-Assistent. "
                    "Du schreibst nüchtern, präzise und ohne generische Journal-Floskeln."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
        max_tokens=520
    )

    summary = response.choices[0].message.content.strip()

    print(f"\n🧠 GPT-Antwort ({len(summary)} Zeichen):\n{summary}")

    backup_to_txt(summary)
    update_summary(entry_id, summary)


if __name__ == "__main__":
    main()
