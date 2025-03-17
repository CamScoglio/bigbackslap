import cv2
import time
import datetime
import os
import requests
import base64
import json
from dotenv import load_dotenv
import serial


arduino_port = "/dev/cu.usbmodem1301"  # Change this to your Arduino port (e.g., COM3 on Windows)
baud_rate = 9600
arduino = serial.Serial(arduino_port, baud_rate, timeout=1)
time.sleep(2)  # Wait for the connection to establish

def send_command_to_arduino(command):
    """Send a command string to Arduino."""
    arduino.write(f"{command}\n".encode())
    time.sleep(0.1)  # Give Arduino time to process
    
    # Read response from Arduino (optional)
    response = arduino.readline().decode().strip()
    print(f"Arduino says: {response}")

def capture_face_and_analyze():
    # Load environment variables for API key
    load_dotenv()
    
    # Get OpenAI API key from environment variable
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        return
    
    # Create directory for screenshots if it doesn't exist
    if not os.path.exists('face_screenshots'):
        os.makedirs('face_screenshots')
    
    # Initialize face detector
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    # Initialize camera
    camera_url = "http://192.168.1.225:8080"  # Update with your camera URL
    cap = cv2.VideoCapture(camera_url)
    
    # Check if camera opened successfully
    if not cap.isOpened():
        print("Error: Could not open camera.")
        # Try alternative URL formats
        alternative_urls = [
            "http://192.168.1.225:8080/video",
            "http://192.168.1.225:8080/videostream.cgi",
            "rtsp://192.168.1.225:554"
        ]
        for url in alternative_urls:
            print(f"Trying alternative URL: {url}")
            cap = cv2.VideoCapture(url)
            if cap.isOpened():
                print(f"Success with URL: {url}")
                break
        if not cap.isOpened():
            print("Failed to connect to camera after trying alternative URLs.")
            return
    
    print("Camera connected successfully")
    
    # Flag to track if screenshot has been taken
    screenshot_taken = False
    
    while True:
        # Read a frame from the video stream
        ret, frame = cap.read()
        
        if not ret:
            print("Failed to grab frame")
            # Try to reconnect
            cap.release()
            time.sleep(2)
            cap = cv2.VideoCapture(camera_url)
            continue
        
        # Make a copy of the full frame for screenshot
        full_frame = frame.copy()
        
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        # Check if faces are detected
        face_detected = len(faces) > 0
        
        # Draw rectangles around faces for display
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        # Take screenshot and send to OpenAI API only if face is detected and screenshot hasn't been taken yet
        if face_detected and not screenshot_taken:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"face_screenshots/face_{timestamp}.jpg"
            cv2.imwrite(screenshot_path, full_frame)  # Save the full frame without rectangles
            print(f"Face detected! Screenshot saved to {screenshot_path}")
            
            # Call OpenAI API and send the screenshot
            try:
                send_to_openai(screenshot_path, api_key)
                print("Screenshot sent to OpenAI API")
            except Exception as e:
                print(f"Error sending to OpenAI API: {e}")
            
            screenshot_taken = True
            print("Program will continue running for monitoring, but no more screenshots will be taken.")
        
        # Display the frame with rectangles
        status_text = "Face Detected" if face_detected else "No Face Detected"
        cv2.putText(frame, status_text, (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        if screenshot_taken:
            cv2.putText(frame, "Screenshot taken and sent to OpenAI", (10, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        cv2.imshow('Face Detection', frame)
        
        # Exit on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Release resources
    cap.release()
    cv2.destroyAllWindows()

def send_to_openai(image_path, api_key):
    """Send the image to OpenAI API for analysis"""
    
    # Read the image file as binary
    with open(image_path, "rb") as image_file:
        image_data = image_file.read()
    
    # Convert to base64
    base64_image = base64.b64encode(image_data).decode('utf-8')
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "If there's food in the photo, please say 'yes', otherwise say 'no'."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 300
    }
    
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    
    if response.status_code == 200:
        response_data = response.json()
        yes_or_no = response_data["choices"][0]["message"]["content"]
        print("\nOpenAI statement:")
        print(yes_or_no)
        
        send_command_to_arduino(yes_or_no)
        
    else:
        print(f"Error from OpenAI API: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    capture_face_and_analyze()