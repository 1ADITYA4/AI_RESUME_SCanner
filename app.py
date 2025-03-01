import os
import logging
from flask import Flask, request, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from resume_scanner import load_resumes, load_job_description, match_resumes, save_results_to_csv

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Handle file uploads
        resumes = request.files.getlist('resumes')
        job_description_file = request.files['job_description']

        # Save uploaded resumes
        resume_names = []
        for resume in resumes:
            if resume:
                filename = secure_filename(resume.filename)
                resume.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                resume_names.append(filename)

        # Save job description
        job_description_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(job_description_file.filename))
        job_description_file.save(job_description_path)

        # Load resumes and job description
        resume_names, resume_texts = load_resumes(UPLOAD_FOLDER)
        job_description = load_job_description(job_description_path)

        if not resume_texts:
            logging.error("❌ No resumes found! Please check the folder path.")
            return redirect(url_for('index'))
        elif not job_description:
            logging.error("❌ Job description file is missing or empty!")
            return redirect(url_for('index'))
        else:
            scores = match_resumes(resume_texts, job_description)

            if not scores.any():
                logging.error("❌ No valid similarity scores computed.")
                return redirect(url_for('index'))
            else:
                save_results_to_csv(resume_names, scores)
                return render_template('results.html', resume_names=resume_names, scores=scores)

    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
