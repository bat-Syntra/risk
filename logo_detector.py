"""
Logo detection using template matching with OpenCV
Compares casino logos in screenshots with reference PNG files
"""
import cv2
import numpy as np
import os
from PIL import Image
from io import BytesIO
import json
from typing import List, Dict, Tuple, Optional

class LogoDetector:
    def __init__(self, logo_dir: str = "logos/", config_file: str = "casino_logos.json"):
        self.logo_dir = logo_dir
        self.templates = {}
        self.casino_names = {}
        self._load_templates(config_file)
    
    def _load_templates(self, config_file: str):
        """Load all logo templates from PNG files."""
        try:
            # Load casino configuration
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for casino in data.get("casinos", []):
                name = casino.get("name")
                logo_file = casino.get("logo_file")
                if name and logo_file:
                    logo_path = os.path.join(self.logo_dir, logo_file)
                    if os.path.exists(logo_path):
                        # Load template in grayscale for better matching
                        template = cv2.imread(logo_path, cv2.IMREAD_GRAYSCALE)
                        if template is not None:
                            # Store multiple scales for scale-invariant matching
                            self.templates[name] = {
                                "original": template,
                                "scales": self._create_scaled_templates(template)
                            }
                            self.casino_names[name] = {
                                "emoji": casino.get("emoji", "🎰"),
                                "aliases": casino.get("aliases", [])
                            }
                            print(f"✅ Loaded logo template: {name}")
        except Exception as e:
            print(f"❌ Error loading templates: {e}")
    
    def _create_scaled_templates(self, template: np.ndarray, scales: List[float] = None) -> List[np.ndarray]:
        """Create scaled versions of template for multi-scale matching."""
        if scales is None:
            scales = [0.5, 0.75, 1.0, 1.25, 1.5]
        
        scaled_templates = []
        for scale in scales:
            width = int(template.shape[1] * scale)
            height = int(template.shape[0] * scale)
            if width > 10 and height > 10:  # Minimum size check
                scaled = cv2.resize(template, (width, height))
                scaled_templates.append((scale, scaled))
        return scaled_templates
    
    def detect_logos(self, image_bytes: bytes, threshold: float = 0.5) -> List[Dict]:
        """
        Detect casino logos in an image.
        Returns list of detected casinos with confidence and location.
        """
        detected = []
        
        try:
            # Convert bytes to OpenCV image
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return detected
            
            # For each casino template
            for casino_name, template_data in self.templates.items():
                best_match = None
                best_score = 0
                
                # Try multiple scales
                for scale, scaled_template in template_data["scales"]:
                    # Skip if template is larger than image
                    if scaled_template.shape[0] > img.shape[0] or scaled_template.shape[1] > img.shape[1]:
                        continue
                    
                    # Template matching
                    result = cv2.matchTemplate(img, scaled_template, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    
                    if max_val > best_score and max_val > threshold:
                        best_score = max_val
                        best_match = {
                            "casino": casino_name,
                            "confidence": float(max_val),
                            "location": max_loc,
                            "scale": scale,
                            "emoji": self.casino_names[casino_name]["emoji"]
                        }
                
                if best_match:
                    detected.append(best_match)
                    print(f"🎯 Detected {casino_name}: confidence={best_score:.2f}")
        
        except Exception as e:
            print(f"❌ Error detecting logos: {e}")
        
        return detected
    
    def find_casino_in_region(self, image_bytes: bytes, region: Tuple[int, int, int, int]) -> Optional[str]:
        """
        Look for casino logo in specific region of image.
        region = (x, y, width, height)
        """
        try:
            # Convert bytes to OpenCV image
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return None
            
            # Extract region of interest
            x, y, w, h = region
            roi = img[y:y+h, x:x+w]
            
            # Create temporary image bytes from ROI
            _, buffer = cv2.imencode('.png', roi)
            roi_bytes = buffer.tobytes()
            
            # Detect logos in ROI
            detections = self.detect_logos(roi_bytes, threshold=0.6)
            
            if detections:
                # Return casino with highest confidence
                best = max(detections, key=lambda d: d["confidence"])
                return best["casino"]
        
        except Exception as e:
            print(f"❌ Error in region detection: {e}")
        
        return None
    
    def enhance_ocr_with_logos(self, image_bytes: bytes, ocr_text: str) -> Dict[str, str]:
        """
        Enhance OCR results by detecting actual logos in image.
        Returns mapping of detected casino positions to names.
        """
        detected_logos = self.detect_logos(image_bytes, threshold=0.65)
        
        casino_map = {}
        for detection in detected_logos:
            # Map approximate position to casino name
            x, y = detection["location"]
            position_key = f"{x//100}_{y//100}"  # Grid-based position
            casino_map[position_key] = detection["casino"]
        
        return casino_map
    
    def match_logo_with_text(self, image_bytes: bytes, text_lines: List[str]) -> List[Tuple[str, str]]:
        """
        Match detected logos with nearby OCR text lines.
        Returns list of (text, casino_name) pairs.
        """
        detected_logos = self.detect_logos(image_bytes)
        matches = []
        
        # Simple proximity matching (can be enhanced with actual OCR bounding boxes)
        for i, line in enumerate(text_lines):
            # Check if any detected logo is likely near this text line
            line_y_estimate = i * 50  # Rough estimate of line position
            
            for logo in detected_logos:
                logo_y = logo["location"][1]
                # If logo is within ~100 pixels of estimated line position
                if abs(logo_y - line_y_estimate) < 100:
                    matches.append((line, logo["casino"]))
                    break
        
        return matches


# Standalone function for integration with bridge.py
def detect_casinos_in_image(image_bytes: bytes, fallback_ocr_casinos: List[str] = None) -> List[str]:
    """
    Simple function to detect casinos in an image.
    Returns list of detected casino names, with OCR fallback.
    """
    detector = LogoDetector()
    # Use lower base threshold to detect real logos
    detections = detector.detect_logos(image_bytes, threshold=0.75)
    
    # Extract unique casino names sorted by confidence with smart filtering
    visual_casinos = []
    seen = set()
    for d in sorted(detections, key=lambda x: x["confidence"], reverse=True):
        name = d["casino"]
        conf = d["confidence"]
        
        # Seuils différents selon le bookmaker
        if name in ["Betway", "Casumo"]:
            # Ces bookmakers créent souvent des faux positifs → seuil très haut
            if conf < 0.98:  # Quasi-parfait seulement
                print(f"⚠️ Skipping likely false positive: {name} ({conf:.2f} < 0.98)")
                continue
            else:
                print(f"⚠️ WARNING: {name} detected with HIGH confidence ({conf:.2f}) - may still be false positive")
        elif name in ["BET99", "iBet", "Betsson", "Coolbet"]:
            # Vrais bookmakers qu'on cherche → seuil normal
            if conf < 0.78:
                print(f"⚠️ Low confidence for {name}: {conf:.2f}")
                continue
        else:
            # Autres bookmakers → seuil moyen
            if conf < 0.82:
                continue
        
        if name not in seen:
            print(f"✅ Accepted: {name} ({conf:.2f})")
            visual_casinos.append(name)
            seen.add(name)
    
    # If we found at least 2 casinos visually, trust them
    if len(visual_casinos) >= 2:
        print(f"✅ Visual detection found: {visual_casinos[:2]}")
        return visual_casinos[:2]
    
    # Otherwise merge with OCR fallback
    if fallback_ocr_casinos:
        combined = visual_casinos + [c for c in fallback_ocr_casinos if c not in visual_casinos]
        return combined[:2]
    
    return visual_casinos


if __name__ == "__main__":
    # Test with a sample image
    detector = LogoDetector()
    
    # Test with a local image file
    test_image = "test_screenshot.png"
    if os.path.exists(test_image):
        with open(test_image, "rb") as f:
            image_bytes = f.read()
        
        print("\n🔍 Detecting logos in test image...")
        results = detector.detect_logos(image_bytes)
        
        for r in results:
            print(f"  {r['emoji']} {r['casino']}: {r['confidence']:.2%} confidence at {r['location']}")
    else:
        print(f"⚠️ Test image '{test_image}' not found. Place a screenshot to test.")
