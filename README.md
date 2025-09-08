# Spam Email Detection with BERT & Scikit-learn

A complete **email classification system** combining **BERT embeddings** and **Scikit-learn classifiers**, trained on multiple datasets and deployable via **FastAPI**.  

---

## Overview

This project uses **BERT embeddings** to capture context and semantics, improving spam and phishing detection. Later, classical ML classifiers (Logistic Regression, SVM, Random Forest) are trained on these embeddings for production deployment.
**Key Highlights:**

- Fine-tuned **BERT model** for phishing detection (offline)
- Multi-dataset combination for robust training
- Classical ML classifiers trained on TF-IDF features
- Saved as `.pkl` files for deployment
- **FastAPI endpoints** for real-time email scanning
- Hugging Face integration for model sharing

---

## Model Details

### BERT Fine-tuning
- Combined 3 public spam datasets
- Classifiers: Logistic Regression, SVM, Random Forest
- Feature extraction: TF-IDF vectorization
- Best model saved as `spam_model_fixed.pkl`
- Hugging Face link for BERT embeddings:  
  👉 [Your Hugging Face Model](https://huggingface.co/your-username/your-model-name)

---

## Features

- 🔐 Secure Gmail API connection  
- 📥 Fetch recent emails  
- 🤖 Classify as **Spam / Legitimate / Phishing**  
- 📊 Generate evaluation metrics 
- 🌐 RESTful API powered by FastAPI

---

## Installation & Dependencies

1. **Create a virtual environment**
```bash
# Windows
python -m venv env
.\env\Scripts\activate

# Linux / macOS
python3 -m venv env
source env/bin/activate
```
2. **Install required packages**
```bash
pip install -r Requirements.txt
```
3. **Run the FastAPI server**
```bash
uvicorn main:app --reload
```
