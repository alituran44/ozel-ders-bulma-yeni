import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Setup Gemini API
# You should set your GOOGLE_API_KEY as an environment variable
# API_KEY = os.getenv("GOOGLE_API_KEY")
# genai.configure(api_key=API_KEY)

class LeadClassifier:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
            except Exception as e:
                print(f"ERROR: Failed to configure Gemini API: {e}")
                self.model = None
        else:
            self.model = None
            print("WARNING: GOOGLE_API_KEY not found. Running in basic extraction mode (Regex only).")
        
        self.system_prompt = """
        Sen uzman bir veri analistisin. Görevin, Türkiye genelindeki özel ders platformlarından çekilen ham metinleri analiz etmek ve bunları 'Lead' (Öğrenci/Veli Talebi) veya 'Ad' (Öğretmen/Kurum Reklamı) olarak sınıflandırmaktır.

        KURAL - REDDEDİLECEKLER (AD):
        - İçinde "öğrenci arıyorum", "öğrenci arayışım", "öğrenciler arıyorum", "ders verilir", "uzman öğretmen", "saati X TL", "ilk ders ücretsiz", "tecrübeliyim", "mezunuyum" gibi öğretmen/kurum tanıtımı ve reklamı barındıran tüm içerikleri 'AD' olarak işaretle.
        
        KURAL - KABUL EDİLECEKLER (LEAD):
        - İçinde "arıyorum", "tavsiye", "lazım", "yardımcı olabilecek", "çocuğum için" kelimeleri geçen, sadece öğrenci/veli tarafından açılmış hoca arayışı belirten metinleri 'LEAD' olarak işaretle.

        ÇIKTI FORMATI:
        Sadece aşağıdaki JSON formatında yanıt ver:
        {
            "is_lead": boolean,
            "subject": "Matematik/İngilizce/vb.",
            "location": "Şehir veya İlçe",
            "contact_info": "Başında 0 olan 11 haneli telefon numarası veya email",
            "reason": "Neden 'AD' veya 'LEAD' olarak seçildiğinin kısa özeti"
        }
        """

    def is_strict_lead(self, text):
        text_lower = text.lower()
        
        ad_keywords = [
            "ders verilir", "öğretmeninden", "tecrübeliyim", "ücretsiz deneme", 
            "ilk ders", "saatlik ücret", "öğretmeniyim", "kayıtlarımız", 
            "danışmanlık", "uygun fiyata", "ödev yapılır", "ödevlere yardımcı",
            "mezunuyum", "atama bekleyen", "ders anlatılır", "öğrenci arıyorum",
            "öğrenci arayışım", "öğrenci arayışı", "öğrenciler arıyorum", "grup dersleri"
        ]
        
        # Öğrenci/Veli arayışına işaret eden kelimeler (Lead)
        lead_keywords = [
            "arıyorum", "arıyoruz", "aranıyor", "aranmaktadır", "lazım", "gerekiyor",
            "tavsiye", "yardımcı olabilecek", "yardımcı olacak",
            "hoca arıyoruz", "hoca arıyorum", "hoca arayışı", "hocası arıyoruz", "hocası arıyorum",
            "öğretmen arıyoruz", "öğretmen arıyorum", "öğretmen arayışı", "öğretmeni arıyoruz",
            "çocuğum için", "oğlum için", "kızım için", "kendim için", "yeğenim için",
            "ders verebilecek", "ders verecek", "ders aldıracağız", "ders aldırmak", "ders almak",
            "özel ders arayışımız", "özel ders arayışı", "hocası lazım", "öğretmen lazım",
            "ilanı arıyorum", "antrenörü arıyoruz"
        ]
        
        for ad_kw in ad_keywords:
            if ad_kw in text_lower:
                return False
                
        for lead_kw in lead_keywords:
            if lead_kw in text_lower:
                return True
                
        return False

    def extract_phone(self, text):
        import re
        # Standard Turkish phone regex (05xx xxx xx xx etc)
        pattern = r"(05\d{2}[- ]?\d{3}[- ]?\d{2}[- ]?\d{2}|05\d{9}|5\d{9})"
        match = re.search(pattern, text)
        if match:
            # Clean non-digit characters
            phone = "".join(filter(str.isdigit, match.group(0)))
            # Canonical Turkish format for WhatsApp (905...)
            if phone.startswith("05"): phone = "9" + phone
            elif phone.startswith("5"): phone = "90" + phone
            elif not phone.startswith("90"): phone = "90" + phone
            return phone
        return None

    def classify(self, text):
        # If no API key, skip AI analysis and just do basic regex
        if not self.model:
            found_phone = self.extract_phone(text)
            is_lead = self.is_strict_lead(text)
            return {
                "is_lead": is_lead,
                "subject": "Özel Ders (AI Kapalı)",
                "contact_info": found_phone,
                "whatsapp_link": f"https://wa.me/{found_phone}" if found_phone else None
            }

        prompt = f"{self.system_prompt}\n\nGirdi Metni:\n{text}"
        try:
            response = self.model.generate_content(prompt)
            json_text = response.text.strip()
            
            # Robust JSON extraction
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "{" in json_text:
                json_text = json_text[json_text.find("{"):json_text.rfind("}")+1]
            
            import json
            result = json.loads(json_text)
            
            # Enrich with regex fallback
            found_phone = self.extract_phone(text)
            if found_phone:
                result["contact_info"] = found_phone
                result["whatsapp_link"] = f"https://wa.me/{found_phone}"
            
            return result
        except (Exception, NotImplementedError) as e:
            # Fallback to basic mode if AI call fails for any reason
            print(f"Classification Warning (Falling back to Basic Mode): {e}")
            is_lead = self.is_strict_lead(text)
            found_phone = self.extract_phone(text)
            return {
                "is_lead": is_lead,
                "subject": "Özel Ders (Basic)",
                "contact_info": found_phone,
                "whatsapp_link": f"https://wa.me/{found_phone}" if found_phone else None,
                "reason": f"AI Analiz Hatası: {str(e)}"
            }

# Test Code
if __name__ == "__main__":
    classifier = LeadClassifier()
    test_text = "Matematik öğretmeni arıyorum, 8. sınıf öğrencisi için."
    # response = classifier.classify(test_text)
    # print(json.dumps(response, indent=2))
    print("Classifier Logic Ready. API Key needed for actual execution.")
