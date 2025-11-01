# -*- coding: utf-8 -*-
"""
Gemini API Servis Modülü
Gelişmiş rate limiting, batch processing, error handling özellikleri ile
"""

import os
import time
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import google.generativeai as genai
from functools import wraps
import logging

# Logger yapılandırması
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RateLimiter:
    """API çağrıları için rate limiting."""
    
    def __init__(self, max_calls_per_minute=60, max_calls_per_day=1500):
        self.max_calls_per_minute = max_calls_per_minute
        self.max_calls_per_day = max_calls_per_day
        self.minute_calls = []
        self.day_calls = []
    
    def can_make_call(self) -> bool:
        """Yeni bir API çağrısı yapılabilir mi kontrol eder."""
        now = datetime.now()
        
        # Eski çağrıları temizle
        self.minute_calls = [t for t in self.minute_calls if now - t < timedelta(minutes=1)]
        self.day_calls = [t for t in self.day_calls if now - t < timedelta(days=1)]
        
        # Limit kontrolü
        if len(self.minute_calls) >= self.max_calls_per_minute:
            return False
        if len(self.day_calls) >= self.max_calls_per_day:
            return False
        
        return True
    
    def record_call(self):
        """Yeni bir API çağrısını kaydeder."""
        now = datetime.now()
        self.minute_calls.append(now)
        self.day_calls.append(now)
    
    def wait_if_needed(self):
        """Gerekirse rate limit için bekler."""
        while not self.can_make_call():
            logger.warning("Rate limit reached. Waiting 5 seconds...")
            time.sleep(5)


class GeminiService:
    """Gemini API için gelişmiş servis sınıfı."""
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-pro"):
        """
        Args:
            api_key: Gemini API anahtarı (None ise env'den alınır)
            model_name: Kullanılacak model adı
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.model = None
        self.rate_limiter = RateLimiter()
        
        if not self.api_key:
            logger.error("GEMINI_API_KEY bulunamadı!")
            raise ValueError("GEMINI_API_KEY gerekli")
        
        self._configure_api()
    
    def _configure_api(self):
        """API'yi yapılandırır."""
        try:
            genai.configure(api_key=self.api_key)
            
            # Mevcut modelleri listele ve uygun olanı seç
            available_models = []
            try:
                models_list = genai.list_models()
                for m in models_list:
                    name = None
                    if isinstance(m, dict):
                        name = m.get('name') or m.get('id')
                    elif hasattr(m, 'name'):
                        name = m.name
                    elif hasattr(m, 'model_name'):
                        name = m.model_name
                    
                    if name and 'generateContent' in str(getattr(m, 'supported_generation_methods', [])):
                        available_models.append(name)
            except Exception as e:
                logger.warning(f"Model listesi alınamadı: {e}")
            
            # Model seç
            if available_models:
                chosen = available_models[0]
                self.model = genai.GenerativeModel(chosen)
                logger.info(f"Gemini modeli başarıyla yüklendi: {chosen}")
            else:
                # Varsayılan model
                self.model = genai.GenerativeModel('gemini-pro')
                logger.info("Varsayılan Gemini Pro modeli yüklendi")
                
        except Exception as e:
            logger.error(f"Gemini API yapılandırma hatası: {e}")
            raise
    
    def generate_content(self, prompt: str, retry_count: int = 3) -> Dict[str, Any]:
        """
        İçerik üretir, hata yönetimi ve retry mekanizması ile.
        
        Args:
            prompt: Üretilecek içerik için prompt
            retry_count: Hata durumunda deneme sayısı
            
        Returns:
            Dict: {'success': bool, 'text': str, 'error': str}
        """
        if not self.model:
            return {'success': False, 'error': 'Model yüklenmedi', 'text': ''}
        
        for attempt in range(retry_count):
            try:
                # Rate limiting kontrol
                self.rate_limiter.wait_if_needed()
                self.rate_limiter.record_call()
                
                # API çağrısı
                response = self.model.generate_content(prompt)
                
                return {
                    'success': True,
                    'text': response.text,
                    'error': None
                }
                
            except Exception as e:
                logger.error(f"Gemini API hatası (deneme {attempt + 1}/{retry_count}): {e}")
                
                if attempt < retry_count - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    logger.info(f"{wait_time} saniye bekleniyor...")
                    time.sleep(wait_time)
                else:
                    return {
                        'success': False,
                        'error': str(e),
                        'text': ''
                    }
        
        return {'success': False, 'error': 'Bilinmeyen hata', 'text': ''}
    
    def batch_generate(self, prompts: List[str], delay_between_calls: float = 1.0) -> List[Dict[str, Any]]:
        """
        Birden fazla prompt için toplu içerik üretimi.
        
        Args:
            prompts: Prompt listesi
            delay_between_calls: Çağrılar arası bekleme süresi (saniye)
            
        Returns:
            List[Dict]: Her prompt için sonuç listesi
        """
        results = []
        
        for i, prompt in enumerate(prompts):
            logger.info(f"Batch işlemi: {i + 1}/{len(prompts)}")
            
            result = self.generate_content(prompt)
            results.append(result)
            
            # Son prompt değilse bekle
            if i < len(prompts) - 1 and delay_between_calls > 0:
                time.sleep(delay_between_calls)
        
        return results
    
    def score_answer(self, user_answer: str, gold_answer: str, category: str) -> Dict[str, Any]:
        """
        Kullanıcı yanıtını değerlendirir.
        
        Args:
            user_answer: Kullanıcının cevabı
            gold_answer: Altın standart cevap
            category: Kategori (tanı, tedavi, vb.)
            
        Returns:
            Dict: {'score': int, 'reasoning': str, 'success': bool}
        """
        prompt = f"""
Sen, bir hekimin vaka yanıtının '{category}' bölümünü değerlendiren, pragmatik ve deneyimli bir klinik uzmansın.
Temel görevin, "Kullanıcı Yanıtı"nın, hastanın doğru ve güvenli bir şekilde tedavi edilmesini sağlayacak kadar YETERLİ olup olmadığını değerlendirmektir.
Kullanıcının yanıtını "Altın Standart Yanıt" ile anlamsal olarak karşılaştır ve 0-100 arasında bir puan ver.

Değerlendirme Kuralları:
1. YETERLİLİK: Kullanıcının yanıtı, klinik olarak en önemli unsurları içeriyorsa tam puan ver.
2. TETKİK: 'Tetkik' kategorisinde, altın standart 'gerekmez' diyorsa, kullanıcının da 'yok' veya 'gerekmez' demesine tam puan ver.
3. DOZAJ: 'Dozaj' kategorisinde, ilacın adından ziyade dozun, sıklığın ve uygulama şeklinin doğruluğuna odaklan.

Yanıtını SADECE şu JSON formatında ver:
{{ "score": <0-100 arası sayı>, "reasoning": "<1 cümlelik Türkçe gerekçe>" }}
---
Altın Standart Yanıt ({category}): "{gold_answer}"
---
Kullanıcı Yanıtı ({category}): "{user_answer}"
---
"""
        
        result = self.generate_content(prompt)
        
        if not result['success']:
            return {
                'score': 0,
                'reasoning': f"API Hatası: {result['error']}",
                'success': False
            }
        
        try:
            parsed = json.loads(result['text'])
            return {
                'score': int(parsed.get('score', 0)),
                'reasoning': parsed.get('reasoning', 'Gerekçe alınamadı'),
                'success': True
            }
        except Exception as e:
            logger.error(f"JSON parse hatası: {e}, Response: {result['text']}")
            return {
                'score': 0,
                'reasoning': f"Parse hatası: {e}",
                'success': False
            }
    
    def generate_research_summary(self, research_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Araştırma verilerinden özet/bulgu metni oluşturur.
        
        Args:
            research_data: Araştırma istatistikleri ve verileri
            
        Returns:
            Dict: {'success': bool, 'summary': str}
        """
        prompt = f"""
Sen deneyimli bir tıbbi araştırmacısın. Aşağıdaki araştırma verilerine dayalı olarak akademik bir "Bulgular" bölümü yaz.

Araştırma Başlığı: {research_data.get('title', 'Bilinmiyor')}
Toplam Katılımcı: {research_data.get('total_participants', 0)}
Toplam Yanıt: {research_data.get('total_responses', 0)}
Ortalama Deneyim: {research_data.get('avg_experience', 0):.1f} yıl
Ortalama Güven Skoru: {research_data.get('avg_confidence', 0):.1f}
Ortalama Performans: {research_data.get('avg_performance', 0):.1f}

Lütfen:
1. Profesyonel, bilimsel bir dil kullan
2. Sayısal verileri yorumla
3. Önemli bulguları vurgula
4. 3-4 paragraf halinde yaz
5. Tablo ve grafiklerle desteklenebilecek şekilde yapılandır

Bulgular:
"""
        
        result = self.generate_content(prompt)
        
        return {
            'success': result['success'],
            'summary': result['text'] if result['success'] else '',
            'error': result.get('error')
        }


# Global servis instance
_gemini_service = None

def get_gemini_service() -> Optional[GeminiService]:
    """Global Gemini servis instance'ını döndürür."""
    global _gemini_service
    
    if _gemini_service is None:
        try:
            _gemini_service = GeminiService()
        except Exception as e:
            logger.error(f"Gemini servis başlatılamadı: {e}")
            return None
    
    return _gemini_service


# Decorator: Rate limiting ile fonksiyonları korur
def with_rate_limit(func):
    """Rate limiting decorator."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        service = get_gemini_service()
        if service:
            service.rate_limiter.wait_if_needed()
            service.rate_limiter.record_call()
        return func(*args, **kwargs)
    return wrapper
