import os
import sys
import json
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.stdout.reconfigure(encoding='utf-8')

from core.classifier import LeadClassifier

def run_tests():
    # Load dataset
    dataset_path = os.path.join(os.path.dirname(__file__), "golden_dataset.json")
    if not os.path.exists(dataset_path):
        print(f"❌ Golden dataset not found at {dataset_path}!")
        sys.exit(1)
        
    with open(dataset_path, 'r', encoding='utf-8') as f:
        test_cases = json.load(f)
        
    print(f"📊 Altın Veri Kümesi Sınıflandırma Testi Başlatıldı ({len(test_cases)} İlan)...")
    print("="*60)
    
    classifier = LeadClassifier()
    passed = 0
    failed = 0
    failures = []
    
    for idx, case in enumerate(test_cases):
        text = case["text"]
        expected_lead = case["is_lead"]
        
        # Run classification
        res = classifier.classify(text)
        actual_lead = res.get("is_lead", False)
        
        if actual_lead == expected_lead:
            passed += 1
            status = "✅ PASSED"
        else:
            failed += 1
            status = "❌ FAILED"
            failures.append({
                "index": idx + 1,
                "text": text,
                "expected": "LEAD" if expected_lead else "SPAM/AD",
                "actual": "LEAD" if actual_lead else "SPAM/AD",
                "extracted_info": res
            })
            
        print(f"[{idx+1:02d}] Expected: {'LEAD' if expected_lead else 'SPAM':4s} | Actual: {'LEAD' if actual_lead else 'SPAM':4s} | {status}")
        
    print("="*60)
    accuracy = (passed / len(test_cases)) * 100
    print(f"📈 Sonuç: {passed} Başarılı, {failed} Başarısız")
    print(f"🎯 Doğruluk Oranı (Accuracy): {accuracy:.2f}%")
    print("="*60)
    
    if failures:
        print("\n🚨 BAŞARISIZ OLAN İLAN DETAYLARI:")
        for fail in failures:
            print(f"\nİlan #{fail['index']}:")
            print(f"  Metin: \"{fail['text']}\"")
            print(f"  Beklenen Sınıf: {fail['expected']}")
            print(f"  Verilen Sınıf:   {fail['actual']}")
            print(f"  AI Çıktısı:      {json.dumps(fail['extracted_info'], ensure_ascii=False)}")
            print("-" * 40)
            
    # Exit with error code if accuracy is below 90%
    if accuracy < 90.0:
        print("❌ HATA: Sınıflandırma başarı oranı kabul edilebilir limitin (%90) altında!")
        sys.exit(1)
    else:
        print("🎉 TEBRİKLER: Sınıflandırma testleri başarıyla geçti!")
        sys.exit(0)

if __name__ == "__main__":
    run_tests()
