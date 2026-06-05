import cv2
import easyocr
import argparse
import numpy as np
import os
import csv
import time
from datetime import datetime
import re
from ultralytics import YOLO

class ALPRSystem:
    def __init__(self, model_path, csv_path='detections.csv', delay_seconds=30):
        """Initialize the ALPR System"""
        print(f"Loading YOLOv8 model from {model_path}...")
        try:
            self.model = YOLO(model_path)
        except Exception as e:
            print(f"Error loading model: {e}")
            print("Make sure your 'best.pt' file is in the correct location!")
            exit(1)
            
        print("Initializing EasyOCR...")
        # Set gpu=True if you have CUDA installed and configured
        self.reader = easyocr.Reader(['en'], gpu=False)
        
        self.csv_path = csv_path
        self.delay_seconds = delay_seconds
        self.last_seen = {} # Dictionary to track {plate_text: last_seen_timestamp}
        
        # Create CSV file with headers if it doesn't exist
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['Vehicle Number', 'Date', 'Time'])

    def clean_text(self, text):
        """Clean OCR text: keep only uppercase letters and numbers"""
        # Remove anything that is not A-Z or 0-9 and convert to uppercase
        cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
        return cleaned

    def save_to_csv(self, plate_text, date_str, time_str):
        """Save detection to CSV file"""
        with open(self.csv_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([plate_text, date_str, time_str])
        print(f"[*] Saved to CSV: {plate_text} at {date_str} {time_str}")

    def draw_overlays(self, frame, x1, y1, x2, y2, text, date_str, time_str):
        """Draw bounding box, black text panels, and text"""
        # 1. Draw Green Bounding Box
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        display_text = text if text else "Unknown Plate"
        date_time_text = f"{date_str} {time_str}"
        
        # 2. Top Panel for Vehicle Number
        (text_w, text_h), _ = cv2.getTextSize(display_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        # Draw black background above box
        cv2.rectangle(frame, (x1, y1 - text_h - 10), (x1 + text_w, y1), (0, 0, 0), -1)
        # Draw green text
        cv2.putText(frame, display_text, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 3. Bottom Panel for Date & Time
        (dt_w, dt_h), _ = cv2.getTextSize(date_time_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        # Draw black background below box
        cv2.rectangle(frame, (x1, y2), (x1 + dt_w, y2 + dt_h + 10), (0, 0, 0), -1)
        # Draw green text
        cv2.putText(frame, date_time_text, (x1, y2 + dt_h + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    def process_frame(self, frame):
        """Process a single image frame (Inference + OCR + Logging + Drawing)"""
        # Run YOLO inference
        results = self.model(frame, stream=True, verbose=False)
        
        # Get current date and time
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        current_timestamp = time.time()

        for result in results:
            for box in result.boxes:
                # Bounding box coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                confidence = box.conf[0].item()

                if confidence > 0.5:
                    # Crop license plate with slight padding
                    pad = 5
                    h, w = frame.shape[:2]
                    y1_p = max(0, y1 - pad)
                    y2_p = min(h, y2 + pad)
                    x1_p = max(0, x1 - pad)
                    x2_p = min(w, x2 + pad)
                    
                    plate_crop = frame[y1_p:y2_p, x1_p:x2_p]
                    
                    if plate_crop.size == 0:
                        continue
                        
                    # Perform OCR
                    gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
                    ocr_results = self.reader.readtext(gray)
                    
                    raw_text = ""
                    for (bbox, text, prob) in ocr_results:
                        if prob > 0.3: # OCR confidence threshold
                            raw_text += text
                            
                    # Clean OCR text
                    cleaned_text = self.clean_text(raw_text)
                    
                    # Logic: If text is not empty
                    if cleaned_text:
                        # Check duplicate logic (30 seconds delay)
                        if cleaned_text not in self.last_seen or (current_timestamp - self.last_seen[cleaned_text]) > self.delay_seconds:
                            # Save to CSV and update tracking dict
                            self.save_to_csv(cleaned_text, date_str, time_str)
                            self.last_seen[cleaned_text] = current_timestamp

                    # Draw the UI components
                    self.draw_overlays(frame, x1, y1, x2, y2, cleaned_text, date_str, time_str)
                    
        return frame


def run_image_folder(alpr, folder_path):
    """Run ALPR on all images inside a specific folder"""
    print(f"\nProcessing images in folder: {folder_path}")
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            filepath = os.path.join(folder_path, filename)
            frame = cv2.imread(filepath)
            
            if frame is not None:
                processed_frame = alpr.process_frame(frame)
                
                # Resize if image is too large for the screen
                h, w = processed_frame.shape[:2]
                if w > 1280:
                    processed_frame = cv2.resize(processed_frame, (1280, int(h * 1280 / w)))
                    
                cv2.imshow("ALPR Image Viewer", processed_frame)
                print(f"Showing {filename}. Press ANY key to see next image, or 'q' to quit.")
                
                key = cv2.waitKey(0) & 0xFF
                if key == ord('q'):
                    break
    cv2.destroyAllWindows()


def run_video_stream(alpr, source):
    """Run ALPR on a continuous video stream (Webcam or RTSP)"""
    # Convert '0' (string) to 0 (int) for webcam
    if source.isdigit():
        source = int(source)
        print(f"\nStarting webcam stream...")
    else:
        print(f"\nStarting RTSP CCTV stream: {source}")
        
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Error: Could not open video source {source}")
        return

    print("Stream active. Press 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("End of stream or connection lost.")
            break

        processed_frame = alpr.process_frame(frame)
        cv2.imshow("ALPR Live Stream", processed_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="Modular YOLOv8 ALPR System")
    parser.add_argument('--source', type=str, default='0', help='0 for Webcam, RTSP URL for CCTV, or Path to Image Folder')
    parser.add_argument('--model', type=str, default='models/best.pt', help='Path to YOLOv8 model')
    parser.add_argument('--csv', type=str, default='detections.csv', help='Path to save CSV records')
    parser.add_argument('--delay', type=int, default=30, help='Seconds to wait before recording the same plate again')
    args = parser.parse_args()

    # Initialize System
    alpr = ALPRSystem(model_path=args.model, csv_path=args.csv, delay_seconds=args.delay)

    # Determine mode based on source
    if os.path.isdir(args.source):
        # Image Folder Mode
        run_image_folder(alpr, args.source)
    else:
        # Webcam or RTSP Stream Mode
        run_video_stream(alpr, args.source)

if __name__ == "__main__":
    main()
