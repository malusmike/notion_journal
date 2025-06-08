# notion_journal.py
# 🧠 Notion Daily Journal Automation with GPT Summary

This project automates the creation of daily journal entries in Notion, enriched with a contextual GPT-generated summary based on your PARA system (Projects, Areas, Resources, Archives).

---

## 📌 Features

- Automatically creates a journal entry every morning for the previous day
- Links relevant:
  - ✅ Tasks created yesterday
  - ✅ Notes created yesterday
  - ✅ Projects & Areas/Resources (via relation)
- GPT-4 powered **intelligent summary** of daily activity:
  - Counts of created/viewed tasks and notes
  - Analysis of PARA relations
  - Thematic clusters based on **tags** and **categories**
  - Detection of **Inbox tasks** (no due date, no project/area)
  - Learnings, trends, and productivity insights

---

## 📁 Repository Structure

```bash
.
├── journal_creator.py         # Main script to create Notion journal entry
├── gpt_summary.py             # Modular GPT logic (summarization prompt & generation)
├── .env                       # Local environment variables (see below)
├── journal_debug.txt          # Debug log (can be disabled)
└── README.md                  # You’re reading it.

