"""
LLM Research Platform - API Kullanım Örnekleri
Bu dosya, RESTful API'nin farklı dillerde nasıl kullanılacağını gösterir
"""

# ============================================
# PYTHON ÖRNEĞI
# ============================================

import requests
import json

BASE_URL = "http://localhost:8080/api/v1"

class LLMResearchClient:
    """Python API Client"""
    
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.token = None
    
    def login(self, email=None, username=None, anonymous=False):
        """Kullanıcı girişi yapar ve token alır"""
        data = {}
        if anonymous:
            data['anonymous'] = True
        elif email:
            data['email'] = email
            if username:
                data['username'] = username
        elif username:
            data['username'] = username
        else:
            raise ValueError("Email, username veya anonymous gerekli")
        
        response = requests.post(f"{self.base_url}/auth/login", json=data)
        response.raise_for_status()
        
        result = response.json()
        self.token = result['token']
        return result['user']
    
    def get_researches(self):
        """Aktif araştırmaları getirir"""
        response = requests.get(f"{self.base_url}/researches")
        response.raise_for_status()
        return response.json()['researches']
    
    def get_research(self, research_id):
        """Belirli bir araştırmanın detaylarını getirir"""
        response = requests.get(f"{self.base_url}/research/{research_id}")
        response.raise_for_status()
        return response.json()['research']
    
    def submit_response(self, case_id, answers, confidence_score=None, 
                       clinical_rationale=None, duration_seconds=None):
        """Vaka yanıtı gönderir"""
        if not self.token:
            raise ValueError("Önce login olmalısınız")
        
        data = {
            'case_id': case_id,
            'answers': answers
        }
        if confidence_score:
            data['confidence_score'] = confidence_score
        if clinical_rationale:
            data['clinical_rationale'] = clinical_rationale
        if duration_seconds:
            data['duration_seconds'] = duration_seconds
        
        headers = {'Authorization': f'Bearer {self.token}'}
        response = requests.post(
            f"{self.base_url}/response",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def get_user_responses(self):
        """Kullanıcının tüm yanıtlarını getirir"""
        if not self.token:
            raise ValueError("Önce login olmalısınız")
        
        headers = {'Authorization': f'Bearer {self.token}'}
        response = requests.get(
            f"{self.base_url}/user/responses",
            headers=headers
        )
        response.raise_for_status()
        return response.json()['responses']
    
    def get_research_findings(self, research_id, published_only=False):
        """Araştırma bulgularını getirir"""
        params = {'published_only': 'true' if published_only else 'false'}
        response = requests.get(
            f"{self.base_url}/research/{research_id}/findings",
            params=params
        )
        response.raise_for_status()
        return response.json()['findings']


# Kullanım örneği
if __name__ == "__main__":
    # Client oluştur
    client = LLMResearchClient()
    
    # Anonim giriş yap
    user = client.login(anonymous=True)
    print(f"Giriş yapıldı: {user['display_name']}")
    
    # Araştırmaları listele
    researches = client.get_researches()
    print(f"\n{len(researches)} araştırma bulundu:")
    for r in researches:
        print(f"  - {r['title']} ({r['case_count']} vaka)")
    
    # İlk araştırmanın detaylarını al
    if researches:
        research = client.get_research(researches[0]['id'])
        print(f"\nAraştırma: {research['title']}")
        print(f"Vaka sayısı: {len(research['cases'])}")
        
        # İlk vakaya yanıt gönder
        if research['cases']:
            case = research['cases'][0]
            response = client.submit_response(
                case_id=case['id'],
                answers={
                    'diagnosis': 'Akut apandisit',
                    'treatment': 'Apendektomi',
                    'tests': 'USG, tam kan sayımı'
                },
                confidence_score=85,
                duration_seconds=120
            )
            print(f"\n✓ Yanıt gönderildi: Response ID {response['response_id']}")
    
    # Kullanıcı yanıtlarını listele
    my_responses = client.get_user_responses()
    print(f"\nToplam {len(my_responses)} yanıt gönderildi")


# ============================================
# JAVASCRIPT/NODE.JS ÖRNEĞI
# ============================================

"""
// Node.js örneği (async/await ile)
const axios = require('axios');

const BASE_URL = 'http://localhost:8080/api/v1';

class LLMResearchClient {
  constructor(baseUrl = BASE_URL) {
    this.baseUrl = baseUrl;
    this.token = null;
  }

  async login({ email, username, anonymous = false }) {
    const data = {};
    if (anonymous) {
      data.anonymous = true;
    } else if (email) {
      data.email = email;
      if (username) data.username = username;
    } else if (username) {
      data.username = username;
    }

    const response = await axios.post(`${this.baseUrl}/auth/login`, data);
    this.token = response.data.token;
    return response.data.user;
  }

  async getResearches() {
    const response = await axios.get(`${this.baseUrl}/researches`);
    return response.data.researches;
  }

  async getResearch(researchId) {
    const response = await axios.get(`${this.baseUrl}/research/${researchId}`);
    return response.data.research;
  }

  async submitResponse(data) {
    const response = await axios.post(
      `${this.baseUrl}/response`,
      data,
      {
        headers: { 'Authorization': `Bearer ${this.token}` }
      }
    );
    return response.data;
  }

  async getUserResponses() {
    const response = await axios.get(
      `${this.baseUrl}/user/responses`,
      {
        headers: { 'Authorization': `Bearer ${this.token}` }
      }
    );
    return response.data.responses;
  }
}

// Kullanım
(async () => {
  const client = new LLMResearchClient();
  
  // Anonim giriş
  const user = await client.login({ anonymous: true });
  console.log(`Giriş yapıldı: ${user.display_name}`);
  
  // Araştırmaları listele
  const researches = await client.getResearches();
  console.log(`${researches.length} araştırma bulundu`);
  
  // Yanıt gönder
  if (researches.length > 0) {
    const research = await client.getResearch(researches[0].id);
    if (research.cases.length > 0) {
      const response = await client.submitResponse({
        case_id: research.cases[0].id,
        answers: {
          diagnosis: 'Akut apandisit',
          treatment: 'Apendektomi'
        },
        confidence_score: 90
      });
      console.log(`✓ Yanıt gönderildi: ${response.response_id}`);
    }
  }
})();
"""


# ============================================
# CURL ÖRNEKLERI
# ============================================

CURL_EXAMPLES = """
# 1. Anonim Giriş
curl -X POST http://localhost:8080/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"anonymous": true}'

# 2. Email ile Giriş
curl -X POST http://localhost:8080/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"email": "user@example.com", "username": "Dr. Ahmet"}'

# 3. Araştırma Listesi
curl http://localhost:8080/api/v1/researches

# 4. Araştırma Detayları
curl http://localhost:8080/api/v1/research/1

# 5. Yanıt Gönder (token gerekli)
curl -X POST http://localhost:8080/api/v1/response \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \\
  -d '{
    "case_id": 1,
    "answers": {
      "diagnosis": "Akut apandisit",
      "treatment": "Apendektomi",
      "tests": "USG, tam kan"
    },
    "confidence_score": 85,
    "duration_seconds": 120
  }'

# 6. Kullanıcı Yanıtları
curl http://localhost:8080/api/v1/user/responses \\
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# 7. Araştırma İstatistikleri (Admin)
curl http://localhost:8080/api/v1/research/1/stats \\
  -H "Authorization: Bearer ADMIN_TOKEN_HERE"

# 8. Araştırma Bulguları
curl "http://localhost:8080/api/v1/research/1/findings?published_only=true"

# 9. Health Check
curl http://localhost:8080/api/v1/health
"""

print("\n" + "="*60)
print("CURL KOMUT ÖRNEKLERİ")
print("="*60)
print(CURL_EXAMPLES)
