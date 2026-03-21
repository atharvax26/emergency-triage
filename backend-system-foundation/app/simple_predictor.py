"""Enhanced predictor with vital signs AND symptom analysis - CALIBRATED VERSION."""

import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SimplePredictor:
    """
    Clinical decision predictor based on established triage protocols.
    
    ENHANCED VERSION - Combines vital signs AND symptoms for triage decisions.
    
    Key features:
    - Vital signs analysis (heart rate, BP, SpO2, temperature, respiratory rate)
    - Symptom analysis (pain, bleeding, trauma, neurological, respiratory, etc.)
    - Combined scoring for accurate triage
    - Backward compatible (works with or without symptoms)
    - Calibrated thresholds (CRITICAL ≥ 0.85, HIGH ≥ 0.60, MEDIUM ≥ 0.30)
    """
    
    def __init__(self):
        """Initialize clinical predictor."""
        self.model_version = "4.0.0-enhanced"
        self.model_id = "clinical-protocol-v4-enhanced"
        logger.info("SimplePredictor initialized (clinical protocol v4 - enhanced with symptoms)")
    
    
    def _assess_vital_severity(self, vital_name: str, value: float, age: int) -> Tuple[int, str]:
        """
        Assess severity of a single vital sign.
        
        Returns:
            (severity_score, description)
            severity_score: 0=normal, 1=mild, 2=moderate, 3=severe, 4=critical
        """
        # Heart Rate Assessment (age-adjusted)
        if vital_name == 'heart_rate':
            if age > 65:
                if value < 45: return (4, "Critical bradycardia")
                if value < 55: return (3, "Severe bradycardia")
                if value < 60: return (1, "Mild bradycardia")
                if value > 120: return (3, "Severe tachycardia")
                if value > 105: return (2, "Moderate tachycardia")
                if value > 90: return (1, "Mild tachycardia")
            else:
                if value < 40: return (4, "Critical bradycardia")
                if value < 50: return (3, "Severe bradycardia")
                if value < 60: return (1, "Mild bradycardia")
                if value > 140: return (4, "Critical tachycardia")
                if value > 130: return (3, "Severe tachycardia")
                if value > 110: return (2, "Moderate tachycardia")
                if value > 95: return (1, "Mild tachycardia")
            return (0, None)
        
        # Systolic Blood Pressure
        elif vital_name == 'systolic_bp':
            if value < 70: return (4, "Critical hypotension")
            if value < 80: return (3, "Severe hypotension")
            if value < 90: return (2, "Moderate hypotension")
            if value < 100: return (1, "Mild hypotension")
            if value > 200: return (4, "Hypertensive crisis")
            if value > 180: return (3, "Severe hypertension")
            if value > 160: return (2, "Stage 2 hypertension")
            if value > 140: return (1, "Stage 1 hypertension")
            if value > 130: return (1, "Elevated blood pressure")
            return (0, None)
        
        # Oxygen Saturation (SpO2)
        elif vital_name == 'spo2':
            if value < 85: return (4, "Critical hypoxemia")
            if value < 90: return (3, "Severe hypoxemia")
            if value < 93: return (2, "Moderate hypoxemia")
            if value < 95: return (1, "Mild hypoxemia")
            return (0, None)
        
        # Temperature
        elif vital_name == 'temperature':
            if value < 34.0: return (4, "Severe hypothermia")
            if value < 35.0: return (3, "Moderate hypothermia")
            if value < 36.0: return (1, "Mild hypothermia")
            if value > 40.5: return (4, "Hyperpyrexia")
            if value > 39.5: return (3, "High fever")
            if value > 38.5: return (2, "Moderate fever")
            if value > 38.0: return (1, "Mild fever")
            return (0, None)
        
        # Respiratory Rate
        elif vital_name == 'respiratory_rate':
            if value < 8: return (4, "Critical bradypnea")
            if value < 10: return (3, "Severe bradypnea")
            if value < 12: return (1, "Mild bradypnea")
            if value > 30: return (4, "Critical tachypnea")
            if value > 26: return (3, "Severe tachypnea")
            if value > 22: return (2, "Moderate tachypnea")
            if value > 20: return (1, "Mild tachypnea")
            return (0, None)
        
        return (0, None)
    
    def _assess_symptom_severity(self, symptoms: List[str]) -> Tuple[int, List[str]]:
        """
        Assess severity based on symptoms.
        
        Args:
            symptoms: List of symptom strings
        
        Returns:
            (max_severity, symptom_descriptions)
            max_severity: 0=none, 1=mild, 2=moderate, 3=severe, 4=critical
        """
        if not symptoms:
            return (0, [])
        
        max_severity = 0
        symptom_factors = []
        
        # Convert symptoms to lowercase for matching
        symptoms_lower = [s.lower() for s in symptoms]
        symptoms_text = ' '.join(symptoms_lower)
        
        # Context-aware filtering - downgrade severity if benign context detected
        benign_contexts = [
            'paper cut', 'gym yesterday', 'muscle pain from', 'on period', 'menstrual',
            'chronic pain', 'usual pain', 'history of migraines', 'migraine pattern',
            'after seeing blood', 'woke up immediately', 'feeling better now',
            'anxious', 'panic', 'anxiety', 'hyperventilating',
            'from nose', 'nosebleed', 'blowing nose',
            'diabetic', 'forgot to eat', 'low blood sugar',
            'ate bad food', 'food poisoning',
            'playing basketball', 'sports injury', 'twisted ankle',
            'no breathing problems', 'no swelling of face',
            'havent drunk water', 'dehydration'
        ]
        
        has_benign_context = any(context in symptoms_text for context in benign_contexts)
        
        # CRITICAL symptoms (severity = 4) - Life-threatening, immediate intervention
        # Skip if benign context detected (e.g., "passed out briefly after seeing blood")
        critical_keywords = [
            # Airway/Breathing - but NOT if anxiety/panic context
            'unresponsive', 'unconscious', 'not breathing', 'no pulse', 'no heartbeat',
            'cardiac arrest', 'respiratory arrest', 'stopped breathing',
            'cannot breathe', 'cant breathe', 'unable to breathe', 'choking',
            'throat closing', 'airway obstruction', 'airway blocked',
            
            # Bleeding - but NOT if minor context (paper cut, nosebleed)
            'severe bleeding', 'massive bleeding', 'uncontrolled bleeding',
            'arterial bleeding', 'spurting blood', 'pulsating blood', 'gushing blood',
            'hemorrhaging', 'bleeding out', 'blood everywhere',
            
            # Cardiac
            'crushing chest pain', 'severe chest pain radiating', 'heart attack',
            'chest pain radiating to arm', 'chest pain radiating to jaw',
            'cardiac symptoms', 'heart stopped',
            
            # Neurological
            'seizure ongoing', 'actively seizing', 'convulsing', 'status epilepticus',
            'stroke symptoms', 'stroke', 'face drooping', 'arm weakness speech',
            'paralysis', 'cannot speak', 'slurred speech sudden', 'sudden weakness',
            'severe head injury', 'skull fracture', 'brain injury', 'head trauma severe',
            'loss of consciousness', 'passed out', 'fainted', 'collapsed',
            
            # Allergic/Anaphylaxis
            'anaphylaxis', 'anaphylactic shock',
            'throat swelling shut', 'tongue swelling', 'face swelling rapidly',
            
            # Trauma
            'impaled object', 'penetrating trauma', 'gunshot wound', 'stab wound',
            'amputation', 'severed limb', 'limb severed', 'body part severed',
            'evisceration', 'organs exposed', 'internal organs visible',
            
            # Other Critical
            'cyanosis', 'blue lips', 'turning blue', 'grey skin',
            'agonal breathing', 'gasping for air', 'death rattle',
            'severe burns over', 'burns covering', 'full thickness burns'
        ]
        
        for keyword in critical_keywords:
            if keyword in symptoms_text:
                # Skip critical classification if benign context present
                if has_benign_context:
                    # Check specific benign contexts
                    if ('passed out' in keyword or 'unconscious' in keyword or 'loss of consciousness' in keyword) and ('woke up' in symptoms_text or 'feeling better' in symptoms_text or 'briefly' in symptoms_text):
                        # Vasovagal syncope - downgrade to MODERATE
                        max_severity = max(max_severity, 2)
                        symptom_factors.append(f"Moderate symptom: brief loss of consciousness")
                        continue
                    if ('cant breathe' in keyword or 'cannot breathe' in keyword) and ('panic' in symptoms_text or 'anxious' in symptoms_text or 'anxiety' in symptoms_text):
                        # Anxiety/panic attack - downgrade to MODERATE
                        max_severity = max(max_severity, 2)
                        symptom_factors.append(f"Moderate symptom: anxiety/panic attack with breathing difficulty")
                        continue
                    if ('paper cut' in symptoms_text):
                        # Paper cut context - downgrade to MILD regardless of bleeding keywords
                        max_severity = max(max_severity, 1)
                        symptom_factors.append(f"Mild symptom: minor bleeding from paper cut")
                        continue
                    if 'bleeding' in keyword and ('from nose' in symptoms_text or 'nosebleed' in symptoms_text):
                        continue  # Skip - minor bleeding
                
                max_severity = 4
                symptom_factors.append(f"Critical symptom: {keyword}")
        
        # SEVERE symptoms (severity = 3) - Urgent, needs immediate medical attention
        severe_keywords = [
            # Pain - ONLY truly severe/life-threatening pain
            'excruciating pain', 'unbearable pain', 'worst pain',
            'pain 10/10', 'pain 9/10', 'extreme pain', 'agonizing pain',
            'intense pain', 'terrible pain', 'pain unbearable',
            
            # Bleeding - but NOT if paper cut context
            'heavy bleeding', 'profuse bleeding', 'bleeding heavily', 'significant bleeding',
            'continuous bleeding', 'wont stop bleeding', 'bleeding wont stop',
            'soaked through bandages', 'blood soaking through',
            
            # Respiratory
            'difficulty breathing', 'shortness of breath', 'gasping', 'labored breathing',
            'rapid breathing', 'breathing fast', 'wheezing severe', 'cant catch breath',
            'respiratory distress', 'struggling to breathe',
            
            # Cardiac/Chest
            'chest pain', 'chest pressure', 'chest tightness', 'chest discomfort',
            'pain in chest', 'pressure in chest', 'squeezing chest',
            'chest pain with sweating', 'chest pain with nausea',
            
            # Neurological
            'confusion', 'disoriented', 'altered mental status', 'not making sense',
            'dizzy severe', 'severe dizziness', 'room spinning', 'vertigo severe',
            'numbness', 'tingling', 'weakness one side', 'facial droop',
            
            # Abdominal - ONLY truly severe cases
            'acute abdomen', 'rigid abdomen', 'board-like abdomen',
            'guarding abdomen',
            
            # Trauma/Orthopedic - ONLY open/compound fractures
            'compound fracture', 'bone protruding', 'open fracture', 'bone sticking out',
            'bone visible', 'deformity severe', 'limb deformed',
            'joint dislocation', 'dislocated joint', 'joint out of place',
            
            # Burns - ONLY third degree
            'third degree burn', 'full thickness burn', 'deep burn',
            'chemical burn', 'electrical burn',
            
            # Pregnancy/OB
            'pregnant and bleeding', 'pregnancy bleeding', 'severe pregnancy pain',
            'contractions severe', 'baby coming', 'crowning',
            
            # Other Severe
            'vomiting blood', 'coughing up blood', 'blood in vomit', 'hematemesis',
            'blood in stool', 'rectal bleeding severe', 'bloody diarrhea',
            'severe dehydration', 'not urinated', 'no urine output',
            'diabetic emergency', 'blood sugar very high', 'blood sugar very low',
            'overdose', 'took too many pills', 'poisoning', 'ingested poison',
            'severe allergic reaction', 'anaphylaxis suspected'
        ]
        
        for keyword in severe_keywords:
            if keyword in symptoms_text:
                # Skip severe classification if benign context present
                if has_benign_context:
                    if ('heavy bleeding' in keyword or 'severe pain' in keyword) and ('on period' in symptoms_text or 'menstrual' in symptoms_text):
                        continue  # Skip - likely menstrual cramps
                    if 'bleeding' in keyword and ('from nose' in symptoms_text or 'nosebleed' in symptoms_text):
                        continue  # Skip - nosebleed
                    if 'bleeding' in keyword and ('paper cut' in symptoms_text):
                        # Paper cut context - downgrade to MILD
                        max_severity = max(max_severity, 1)
                        symptom_factors.append(f"Mild symptom: minor bleeding from paper cut")
                        continue
                    # Breathing difficulty in panic/anxiety context → cap at MODERATE
                    if any(b in keyword for b in ['breathing', 'breath', 'respiratory', 'gasping', 'wheezing']):
                        if any(p in symptoms_text for p in ['panic', 'anxiety', 'anxious', 'hyperventilating']):
                            max_severity = max(max_severity, 2)
                            symptom_factors.append(f"Moderate symptom: breathing difficulty in anxiety/panic context")
                            continue
                
                max_severity = max(max_severity, 3)
                symptom_factors.append(f"Severe symptom: {keyword}")
        
        # MILD symptoms (severity = 1) - Minor issues, can wait for routine care
        # CHECK THESE FIRST to catch "minor" modifiers before broader keywords
        mild_keywords_priority = [
            'minor bleeding', 'small amount of blood', 'spotting minor',
            'minor cut', 'small cut', 'superficial cut', 'paper cut',
            'minor pain', 'slight pain', 'little pain', 'tolerable pain',
            'minor swelling', 'slight swelling', 'little swelling',
            'minor burn', 'first degree burn', 'sunburn',
            'minor headache', 'slight headache', 'tension headache', 'mild headache',
            'minor dizziness', 'slightly dizzy',
            'minor sprain', 'minor strain', 'pulled muscle minor',
            'minor wound', 'minor injury', 'minor trauma'
        ]
        
        for keyword in mild_keywords_priority:
            if keyword in symptoms_text:
                max_severity = max(max_severity, 1)
                symptom_factors.append(f"Mild symptom: {keyword}")
        
        # MODERATE symptoms (severity = 2) - Needs medical attention, not immediately life-threatening
        # Check for severe/heavy modifiers first
        moderate_keywords_severe = [
            # Swelling
            'heavy swelling', 'severe swelling', 'significant swelling', 'massive swelling',
            'swelling rapidly', 'swelling getting worse', 'swelling increasing',
            
            # Bleeding (moderate level) - but NOT if already matched as "minor bleeding"
            'significant bleeding', 'continuous bleeding',
            
            # Fracture/Trauma
            'suspected fracture', 'possible fracture', 'think its broken',
            'might be broken', 'feels broken', 'looks broken',
            
            # Mobility
            'restricted mobility', 'cannot move', 'immobile', 'cant move',
            'unable to move', 'difficulty moving', 'cant walk', 'cannot walk',
            'cant stand', 'cannot stand', 'cant bear weight', 'cannot bear weight',
            'cannot properly walk', 'cant walk properly', 'difficulty walking',
            
            # Knee/Joint Instability
            'knee giving up', 'knee giving way', 'knee giving out', 'knee buckling',
            'knee instability', 'knee feels unstable', 'knee feels loose',
            'not having confidence on knee', 'no confidence in knee', 'cant trust knee',
            'knee will collapse', 'knee wobbles', 'joint instability', 'joint feels loose',
            'knee weakness', 'feeling knee will give out',
            
            # Vomiting
            'persistent vomiting', 'severe vomiting', 'vomiting repeatedly',
            'cant keep anything down', 'vomiting everything', 'continuous vomiting',
            
            # Fever
            'high fever', 'significant fever', 'fever very high', 'burning up',
            'fever with chills', 'fever with rigors'
        ]
        
        for keyword in moderate_keywords_severe:
            if keyword in symptoms_text:
                # Skip if already matched as mild
                already_matched = any(keyword in factor for factor in symptom_factors)
                if not already_matched:
                    max_severity = max(max_severity, 2)
                    symptom_factors.append(f"Moderate symptom: {keyword}")
        
        # Then check for moderate keywords (only if not already matched)
        # Special handling for "bleeding" and "swelling" - only moderate if NOT preceded by "minor"
        moderate_keywords = [
            # Pain - severe but not life-threatening
            'severe pain', 'moderate pain', 'significant pain', 'sharp pain', 'stabbing pain',
            'throbbing pain', 'aching pain', 'pain when moving', 'pain on movement',
            'pain with pressure', 'tender to touch', 'painful to touch',
            
            # Neurological/Head
            'severe headache', 'worst headache', 'sudden headache', 'thunderclap headache',
            'headache with vision changes', 'headache with vomiting',
            
            # Abdominal
            'severe abdominal pain', 'abdominal pain severe', 'stomach pain severe', 
            'belly pain severe', 'pain in abdomen severe',
            
            # Bleeding/Wounds - check only if not already matched as "minor bleeding"
            'laceration', 'deep cut', 'gash', 'wound',
            'puncture wound', 'cut deep', 'needs stitches', 'stitches needed',
            
            # Fracture/Orthopedic
            'fracture', 'broken bone', 'bone broken', 'broken',
            'dislocation', 'joint injury', 'sprain', 'strain',
            'twisted ankle', 'twisted knee', 'twisted wrist',
            'shoulder injury', 'knee injury', 'ankle injury', 'wrist injury',
            'back injury', 'neck injury', 'hip injury',
            
            # Swelling (general) - only if not "minor swelling"
            'joint swelling', 'limb swelling', 'extremity swelling',
            
            # GI Symptoms
            'vomiting', 'throwing up', 'nausea', 'nauseous', 'sick to stomach',
            'diarrhea', 'loose stools', 'frequent bowel movements',
            'abdominal pain', 'stomach pain', 'belly pain', 'cramping',
            'constipation severe', 'havent had bowel movement',
            
            # Fever/Infection
            'fever', 'chills', 'shaking chills', 'rigors', 'sweating',
            'night sweats', 'hot and cold', 'feverish',
            'infection', 'infected', 'pus', 'discharge', 'drainage',
            'red streaks', 'red lines', 'spreading redness',
            
            # Burns - second degree and with blisters
            'severe burn', 'burn with blisters', 'second degree burn', 'partial thickness burn',
            'blistering', 'burned', 'scald', 'scalded',
            
            # Head/Neuro - only if not "minor headache" or "mild headache"
            'head injury', 'concussion', 'hit head', 'bumped head',
            'migraine', 'head pain', 'headache',
            'vision changes', 'blurry vision', 'double vision', 'seeing spots',
            
            # Respiratory
            'coughing', 'productive cough', 'coughing up phlegm',
            'wheezing', 'tight chest', 'chest congestion',
            'difficulty swallowing', 'painful swallowing',
            
            # Allergic
            'allergic reaction', 'hives', 'rash spreading', 'itching severe',
            'swelling face', 'swelling lips', 'swelling tongue',
            
            # Urinary
            'painful urination', 'burning urination', 'blood in urine',
            'frequent urination', 'urgency', 'cant hold urine',
            'flank pain', 'kidney pain', 'back pain lower',
            
            # Pregnancy
            'pregnant', 'pregnancy', 'contractions', 'labor pains',
            'vaginal bleeding', 'cramping pregnant',
            
            # Dental
            'tooth pain', 'toothache', 'dental pain', 'jaw pain',
            'tooth broken', 'tooth knocked out', 'dental trauma',
            
            # Eye/Ear
            'eye pain', 'eye injury', 'something in eye', 'foreign body eye',
            'ear pain', 'earache', 'ear drainage', 'hearing loss sudden',
            
            # Skin
            'abscess', 'boil', 'cellulitis', 'skin infection',
            'wound infected', 'cut infected', 'red and swollen',
            
            # Other
            'dehydration', 'dehydrated', 'not drinking', 'dry mouth',
            'weakness', 'fatigue severe', 'exhaustion', 'cant function',
            'palpitations', 'heart racing', 'irregular heartbeat',
            'anxiety severe', 'panic attack', 'hyperventilating'
        ]
        
        for keyword in moderate_keywords:
            if keyword in symptoms_text:
                # Skip if already matched as mild or severe
                already_matched = any(keyword in factor for factor in symptom_factors)
                if not already_matched:
                    max_severity = max(max_severity, 2)
                    symptom_factors.append(f"Moderate symptom: {keyword}")
        
        # Check for standalone "bleeding" and "swelling" ONLY if not already matched
        # and NOT preceded by "minor"
        if 'bleeding' in symptoms_text and not any('bleeding' in f.lower() for f in symptom_factors):
            # Check if it's "minor bleeding" or just "bleeding"
            if 'minor bleeding' not in symptoms_text and 'small amount of blood' not in symptoms_text:
                max_severity = max(max_severity, 2)
                symptom_factors.append("Moderate symptom: bleeding")
        
        if 'swelling' in symptoms_text and not any('swelling' in f.lower() for f in symptom_factors):
            # Check if it's "minor swelling" or just "swelling"
            if 'minor swelling' not in symptoms_text and 'slight swelling' not in symptoms_text:
                max_severity = max(max_severity, 2)
                symptom_factors.append("Moderate symptom: swelling")
        
        # Additional MILD keywords (check after moderate to avoid conflicts)
        mild_keywords = [
            # Pain
            'mild pain', 'discomfort',
            
            # Skin/Wounds
            'bruising', 'bruise', 'scrape', 'abrasion',
            'scratch', 'superficial',
            
            # Respiratory - only if not already matched
            'cough', 'minor cough', 'slight cough', 'tickle in throat',
            'sore throat', 'scratchy throat', 'throat irritation',
            'runny nose', 'stuffy nose', 'congestion', 'sneezing',
            'post nasal drip', 'sinus pressure', 'sinus congestion',
            
            # Skin Conditions
            'rash', 'minor rash', 'small rash', 'itching', 'itchy',
            'dry skin', 'skin irritation', 'minor skin issue',
            'bug bite', 'insect bite', 'mosquito bite', 'bee sting minor',
            
            # GI
            'upset stomach', 'indigestion', 'heartburn', 'acid reflux',
            'gas', 'bloating', 'mild nausea', 'queasy',
            
            # Musculoskeletal
            'stiffness', 'soreness', 'muscle ache', 'muscle soreness',
            'cramp', 'muscle cramp', 'charlie horse',
            
            # Other
            'tired', 'fatigue', 'low energy', 'feeling run down',
            'cold symptoms', 'flu-like symptoms minor', 'feeling unwell'
        ]
        
        for keyword in mild_keywords:
            if keyword in symptoms_text:
                # Skip if already matched as moderate or severe
                already_matched = any(keyword in factor for factor in symptom_factors)
                if not already_matched:
                    # Special handling: only add as mild if max_severity is still 0 or 1
                    # This prevents downgrading from moderate/severe
                    if max_severity <= 1:
                        max_severity = max(max_severity, 1)
                        symptom_factors.append(f"Mild symptom: {keyword}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_factors = []
        for factor in symptom_factors:
            if factor not in seen:
                seen.add(factor)
                unique_factors.append(factor)
        
        return (max_severity, unique_factors)
    
    def _calculate_composite_scores(self, vitals: Dict[str, float], age: int) -> Dict[str, Any]:
        """
        Calculate composite clinical scores.
        
        Returns dict with composite scores and their max severity.
        Does NOT add to risk_factors list to avoid factor count inflation.
        """
        hr = vitals.get('heart_rate', 75)
        sbp = vitals.get('systolic_bp', 120)
        dbp = vitals.get('diastolic_bp', 80)
        temp = vitals.get('temperature', 37.0)
        spo2 = vitals.get('spo2', 98)
        rr = vitals.get('respiratory_rate', 16)
        
        composite_max_severity = 0
        composite_descriptions = []
        
        # Shock Index (HR / SBP) - RECALIBRATED
        shock_index = hr / sbp if sbp > 0 else 0
        if shock_index > 1.5:
            composite_max_severity = max(composite_max_severity, 4)
            composite_descriptions.append("Critical shock index")
        elif shock_index > 1.3:
            composite_max_severity = max(composite_max_severity, 3)
            composite_descriptions.append("Severe shock index")
        elif shock_index > 1.1:
            composite_max_severity = max(composite_max_severity, 2)
            composite_descriptions.append("Elevated shock index")
        elif shock_index > 0.9:
            composite_max_severity = max(composite_max_severity, 1)
            composite_descriptions.append("Borderline shock index")
        
        # Mean Arterial Pressure (MAP)
        map_value = (sbp + 2 * dbp) / 3
        if map_value < 60:
            composite_max_severity = max(composite_max_severity, 4)
            composite_descriptions.append("Critical MAP")
        elif map_value < 65:
            composite_max_severity = max(composite_max_severity, 3)
            composite_descriptions.append("Low MAP")
        elif map_value < 70:
            composite_max_severity = max(composite_max_severity, 2)
            composite_descriptions.append("Borderline MAP")
        
        # Pulse Pressure
        pulse_pressure = sbp - dbp
        if pulse_pressure < 25:
            composite_max_severity = max(composite_max_severity, 2)
            composite_descriptions.append("Narrow pulse pressure")
        elif pulse_pressure > 60:
            composite_max_severity = max(composite_max_severity, 1)
            composite_descriptions.append("Wide pulse pressure")
        
        # Modified Early Warning Score (MEWS)
        mews_score = 0
        
        if rr < 9: mews_score += 2
        elif rr >= 9 and rr <= 14: mews_score += 0
        elif rr >= 15 and rr <= 20: mews_score += 1
        elif rr >= 21 and rr <= 29: mews_score += 2
        else: mews_score += 3
        
        if hr < 40: mews_score += 2
        elif hr >= 40 and hr <= 50: mews_score += 1
        elif hr >= 51 and hr <= 100: mews_score += 0
        elif hr >= 101 and hr <= 110: mews_score += 1
        elif hr >= 111 and hr <= 129: mews_score += 2
        else: mews_score += 3
        
        if sbp < 70: mews_score += 3
        elif sbp >= 70 and sbp <= 80: mews_score += 2
        elif sbp >= 81 and sbp <= 100: mews_score += 1
        elif sbp >= 101 and sbp <= 199: mews_score += 0
        else: mews_score += 2
        
        if temp < 35.0: mews_score += 2
        elif temp >= 35.0 and temp < 38.5: mews_score += 0
        else: mews_score += 2
        
        if mews_score >= 7:
            composite_max_severity = max(composite_max_severity, 3)
            composite_descriptions.append(f"High MEWS score ({mews_score})")
        elif mews_score >= 5:
            composite_max_severity = max(composite_max_severity, 2)
            composite_descriptions.append(f"Moderate MEWS score ({mews_score})")
        
        return {
            'max_severity': composite_max_severity,
            'descriptions': composite_descriptions
        }
    
    def predict(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict triage severity from vital signs AND symptoms.
        
        Args:
            input_data: Dictionary with vital signs, age, and optional symptoms
        
        Returns:
            Prediction dictionary
        """
        import time
        start_time = time.time()
        
        # Extract vitals
        hr = input_data.get('heart_rate', 75)
        sbp = input_data.get('systolic_bp', 120)
        dbp = input_data.get('diastolic_bp', 80)
        temp = input_data.get('temperature', 37.0)
        spo2 = input_data.get('spo2', 98)
        rr = input_data.get('respiratory_rate', 16)
        age = input_data.get('age', 45)
        
        # Extract symptoms (optional - backward compatible)
        symptoms = input_data.get('symptoms', [])
        if isinstance(symptoms, str):
            symptoms = [symptoms]  # Convert single string to list
        
        # Assess vital signs
        vital_assessments = []
        max_vital_severity = 0
        risk_factors = []
        
        vitals = {
            'heart_rate': hr,
            'systolic_bp': sbp,
            'spo2': spo2,
            'temperature': temp,
            'respiratory_rate': rr
        }
        
        for vital_name, value in vitals.items():
            severity, description = self._assess_vital_severity(vital_name, value, age)
            if severity > 0:
                vital_assessments.append((vital_name, severity, description))
                max_vital_severity = max(max_vital_severity, severity)
                risk_factors.append(description)
        
        # Assess symptoms
        symptom_severity, symptom_factors = self._assess_symptom_severity(symptoms)
        risk_factors.extend(symptom_factors)
        
        # Calculate composite scores
        composite_scores = self._calculate_composite_scores(
            {'heart_rate': hr, 'systolic_bp': sbp, 'diastolic_bp': dbp,
             'temperature': temp, 'spo2': spo2, 'respiratory_rate': rr},
            age
        )
        
        composite_descriptions = composite_scores['descriptions']
        
        # Determine overall max severity (vitals, symptoms, composite, age)
        max_severity = max(max_vital_severity, symptom_severity, composite_scores['max_severity'])
        
        # Age risk factor
        age_severity = 0
        if age > 80:
            risk_factors.append("Very elderly patient (>80)")
            age_severity = 1
        elif age > 75:
            risk_factors.append("Elderly patient (>75)")
            age_severity = 1
        elif age > 65:
            risk_factors.append("Senior patient (>65)")
            age_severity = 0
        
        max_severity = max(max_severity, age_severity)
        
        # Calculate weighted risk score
        num_factors = len(risk_factors)
        
        if max_severity == 4:
            base_probability = 0.92
        elif max_severity == 3:
            # ADJUSTED: Reduce probabilities to keep most cases in HIGH range (0.60-0.84)
            if num_factors >= 7:
                base_probability = 0.82  # Reduced from 0.88
            elif num_factors >= 5:
                base_probability = 0.72
            elif num_factors >= 3:
                base_probability = 0.65
            elif num_factors >= 2:
                base_probability = 0.62
            else:
                base_probability = 0.58
        elif max_severity == 2:
            if num_factors >= 9:
                base_probability = 0.58  # Reduced: MEDIUM cases should not reach HIGH
            elif num_factors >= 7:
                base_probability = 0.52
            elif num_factors >= 5:
                base_probability = 0.48
            elif num_factors >= 3:
                base_probability = 0.42
            elif num_factors >= 2:
                base_probability = 0.38
            else:
                base_probability = 0.33
        elif max_severity == 1:
            # ADJUSTED: Different handling for vital signs vs symptoms
            # If max severity is from vital signs (not just symptoms), use original thresholds
            # If max severity is ONLY from mild symptoms, use lower thresholds
            if max_vital_severity >= 1:
                # Vital signs abnormalities - use original thresholds
                if num_factors >= 6:
                    base_probability = 0.45
                elif num_factors >= 4:
                    base_probability = 0.38
                elif num_factors >= 3:
                    base_probability = 0.32
                elif num_factors >= 2:
                    base_probability = 0.30  # Adjusted to hit MEDIUM threshold
                else:
                    base_probability = 0.20
            else:
                # Only mild symptoms, no vital abnormalities - use lower thresholds
                if num_factors >= 6:
                    base_probability = 0.28
                elif num_factors >= 4:
                    base_probability = 0.25
                elif num_factors >= 3:
                    base_probability = 0.22
                elif num_factors >= 2:
                    base_probability = 0.20
                else:
                    base_probability = 0.15
        else:
            base_probability = 0.05
        
        # Age adjustments
        if age > 80 and max_severity >= 3:
            base_probability += 0.02
        elif age > 75 and max_severity >= 3:
            base_probability += 0.01
        
        # Isolated hypertension adjustment
        if age > 60 and max_severity == 1 and num_factors == 1:
            for factor in risk_factors:
                if "Elevated blood pressure" in factor:
                    base_probability -= 0.05
                    break
                elif "Stage 1 hypertension" in factor:
                    base_probability += 0.02
                    break
                elif "Stage 2 hypertension" in factor:
                    base_probability += 0.05
                    break
        
        raw_probability = min(base_probability, 0.95)
        calibrated_probability = raw_probability
        
        # Determine risk tier
        if calibrated_probability >= 0.85:
            risk_tier = "CRITICAL"
            decision_label = "IMMEDIATE"
        elif calibrated_probability >= 0.60:
            risk_tier = "HIGH"
            decision_label = "URGENT"
        elif calibrated_probability >= 0.30:
            risk_tier = "MEDIUM"
            decision_label = "MONITOR"
        else:
            risk_tier = "LOW"
            decision_label = "ROUTINE"
        
        # Calculate confidence
        if max_severity >= 3 or num_factors >= 4:
            confidence = 0.90
        elif max_severity >= 2 or num_factors >= 2:
            confidence = 0.85
        elif max_severity >= 1:
            confidence = 0.75
        else:
            confidence = 0.80
        
        # Safety overrides
        safety_override = False
        override_reason = None
        
        if spo2 < 85 or sbp < 70 or hr < 40 or hr > 150 or temp < 34.0 or rr < 8:
            safety_override = True
            override_reason = "Immediately life-threatening vital signs"
            risk_tier = "CRITICAL"
            decision_label = "IMMEDIATE"
            calibrated_probability = 0.95
            confidence = 0.95
        
        # Symptom-based safety overrides
        if symptom_severity == 4:
            safety_override = True
            override_reason = "Critical symptoms detected"
            risk_tier = "CRITICAL"
            decision_label = "IMMEDIATE"
            calibrated_probability = 0.95
            confidence = 0.95
        
        inference_time_ms = (time.time() - start_time) * 1000
        
        # Build result
        all_factors = risk_factors + composite_descriptions
        
        result = {
            'raw_probability': float(raw_probability),
            'calibrated_probability': float(calibrated_probability),
            'risk_tier': risk_tier,
            'decision_label': decision_label,
            'confidence': float(confidence),
            'safety_override': safety_override,
            'override_reason': override_reason,
            'model_version': self.model_version,
            'model_id': self.model_id,
            'inference_time_ms': float(inference_time_ms),
            'timestamp': datetime.utcnow().isoformat(),
            'cache_hit': False,
            'risk_factors': all_factors,
            'max_severity': max_severity,
            'num_factors': num_factors,
            'vital_severity': max_vital_severity,
            'symptom_severity': symptom_severity
        }
        
        logger.info(
            f"Clinical prediction: {risk_tier} "
            f"(prob={calibrated_probability:.3f}, "
            f"vital_sev={max_vital_severity}, "
            f"symptom_sev={symptom_severity}, "
            f"factors={num_factors}, "
            f"time={inference_time_ms:.1f}ms)"
        )
        
        return result
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.
        
        Returns:
            Health status
        """
        return {
            'healthy': True,
            'model_loaded': True,
            'model_version': self.model_version,
            'model_id': self.model_id,
            'timestamp': datetime.utcnow().isoformat()
        }
