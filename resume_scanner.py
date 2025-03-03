import os
import pdfplumber
import docx
import nltk
import string
import csv
import logging
import argparse
import torch
from transformers import BertTokenizer, BertModel


from sklearn.metrics.pairwise import cosine_similarity

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Download NLTK resources
try:
    nltk.download('punkt')
    nltk.download('stopwords')
except Exception as e:
    logging.error(f"Error downloading NLTK resources: {e}")

from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    try:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except Exception as e:
        logging.error(f"Error reading {pdf_path}: {e}")
        return ""

# Function to extract text from DOCX
def extract_text_from_docx(docx_path):
    try:
        doc = docx.Document(docx_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        logging.error(f"Error reading {docx_path}: {e}")
        return ""

# Function to preprocess text (tokenization, stopword removal)
def preprocess_text(text):
    stop_words = set(stopwords.words("english"))
    tokens = word_tokenize(text.lower())  
    tokens = [word for word in tokens if word.isalnum() and word not in stop_words]
    return " ".join(tokens)

# Load resumes and preprocess
def load_resumes(folder_path):
    logging.info(f"Loading resumes from folder: {folder_path}")
    resume_texts = []
    resume_names = []

    if not os.path.exists(folder_path):
        logging.error(f"Folder not found: {folder_path}")
        return [], []

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)

        if filename.endswith(".pdf"):
            text = extract_text_from_pdf(file_path)
        elif filename.endswith(".docx"):
            text = extract_text_from_docx(file_path)
        else:
            continue  

        if text.strip():
            processed_text = preprocess_text(text)
            resume_texts.append(processed_text)
            resume_names.append(filename)

    return resume_names, resume_texts

# Load job description
def load_job_description(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return preprocess_text(file.read())
    except Exception as e:
        logging.error(f"Error reading job description file: {e}")
        return ""

# Match resumes with job description using TF-IDF & Cosine Similarity
def match_resumes(resumes, job_desc):
    if not resumes or not job_desc:
        logging.error("❌ Cannot compute similarity: No valid resume or job description found!")
        return []

    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
    model = BertModel.from_pretrained('bert-base-uncased')

    # Tokenize and encode the resumes and job description
    inputs = tokenizer(resumes + [job_desc], return_tensors='pt', padding=True, truncation=True)
    with torch.no_grad():
        embeddings = model(**inputs).last_hidden_state.mean(dim=1)

    job_vector = embeddings[-1]  # Last embedding is for the job description

    similarities = cosine_similarity(job_vector.unsqueeze(0), embeddings[:-1]).flatten()  # Compare with resumes


    return similarities

# Save results to CSV
def save_results_to_csv(resume_names, scores, output_file="resume_scores.csv"):
    with open(output_file, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Resume Name", "Matching Score (%)"])
        for name, score in zip(resume_names, scores):
            writer.writerow([name, round(score * 100, 2)])
    logging.info(f"✅ Results saved to {output_file}")

# Main function
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-Powered Resume Scanner")
    parser.add_argument("--resumes", type=str, default="resumes", help="Path to the resumes folder")
    parser.add_argument("--job_description", type=str, default="job_description.txt", help="Path to the job description file")
    args = parser.parse_args()

    resume_names, resume_texts = load_resumes(args.resumes)
    job_description = load_job_description(args.job_description)

    if not resume_texts:
        logging.error("❌ No resumes found! Please check the folder path.")
    elif not job_description:
        logging.error("❌ Job description file is missing or empty!")
    else:
        scores = match_resumes(resume_texts, job_description)

        if not scores.any():
            logging.error("❌ No valid similarity scores computed.")
        else:
            print("\n🔹 Resume Matching Scores:\n")
            for i, score in enumerate(scores):
                print(f"{i+1}. {resume_names[i]}: {score * 100:.2f}% match")

            best_match_idx = scores.argmax()
            print(f"\n🏆 Best Matched Resume: {resume_names[best_match_idx]}")

            save_results_to_csv(resume_names, scores)
