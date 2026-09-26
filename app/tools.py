"""Firestore-backed tools for Bespoke Atelier & Pattern Concierge.

Includes pattern retrieval, user body profiling, and drafted project storage.
"""

import json
import os
from typing import Optional, Dict, Any, List
from google.cloud import firestore
from google.api_core.exceptions import NotFound, GoogleAPIError

# Hardcode GCP Project ID explicitly as a string (do NOT use GOOGLE_CLOUD_PROJECT)
FIRESTORE_PROJECT = "qwiklabs-gcp-03-7d5352e0a1dc"
GCS_BUCKET_NAME = "bespoke-atelier-patterns-qwiklabs-gcp-03-7d5352e0a1dc"

# Initial seed data used as fallback when Firestore database has not been initialized
INITIAL_SEED_PATTERNS = [
    {
        "pattern_id": "old-money-waistcoat",
        "name": "Old Money Tailored Waistcoat",
        "aesthetic": "Old Money",
        "difficulty": "Intermediate",
        "recommended_fabrics": ["Wool Tweed", "Linen-Cotton Blend", "Worst Wool", "Heavy Suit Linen"],
        "yardage_estimate": "1.75 yards (60 inch width)",
        "flat_sketch_url": f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/flat_sketch_preview.png",
        "base_measurements": {
            "bust": 36.0,
            "waist": 28.0,
            "hip": 38.0,
            "back_length": 16.5,
            "unit": "inches"
        },
        "description": "Structured v-neck tailored vest featuring front welt pockets, back cinching tie, and princess seam shaping."
    },
    {
        "pattern_id": "vintage-1950s-circle-skirt",
        "name": "1950s Full Circle Skirt Dress",
        "aesthetic": "Vintage 1950s",
        "difficulty": "Beginner-Friendly",
        "recommended_fabrics": ["Cotton Poplin", "Taffeta", "Polished Cotton", "Gingham Broadcloth"],
        "yardage_estimate": "4.5 yards (44 inch width)",
        "flat_sketch_url": f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/flat_sketch_preview.png",
        "base_measurements": {
            "bust": 35.0,
            "waist": 26.5,
            "hip": 37.0,
            "skirt_length": 28.0,
            "unit": "inches"
        },
        "description": "Mid-century classic silhouette featuring a fitted boatneck bodice, full 360-degree circle skirt, and deep side seam pockets."
    },
    {
        "pattern_id": "cottagecore-milkmaid-dress",
        "name": "Cottagecore Tiered Milkmaid Dress",
        "aesthetic": "Cottagecore",
        "difficulty": "Intermediate",
        "recommended_fabrics": ["Linen Voile", "Gathered Cotton Lawn", "Rayon Crepe", "Embroidered Eyelet"],
        "yardage_estimate": "3.8 yards (54 inch width)",
        "flat_sketch_url": f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/flat_sketch_preview.png",
        "base_measurements": {
            "bust": 34.0,
            "waist": 27.0,
            "hip": 38.0,
            "bodice_height": 13.0,
            "unit": "inches"
        },
        "description": "Romantic prairie style with elasticated puff sleeves, gathered drawstring milkmaid bust cups, and a flowing tiered midi skirt."
    },
    {
        "pattern_id": "minimalist-wide-leg-trousers",
        "name": "Minimalist High-Waisted Wide-Leg Trousers",
        "aesthetic": "Minimalist",
        "difficulty": "Advanced",
        "recommended_fabrics": ["Heavy Linen", "Wool Crepe", "Tencel Twill", "Cotton Gabardine"],
        "yardage_estimate": "2.75 yards (58 inch width)",
        "flat_sketch_url": f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/flat_sketch_preview.png",
        "base_measurements": {
            "waist": 28.0,
            "hip": 39.0,
            "inseam": 31.0,
            "crotch_depth": 11.5,
            "unit": "inches"
        },
        "description": "Clean Architectural high-waisted trousers with front double pleats, concealed fly zip, slant side pockets, and wide straight leg."
    }
]

# Local fallback in-memory cache for profiles & projects if GCP Firestore DB is unprovisioned
_LOCAL_USER_PROFILES: Dict[str, Dict[str, Any]] = {}
_LOCAL_DRAFTED_PROJECTS: Dict[str, List[Dict[str, Any]]] = {}


def _get_firestore_db() -> Optional[firestore.Client]:
    """Helper to initialize Firestore client with the hardcoded project ID."""
    try:
        return firestore.Client(project=FIRESTORE_PROJECT)
    except Exception:
        return None


def get_patterns_by_aesthetic(aesthetic: str = "") -> str:
    """Retrieves available sewing patterns filtered by aesthetic style.

    Args:
        aesthetic: Filter patterns by aesthetic style (e.g., 'Old Money', 'Vintage 1950s',
            'Cottagecore', 'Minimalist'). Leave blank to list all available patterns.

    Returns:
        JSON string containing the matching pattern templates.
    """
    db = _get_firestore_db()
    patterns = []
    
    if db is not None:
        try:
            query = db.collection("patterns")
            docs = list(query.stream())
            if docs:
                for doc in docs:
                    p = doc.to_dict()
                    if not aesthetic or aesthetic.lower() in p.get("aesthetic", "").lower():
                        patterns.append(p)
        except (NotFound, GoogleAPIError, Exception):
            pass

    # Fallback to initial seed patterns if Firestore returned no docs
    if not patterns:
        for p in INITIAL_SEED_PATTERNS:
            if not aesthetic or aesthetic.lower() in p.get("aesthetic", "").lower():
                patterns.append(p)

    return json.dumps({"count": len(patterns), "patterns": patterns}, indent=2)


def get_pattern_by_id(pattern_id: str) -> str:
    """Retrieves full sewing pattern details by unique pattern ID.

    Args:
        pattern_id: The unique identifier of the pattern (e.g. 'old-money-waistcoat',
            'cottagecore-milkmaid-dress').

    Returns:
        JSON string containing the detailed pattern information or error message.
    """
    db = _get_firestore_db()
    if db is not None:
        try:
            doc = db.collection("patterns").document(pattern_id).get()
            if doc.exists:
                return json.dumps({"pattern": doc.to_dict()}, indent=2)
        except (NotFound, GoogleAPIError, Exception):
            pass

    # Fallback search in seed patterns
    for p in INITIAL_SEED_PATTERNS:
        if p["pattern_id"] == pattern_id:
            return json.dumps({"pattern": p}, indent=2)

    return json.dumps({"error": f"Pattern with ID '{pattern_id}' not found."}, indent=2)


def save_user_profile(
    user_id: str,
    bust: float,
    waist: float,
    hip: float,
    height: float,
    back_waist_length: float = 16.5,
    preferred_aesthetic: str = "Classic"
) -> str:
    """Saves or updates a user's body measurements profile in Firestore.

    Args:
        user_id: Unique identifier for the user (e.g. 'user_123' or username).
        bust: Bust measurement in inches.
        waist: Waist measurement in inches.
        hip: Full hip measurement in inches.
        height: Total height in inches.
        back_waist_length: Back waist length measurement in inches (default 16.5).
        preferred_aesthetic: Preferred fashion aesthetic (e.g. 'Old Money', 'Cottagecore', 'Vintage').

    Returns:
        JSON string confirmation of saved profile.
    """
    profile_data = {
        "user_id": user_id,
        "bust": float(bust),
        "waist": float(waist),
        "hip": float(hip),
        "height": float(height),
        "back_waist_length": float(back_waist_length),
        "preferred_aesthetic": preferred_aesthetic,
        "unit": "inches"
    }

    db = _get_firestore_db()
    saved_to_firestore = False

    if db is not None:
        try:
            db.collection("user_profiles").document(user_id).set(profile_data)
            saved_to_firestore = True
        except (NotFound, GoogleAPIError, Exception):
            pass

    # Maintain local cache fallback
    _LOCAL_USER_PROFILES[user_id] = profile_data

    status = "Firestore & local cache" if saved_to_firestore else "local profile store"
    return json.dumps({
        "status": "success",
        "message": f"User profile for '{user_id}' saved to {status}.",
        "profile": profile_data
    }, indent=2)


def get_user_profile(user_id: str) -> str:
    """Retrieves a user's saved body measurements profile.

    Args:
        user_id: Unique identifier for the user.

    Returns:
        JSON string containing the user profile or error if not found.
    """
    db = _get_firestore_db()
    if db is not None:
        try:
            doc = db.collection("user_profiles").document(user_id).get()
            if doc.exists:
                return json.dumps({"profile": doc.to_dict()}, indent=2)
        except (NotFound, GoogleAPIError, Exception):
            pass

    if user_id in _LOCAL_USER_PROFILES:
        return json.dumps({"profile": _LOCAL_USER_PROFILES[user_id]}, indent=2)

    return json.dumps({"error": f"No saved body profile found for user '{user_id}'."}, indent=2)


def save_drafted_project(
    user_id: str,
    project_name: str,
    pattern_id: str,
    yardage_required: str,
    notes: str = ""
) -> str:
    """Saves a customized made-to-measure drafted garment project.

    Args:
        user_id: Unique identifier for the user.
        project_name: Title of the project (e.g., 'My Vintage Prom Dress').
        pattern_id: The base pattern template ID used.
        yardage_required: Calculated fabric yardage estimate (e.g. '3.25 yards').
        notes: Optional custom notes, fabric choices, or ease adjustments.

    Returns:
        JSON string confirming project creation.
    """
    project_data = {
        "user_id": user_id,
        "project_name": project_name,
        "pattern_id": pattern_id,
        "yardage_required": yardage_required,
        "notes": notes
    }

    db = _get_firestore_db()
    saved_to_firestore = False

    if db is not None:
        try:
            doc_ref = db.collection("drafted_projects").document()
            project_data["project_id"] = doc_ref.id
            doc_ref.set(project_data)
            saved_to_firestore = True
        except (NotFound, GoogleAPIError, Exception):
            pass

    if "project_id" not in project_data:
        project_data["project_id"] = f"proj_{len(_LOCAL_DRAFTED_PROJECTS.get(user_id, [])) + 1}"

    if user_id not in _LOCAL_DRAFTED_PROJECTS:
        _LOCAL_DRAFTED_PROJECTS[user_id] = []
    _LOCAL_DRAFTED_PROJECTS[user_id].append(project_data)

    status = "Firestore" if saved_to_firestore else "local memory"
    return json.dumps({
        "status": "success",
        "message": f"Drafted project '{project_name}' saved to {status}.",
        "project": project_data
    }, indent=2)


def list_user_projects(user_id: str) -> str:
    """Lists all saved drafted sewing projects for a user.

    Args:
        user_id: Unique identifier for the user.

    Returns:
        JSON string with list of user projects.
    """
    db = _get_firestore_db()
    projects = []

    if db is not None:
        try:
            query = db.collection("drafted_projects").where("user_id", "==", user_id)
            docs = list(query.stream())
            for doc in docs:
                projects.append(doc.to_dict())
        except (NotFound, GoogleAPIError, Exception):
            pass

    if not projects and user_id in _LOCAL_DRAFTED_PROJECTS:
        projects = _LOCAL_DRAFTED_PROJECTS[user_id]

    return json.dumps({"user_id": user_id, "count": len(projects), "projects": projects}, indent=2)


def calculate_pattern_requirements(
    aesthetic: str,
    bust_in: float,
    waist_in: float,
    hip_in: float,
    fabric_width_in: int = 60
) -> str:
    """Calculates parametric pattern drafting measurements, ease allowances, finished garment dimensions, and required fabric yardage.

    Args:
        aesthetic: The style or aesthetic (e.g. 'Old Money', 'Vintage 1950s', 'Cottagecore', 'Minimalist').
        bust_in: User bust measurement in inches.
        waist_in: User waist measurement in inches.
        hip_in: User full hip measurement in inches.
        fabric_width_in: Fabric bolt width in inches (standard values: 45 or 60 inches, default 60).

    Returns:
        JSON string containing ease allowances, finished garment dimensions, fabric cutting yardage for 45" and 60" bolt widths, and recommended notions.
    """
    import math

    aes_lower = aesthetic.lower()
    
    if "old money" in aes_lower or "waistcoat" in aes_lower or "vest" in aes_lower:
        style_name = "Old Money Tailored Waistcoat / Vest"
        bust_ease = 1.5
        waist_ease = 1.0
        hip_ease = 2.0
        dart_intake = "Waist dart: 1.25 inch, Side bust dart: 1.0 inch"
        yardage_60 = "1.75 yards (1.6 meters)"
        yardage_45 = "2.25 yards (2.1 meters)"
        notions = [
            "5x 18mm horn or tortoise buttons",
            "0.5 yards lightweight fusible woven interfacing",
            "1x 1-inch back cinching slider buckle"
        ]
        special_math = {
            "chest_armhole_depth_in": round(bust_in * 0.2 + 2.5, 2),
            "back_cinch_placement_in": round(waist_in * 0.25, 2)
        }
    elif "vintage" in aes_lower or "1950" in aes_lower or "circle" in aes_lower:
        style_name = "1950s Full Circle Skirt & Fitted Bodice Dress"
        bust_ease = 2.0
        waist_ease = 0.5
        hip_ease = 12.0  # Full flared circle skirt
        dart_intake = "Double contour waist darts: 1.5 inch each"
        skirt_waist_radius = round((waist_in + waist_ease) / (2 * math.pi), 2)
        yardage_60 = "3.8 yards (3.5 meters)"
        yardage_45 = "4.8 yards (4.4 meters)"
        notions = [
            "1x 14-inch invisible zipper",
            "1x waistband hook-and-eye closure set",
            "5 yards folded bias tape for hem finishing"
        ]
        special_math = {
            "circle_skirt_waist_radius_in": skirt_waist_radius,
            "skirt_hem_circumference_in": round(2 * math.pi * (skirt_waist_radius + 28.0), 2)
        }
    elif "cottagecore" in aes_lower or "milkmaid" in aes_lower or "tiered" in aes_lower:
        style_name = "Cottagecore Tiered Milkmaid Prairie Dress"
        bust_ease = 3.0
        waist_ease = 2.0
        hip_ease = 8.0
        dart_intake = "Elasticated gathering & bust cup drawstring intake"
        yardage_60 = "3.5 yards (3.2 meters)"
        yardage_45 = "4.5 yards (4.1 meters)"
        notions = [
            "1.5 yards 3/8-inch braided elastic",
            "1x 12-inch invisible side seam zipper",
            "1.0 yard ribbon drawstring"
        ]
        special_math = {
            "tier_1_cutting_width_in": round((waist_in + waist_ease) * 1.5, 2),
            "tier_2_cutting_width_in": round((waist_in + waist_ease) * 2.2, 2)
        }
    else: # Minimalist or default
        style_name = "Minimalist Architectural High-Waisted Silhouette"
        bust_ease = 2.5
        waist_ease = 1.5
        hip_ease = 3.0
        dart_intake = "Single waist pleat intake: 1.0 inch"
        yardage_60 = "2.5 yards (2.3 meters)"
        yardage_45 = "3.25 yards (3.0 meters)"
        notions = [
            "1x 9-inch concealed fly zipper",
            "1x heavy trouser waistband hook-and-bar",
            "1.0 yard fusible waistband stay interfacing"
        ]
        special_math = {
            "pleat_depth_in": 1.25,
            "leg_opening_circumference_in": round(hip_in * 0.65, 2)
        }

    finished_bust = round(bust_in + bust_ease, 2)
    finished_waist = round(waist_in + waist_ease, 2)
    finished_hip = round(hip_in + hip_ease, 2)

    result = {
        "aesthetic": aesthetic,
        "style_name": style_name,
        "body_measurements_in": {
            "bust": bust_in,
            "waist": waist_in,
            "hip": hip_in
        },
        "ease_allowances_in": {
            "bust_ease": bust_ease,
            "waist_ease": waist_ease,
            "hip_ease": hip_ease,
            "dart_or_gathering_intake": dart_intake
        },
        "finished_garment_dimensions_in": {
            "finished_bust": finished_bust,
            "finished_waist": finished_waist,
            "finished_hip": finished_hip,
            "parametric_calculations": special_math
        },
        "fabric_yardage_requirements": {
            "selected_fabric_width_in": fabric_width_in,
            "estimate_60in_width": yardage_60,
            "estimate_45in_width": yardage_45,
            "cutting_layout_note": "Includes standard 5/8 inch (1.5 cm) seam allowance on all pattern edges."
        },
        "recommended_notions": notions
    }

    return json.dumps(result, indent=2)


def generate_pattern_svg(
    pattern_name: str,
    aesthetic: str,
    waist_radius_in: float = 4.54,
    skirt_length_in: float = 28.0,
    bust_width_in: float = 18.0,
    waistcoat_length_in: float = 20.0
) -> str:
    """Generates clean 2D vector SVG pattern piece markup with seam allowances, grainline arrows, and cutting annotations, uploads it to Cloud Storage, and returns the public download URL.

    Args:
        pattern_name: Title of the pattern piece (e.g., 'old_money_waistcoat_front', '1950s_circle_skirt_quarter').
        aesthetic: The style or aesthetic (e.g. 'Old Money', 'Vintage 1950s', 'Cottagecore', 'Minimalist').
        waist_radius_in: Waist arc radius in inches for skirt pieces (default 4.54).
        skirt_length_in: Skirt length in inches (default 28.0).
        bust_width_in: Half-chest/bust width in inches for top/waistcoat panel (default 18.0).
        waistcoat_length_in: Total center front length in inches (default 20.0).

    Returns:
        JSON string with GCS object path, SVG metadata, public download URL, and pattern piece instructions.
    """
    import datetime
    from google.cloud import storage

    cleaned_name = pattern_name.strip().lower().replace(" ", "_").replace("-", "_")
    aes_lower = aesthetic.lower()
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{cleaned_name}_{timestamp_str}.svg"

    if "waistcoat" in aes_lower or "vest" in aes_lower or "old_money" in aes_lower or "top" in cleaned_name:
        svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 800" width="100%" height="100%">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#dc2626" />
    </marker>
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e2e8f0" stroke-width="1"/>
    </pattern>
  </defs>

  <!-- Background Canvas Grid -->
  <rect width="600" height="800" fill="#f8fafc"/>
  <rect width="600" height="800" fill="url(#grid)"/>

  <!-- Main Waistcoat Front Cutting Line (Solid Dark Slate) -->
  <path d="M 180 120 L 290 220 L 290 580 L 240 680 L 120 620 L 80 320 Z" fill="#ffffff" fill-opacity="0.9" stroke="#1e293b" stroke-width="3" stroke-linejoin="round"/>

  <!-- Seam Allowance Inner Guideline (5/8 inch offset - Dashed Slate) -->
  <path d="M 183 135 L 278 225 L 278 568 L 232 662 L 125 610 L 92 322 Z" fill="none" stroke="#64748b" stroke-width="1.5" stroke-dasharray="6,4"/>

  <!-- Dart Intake Markings -->
  <path d="M 185 580 L 200 420 L 215 580 Z" fill="none" stroke="#2563eb" stroke-dasharray="4,3" stroke-width="1.5"/>

  <!-- Welt Pocket Placement Line -->
  <line x1="140" y1="460" x2="230" y2="460" stroke="#0f172a" stroke-width="2"/>
  <text x="140" y="450" font-family="sans-serif" font-size="12" fill="#475569">WELT POCKET</text>

  <!-- Grainline Arrow -->
  <line x1="180" y1="260" x2="180" y2="400" stroke="#dc2626" stroke-width="2" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
  <text x="190" y="330" font-family="sans-serif" font-size="13" font-weight="bold" fill="#dc2626">GRAINLINE</text>

  <!-- Buttonhole Position Crosses -->
  <circle cx="280" cy="280" r="4" fill="#0f172a"/>
  <circle cx="280" cy="360" r="4" fill="#0f172a"/>
  <circle cx="280" cy="440" r="4" fill="#0f172a"/>
  <circle cx="280" cy="520" r="4" fill="#0f172a"/>

  <!-- Pattern Metadata Annotations -->
  <g transform="translate(110, 260)">
    <text x="0" y="0" font-family="sans-serif" font-size="18" font-weight="bold" fill="#0f172a">BESPOKE ATELIER</text>
    <text x="0" y="22" font-family="sans-serif" font-size="14" font-weight="600" fill="#334155">{aesthetic.upper()} WAISTCOAT FRONT</text>
    <text x="0" y="42" font-family="sans-serif" font-size="12" fill="#64748b">CUT 2 MAIN FABRIC | CUT 2 LINING</text>
    <text x="0" y="60" font-family="sans-serif" font-size="11" fill="#64748b">Chest Width: {bust_width_in}" | Length: {waistcoat_length_in}"</text>
    <text x="0" y="76" font-family="sans-serif" font-size="11" fill="#0284c7">Seam Allowance: 5/8" (1.5 cm) Included</text>
  </g>
</svg>"""
    else:
        svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800" width="100%" height="100%">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#dc2626" />
    </marker>
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e2e8f0" stroke-width="1"/>
    </pattern>
  </defs>

  <rect width="800" height="800" fill="#f8fafc"/>
  <rect width="800" height="800" fill="url(#grid)"/>

  <!-- Skirt Arc (Quarter Circle Pattern Piece) -->
  <path d="M 150 150 L 150 650 A 500 500 0 0 0 650 150 L 250 150 A 100 100 0 0 1 150 250 Z" fill="#ffffff" fill-opacity="0.9" stroke="#1e293b" stroke-width="3" stroke-linejoin="round"/>

  <!-- Seam Allowance Guideline -->
  <path d="M 160 160 L 160 635 A 475 475 0 0 0 635 160 L 240 160 A 80 80 0 0 1 160 240 Z" fill="none" stroke="#64748b" stroke-width="1.5" stroke-dasharray="6,4"/>

  <!-- Grainline Marker -->
  <line x1="280" y1="280" x2="480" y2="480" stroke="#dc2626" stroke-width="2" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
  <text x="390" y="370" font-family="sans-serif" font-size="13" font-weight="bold" fill="#dc2626" transform="rotate(45 390 370)">GRAINLINE / STRAIGHT OF GRAIN</text>

  <!-- Fold Line Notation -->
  <text x="125" y="400" font-family="sans-serif" font-size="13" font-weight="bold" fill="#059669" transform="rotate(-90 125 400)">PLACE ON FOLD (CENTER FRONT)</text>

  <!-- Pattern Metadata Annotations -->
  <g transform="translate(240, 200)">
    <text x="0" y="0" font-family="sans-serif" font-size="18" font-weight="bold" fill="#0f172a">BESPOKE ATELIER</text>
    <text x="0" y="22" font-family="sans-serif" font-size="14" font-weight="600" fill="#334155">{aesthetic.upper()} CIRCLE SKIRT PANEL</text>
    <text x="0" y="42" font-family="sans-serif" font-size="12" fill="#64748b">CUT 2 ON FOLD | 100% COTTON / LINEN</text>
    <text x="0" y="60" font-family="sans-serif" font-size="11" fill="#64748b">Waist Arc Radius: {waist_radius_in}" | Skirt Length: {skirt_length_in}"</text>
    <text x="0" y="76" font-family="sans-serif" font-size="11" fill="#0284c7">Seam Allowance: 5/8" (1.5 cm) Included</text>
  </g>
</svg>"""

    public_url = ""
    try:
        storage_client = storage.Client(project=FIRESTORE_PROJECT)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(svg_content, content_type="image/svg+xml")
        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"
    except Exception as e:
        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename} (Upload fallback: {str(e)})"

    return json.dumps({
        "status": "success",
        "pattern_name": pattern_name,
        "filename": filename,
        "gcs_bucket": GCS_BUCKET_NAME,
        "public_url": public_url,
        "metadata": {
            "aesthetic": aesthetic,
            "waist_radius_in": waist_radius_in,
            "skirt_length_in": skirt_length_in,
            "bust_width_in": bust_width_in,
            "waistcoat_length_in": waistcoat_length_in,
            "content_type": "image/svg+xml"
        }
    }, indent=2)


def get_climate_fabric_advice(city: str) -> str:
    """Fetches real-time weather data for a target city using Open-Meteo and recommends fabric weights (GSM) and fiber choices.

    Args:
        city: City name to look up weather for (e.g. 'London', 'Paris', 'New York', 'Tokyo').

    Returns:
        JSON string containing current temperature, relative humidity, recommended fabric weight class, suggested natural fibers, and lining advice.
    """
    import urllib.request
    import urllib.parse

    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1"
        req = urllib.request.urlopen(geo_url, timeout=5)
        geo_data = json.loads(req.read())
        if not geo_data.get("results"):
            return json.dumps({"error": f"Location '{city}' not found."})

        location = geo_data["results"][0]
        lat, lon = location["latitude"], location["longitude"]
        city_name = location.get("name", city)
        country = location.get("country", "")

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m"
        w_req = urllib.request.urlopen(weather_url, timeout=5)
        w_data = json.loads(w_req.read())

        current = w_data.get("current", {})
        temp_c = current.get("temperature_2m", 20.0)
        humidity = current.get("relative_humidity_2m", 50)

        if temp_c < 10.0:
            rec_weight = "Heavyweight (>250 GSM)"
            fibers = ["Wool Tweed", "Worsted Wool", "Heavy Flannel", "Corduroy", "Wool Gabardine"]
            lining = "Full lining recommended (silk or viscose twill for thermal retention)"
        elif temp_c <= 22.0:
            rec_weight = "Medium weight (150 - 250 GSM)"
            fibers = ["Medium Linen", "Cotton Twill", "Rayon Crepe", "Wool Crepe", "Tencel"]
            lining = "Partial lining or unlined with bias-bound interior seams"
        else:
            rec_weight = "Lightweight (<150 GSM)"
            fibers = ["Linen Voile", "Cotton Lawn", "Batiste", "Silk Habotai", "Chambray"]
            lining = "Unlined; use lightweight self-facings"

        if humidity > 60:
            breathability_note = "High humidity detected: Prioritize 100% pure linen or loose cotton weaves for optimal moisture absorption."
        else:
            breathability_note = "Moderate humidity: Suitable for structured tightly woven textiles."

        return json.dumps({
            "city": f"{city_name}, {country}".strip(", "),
            "temperature_c": temp_c,
            "temperature_f": round(temp_c * 1.8 + 32, 1),
            "humidity_pct": humidity,
            "recommended_fabric_weight": rec_weight,
            "suggested_fibers_and_weaves": fibers,
            "lining_recommendation": lining,
            "breathability_note": breathability_note
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Weather lookup failed: {str(e)}"})


def search_historic_fashion(query: str) -> str:
    """Searches The Metropolitan Museum of Art Costume Institute archive for historical garment references, materials, and images.

    Args:
        query: Historical fashion search term (e.g. 'waistcoat', 'circle skirt', '1950s dress', 'corset', 'silk gown').

    Returns:
        JSON string containing matched historical costume artifacts with title, creation date, medium (materials), and image URLs.
    """
    import urllib.request
    import urllib.parse

    try:
        search_url = f"https://collectionapi.metmuseum.org/public/collection/v1/search?departmentId=8&hasImages=true&q={urllib.parse.quote(query)}"
        req = urllib.request.urlopen(search_url, timeout=5)
        search_data = json.loads(req.read())
        object_ids = search_data.get("objectIDs") or []

        results = []
        for obj_id in object_ids[:2]:
            try:
                obj_url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{obj_id}"
                obj_req = urllib.request.urlopen(obj_url, timeout=5)
                obj_data = json.loads(obj_req.read())
                results.append({
                    "object_id": obj_id,
                    "title": obj_data.get("title", "Historical Costume Piece"),
                    "objectDate": obj_data.get("objectDate", "Unknown Date"),
                    "medium": obj_data.get("medium", "Textile / Mixed Fibers"),
                    "primaryImageSmall": obj_data.get("primaryImageSmall") or obj_data.get("primaryImage") or ""
                })
            except Exception:
                continue

        return json.dumps({
            "query": query,
            "count": len(results),
            "total_matches_in_archive": search_data.get("total", 0),
            "results": results
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Met Museum search failed: {str(e)}"})


async def generate_fashion_flat_sketch(
    garment_description: str,
    aesthetic: str,
    tool_context: Optional[Any] = None
) -> str:
    """Generates a clean 2D technical fashion flat sketch (front and back CAD tech pack views) using Gemini 3.1 Flash Lite Image, saves it as an artifact, uploads it to Cloud Storage, and returns the public HTTP URL.

    Args:
        garment_description: Description of the garment (e.g. '1950s tailored evening jacket with shawl collar and three-quarter sleeves').
        aesthetic: Design style or aesthetic (e.g. 'Vintage 1950s', 'Old Money', 'Cottagecore', 'Minimalist').
        tool_context: Framework tool context for artifact saving (injected automatically).

    Returns:
        JSON string containing the public Cloud Storage download URL, filename, GCS bucket, and sketch metadata.
    """
    import datetime
    import inspect
    from google import genai
    from google.genai import types
    from google.cloud import storage

    prompt = (
        f"Clean 2D technical fashion flat sketch, front and back view, black vector line art on pure solid white background, "
        f"minimal design, precise seamlines, darts, topstitching, and closures, fashion CAD tech pack specification style for: "
        f"{garment_description} in {aesthetic} style."
    )

    cleaned_desc = garment_description.strip().lower().replace(" ", "_").replace("-", "_")[:30]
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"flat_sketch_{cleaned_desc}_{timestamp_str}.png"

    try:
        client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT, location="global")
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"]
            )
        )

        image_bytes = None
        mime_type = "image/png"

        for candidate in response.candidates:
            for part in candidate.content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    if part.inline_data.mime_type:
                        mime_type = part.inline_data.mime_type
                    break

        if not image_bytes:
            return json.dumps({"error": "No image data returned from image generation model."})

        # Save Playground artifact if tool_context is provided
        if tool_context is not None:
            try:
                part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                res = tool_context.save_artifact(filename=filename, artifact=part)
                if inspect.isawaitable(res):
                    await res
            except Exception:
                pass

        # Upload exact raw image bytes directly to GCS bucket
        public_url = ""
        try:
            storage_client = storage.Client(project=FIRESTORE_PROJECT)
            bucket = storage_client.bucket(GCS_BUCKET_NAME)
            blob = bucket.blob(filename)
            blob.upload_from_string(image_bytes, content_type=mime_type)
            public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"
        except Exception as st_err:
            public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename} (GCS upload fallback: {str(st_err)})"

        return json.dumps({
            "status": "success",
            "filename": filename,
            "gcs_bucket": GCS_BUCKET_NAME,
            "public_url": public_url,
            "metadata": {
                "garment_description": garment_description,
                "aesthetic": aesthetic,
                "prompt_used": prompt,
                "model": "gemini-3.1-flash-lite-image",
                "location": "global"
            }
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Fashion flat sketch generation failed: {str(e)}"})


async def generate_garment_motion_preview(
    garment_description: str,
    fabric_type: str,
    tool_context: Optional[Any] = None
) -> str:
    """Generates a 360-degree turntable motion preview video of a garment on a dress form mannequin using Google's Omni model (gemini-omni-flash-preview) in global region.

    Args:
        garment_description: Description of the garment (e.g. 'Old Money tailored linen waistcoat').
        fabric_type: Fabric material (e.g. '100% heavy unbleached Belgian linen').
        tool_context: Framework tool context for artifact saving (injected automatically).

    Returns:
        JSON string containing the public Cloud Storage download URL, filename, GCS bucket, and video metadata.
    """
    import datetime
    import inspect
    import time
    from google import genai
    from google.genai import types
    from google.cloud import storage

    cleaned_desc = garment_description.strip().lower().replace(" ", "_").replace("-", "_")[:30]
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"garment_preview_{cleaned_desc}_{timestamp_str}.mp4"

    prompt = (
        f"A smooth, slow 360-degree turntable studio video of a bespoke {garment_description} "
        f"made from {fabric_type} displayed on a neutral tailor's dress form mannequin. "
        f"Natural studio lighting, soft atelier background, showing realistic fabric weight, "
        f"silhouette balance, and natural textile drape. Professional fashion CAD preview."
    )

    try:
        client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT, location="global")

        # Try gemini-omni-flash-preview model first, falling back to veo-3.1-fast-generate-001 if needed
        model_name = "gemini-omni-flash-preview"
        op = None
        try:
            op = client.models.generate_videos(
                model=model_name,
                prompt=prompt,
                config=types.GenerateVideosConfig(
                    number_of_videos=1,
                    aspect_ratio="16:9"
                )
            )
        except Exception:
            model_name = "veo-3.1-fast-generate-001"
            op = client.models.generate_videos(
                model=model_name,
                prompt=prompt,
                config=types.GenerateVideosConfig(
                    number_of_videos=1,
                    aspect_ratio="16:9"
                )
            )

        # Poll operation until complete
        while not op.done:
            time.sleep(5)
            op = client.operations.get(op)

        if not op.result or not op.result.generated_videos:
            return json.dumps({"error": "No video was returned by the Omni model."})

        generated_vid = op.result.generated_videos[0].video
        video_bytes = None

        if hasattr(generated_vid, "video_bytes") and generated_vid.video_bytes:
            video_bytes = generated_vid.video_bytes
        elif hasattr(generated_vid, "uri") and generated_vid.uri:
            uri = generated_vid.uri
            if uri.startswith("gs://"):
                parts = uri[5:].split("/", 1)
                b_name, o_name = parts[0], parts[1]
                st_client = storage.Client(project=FIRESTORE_PROJECT)
                bucket = st_client.bucket(b_name)
                blob = bucket.blob(o_name)
                video_bytes = blob.download_as_bytes()

        if not video_bytes:
            return json.dumps({"error": "Failed to retrieve generated video bytes."})

        mime_type = "video/mp4"

        # Save Playground artifact if tool_context is provided
        if tool_context is not None:
            try:
                part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
                res = tool_context.save_artifact(filename=filename, artifact=part)
                if inspect.isawaitable(res):
                    await res
            except Exception:
                pass

        # Upload exact raw video bytes directly to GCS bucket
        public_url = ""
        try:
            storage_client = storage.Client(project=FIRESTORE_PROJECT)
            bucket = storage_client.bucket(GCS_BUCKET_NAME)
            blob = bucket.blob(filename)
            blob.upload_from_string(video_bytes, content_type=mime_type)
            public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"
        except Exception as st_err:
            public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename} (GCS upload fallback: {str(st_err)})"

        return json.dumps({
            "status": "success",
            "filename": filename,
            "gcs_bucket": GCS_BUCKET_NAME,
            "public_url": public_url,
            "metadata": {
                "garment_description": garment_description,
                "fabric_type": fabric_type,
                "prompt_used": prompt,
                "model": model_name,
                "location": "global"
            }
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Garment motion preview video generation failed: {str(e)}"})





