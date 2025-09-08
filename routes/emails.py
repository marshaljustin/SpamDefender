from fastapi import APIRouter, HTTPException, status, Depends
from services.email_scanner import scan_gmail_emails
from routes.auth import get_current_user
from database import email_scans_collection
from datetime import datetime
from bson import ObjectId

router = APIRouter(prefix="/api", tags=["Emails"])


@router.post("/scan-emails")
async def api_scan_emails(current_user: dict = Depends(get_current_user)):
    try:
        print(f"Scanning emails for user: {current_user['email']}")
        result = await scan_gmail_emails()

        if 'error' in result:
            print(f"Scan error: {result['error']}")
            raise HTTPException(status_code=500, detail=result['error'])

        # Store scan results in database with correct user ID
        scan_data = {
            "user_id": ObjectId(current_user["_id"]),  # ✅ Use _id consistently
            "scan_time": datetime.utcnow(),
            "total_emails": result['total_emails'],
            "spam_count": result['spam_count'],
            "legitimate_count": result['legitimate_count'],
            "spam_percentage": result['spam_percentage'],
            "avg_spam_confidence": result['avg_spam_confidence'],
            "avg_legit_confidence": result['avg_legit_confidence'],
            "spam_emails": result['spam_emails'],
            "legitimate_emails": result['legitimate_emails']
        }

        # Delete previous scans for this user to avoid clutter (optional)
        await email_scans_collection.delete_many({"user_id": ObjectId(current_user["_id"])})

        # Insert new scan data
        await email_scans_collection.insert_one(scan_data)

        print(f"Stored scan data for user {current_user['email']}: {result['total_emails']} emails")

        return {
            'total_emails': result['total_emails'],
            'spam_count': result['spam_count'],
            'legitimate_count': result['legitimate_count'],
            'message': result['message']
        }
    except Exception as e:
        print(f"API scan error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def api_get_stats(current_user: dict = Depends(get_current_user)):
    try:
        print(f"Getting stats for user: {current_user['email']}")

        # Get the latest scan for this user
        latest_scan = await email_scans_collection.find_one(
            {"user_id": ObjectId(current_user["_id"])},  # ✅ Use _id consistently
            sort=[("scan_time", -1)]
        )

        if not latest_scan:
            print("No scan data found")
            return {
                'total_emails': 0,
                'spam_count': 0,
                'legitimate_count': 0,
                'spam_percentage': 0,
                'avg_spam_confidence': 0,
                'avg_legit_confidence': 0
            }

        print(f"Found scan data: {latest_scan['total_emails']} emails")
        return {
            'total_emails': latest_scan['total_emails'],
            'spam_count': latest_scan['spam_count'],
            'legitimate_count': latest_scan['legitimate_count'],
            'spam_percentage': latest_scan['spam_percentage'],
            'avg_spam_confidence': latest_scan['avg_spam_confidence'],
            'avg_legit_confidence': latest_scan['avg_legit_confidence']
        }
    except Exception as e:
        print(f"Stats error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/emails/{email_type}")
async def api_get_emails(email_type: str, current_user: dict = Depends(get_current_user)):
    try:
        print(f"Fetching {email_type} emails for user: {current_user['email']}")

        # Get the latest scan for this user
        latest_scan = await email_scans_collection.find_one(
            {"user_id": ObjectId(current_user["_id"])},  # ✅ Use _id consistently
            sort=[("scan_time", -1)]
        )

        if not latest_scan:
            print("No scan data found")
            return {'emails': []}

        if email_type == 'spam':
            emails = latest_scan.get('spam_emails', [])
            print(f"Found {len(emails)} spam emails")
            return {'emails': emails}
        elif email_type == 'legitimate':
            emails = latest_scan.get('legitimate_emails', [])
            print(f"Found {len(emails)} legitimate emails")
            return {'emails': emails}
        else:
            raise HTTPException(status_code=400, detail='Invalid email type. Use "spam" or "legitimate".')

    except Exception as e:
        print(f"Get emails error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
