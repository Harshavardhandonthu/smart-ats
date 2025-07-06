from flask import Flask, render_template, request, send_file
import os
from werkzeug.utils import secure_filename
from resume_parser import parse_resume, extract_fields
from pymongo import MongoClient
from job_roles import job_skill_map
from markupsafe import Markup
from pdf_generator import generate_pdf
import uuid
from bson import ObjectId
from flask import jsonify

# Flask app configuration
app = Flask(__name__, template_folder='frontend/templates', static_folder='frontend/static')


# MongoDB connection (Atlas)
client = MongoClient("mongodb+srv://donthuharsh2004:Dhv%402004@cluster0.il0wvfo.mongodb.net/ats_db?retryWrites=true&w=majority&appName=Cluster0")
db = client.ats_db
resumes_collection = db.resumes

# File upload configuration
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'uploads'))
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Utility: check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Homepage
@app.route('/')
def home():
    return render_template('index.html')

# Upload and process resume
@app.route('/upload', methods=['POST'])
def upload_resume():
    if 'resume' not in request.files:
        return 'Resume file is missing', 400

    file = request.files['resume']
    jd_file = request.files.get('jd_file')
    jd_text_input = request.form.get('job_description', '').strip()
    job_title = request.form.get('job_title', '').strip().lower()

    if file.filename == '':
        return 'No resume selected', 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)

        resume_text = parse_resume(save_path)
        resume_fields = extract_fields(resume_text)
        resume_skills = set(resume_fields['skills'])

        # --- Use job title → skills if no JD text/file provided
        if not jd_text_input and not (jd_file and jd_file.filename):
            if job_title in job_skill_map:
                job_skills = set(job_skill_map[job_title])
            else:
                return f"Unknown job title: {job_title}", 400
        else:
            # Get JD text from file or textarea
            jd_text = ''
            if jd_file and jd_file.filename:
                jd_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(jd_file.filename))
                jd_file.save(jd_path)
                jd_text = parse_resume(jd_path)
            else:
                jd_text = jd_text_input

            jd_fields = extract_fields(jd_text)
            job_skills = set(jd_fields['skills'])

        # Compare skills
        matched = resume_skills & job_skills
        missing = job_skills - resume_skills
        match_percent = int((len(matched) / len(job_skills)) * 100) if job_skills else 0

        # Recommend other jobs
        recommendations = []
        for role, skills in job_skill_map.items():
            overlap = resume_skills & set(skills)
            score = len(overlap) / len(skills)
            if score >= 0.5 and role != job_title:
                recommendations.append((role, int(score * 100)))
        recommendations.sort(key=lambda x: x[1], reverse=True)

        # Generate PDF
        report_name = f"report_{uuid.uuid4().hex}.pdf"
        report_path = os.path.join(app.config['UPLOAD_FOLDER'], report_name)
        generate_pdf(report_path, resume_fields, matched, missing, match_percent)

        matched_html = ''.join(f'<span class="bg-green-200 text-green-800 px-2 py-1 rounded">{skill}</span>' for skill in matched)
        missing_html = ''.join(f'<span class="bg-red-200 text-red-800 px-2 py-1 rounded">{skill} <a href="https://www.google.com/search?q=learn+{skill}+free" target="_blank" class="text-blue-700 underline ml-1">Learn</a></span>' for skill in missing)
        recommended_roles_html = ''
        if recommendations:
            recommended_roles_html += '<h2 class="text-lg font-semibold text-blue-700 mt-6 mb-2">💼 Recommended Roles for You</h2>'
            recommended_roles_html += '<ul class="list-disc ml-6 text-gray-800">'
            for role, score in recommendations:
                recommended_roles_html += f'<li>{role.title()} - {score}% match</li>'
            recommended_roles_html += '</ul>'

        chart_script = f'''
        <div class="mt-10 max-w-md mx-auto">
            <canvas id="skillsChart" width="300" height="300"></canvas>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            const ctx = document.getElementById('skillsChart').getContext('2d');
            new Chart(ctx, {{
              type: 'pie',
              data: {{
                labels: ['Matched Skills', 'Missing Skills'],
                datasets: [{{
                  label: 'Skill Match',
                  data: [{len(matched)}, {len(missing)}],
                  backgroundColor: ['#16a34a', '#dc2626'],
                  hoverOffset: 6
                }}]
              }},
              options: {{
                plugins: {{
                  legend: {{
                    position: 'bottom'
                  }}
                }}
              }}
            }});
        </script>
        '''

        html_output = f'''
        <!DOCTYPE html>
        <html>
        <head>
        <title>Job Match Result</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gray-100 p-6">
          <div class="max-w-3xl mx-auto bg-white p-6 rounded-xl shadow-md">
            <h1 class="text-2xl font-bold text-blue-600 mb-4">🔍 Match Result</h1>
            <p class="mb-4">
              <b class="text-gray-700">Match Percentage:</b> 
              <span class="text-xl text-green-600 font-semibold">{match_percent}%</span>
            </p>
            <h2 class="text-lg font-semibold text-green-700 mb-2">✅ Matched Skills</h2>
            <div class="flex flex-wrap gap-2 mb-4">{matched_html}</div>
            <h2 class="text-lg font-semibold text-red-700 mb-2">❌ Missing Skills & Learning Links</h2>
            <div class="flex flex-wrap gap-2 mb-4">{missing_html}</div>
            <hr class="my-6">
            <p><b>Email:</b> {resume_fields['email']}<br><b>Phone:</b> {resume_fields['phone']}</p>
            {recommended_roles_html}
            <a href="/download_report/{report_name}" class="block w-full sm:inline-block sm:w-auto mt-4 bg-gray-700 text-white px-4 py-2 rounded shadow hover:bg-gray-900 text-center">
            📥 Download PDF Report
            </a>
            <a href="/" class="block w-full sm:inline-block sm:w-auto mt-6 text-blue-600 hover:underline text-center">
             ← Analyze Another Resume
            </a>

          </div>
          {chart_script}
        </body>
        </html>
        '''

        return Markup(html_output)
    else:
        return 'Invalid resume file type', 400

# Dashboard route (optional for admin view)
@app.route('/dashboard', methods=['GET'])
def dashboard():
    query = request.args.get('q', '').strip().lower()
    if query:
        resumes = list(resumes_collection.find({
            "$or": [
                {"email": {"$regex": query, "$options": "i"}},
                {"skills": {"$in": [query]}}
            ]
        }))
    else:
        resumes = list(resumes_collection.find())
    return render_template('dashboard.html', resumes=resumes)


@app.route('/delete_resume/<resume_id>', methods=['POST'])
def delete_resume(resume_id):
    resumes_collection.delete_one({"_id": ObjectId(resume_id)})
    return jsonify({"success": True})

# Download generated PDF
@app.route('/download_report/<filename>')
def download_report(filename):
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    return send_file(path, as_attachment=True)

# Run the Flask server
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

