# -*- coding: utf-8 -*-
"""
RESTful API Endpoints
Flask-CORS ile CORS desteği, token authentication, veri validasyonu
"""

from flask import Blueprint, jsonify, request
from flask_cors import cross_origin
from functools import wraps
import jwt
import datetime
import os

# API Blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# JWT Secret Key
JWT_SECRET = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'

# Import edilecek modüller lazy import ile
def get_models():
    """Lazy import to avoid circular imports"""
    from app import db, User, Research, Case, UserResponse, ResearchFinding
    return db, User, Research, Case, UserResponse, ResearchFinding

def get_analysis_functions():
    """Lazy import for analysis functions"""
    from analysis import get_research_responses_df, calculate_participant_stats, calculate_scientific_analytics
    return get_research_responses_df, calculate_participant_stats, calculate_scientific_analytics


# --- AUTHENTICATION ---

def generate_token(user_id: int, email: str) -> str:
    """JWT token oluşturur."""
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=30)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def token_required(f):
    """API endpoint'leri için token authentication decorator."""
    @wraps(f)
    def decorated(*args, **kwargs):
        db, User, Research, Case, UserResponse, ResearchFinding = get_models()
        
        token = None
        
        # Header'dan token al
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # "Bearer TOKEN"
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            current_user = db.session.get(User, data['user_id'])
            
            if not current_user:
                return jsonify({'error': 'User not found'}), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated


# --- API ENDPOINTS ---

@api_bp.route('/auth/login', methods=['POST'])
@cross_origin()
def api_login():
    """
    API Login endpoint
    POST /api/v1/auth/login
    Body: {"email": "user@example.com"} or {"username": "user"} or {"anonymous": true}
    """
    db, User, Research, Case, UserResponse, ResearchFinding = get_models()
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    user = None
    
    # Anonim kullanıcı
    if data.get('anonymous'):
        import uuid
        user = User(
            anonymous_id=str(uuid.uuid4()),
            is_anonymous=True
        )
        db.session.add(user)
        db.session.commit()
    
    # Email ile giriş
    elif 'email' in data:
        email = data['email'].lower().strip()
        user = User.query.filter_by(email=email).first()
        
        if not user:
            user = User(email=email, username=data.get('username'))
            db.session.add(user)
            db.session.commit()
    
    # Username ile giriş
    elif 'username' in data:
        username = data['username'].strip()
        user = User.query.filter_by(username=username).first()
        
        if not user:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()
    
    else:
        return jsonify({'error': 'Email, username or anonymous flag required'}), 400
    
    # Token oluştur
    token = generate_token(user.id, user.email or 'anonymous')
    
    return jsonify({
        'success': True,
        'token': token,
        'user': {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'is_anonymous': user.is_anonymous,
            'display_name': user.get_display_name()
        }
    }), 200


@api_bp.route('/researches', methods=['GET'])
@cross_origin()
def get_researches():
    """
    Aktif araştırmaları listeler
    GET /api/v1/researches
    """
    db, User, Research, Case, UserResponse, ResearchFinding = get_models()
    
    researches = Research.query.filter_by(is_active=True).all()
    
    return jsonify({
        'success': True,
        'researches': [{
            'id': r.id,
            'title': r.title,
            'description': r.description,
            'is_active': r.is_active,
            'case_count': len(r.cases)
        } for r in researches]
    }), 200


@api_bp.route('/research/<int:research_id>', methods=['GET'])
@cross_origin()
def get_research(research_id):
    """
    Belirli bir araştırmanın detaylarını getirir
    GET /api/v1/research/<id>
    """
    db, User, Research, Case, UserResponse, ResearchFinding = get_models()
    
    research = db.session.get(Research, research_id)
    
    if not research:
        return jsonify({'error': 'Research not found'}), 404
    
    return jsonify({
        'success': True,
        'research': {
            'id': research.id,
            'title': research.title,
            'description': research.description,
            'is_active': research.is_active,
            'case_count': len(research.cases),
            'cases': [{
                'id': c.id,
                'title': (c.content or {}).get('title', 'Untitled'),
                'content': c.content
            } for c in research.cases]
        }
    }), 200


@api_bp.route('/research/<int:research_id>/stats', methods=['GET'])
@cross_origin()
@token_required
def get_research_stats(current_user, research_id):
    """
    Araştırma istatistiklerini getirir
    GET /api/v1/research/<id>/stats
    Requires: Authorization header with Bearer token
    """
    db, User, Research, Case, UserResponse, ResearchFinding = get_models()
    get_research_responses_df, calculate_participant_stats, calculate_scientific_analytics = get_analysis_functions()
    
    research = db.session.get(Research, research_id)
    
    if not research:
        return jsonify({'error': 'Research not found'}), 404
    
    # Admin kontrolü (opsiyonel)
    if not current_user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
    
    df = get_research_responses_df(research_id)
    
    if df.empty:
        return jsonify({
            'success': True,
            'stats': None,
            'message': 'No data available'
        }), 200
    
    stats = calculate_participant_stats(df)
    analytics = calculate_scientific_analytics(df)
    
    return jsonify({
        'success': True,
        'stats': stats,
        'analytics': analytics
    }), 200


@api_bp.route('/case/<int:case_id>', methods=['GET'])
@cross_origin()
def get_case(case_id):
    """
    Vaka detaylarını getirir
    GET /api/v1/case/<id>
    """
    db, User, Research, Case, UserResponse, ResearchFinding = get_models()
    
    case = db.session.get(Case, case_id)
    
    if not case:
        return jsonify({'error': 'Case not found'}), 404
    
    return jsonify({
        'success': True,
        'case': {
            'id': case.id,
            'research_id': case.research_id,
            'content': case.content,
            'llm_scores': case.llm_scores
        }
    }), 200


@api_bp.route('/response', methods=['POST'])
@cross_origin()
@token_required
def submit_response(current_user):
    """
    Kullanıcı yanıtı gönderir
    POST /api/v1/response
    Body: {
        "case_id": 1,
        "answers": {...},
        "confidence_score": 85,
        "clinical_rationale": "...",
        "duration_seconds": 120
    }
    """
    db, User, Research, Case, UserResponse, ResearchFinding = get_models()
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Validasyon
    required_fields = ['case_id', 'answers']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    case = db.session.get(Case, data['case_id'])
    if not case:
        return jsonify({'error': 'Case not found'}), 404
    
    # Yanıt oluştur
    response = UserResponse(
        case_id=data['case_id'],
        user_id=current_user.id,
        answers=data['answers'],
        confidence_score=data.get('confidence_score'),
        clinical_rationale=data.get('clinical_rationale'),
        duration_seconds=data.get('duration_seconds')
    )
    
    db.session.add(response)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'response_id': response.id,
        'message': 'Response submitted successfully'
    }), 201


@api_bp.route('/user/responses', methods=['GET'])
@cross_origin()
@token_required
def get_user_responses(current_user):
    """
    Kullanıcının tüm yanıtlarını getirir
    GET /api/v1/user/responses
    """
    db, User, Research, Case, UserResponse, ResearchFinding = get_models()
    
    responses = UserResponse.query.filter_by(user_id=current_user.id).all()
    
    return jsonify({
        'success': True,
        'responses': [{
            'id': r.id,
            'case_id': r.case_id,
            'answers': r.answers,
            'confidence_score': r.confidence_score,
            'scores': r.scores,
            'created_at': r.created_at.isoformat() if r.created_at else None
        } for r in responses]
    }), 200


@api_bp.route('/research/<int:research_id>/findings', methods=['GET'])
@cross_origin()
def get_research_findings(research_id):
    """
    Araştırma bulgularını getirir
    GET /api/v1/research/<id>/findings
    Query params: ?published_only=true
    """
    db, User, Research, Case, UserResponse, ResearchFinding = get_models()
    
    research = db.session.get(Research, research_id)
    
    if not research:
        return jsonify({'error': 'Research not found'}), 404
    
    published_only = request.args.get('published_only', 'false').lower() == 'true'
    
    query = ResearchFinding.query.filter_by(research_id=research_id)
    if published_only:
        query = query.filter_by(is_published=True)
    
    findings = query.order_by(ResearchFinding.order_index).all()
    
    return jsonify({
        'success': True,
        'findings': [{
            'id': f.id,
            'title': f.title,
            'finding_type': f.finding_type,
            'content': f.content,
            'is_published': f.is_published,
            'order_index': f.order_index,
            'created_at': f.created_at.isoformat() if f.created_at else None
        } for f in findings]
    }), 200


@api_bp.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    """
    API health check
    GET /api/v1/health
    """
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'timestamp': datetime.datetime.utcnow().isoformat()
    }), 200


# --- ERROR HANDLERS ---

@api_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@api_bp.errorhandler(500)
def internal_error(error):
    db, User, Research, Case, UserResponse, ResearchFinding = get_models()
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500
