# -*- coding: utf-8 -*-
"""
Gelişmiş İstatistiksel Analiz Modülü
Korelasyon, regresyon, dağılım analizleri ve interaktif görselleştirmeler
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # GUI gerektirmeyen backend
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import io
import base64
import json


def set_plot_style():
    """Grafik stil ayarlarını uygular."""
    sns.set_theme(style="whitegrid", palette="muted")
    plt.rcParams['figure.figsize'] = (10, 6)
    plt.rcParams['font.size'] = 10


def create_correlation_matrix(df, research_id):
    """
    Numerik değişkenler arasında korelasyon matrisi oluşturur.
    
    Args:
        df: Analiz edilecek DataFrame
        research_id: Araştırma ID
        
    Returns:
        dict: Plotly figure ve insights içeren dict
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    # Anlamlı sütunları filtrele
    exclude_cols = ['id', 'response_id', 'user_id', 'case_id', 'research_id']
    numeric_cols = [col for col in numeric_cols if col not in exclude_cols]
    
    if len(numeric_cols) < 2:
        return {'error': 'Korelasyon analizi için yeterli numerik değişken yok'}
    
    # Korelasyon hesapla
    corr_matrix = df[numeric_cols].corr()
    
    # Plotly ile heatmap
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.columns,
        colorscale='RdBu',
        zmid=0,
        text=corr_matrix.values.round(2),
        texttemplate='%{text}',
        textfont={"size": 10},
        colorbar=dict(title="Korelasyon")
    ))
    
    fig.update_layout(
        title='Değişkenler Arası Korelasyon Matrisi',
        xaxis_title='Değişkenler',
        yaxis_title='Değişkenler',
        height=600,
        width=800
    )
    
    # Güçlü korelasyonları bul
    strong_correlations = []
    for i in range(len(corr_matrix.columns)):
        for j in range(i+1, len(corr_matrix.columns)):
            corr_val = corr_matrix.iloc[i, j]
            if abs(corr_val) > 0.5:
                strong_correlations.append({
                    'var1': corr_matrix.columns[i],
                    'var2': corr_matrix.columns[j],
                    'correlation': round(corr_val, 3)
                })
    
    return {
        'figure': fig.to_json(),
        'strong_correlations': strong_correlations,
        'correlation_matrix': corr_matrix.to_dict()
    }


def perform_regression_analysis(df, target_var='user_final_score', predictors=None):
    """
    Çoklu doğrusal regresyon analizi yapar.
    
    Args:
        df: DataFrame
        target_var: Hedef değişken (bağımlı değişken)
        predictors: Bağımsız değişkenler listesi (None ise otomatik seçilir)
        
    Returns:
        dict: Regresyon sonuçları ve görselleştirmeler
    """
    if target_var not in df.columns:
        return {'error': f'{target_var} sütunu bulunamadı'}
    
    # Bağımsız değişkenleri belirle
    if predictors is None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        exclude = ['id', 'response_id', 'user_id', 'case_id', target_var]
        predictors = [col for col in numeric_cols if col not in exclude]
    
    # Eksik değerleri temizle
    analysis_df = df[[target_var] + predictors].dropna()
    
    if len(analysis_df) < 10:
        return {'error': 'Regresyon için yeterli veri yok'}
    
    X = analysis_df[predictors]
    y = analysis_df[target_var]
    
    # Model oluştur
    model = LinearRegression()
    model.fit(X, y)
    
    # Predictions
    y_pred = model.predict(X)
    
    # R² skorunu hesapla
    r2_score = model.score(X, y)
    
    # Katsayılar
    coefficients = pd.DataFrame({
        'Değişken': predictors,
        'Katsayı': model.coef_,
        'Abs_Katsayı': np.abs(model.coef_)
    }).sort_values('Abs_Katsayı', ascending=False)
    
    # Visualization: Actual vs Predicted
    fig_scatter = go.Figure()
    fig_scatter.add_trace(go.Scatter(
        x=y, y=y_pred,
        mode='markers',
        name='Veri Noktaları',
        marker=dict(size=8, color='blue', opacity=0.6)
    ))
    
    # Perfect prediction line
    min_val, max_val = y.min(), y.max()
    fig_scatter.add_trace(go.Scatter(
        x=[min_val, max_val],
        y=[min_val, max_val],
        mode='lines',
        name='Mükemmel Tahmin',
        line=dict(color='red', dash='dash')
    ))
    
    fig_scatter.update_layout(
        title=f'Gerçek vs Tahmin Edilen {target_var}<br>R² = {r2_score:.3f}',
        xaxis_title=f'Gerçek {target_var}',
        yaxis_title=f'Tahmin Edilen {target_var}',
        height=500
    )
    
    # Coefficient importance plot
    fig_coef = px.bar(
        coefficients,
        x='Katsayı',
        y='Değişken',
        orientation='h',
        title='Değişken Önem Sıralaması (Regresyon Katsayıları)'
    )
    
    return {
        'r2_score': round(r2_score, 4),
        'intercept': round(model.intercept_, 4),
        'coefficients': coefficients.to_dict('records'),
        'scatter_plot': fig_scatter.to_json(),
        'coefficient_plot': fig_coef.to_json(),
        'n_samples': len(analysis_df)
    }


def create_distribution_plots(df):
    """
    Ana değişkenlerin dağılım grafiklerini oluşturur.
    
    Returns:
        dict: Farklı dağılım grafikleri
    """
    plots = {}
    
    # 1. Confidence Score Distribution
    if 'confidence_score' in df.columns:
        valid_conf = df[df['confidence_score'] > 0]['confidence_score']
        if not valid_conf.empty:
            fig_conf = go.Figure()
            fig_conf.add_trace(go.Histogram(
                x=valid_conf,
                nbinsx=20,
                name='Güven Skoru',
                marker_color='lightblue'
            ))
            fig_conf.update_layout(
                title='Güven Skoru Dağılımı',
                xaxis_title='Güven Skoru',
                yaxis_title='Frekans',
                height=400
            )
            plots['confidence_distribution'] = fig_conf.to_json()
    
    # 2. Experience Distribution
    if 'user_experience' in df.columns:
        fig_exp = px.histogram(
            df,
            x='user_experience',
            nbins=15,
            title='Deneyim Yılı Dağılımı',
            labels={'user_experience': 'Deneyim (Yıl)'}
        )
        plots['experience_distribution'] = fig_exp.to_json()
    
    # 3. Duration Distribution
    if 'duration_seconds' in df.columns:
        valid_duration = df[df['duration_seconds'] > 0]['duration_seconds']
        if not valid_duration.empty:
            fig_dur = go.Figure()
            fig_dur.add_trace(go.Box(
                y=valid_duration,
                name='Tamamlanma Süresi',
                marker_color='lightgreen'
            ))
            fig_dur.update_layout(
                title='Vaka Tamamlanma Süresi Dağılımı',
                yaxis_title='Süre (Saniye)',
                height=400
            )
            plots['duration_distribution'] = fig_dur.to_json()
    
    # 4. Final Score Distribution
    if 'user_final_score' in df.columns:
        valid_scores = df[df['user_final_score'] > 0]['user_final_score']
        if not valid_scores.empty:
            fig_score = px.violin(
                y=valid_scores,
                box=True,
                title='Kullanıcı Final Skor Dağılımı',
                labels={'y': 'Final Skor'}
            )
            plots['score_distribution'] = fig_score.to_json()
    
    return plots


def perform_statistical_tests(df):
    """
    Çeşitli istatistiksel testler gerçekleştirir.
    
    Returns:
        dict: Test sonuçları
    """
    results = {}
    
    # 1. Profession vs Performance (ANOVA)
    if 'user_profession' in df.columns and 'user_final_score' in df.columns:
        groups = df.groupby('user_profession')['user_final_score'].apply(list)
        if len(groups) > 1:
            f_stat, p_value = stats.f_oneway(*groups)
            results['anova_profession_performance'] = {
                'test': 'ANOVA - Meslek vs Performans',
                'f_statistic': round(f_stat, 4),
                'p_value': round(p_value, 4),
                'significant': p_value < 0.05
            }
    
    # 2. Confidence vs Performance (Pearson Correlation)
    if 'confidence_score' in df.columns and 'user_final_score' in df.columns:
        valid_data = df[(df['confidence_score'] > 0) & (df['user_final_score'] > 0)]
        if len(valid_data) > 2:
            corr, p_value = stats.pearsonr(
                valid_data['confidence_score'],
                valid_data['user_final_score']
            )
            results['pearson_confidence_performance'] = {
                'test': 'Pearson Korelasyon - Güven vs Performans',
                'correlation': round(corr, 4),
                'p_value': round(p_value, 4),
                'significant': p_value < 0.05
            }
    
    # 3. Experience vs Duration (Correlation)
    if 'user_experience' in df.columns and 'duration_seconds' in df.columns:
        valid_data = df[(df['user_experience'] > 0) & (df['duration_seconds'] > 0)]
        if len(valid_data) > 2:
            corr, p_value = stats.pearsonr(
                valid_data['user_experience'],
                valid_data['duration_seconds']
            )
            results['pearson_experience_duration'] = {
                'test': 'Pearson Korelasyon - Deneyim vs Süre',
                'correlation': round(corr, 4),
                'p_value': round(p_value, 4),
                'significant': p_value < 0.05
            }
    
    return results


def create_interactive_dashboard_data(df, research_id):
    """
    Interaktif dashboard için tüm analizleri bir arada çalıştırır.
    
    Returns:
        dict: Tüm analiz sonuçları
    """
    dashboard_data = {
        'research_id': research_id,
        'total_responses': len(df),
        'timestamp': pd.Timestamp.now().isoformat()
    }
    
    # Korelasyon analizi
    dashboard_data['correlation'] = create_correlation_matrix(df, research_id)
    
    # Regresyon analizi
    if 'user_final_score' in df.columns:
        dashboard_data['regression'] = perform_regression_analysis(df)
    
    # Dağılım grafikleri
    dashboard_data['distributions'] = create_distribution_plots(df)
    
    # İstatistiksel testler
    dashboard_data['statistical_tests'] = perform_statistical_tests(df)
    
    # Temel istatistikler
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    dashboard_data['descriptive_stats'] = df[numeric_cols].describe().to_dict()
    
    return dashboard_data


def generate_matplotlib_plot(df, plot_type='scatter', x_col=None, y_col=None):
    """
    Matplotlib kullanarak statik grafik oluşturur ve base64 string döndürür.
    
    Args:
        df: DataFrame
        plot_type: 'scatter', 'hist', 'box', 'line'
        x_col, y_col: Sütun adları
        
    Returns:
        str: Base64 encoded image
    """
    set_plot_style()
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    if plot_type == 'scatter' and x_col and y_col:
        ax.scatter(df[x_col], df[y_col], alpha=0.6)
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        ax.set_title(f'{y_col} vs {x_col}')
        
        # Trend line
        z = np.polyfit(df[x_col].dropna(), df[y_col].dropna(), 1)
        p = np.poly1d(z)
        ax.plot(df[x_col], p(df[x_col]), "r--", alpha=0.8, label='Trend')
        ax.legend()
    
    elif plot_type == 'hist' and x_col:
        ax.hist(df[x_col].dropna(), bins=20, edgecolor='black', alpha=0.7)
        ax.set_xlabel(x_col)
        ax.set_ylabel('Frekans')
        ax.set_title(f'{x_col} Histogram')
    
    elif plot_type == 'box' and y_col:
        ax.boxplot(df[y_col].dropna())
        ax.set_ylabel(y_col)
        ax.set_title(f'{y_col} Box Plot')
    
    plt.tight_layout()
    
    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()
    
    return f"data:image/png;base64,{image_base64}"
