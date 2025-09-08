import os
import pickle
import base64
from email import message_from_bytes
import warnings
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from typing import List, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Suppress sklearn version warnings
warnings.filterwarnings('ignore', message='Trying to unpickle estimator')

from config import settings


class SklearnSpamClassifier:
    def __init__(self, model_path):
        print(f"Loading sklearn model from {model_path} ...")
        try:
            with open(model_path, "rb") as f:
                data = pickle.load(f)
            self.model = data["model"]
            self.vectorizer = data["vectorizer"]
            print(f"Model classes: {self.model.classes_}")
        except Exception as e:
            print(f"Error loading model: {e}")
            raise

    def predict(self, email_text):
        """COMPLETELY FIXED prediction method"""
        try:
            if not email_text or email_text.strip() == "":
                return {
                    "is_spam": False,
                    "spam_probability": 0.0,
                    "legitimate_probability": 1.0,
                    "confidence": 1.0,
                    "analysis": "✅ LEGIT (empty email)"
                }

            X = self.vectorizer.transform([email_text])

            if X.nnz == 0:
                return {
                    "is_spam": False,
                    "spam_probability": 0.0,
                    "legitimate_probability": 1.0,
                    "confidence": 0.8,
                    "analysis": "✅ LEGIT (no features)"
                }

            pred = self.model.predict(X)[0]
            probas = self.model.predict_proba(X)[0]

            if len(probas) == 2:
                legit_prob = float(probas[0])
                spam_prob = float(probas[1])
            elif len(probas) == 1:
                if self.model.classes_[0] == 1:
                    spam_prob = float(probas[0])
                    legit_prob = 1.0 - spam_prob
                else:
                    legit_prob = float(probas[0])
                    spam_prob = 1.0 - legit_prob
            else:
                spam_prob = 0.5
                legit_prob = 0.5

            confidence = max(spam_prob, legit_prob)

            return {
                "is_spam": bool(pred),
                "spam_probability": spam_prob,
                "legitimate_probability": legit_prob,
                "confidence": confidence,
                "analysis": f"{'🚨 SPAM' if pred else '✅ LEGIT'} (Confidence: {confidence:.1%})"
            }

        except Exception as e:
            print(f"Prediction error: {e}")
            return {
                "is_spam": False,
                "spam_probability": 0.0,
                "legitimate_probability": 1.0,
                "confidence": 0.5,
                "analysis": "✅ LEGIT (prediction error)"
            }


class GmailSpamDetector:
    def __init__(self):
        self.service = None
        self.classifier = None
        self.executor = ThreadPoolExecutor(max_workers=1)

    def authenticate_gmail(self):
        try:
            creds = None
            if os.path.exists(settings.TOKEN_FILE):
                with open(settings.TOKEN_FILE, 'rb') as token:
                    creds = pickle.load(token)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(settings.CREDENTIALS_FILE):
                        raise FileNotFoundError(
                            f"Please download {settings.CREDENTIALS_FILE} from Google Cloud Console")
                    flow = InstalledAppFlow.from_client_secrets_file(settings.CREDENTIALS_FILE, settings.SCOPES)
                    creds = flow.run_local_server(port=0)
                with open(settings.TOKEN_FILE, 'wb') as token:
                    pickle.dump(creds, token)
            self.service = build('gmail', 'v1', credentials=creds)
            print("✅ Successfully authenticated with Gmail!")
        except Exception as e:
            print(f"❌ Gmail authentication failed: {e}")
            raise

    def load_spam_classifier(self):
        try:
            self.classifier = SklearnSpamClassifier(settings.MODEL_PATH)
            print("✅ Sklearn TF-IDF spam classifier loaded successfully!")
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            raise

    def fetch_emails(self, max_results=10):
        try:
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results
            ).execute()
            messages = results.get('messages', [])
            emails = []
            print(f"📧 Fetching {len(messages)} emails...")

            for i, msg in enumerate(messages, 1):
                print(f"Processing email {i}/{len(messages)}...")
                msg_data = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='raw'
                ).execute()

                msg_bytes = base64.urlsafe_b64decode(msg_data['raw'].encode('UTF-8'))
                email_msg = message_from_bytes(msg_bytes)

                subject = email_msg.get('Subject', '(No Subject)')
                sender = email_msg.get('From', '(Unknown Sender)')
                date = email_msg.get('Date', '(Unknown Date)')
                body = self.extract_email_body(email_msg)
                full_text = f"Subject: {subject}\nFrom: {sender}\n\n{body}"

                emails.append({
                    'id': msg['id'],
                    'subject': subject,
                    'sender': sender,
                    'date': date,
                    'body': body,
                    'full_text': full_text
                })

            print(f"✅ Successfully fetched {len(emails)} emails!")
            return emails
        except Exception as e:
            print(f"❌ Error fetching emails: {e}")
            return []

    def extract_email_body(self, email_msg):
        body = ""
        if email_msg.is_multipart():
            for part in email_msg.walk():
                if part.get_content_type() == 'text/plain':
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                    except:
                        continue
        else:
            try:
                body = email_msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                body = str(email_msg.get_payload())
        return body[:5000] if body else ""

    def classify_emails(self, emails):
        results = []
        spam_count = 0
        print(f"\n🔍 Classifying {len(emails)} emails...")

        for i, email in enumerate(emails, 1):
            print(f"Classifying email {i}/{len(emails)}...")
            prediction = self.classifier.predict(email['full_text'])
            is_spam = prediction['is_spam']
            confidence = prediction['confidence']

            if is_spam:
                spam_count += 1

            # Match the data structure expected by your frontend
            result = {
                'email_id': email['id'],
                'subject': email['subject'][:100],
                'sender': email['sender'],
                'date': email['date'],
                'content': email['body'][:200] + '...' if len(email['body']) > 200 else email['body'],
                'preview': email['body'][:200] + '...' if len(email['body']) > 200 else email['body'],
                # Added for frontend
                'is_spam': is_spam,
                'confidence': confidence,
                'spam_probability': prediction['spam_probability'],
                'legitimate_probability': prediction['legitimate_probability'],
                'analysis': prediction.get('analysis', 'No analysis available'),
                'classification': '🚨 SPAM' if is_spam else '✅ LEGITIMATE'
            }
            results.append(result)

        print(f"✅ Classification complete!")
        return results

    async def scan_async(self, max_results=50):
        """Async wrapper for scanning emails"""
        loop = asyncio.get_event_loop()

        # Run the synchronous operations in a thread pool
        await loop.run_in_executor(self.executor, self.authenticate_gmail)
        await loop.run_in_executor(self.executor, self.load_spam_classifier)

        emails = await loop.run_in_executor(self.executor, self.fetch_emails, max_results)
        if not emails:
            return []

        results = await loop.run_in_executor(self.executor, self.classify_emails, emails)
        return results


# Global detector instance
detector = GmailSpamDetector()


async def scan_gmail_emails(max_emails: int = 50) -> Dict[str, Any]:
    """Async scan Gmail emails for spam detection"""
    try:
        print("Starting email scan...")

        results = await detector.scan_async(max_results=max_emails)

        if not results:
            print("No emails processed")
            return {
                'total_emails': 0,
                'spam_count': 0,
                'legitimate_count': 0,
                'spam_percentage': 0,
                'avg_spam_confidence': 0,
                'avg_legit_confidence': 0,
                'spam_emails': [],
                'legitimate_emails': [],
                'message': 'No emails found'
            }

        # Calculate statistics
        spam_emails = [r for r in results if r['is_spam']]
        legit_emails = [r for r in results if not r['is_spam']]
        total_emails = len(results)
        spam_count = len(spam_emails)
        legit_count = len(legit_emails)

        # Handle division by zero
        avg_spam_confidence = sum([r['confidence'] for r in spam_emails]) / max(spam_count, 1) if spam_count > 0 else 0
        avg_legit_confidence = sum([r['confidence'] for r in legit_emails]) / max(legit_count,
                                                                                  1) if legit_count > 0 else 0
        spam_percentage = (spam_count / total_emails * 100) if total_emails > 0 else 0

        print(f"Scan complete: {total_emails} total, {spam_count} spam, {legit_count} legitimate")

        return {
            'total_emails': total_emails,
            'spam_count': spam_count,
            'legitimate_count': legit_count,
            'spam_percentage': spam_percentage,
            'avg_spam_confidence': avg_spam_confidence,
            'avg_legit_confidence': avg_legit_confidence,
            'spam_emails': spam_emails,
            'legitimate_emails': legit_emails,
            'message': f'Successfully scanned {total_emails} emails'
        }

    except Exception as e:
        print(f"❌ Error in scan_gmail_emails: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
