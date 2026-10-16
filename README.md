# TalentLens — AI-Powered Resume Screening System

A local resume screening and ranking demo built with Python, Flask, Pandas, SQLite and NLP-style text processing. It extracts text from PDF/DOCX/TXT resumes, detects skills from a curated vocabulary, compares them to skills detected in a job description, ranks candidates by overlap, explains matched/missing skills, stores screening history and exports CSV.

## What it does
- Upload up to 30 PDF, DOCX or TXT resumes (8 MB each).
- Extract candidate name/email where detectable and parse text.
- Normalize text and detect skills from an editable dictionary grouped by skill area.
- Calculate an explainable score: `matched detected job skills / all detected job skills × 100`.
- Rank candidates, show matched/missing skills, save results in SQLite and export a CSV report with Pandas.
- Responsive recruiter dashboard, history view and input validation.
- Sample resumes and a sample job description are included.

## Run locally
Requires Python 3.10+.

```bash
# Windows PowerShell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 and select **Screen resumes**. Use `sample_job_description.txt` and the three files under `sample_resumes/` for the demo. If PowerShell blocks activation, use `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` for the current terminal or invoke `.venv\Scripts\python.exe` directly.

## Matching method
This is an explainable baseline rather than a large language model. It uses case-insensitive skill phrase matching with token boundaries to reduce false positives. The score measures overlap among skills detected from the job description and resume. A skill may be absent from the vocabulary, expressed as a synonym, or present without being detected. PDF extraction may not work for scanned/image-only PDFs; OCR is not included. Do not treat the score as a validated prediction of employee performance.

To add or modify skills, edit `SKILL_GROUPS` in `app.py`. A stronger next iteration could add TF-IDF/cosine similarity, synonym maps, unit tests, recruiter review notes and role-specific evaluation.

## Data and privacy
Resume files are read in memory and are not persisted by the application. Extracted candidate names/emails, detected skills, scores and job description are saved in `screening.db` for the history/report features. This demo has no authentication and is intended for local interviewer demonstration only. Use synthetic/sample resumes for demos. Before any real recruitment use, add access controls, CSRF protection, retention/deletion controls, security review, consent/notice and a fairness evaluation.

## Interview walkthrough (3–5 minutes)
1. Open the overview and explain the recruiter workflow.
2. Start a new screening for “Junior Data Analyst.” Paste the sample job description.
3. Upload the three sample resumes in `sample_resumes/` and run screening.
4. Explain why the ranking differs and point to matched and missing skills for each candidate.
5. Export CSV and open screening history.
6. Explain the pipeline: upload → extract text → normalize → detect skills → calculate overlap score → persist to SQLite → export with Pandas.

## Database
- `screening_runs`: role title, job description and timestamp.
- `candidates`: filename, detected identity fields, detected/matched/missing skills, score and explanation, linked to the screening run.

## Main files
- `app.py`: Flask routes, extraction, skill detection, scoring and SQL.
- `templates/`: recruiter UI.
- `static/style.css`: dashboard styling and responsive layout.
- `static/app.js`: file preview and form interactions.
- `sample_resumes/`: synthetic test resumes.

## Deployment
The app can run on Vercel, but its serverless filesystem is read-only except for temporary storage. On Vercel, the app stores SQLite data under `/tmp/ai-resume-screening` so it can start without trying to write into the deployed application directory. This temporary database is not durable: screening history can disappear when an instance is recycled and may not be shared between instances. Use a persistent database for production or whenever screening history must be retained.

For a non-serverless deployment, set `SCREENING_DATA_DIR` to a writable persistent directory to choose where `screening.db` is created. If it is not set, the database stays alongside `app.py`, preserving the local default.
