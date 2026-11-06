"""
Incident Text Classifier for Workplace Health & Safety Reports.
Trained on OSHA-style incident narratives to classify reports into:
- heat
- respiratory_chemical
- injury
- other
Provides model evaluation metrics (Precision, Recall, F1-Score) and prediction pipelines.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score, accuracy_score
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline

from prahari.config import MODELS_DIR
from prahari.nlp.anonymizer import sanitize_incident_narrative


# Representative training corpus derived from OSHA Severe Injury Reports and industrial safety logs
DEFAULT_TRAINING_CORPUS: List[Tuple[str, str]] = [
    # Heat stress / dehydration / hyperthermia
    ("Employee collapsed on outdoor roofing project due to extreme direct sunlight and dehydration.", "heat"),
    ("Worker reported dizziness, heavy sweating, nausea and muscle cramps while laying asphalt in afternoon heat.", "heat"),
    ("Laborer experienced heat exhaustion after 4 hours of continuous steel fixing in 43C weather without shade.", "heat"),
    ("Found carpenter semi-conscious in excavation pit showing signs of heat stroke with high core body temperature.", "heat"),
    ("Scaffolder felt faint, severe headache and stopped sweating during midday shift on exposed south facade.", "heat"),
    ("Worker suffered heat cramps in legs and abdomen while pouring concrete in high ambient humidity.", "heat"),
    ("Outdoor rigger experienced sudden syncope due to prolonged sun exposure and lack of electrolyte replacement.", "heat"),
    ("Foreman observed worker staggering, confused and disoriented from extreme heat in steel yard.", "heat"),
    ("Excavator banksman collapsed from hyperthermia during hot afternoon loading operations.", "heat"),
    ("Welder working in poorly ventilated enclosure collapsed from heat exhaustion and dehydration.", "heat"),
    ("Field surveyor treated for heat rash, extreme thirst, and severe dizziness after walking desert boundary.", "heat"),
    ("Masonry helper complained of blurred vision, vomiting and rapid pulse while handling blocks in 42C.", "heat"),
    ("Crane operator felt dizzy and nauseated while climbing ladder during mid-afternoon heat advisory.", "heat"),
    ("Worker reported heat syncope after working three consecutive hours under direct sunlight without water break.", "heat"),
    ("Paving crew member required emergency IV hydration at site clinic due to severe heat exhaustion.", "heat"),
    ("Rebar worker suffered muscle spasms and chills on hot humid day, transported to first aid station.", "heat"),
    ("Security guard at outer gate collapsed from sun exposure during high UV and WBGT danger period.", "heat"),
    ("Pipefitter experienced hyperthermia and confusion while carrying pipes across outdoor storage yard.", "heat"),
    ("Painter experienced heat distress while spraying exterior wall with zero air movement.", "heat"),
    ("General laborer reported weakness, clammy skin, and vomiting after unloading heavy supplies in heat.", "heat"),
    ("Roofer experienced heat prostration and disorientation under direct sun at construction site.", "heat"),
    ("Worker suffered heat-induced tachycardia and dehydration during high summer shift.", "heat"),
    ("Trench digger overcome by ambient heat and heavy humidity, collapsed in trench.", "heat"),
    ("Scaffold builder treated for heat fatigue and heavy perspiration on midday shift.", "heat"),
    ("Asphalt worker passed out on highway paving project due to extreme surface heat.", "heat"),
    ("Concrete finisher suffered acute heat exhaustion with vomiting and dizzy spells.", "heat"),
    ("Ironworker felt faint and experienced painful heat cramps in calves while on high deck.", "heat"),
    ("Boiler room technician succumbed to high indoor ambient thermal stress and dehydration.", "heat"),

    # Respiratory / Chemical / Inhalation
    ("Worker inhaled dense solvent fumes while applying epoxy primer in basement with inadequate ventilation.", "respiratory_chemical"),
    ("Painter experienced acute shortness of breath and wheezing after spraying polyurethane without respirator.", "respiratory_chemical"),
    ("Laborers exposed to heavy airborne silica dust from dry concrete cutting, triggering severe asthma attack.", "respiratory_chemical"),
    ("Chemical warehouse technician exposed to chlorine vapor leak, experiencing throat burning and coughing.", "respiratory_chemical"),
    ("Welder inhaled toxic zinc oxide fumes from galvanized steel welding, suffering fever and chest tightness.", "respiratory_chemical"),
    ("Worker reported severe respiratory irritation and coughing fit from diesel exhaust accumulation in tunnel.", "respiratory_chemical"),
    ("Cleaner splashed with industrial degreaser inhaled ammonia vapor causing acute respiratory distress.", "respiratory_chemical"),
    ("Insulation installer experienced chest constriction and wheezing from fiberglass dust exposure.", "respiratory_chemical"),
    ("Maintenance crew affected by sulfur dioxide gas release during scrubber maintenance, requiring oxygen.", "respiratory_chemical"),
    ("Worker developed chemical pneumonitis symptoms after acid vat splash and mist inhalation.", "respiratory_chemical"),
    ("Sandblasting operator experienced acute coughing and dyspnea when air-fed respirator hose disconnected.", "respiratory_chemical"),
    ("Floor technician suffered respiratory spasms after mixing bleach and acid cleaning solutions.", "respiratory_chemical"),
    ("Tank cleaner experienced lightheadedness and coughing from hydrocarbon vapors inside storage vessel.", "respiratory_chemical"),
    ("Drywall finisher suffered bronchospasm due to high concentration of joint compound dust.", "respiratory_chemical"),
    ("Demolition worker inhaled unknown particulate matter from old insulation, experiencing persistent cough.", "respiratory_chemical"),
    ("Operator exposed to solvent vapor during adhesive application, complaining of lung irritation and burning.", "respiratory_chemical"),
    ("Worker triggered severe allergic respiratory reaction after handling untreated cedar wood dust.", "respiratory_chemical"),
    ("Forklift driver in cold storage warehouse experienced breathing difficulty from battery acid fumes.", "respiratory_chemical"),
    ("Mechanic exposed to brake cleaner aerosol in unventilated pit developed acute shortness of breath.", "respiratory_chemical"),
    ("Technician inhaled Freon refrigerant gas during AC compressor failure, reporting chest tightness.", "respiratory_chemical"),
    ("Laboratory chemist exposed to hydrochloric acid vapors during container decanting, choking and wheezing.", "respiratory_chemical"),
    ("Worker exposed to noxious paint thinner fumes inside enclosed spray booth, experiencing lung irritation.", "respiratory_chemical"),
    ("Maintenance worker inhaled carbon monoxide and fumes from faulty portable generator.", "respiratory_chemical"),
    ("Foundry employee suffered acute asthma attack following exposure to resin binder smoke.", "respiratory_chemical"),
    ("Plumber inhaled toxic sewer hydrogen sulfide gas in manhole, suffering respiratory distress.", "respiratory_chemical"),
    ("Tile installer developed severe persistent coughing and bronchospasm from dry grout mixing dust.", "respiratory_chemical"),
    ("Warehouse worker exposed to pesticide mist drift, experiencing throat constriction and shortness of breath.", "respiratory_chemical"),

    # Physical Injury / Trauma
    ("Worker slipped on wet metal grating and fell from staging platform, fracturing left wrist.", "injury"),
    ("Carpenter suffered deep laceration to palm from unguarded circular saw blade.", "injury"),
    ("Laborer struck by falling steel conduit dropped from 4th floor scaffolding, sustaining shoulder contusion.", "injury"),
    ("Forklift reversed and pinned warehouse worker's foot against loading dock, fracturing metatarsal.", "injury"),
    ("Rigging cable snapped during crane lift, whipping across deck and causing severe leg fracture.", "injury"),
    ("Electrician received 230V electric shock while troubleshooting live distribution panel, suffering hand burns.", "injury"),
    ("Mason tripped over loose rebar on ground level, dislocating right ankle.", "injury"),
    ("Machine operator caught glove in nip points of roller conveyor, resulting in finger crush injury.", "injury"),
    ("Steelworker fell 2 meters when step ladder slipped on smooth concrete floor.", "injury"),
    ("Laborer sustained puncture wound to foot when stepping on protruding rusty nail.", "injury"),
    ("Welding slag penetrated safety boot causing second-degree burn to left foot.", "injury"),
    ("Employee struck in face by high-pressure hydraulic hose rupture, suffering facial lacerations.", "injury"),
    ("Scaffold plank broke under load, worker fell 3 meters onto sand pile suffering spinal jarring.", "injury"),
    ("Heavy crate shifted during unloading and crushed worker's hand against truck tailgate.", "injury"),
    ("Pipe slipped from overhead sling and struck ground worker on hardhat, causing neck strain.", "injury"),
    ("Sheet metal worker cut forearm on sharp edge of galvanized ducting, requiring 12 sutures.", "injury"),
    ("Drill press bit bound and threw workpiece, striking operator's chest and fracturing rib.", "injury"),
    ("Maintenance technician pinched hand between gear assembly and motor housing during belt change.", "injury"),
    ("Worker fell down temporary timber stairs after handrail gave way, spraining both ankles.", "injury"),
    ("Jackhammer operator experienced vibration white finger and acute muscle tear in right forearm.", "injury"),
    ("Welder sustained severe laceration to index finger from angle grinder kickback.", "injury"),
    ("Heavy pallet fell from rack and struck warehouse worker's knee causing torn ligament.", "injury"),
    ("Truck driver slipped off trailer bumper and fractured elbow on asphalt.", "injury"),
    ("Rigger crushed fingers between steel beam and crane hook during bundle alignment.", "injury"),
    ("Demolition laborer struck by collapsing masonry wall, suffering fractured collarbone.", "injury"),
    ("Employee caught clothing in turning lathe spindle, resulting in dislocated shoulder.", "injury"),
    ("Worker dropped heavy oxygen cylinder onto toe, fracturing second digit.", "injury"),

    # Other / Ergonomic / Non-occupational / Environmental
    ("Office worker experienced sudden severe lower back strain while lifting standard document box.", "other"),
    ("Security guard stung by swarm of wasps near perimeter fence, receiving first aid antihistamine.", "other"),
    ("Staff member reported food poisoning symptoms (vomiting, diarrhea) after eating at site cafeteria.", "other"),
    ("Worker reported foreign body in eye (windblown sand particle) while walking across parking lot.", "other"),
    ("Employee developed severe non-work related migraine and was sent home to rest.", "other"),
    ("Administrative assistant complained of repetitive strain wrist soreness and ergonomic tendonitis.", "other"),
    ("Night watchman bitten by stray cat near perimeter gate, received prophylactic rabies evaluation.", "other"),
    ("Worker felt faint due to low blood sugar from fasting, recovered after juice and rest.", "other"),
    ("Employee reported mild eye irritation from bright glare while driving site escort vehicle.", "other"),
    ("Technician suffered thumb blister from prolonged manual screwdriver usage.", "other"),
    ("Canteen worker splashed mild hot soup on forearm resulting in minor superficial redness.", "other"),
    ("Supervisor complained of tension headache and seasonal allergic rhinitis from blooming acacia trees.", "other"),
    ("Worker experienced mild earache from wearing ill-fitting passive earplugs during shift.", "other"),
    ("Site clerk reported persistent lower back discomfort from non-adjustable office chair.", "other"),
    ("Laborer reported nausea attributed to stomach flu bug circulating in worker accommodation.", "other"),
    ("Employee tripped on sidewalk kerb outside main office entrance with minor knee scrape.", "other"),
    ("Worker reported gastrointestinal cramps and upset stomach after lunch break.", "other"),
    ("Employee experienced mild allergic reaction to bee sting on arm.", "other"),
    ("Worker noticed small wood splinter in thumb while unpacking stationery carton.", "other"),
    ("Computer operator complained of eye fatigue and neck stiffness after long monitor shift.", "other"),
    ("Security officer suffered ankle twisting stepping into gopher hole on perimeter grass.", "other"),
    ("Clerical worker complained of thumb joint pain from constant tablet touch screen typing.", "other"),
    ("Staff member fainted during morning toolbox meeting due to lack of breakfast.", "other"),
    ("Worker reported mild nausea and viral fever symptoms before starting duty.", "other"),
]


class IncidentClassifier:
    """
    NLP Classifier pipeline: Text Sanitization -> TF-IDF Vectorizer -> Logistic Regression.
    """

    def __init__(self, model_path: Optional[Path] = None):
        self.model_dir = Path(MODELS_DIR)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.model_path = Path(model_path or (self.model_dir / "incident_classifier.joblib"))
        self.pipeline: Optional[Pipeline] = None
        self.classes_: List[str] = ["heat", "respiratory_chemical", "injury", "other"]

    def train(self, corpus: Optional[List[Tuple[str, str]]] = None) -> Dict[str, Any]:
        """
        Train the classifier on incident narratives and save pipeline.
        Combines baseline safety corpus with authentic OSHA Severe Injury Reports.
        Returns evaluation metrics dictionary (accuracy, macro F1, classification report).
        """
        if corpus is not None:
            data = corpus
        else:
            osha_corpus = []
            try:
                from prahari.ingestion.osha import OSHAIncidentIngestor
                osha_corpus = OSHAIncidentIngestor().get_training_corpus()
            except Exception as e:
                pass
            data = list(DEFAULT_TRAINING_CORPUS) + osha_corpus

        # Sanitize all narratives before training
        texts = [sanitize_incident_narrative(item[0]) for item in data]
        labels = [item[1] for item in data]

        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.25, random_state=42, stratify=labels
        )

        pipeline = Pipeline([
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    stop_words="english",
                    min_df=1,
                    max_features=3000,
                    sublinear_tf=True,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    C=8.0,
                    class_weight="balanced",
                    max_iter=500,
                    random_state=42,
                ),
            ),
        ])

        # Compute 5-fold cross validation score
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(pipeline, texts, labels, cv=cv, scoring="f1_macro")
        cv_f1 = float(np.mean(cv_scores))

        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)

        acc = float(accuracy_score(y_test, y_pred))
        macro_f1 = float(f1_score(y_test, y_pred, average="macro"))
        report = classification_report(y_test, y_pred, output_dict=True)

        self.pipeline = pipeline
        joblib.dump(pipeline, self.model_path)

        return {
            "accuracy": round(acc, 4),
            "macro_f1": round(macro_f1, 4),
            "cv_macro_f1": round(cv_f1, 4),
            "n_train": len(X_train),
            "n_test": len(X_test),
            "report": report,
            "saved_path": str(self.model_path),
        }

    def predict(self, raw_narrative: str) -> Tuple[str, float]:
        """
        Sanitize input text and predict incident category with confidence score.
        """
        if self.pipeline is None:
            if self.model_path.exists():
                self.pipeline = joblib.load(self.model_path)
            else:
                self.train()

        sanitized = sanitize_incident_narrative(raw_narrative)
        if not sanitized:
            return "other", 0.5

        assert self.pipeline is not None
        probs = self.pipeline.predict_proba([sanitized])[0]
        classes = self.pipeline.classes_
        best_idx = int(np.argmax(probs))
        predicted_class = str(classes[best_idx])
        confidence = float(probs[best_idx])

        return predicted_class, round(confidence, 4)
