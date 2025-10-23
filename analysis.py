import pandas as pd
# DO NOT import app, db or models at the top level

def get_research_responses_df(research_id):
    """
    Belirli bir araştırmaya ait tüm yanıtları ve ilgili kullanıcı/vaka
    bilgilerini içeren bir Pandas DataFrame döndürür.
    """
    # Import app and models *inside* the function where needed
    from app import app, UserResponse, Case 

    with app.app_context(): # Ensure we have application context
        # Now access models via the locally imported names
        responses = UserResponse.query.join(Case).filter(Case.research_id == research_id).all()

        data = []
        for r in responses:
            author = getattr(r, 'author', None)
            case = getattr(r, 'case', None)
            case_content = getattr(case, 'content', {}) or {}
            llm_scores = getattr(case, 'llm_scores', {}) or {}
            user_scores = getattr(r, 'scores', {}) or {}

            row = {
                'response_id': r.id,
                'user_id': getattr(author, 'id', None),
                'user_profession': getattr(author, 'profession', 'Bilinmiyor') or 'Bilinmiyor',
                'user_experience': getattr(author, 'experience', 0) or 0,
                'case_id': getattr(case, 'id', None),
                'case_title': case_content.get('title', ''),
                'duration_seconds': getattr(r, 'duration_seconds', 0) or 0,
                'confidence_score': getattr(r, 'confidence_score', 0) or 0,
                'clinical_rationale': getattr(r, 'clinical_rationale', '') or '',
                'created_at': r.created_at,
                'user_final_score': user_scores.get('final_score', 0.0)
            }

            if isinstance(r.answers, dict):
                row.update(r.answers)

            for llm_name, scores_dict in llm_scores.items():
                 if isinstance(scores_dict, dict):
                     row[f'llm_score_{llm_name}'] = scores_dict.get('overall_score', 0.0)

            data.append(row)

        if not data:
            return pd.DataFrame()

        return pd.DataFrame(data)


def calculate_participant_stats(df):
    """
    Verilen DataFrame'den katılımcı demografileri ve yanıt metrikleri
    ile ilgili temel istatistikleri hesaplar (research_stats sayfası için).
    """
    if df.empty:
        return None 

    stats = {}
    try:
        stats['total_responses'] = len(df)
        if 'user_experience' in df.columns:
            stats['avg_experience'] = float(df['user_experience'].mean())
        else: stats['avg_experience'] = 0.0
        if 'duration_seconds' in df.columns:
            stats['avg_duration'] = float(df['duration_seconds'].mean())
        else: stats['avg_duration'] = 0.0
        if 'confidence_score' in df.columns:
            valid_confidence = df[df['confidence_score'] > 0]['confidence_score']
            stats['avg_confidence'] = float(valid_confidence.mean()) if not valid_confidence.empty else 0.0
        else: stats['avg_confidence'] = 0.0

        if 'user_profession' in df.columns:
            profession_counts = df['user_profession'].value_counts()
            stats['profession_chart'] = {'labels': profession_counts.index.tolist(), 'data': profession_counts.values.tolist()}
        else: stats['profession_chart'] = {'labels': [], 'data': []}

        if 'user_profession' in df.columns and 'confidence_score' in df.columns:
            valid_confidence_df = df[df['confidence_score'] > 0]
            if not valid_confidence_df.empty:
                confidence_by_profession = valid_confidence_df.groupby('user_profession')['confidence_score'].mean().sort_values(ascending=False)
                stats['confidence_by_profession'] = {'labels': confidence_by_profession.index.tolist(), 'data': [float(v) for v in confidence_by_profession.values.tolist()]}
            else: stats['confidence_by_profession'] = {'labels': [], 'data': []}
        else: stats['confidence_by_profession'] = {'labels': [], 'data': []}

        if 'user_experience' in df.columns and 'duration_seconds' in df.columns:
            def categorize_experience(exp):
                if not isinstance(exp, (int, float)) or exp < 0: return 'Bilinmiyor'
                if exp < 5: return '0-5 yıl'
                if exp < 10: return '5-10 yıl'
                if exp < 15: return '10-15 yıl'
                return '15+ yıl'
            df['exp_category'] = df['user_experience'].apply(categorize_experience)
            avg_duration_by_exp = df.groupby('exp_category')['duration_seconds'].mean()
            category_order = ['0-5 yıl', '5-10 yıl', '10-15 yıl', '15+ yıl', 'Bilinmiyor']
            if not avg_duration_by_exp.empty:
                avg_duration_by_exp = avg_duration_by_exp.reindex([c for c in category_order if c in avg_duration_by_exp.index])
                stats['experience_vs_duration'] = {'labels': avg_duration_by_exp.index.tolist(), 'data': [float(v) for v in avg_duration_by_exp.values.tolist()]}
            else: stats['experience_vs_duration'] = {'labels': [], 'data': []}
        else: stats['experience_vs_duration'] = {'labels': [], 'data': []}

        if 'confidence_score' in df.columns:
            confidence_bins = [-1, 0, 25, 50, 75, 100]
            confidence_labels = ['0 (Boş)', '1-25', '26-50', '51-75', '76-100']
            df['confidence_bin'] = pd.cut(df['confidence_score'], bins=confidence_bins, labels=confidence_labels, right=True)
            confidence_dist = df['confidence_bin'].value_counts().sort_index()
            stats['confidence_distribution'] = {'labels': confidence_dist.index.astype(str).tolist(), 'data': confidence_dist.values.tolist()}
        else: stats['confidence_distribution'] = {'labels': [], 'data': []}
        
        return stats
    except Exception as e:
        # Use app logger if possible, otherwise print
        try:
             from app import app
             app.logger.error(f"Katılımcı istatistikleri hesaplanamadı: {e}", exc_info=True)
        except ImportError:
             print(f"HATA: Katılımcı istatistikleri hesaplanamadı: {e}")
        return {'total_responses': len(df)} if not df.empty else None


def calculate_scientific_analytics(df):
    """
    Verilen DataFrame'den İnsan vs. LLM karşılaştırması ve diğer
    bilimsel analizleri yapar (scientific_analytics sayfası için).
    """
    if df.empty:
        return None

    analytics = {}
    try:
        required_human_cols = ['user_profession', 'user_experience', 'user_final_score', 'confidence_score']
        llm_score_cols = sorted([col for col in df.columns if col.startswith('llm_score_')])
        
        avg_human_score = 0.0
        if 'user_final_score' in df.columns:
             valid_human_scores = df[df['user_final_score'] > 0]['user_final_score'] 
             if not valid_human_scores.empty:
                 avg_human_score = float(valid_human_scores.mean())
                 
        performance_labels = []
        performance_data = []
        if 'user_final_score' in df.columns: 
             performance_labels.append('İnsan (Ortalama)')
             performance_data.append(round(avg_human_score, 2))
        for col in llm_score_cols:
            llm_name = col.replace('llm_score_', '')
            avg_llm_score = float(df[col].mean()) if col in df.columns else 0.0 
            performance_labels.append(llm_name)
            performance_data.append(round(avg_llm_score, 2))
        analytics['overall_performance'] = {'labels': performance_labels, 'data': performance_data}

        if 'user_final_score' in df.columns and 'user_profession' in df.columns:
            valid_perf_df = df[df['user_final_score'] > 0]
            if not valid_perf_df.empty:
                perf_by_profession = valid_perf_df.groupby('user_profession')['user_final_score'].mean().sort_values(ascending=False)
                analytics['performance_by_profession'] = {'labels': perf_by_profession.index.tolist(), 'data': [round(float(x), 2) for x in perf_by_profession.values.tolist()]}
            else: analytics['performance_by_profession'] = {'labels': [], 'data': []}
        else: analytics['performance_by_profession'] = {'labels': [], 'data': []}

        analytics['confidence_correlation'] = None 
        if 'user_final_score' in df.columns and 'confidence_score' in df.columns:
            valid_corr_df = df[(df['user_final_score'] > 0) & (df['confidence_score'] > 0)]
            if not valid_corr_df.empty and len(valid_corr_df) > 1: 
                correlation = float(valid_corr_df['confidence_score'].corr(valid_corr_df['user_final_score']))
                if pd.notna(correlation): 
                    analytics['confidence_correlation'] = round(correlation, 3)

        avg_confidence_val = 0.0
        if 'confidence_score' in df.columns:
             valid_confidence_scores = df[df['confidence_score'] > 0]['confidence_score']
             if not valid_confidence_scores.empty:
                 avg_confidence_val = float(valid_confidence_scores.mean())
        analytics['summary'] = {
            'total_responses': len(df),
            'avg_human_score': round(avg_human_score, 2),
            'avg_confidence': round(avg_confidence_val, 2),
            'avg_experience': round(float(df['user_experience'].mean()), 1) if 'user_experience' in df.columns else 0.0
        }
        return analytics
    except Exception as e:
        try:
             from app import app
             app.logger.error(f"Bilimsel analizler hesaplanamadı: {e}", exc_info=True)
        except ImportError:
            print(f"HATA: Bilimsel analizler hesaplanamadı: {e}")
        return analytics if analytics else None # Return partial if available