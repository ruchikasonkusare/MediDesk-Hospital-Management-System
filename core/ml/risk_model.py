"""
Readmission Risk Scoring — Logistic Regression
Run once:  python manage.py shell -c "from core.ml.risk_model import train_and_save; train_and_save()"
"""
import os, pickle, numpy as np
from datetime import date, timedelta

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'risk_model.pkl')

HIGH_RISK_KEYWORDS = [
    'diabetes','hypertension','cardiac','heart','copd','cancer',
    'renal','kidney','stroke','asthma','arthritis','obesity',
    'liver','hepatitis','dementia','alzheimer','parkinson',
]
BLOOD_RISK = {
    'O-':0.8,'AB-':0.7,'B-':0.65,'A-':0.6,
    'O+':0.4,'AB+':0.35,'B+':0.3,'A+':0.25,'':0.5,
}


def _features(patient):
    from core.models import Appointment
    today = date.today()
    age   = min(patient.age / 80.0, 1.0)
    conds = (patient.chronic_conditions or '').lower()
    cond_count   = min(len([c for c in conds.split(',') if c.strip()]) / 5.0, 1.0)
    highrisk_cnt = min(sum(1 for k in HIGH_RISK_KEYWORDS if k in conds) / 3.0, 1.0)
    has_allergy  = 1 if (patient.allergies or '').strip() else 0
    visits_90d   = min(Appointment.objects.filter(
        patient=patient,
        appointment_date__gte=today - timedelta(days=90),
        status__in=['completed','no_show','cancelled'],
    ).count() / 10.0, 1.0)
    total = Appointment.objects.filter(patient=patient).count()
    noshows = Appointment.objects.filter(patient=patient, status='no_show').count()
    no_show_rate = noshows / total if total else 0
    bg_risk      = BLOOD_RISK.get(patient.blood_group, 0.5)
    no_insurance = 0 if patient.insurance_provider else 1
    return np.array([age, cond_count, highrisk_cnt, has_allergy,
                     visits_90d, no_show_rate, bg_risk, no_insurance])


def _factors(patient, score):
    facts = []
    if patient.age >= 60:
        facts.append(f'Age {patient.age} (risk rises above 60)')
    if patient.chronic_conditions:
        n = len([c for c in patient.chronic_conditions.split(',') if c.strip()])
        facts.append(f'{n} chronic condition(s): {patient.chronic_conditions[:80]}')
    if patient.allergies:
        facts.append(f'Known allergies: {patient.allergies[:60]}')
    from core.models import Appointment
    ns = Appointment.objects.filter(patient=patient, status='no_show').count()
    if ns:
        facts.append(f'{ns} previous no-show(s)')
    if not patient.insurance_provider:
        facts.append('No insurance on file')
    if not facts:
        facts.append('No significant risk factors identified')
    return facts


def train_and_save():
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    np.random.seed(42)
    n = 1200
    X = np.random.rand(n, 8)
    y_prob = (0.30*X[:,0] + 0.25*X[:,1] + 0.20*X[:,2] +
              0.10*X[:,3] + 0.05*X[:,4] + 0.10*X[:,5])
    y = (y_prob > 0.38).astype(int)
    model = Pipeline([
        ('sc',  StandardScaler()),
        ('clf', LogisticRegression(random_state=42, max_iter=1000)),
    ])
    model.fit(X, y)
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    print(f'Risk model saved → {MODEL_PATH}')
    return model


def _load():
    if not os.path.exists(MODEL_PATH):
        return train_and_save()
    with open(MODEL_PATH, 'rb') as f:
        return pickle.load(f)


def predict_risk(patient):
    """Returns (score: float|None, factors: list[str])"""
    try:
        model = _load()
        feat  = _features(patient).reshape(1, -1)
        score = float(model.predict_proba(feat)[0][1])
        return round(score, 3), _factors(patient, score)
    except Exception as e:
        return None, [f'Model error: {e}']
