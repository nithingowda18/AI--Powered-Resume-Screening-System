from pathlib import Path
from datetime import datetime
import io, os, re, sqlite3, tempfile
from collections import Counter
from flask import Flask, render_template, request, redirect, url_for, flash, g, send_file
from werkzeug.utils import secure_filename
import pandas as pd

BASE=Path(__file__).resolve().parent
data_dir=os.environ.get('SCREENING_DATA_DIR')
if data_dir:
 DATA_DIR=Path(data_dir)
elif os.environ.get('VERCEL')=='1':
 DATA_DIR=Path(tempfile.gettempdir())/'ai-resume-screening'
else:
 DATA_DIR=BASE
DATA_DIR.mkdir(parents=True,exist_ok=True)
ALLOWED={'.pdf','.docx','.txt'}
app=Flask(__name__)
app.config.update(SECRET_KEY='change-this-demo-secret-before-deployment', DATABASE=str(DATA_DIR/'screening.db'), MAX_CONTENT_LENGTH=8*1024*1024)

SKILL_GROUPS={
 'Programming': ['python','java','c++','c','javascript','typescript','sql','r'],
 'Data & BI': ['pandas','numpy','power bi','tableau','excel','data visualization','data cleaning','statistics','etl'],
 'AI & ML': ['machine learning','deep learning','nlp','natural language processing','scikit-learn','tensorflow','pytorch','opencv','generative ai','llm'],
 'Web & APIs': ['flask','django','fastapi','html','css','rest api','restful api','react','node.js'],
 'Databases & Cloud': ['sqlite','mysql','postgresql','mongodb','aws','azure','gcp','docker','git','linux'],
 'Analytics & Methods': ['data analysis','data analytics','dashboard','reporting','problem solving','a/b testing','data modeling']
}
ALL_SKILLS=sorted({s for skills in SKILL_GROUPS.values() for s in skills}, key=len, reverse=True)


def db():
 if 'db' not in g:
  g.db=sqlite3.connect(app.config['DATABASE']); g.db.row_factory=sqlite3.Row; g.db.execute('PRAGMA foreign_keys=ON')
 return g.db
@app.teardown_appcontext
def close_db(_error=None):
 conn=g.pop('db',None)
 if conn is not None: conn.close()
def init_db():
 conn=sqlite3.connect(app.config['DATABASE'])
 conn.executescript('''CREATE TABLE IF NOT EXISTS screening_runs(id INTEGER PRIMARY KEY AUTOINCREMENT, role_title TEXT NOT NULL, job_description TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
 CREATE TABLE IF NOT EXISTS candidates(id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL, filename TEXT NOT NULL, candidate_name TEXT, email TEXT, skills_json TEXT NOT NULL, matched_json TEXT NOT NULL, missing_json TEXT NOT NULL, score REAL NOT NULL, summary TEXT NOT NULL, FOREIGN KEY(run_id) REFERENCES screening_runs(id) ON DELETE CASCADE);''')
 conn.commit(); conn.close()

def extract_text(filename, data):
 ext=Path(filename).suffix.lower()
 if ext=='.txt': return data.decode('utf-8',errors='ignore')
 if ext=='.pdf':
  try:
   import pdfplumber
   with pdfplumber.open(io.BytesIO(data)) as pdf: return '\n'.join(page.extract_text() or '' for page in pdf.pages)
  except ImportError: raise ValueError('PDF support is missing. Install requirements.txt, including pdfplumber.')
  except Exception as e: raise ValueError(f'Could not read PDF: {e}')
 if ext=='.docx':
  try:
   from docx import Document
   doc=Document(io.BytesIO(data)); return '\n'.join(p.text for p in doc.paragraphs)
  except ImportError: raise ValueError('DOCX support is missing. Install requirements.txt, including python-docx.')
  except Exception as e: raise ValueError(f'Could not read DOCX: {e}')
 raise ValueError('Unsupported file type. Upload PDF, DOCX or TXT.')

def normalise(text):
 text=text.lower().replace('node js','node.js').replace('c plus plus','c++')
 return re.sub(r'\s+',' ',text)
def find_skills(text):
 normalized=normalise(text); found=[]
 for skill in ALL_SKILLS:
  pattern=r'(?<![a-z0-9+#.])'+re.escape(skill)+r'(?![a-z0-9+#.])'
  if re.search(pattern,normalized): found.append(skill)
 return sorted(set(found))
def candidate_info(text, filename):
 email_match=re.search(r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}',text,re.I)
 lines=[re.sub(r'\s+',' ',x).strip() for x in text.splitlines() if x.strip()]
 name=None
 for line in lines[:8]:
  if len(line)<70 and not re.search(r'@|resume|curriculum vitae|phone|mobile|linkedin|github|https?://|\d{5,}',line,re.I) and len(line.split())<=5:
   name=line; break
 return name or Path(filename).stem.replace('_',' ').replace('-',' ').title(), email_match.group(0) if email_match else ''
def score_candidate(resume_skills, jd_text):
 required=find_skills(jd_text)
 if not required:
  return 0.0, [], [], required, 'No supported skills were detected in the job description. Add specific skills to get a meaningful match score.'
 matched=sorted(set(resume_skills)&set(required)); missing=sorted(set(required)-set(resume_skills))
 score=round(100*len(matched)/len(required),1)
 summary=f'Matched {len(matched)} of {len(required)} detected job skills. Review the resume and interview evidence before making a decision.'
 return score,matched,missing,required,summary

@app.context_processor
def inject_globals(): return {'now':datetime.now()}
@app.route('/')
def index():
 runs=db().execute('SELECT r.*,COUNT(c.id) candidate_count FROM screening_runs r LEFT JOIN candidates c ON c.run_id=r.id GROUP BY r.id ORDER BY r.id DESC LIMIT 8').fetchall()
 return render_template('index.html',runs=runs)
@app.route('/screen',methods=['GET','POST'])
def screen():
 if request.method=='POST':
  role=request.form.get('role_title','').strip() or 'Untitled role'; jd=request.form.get('job_description','').strip(); files=request.files.getlist('resumes')
  files=[f for f in files if f and f.filename]
  if len(jd)<30: flash('Please enter a job description with enough detail (at least 30 characters).','danger'); return render_template('screen.html',role=role,jd=jd)
  if not files: flash('Choose at least one resume file.','danger'); return render_template('screen.html',role=role,jd=jd)
  if len(files)>30: flash('Upload up to 30 resumes per screening run.','danger'); return render_template('screen.html',role=role,jd=jd)
  prepared=[]
  for f in files:
   filename=secure_filename(f.filename)
   if Path(filename).suffix.lower() not in ALLOWED:
    flash(f'{filename or "A file"}: unsupported format. Use PDF, DOCX or TXT.','danger'); continue
   data=f.read()
   if len(data)>8*1024*1024: flash(f'{filename} is over the 8 MB file limit.','danger'); continue
   try: text=extract_text(filename,data)
   except ValueError as e: flash(f'{filename}: {e}','danger'); continue
   if not text.strip(): flash(f'{filename}: no readable text was found. Scanned PDFs may need OCR first.','warning'); continue
   prepared.append((filename,text))
  if not prepared: return render_template('screen.html',role=role,jd=jd)
  cur=db().execute('INSERT INTO screening_runs(role_title,job_description) VALUES(?,?)',(role,jd)); run_id=cur.lastrowid
  for filename,text in prepared:
   skills=find_skills(text); name,email=candidate_info(text,filename); score,matched,missing,required,summary=score_candidate(skills,jd)
   db().execute('INSERT INTO candidates(run_id,filename,candidate_name,email,skills_json,matched_json,missing_json,score,summary) VALUES(?,?,?,?,?,?,?,?,?)',(run_id,filename,name,email,','.join(skills),','.join(matched),','.join(missing),score,summary))
  db().commit(); return redirect(url_for('results',run_id=run_id))
 return render_template('screen.html',role='',jd='')
@app.route('/results/<int:run_id>')
def results(run_id):
 run=db().execute('SELECT * FROM screening_runs WHERE id=?',(run_id,)).fetchone()
 if not run: flash('Screening run not found.','danger'); return redirect(url_for('index'))
 rows=db().execute('SELECT * FROM candidates WHERE run_id=? ORDER BY score DESC,candidate_name COLLATE NOCASE',(run_id,)).fetchall()
 candidates=[]
 for r in rows:
  d=dict(r); d['skills']=r['skills_json'].split(',') if r['skills_json'] else []; d['matched']=r['matched_json'].split(',') if r['matched_json'] else []; d['missing']=r['missing_json'].split(',') if r['missing_json'] else []; candidates.append(d)
 return render_template('results.html',run=run,candidates=candidates)
@app.route('/history')
def history():
 runs=db().execute('SELECT r.*,COUNT(c.id) candidate_count,ROUND(AVG(c.score),1) avg_score FROM screening_runs r LEFT JOIN candidates c ON c.run_id=r.id GROUP BY r.id ORDER BY r.id DESC').fetchall()
 return render_template('history.html',runs=runs)
@app.route('/export/<int:run_id>.csv')
def export_csv(run_id):
 run=db().execute('SELECT * FROM screening_runs WHERE id=?',(run_id,)).fetchone()
 if not run: flash('Screening run not found.','danger'); return redirect(url_for('index'))
 rows=db().execute('SELECT candidate_name,email,filename,score,skills_json,matched_json,missing_json,summary FROM candidates WHERE run_id=? ORDER BY score DESC',(run_id,)).fetchall()
 df=pd.DataFrame([dict(r) for r in rows],columns=['candidate_name','email','filename','score','skills_json','matched_json','missing_json','summary'])
 df.rename(columns={'skills_json':'detected_skills','matched_json':'matched_skills','missing_json':'missing_skills'},inplace=True)
 buffer=io.BytesIO(df.to_csv(index=False).encode('utf-8-sig')); buffer.seek(0)
 return send_file(buffer,mimetype='text/csv',as_attachment=True,download_name=f'screening-{run_id}.csv')
@app.errorhandler(413)
def too_large(_error): return 'Upload too large. Each resume must be no more than 8 MB.',413
init_db()
if __name__=='__main__':
   app.run(debug=True)
