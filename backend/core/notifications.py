import os
import json
import urllib.request
import urllib.parse
import threading

def send_telegram_notification(lead_data):
    """Sends a real-time notification to Telegram in a non-blocking background thread."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    # Skip if environment variables are not configured
    if not token or not chat_id:
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Format message content
    subject = lead_data.get("subject", "Özel Ders")
    location = lead_data.get("location", "Belirtilmemiş")
    content = lead_data.get("content", "")
    if len(content) > 200:
        content = content[:200] + "..."
        
    text = (
        f"🎯 *YENİ ÖZEL DERS TALEBİ!*\n\n"
        f"📚 *Ders/Konu:* {subject}\n"
        f"📍 *Konum:* {location}\n"
        f"📝 *Açıklama:* {content}\n"
    )
    
    if lead_data.get("contact_info"):
        text += f"📞 *İletişim:* {lead_data.get('contact_info')}\n"
        
    if lead_data.get("whatsapp_link"):
        text += f"💬 [WhatsApp İletişim]({lead_data.get('whatsapp_link')})\n"
        
    text += f"🔗 [Kaynağa Git]({lead_data.get('original_link')})"
    
    # Background execution to prevent blocking the main server
    def _send():
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps({
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True
                }).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req) as response:
                response.read()
        except Exception as e:
            print(f"Telegram Notification Error: {e}")
            
    threading.Thread(target=_send, daemon=True).start()
