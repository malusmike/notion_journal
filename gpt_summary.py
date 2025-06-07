def generate_gpt_summary(tasks_created, notes_created, all_tasks, all_projects, all_areas, date_str):
    tasks_edited = filter_by_last_edited_time(all_tasks, date_str)
    projects_edited = filter_by_last_edited_time(all_projects, date_str)
    areas_edited = filter_by_last_edited_time(all_areas, date_str)

    prompt = f"""Fasse die Arbeitsaktivität vom {date_str} kurz und strukturiert zusammen:

- Wie viele neue Tasks wurden erstellt? (Tasks: {len(tasks_created)})
- Wie viele bestehende Tasks wurden bearbeitet? (Bearbeitet: {len(tasks_edited)})
- Wie viele neue Notizen wurden erstellt? (Notizen: {len(notes_created)})
- Welche thematischen Schwerpunkte lassen sich erkennen (z. B. aus Tags, Kategorien oder Titeln)?
- Welche Projekte oder Bereiche waren durch verknüpfte Tasks oder Notizen beteiligt?
- Was lässt sich daraus an Learnings oder Empfehlungen ableiten?

Verwende klare Bulletpoints und max. 5 Absätze. Führe keine einzelnen Titel oder Inhalte der Tasks/Notizen an."""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=600,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        log_debug(f"❌ GPT Fehler: {str(e)}")
        return "GPT-Zusammenfassung konnte nicht erstellt werden."