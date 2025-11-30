"""
Simplified logo detection using color and position analysis
This is a fallback when template matching doesn't work well
"""
from PIL import Image
from io import BytesIO
import numpy as np
from typing import List, Dict, Optional

class SimpleLogoDetector:
    """
    Detect casinos based on dominant colors and positions in screenshots.
    Based on observation:
    - iBet = red logo
    - Coolbet = blue/turquoise logo
    - Betsson = orange logo
    - bet365 = green logo
    """
    
    def __init__(self):
        self.casino_colors = {
            "iBet": [(255, 0, 0), (220, 38, 127)],  # Red/pink
            "Coolbet": [(0, 150, 255), (0, 191, 255)],  # Blue/cyan
            "Betsson": [(255, 140, 0), (255, 165, 0)],  # Orange
            "bet365": [(0, 128, 0), (34, 139, 34)],  # Green
            "BET99": [(255, 0, 0), (220, 20, 60)],  # Red
            "Stake": [(128, 0, 128), (147, 112, 219)],  # Purple
        }
    
    def detect_from_image(self, image_bytes: bytes) -> List[str]:
        """
        Detect casinos by analyzing color regions in the image.
        Returns list of detected casino names.
        """
        try:
            img = Image.open(BytesIO(image_bytes)).convert('RGB')
            width, height = img.size
            detected = []
            
            # Analyze typical logo positions
            # Based on screenshot: logos are around x=40-60 (left) and x=260-280 (right)
            regions = []
            
            # Scan multiple Y positions for calls
            y_positions = [0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85]
            for y_ratio in y_positions:
                # Left side logos (like iBet)
                regions.append((45, height * y_ratio))
                # Right side logos (like Coolbet)  
                regions.append((270, height * y_ratio))
            
            for x, y in regions:
                x, y = int(x), int(y)
                if x < width and y < height:
                    # Sample a small region around the point
                    region = img.crop((max(0, x-20), max(0, y-20), 
                                     min(width, x+20), min(height, y+20)))
                    
                    # Get dominant color
                    pixels = np.array(region)
                    avg_color = tuple(pixels.mean(axis=(0,1)).astype(int))
                    
                    # Match to known casino colors
                    casino = self._match_color(avg_color)
                    if casino and casino not in detected:
                        detected.append(casino)
            
            return detected[:4]  # Return up to 4 casinos
            
        except Exception as e:
            print(f"Color detection error: {e}")
            return []
    
    def _match_color(self, color: tuple) -> Optional[str]:
        """Match a color to a known casino."""
        r, g, b = color
        
        # Simple color matching based on dominant channel
        if r > 150 and g < 100 and b < 100:
            return "iBet"  # Red dominant
        elif b > 150 and r < 100:
            return "Coolbet"  # Blue dominant
        elif r > 200 and g > 100 and g < 200 and b < 100:
            return "Betsson"  # Orange (high red, medium green)
        elif g > 150 and r < 150 and b < 150:
            return "bet365"  # Green dominant
        elif r > 100 and b > 100 and g < 100:
            return "Stake"  # Purple (red + blue)
        
        return None


def enhance_ocr_with_simple_detection(image_bytes: bytes, ocr_casinos: List[str]) -> List[str]:
    """
    Enhance OCR results with simple color-based detection.
    """
    detector = SimpleLogoDetector()
    visual = detector.detect_from_image(image_bytes)
    
    if len(visual) >= 2:
        print(f"✅ Simple detection found: {visual[:2]}")
        return visual[:2]
    
    # Merge with OCR results
    combined = visual + [c for c in ocr_casinos if c not in visual]
    return combined[:2]


if __name__ == "__main__":
    # Test with a local image
    import os
    test_files = ["test_screenshot.png", "screenshot.png"]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\n🔍 Testing with {test_file}...")
            with open(test_file, "rb") as f:
                image_bytes = f.read()
            
            detector = SimpleLogoDetector()
            casinos = detector.detect_from_image(image_bytes)
            print(f"Detected: {casinos}")
            break
    else:
        print("No test image found. Place a screenshot to test.")
