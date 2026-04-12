from fastapi import APIRouter, Depends
import json

router = APIRouter()

@router.get("/leads")
async def get_leads(platform: str = None, subject: str = None):
    """
    API endpoint to fetch leads with filters.
    In the real implementation, this will query the PostgreSQL database.
    """
    # Placeholder response
    return {
        "status": "success",
        "data": [
            {
                "platform": "Twitter",
                "content": "Matematik özel ders arıyorum, lise 2 öğrencisi için.",
                "subject": "Matematik",
                "location": "İstanbul",
                "date": "10 dk önce"
            }
        ]
    }

@router.get("/stats")
async def get_stats():
    """Returns basic stats for the dashboard."""
    return {
        "total_leads": 124,
        "today_leads": 12,
        "top_subjects": ["Matematik", "İngilizce", "Fizik"]
    }
