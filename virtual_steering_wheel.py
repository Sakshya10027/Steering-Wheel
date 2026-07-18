import cv2
import mediapipe as mp
import numpy as np
import pydirectinput
import sys

pydirectinput.PAUSE = 0

def main():
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    pose = mp_pose.Pose(
        static_image_mode=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        sys.exit(1)
        
    current_steering = "STRAIGHT"
    current_throttle = "NEUTRAL"
    
    for key in ['w', 'a', 's', 'd']:
        pydirectinput.keyUp(key)
    
    def set_steering(new_state):
        nonlocal current_steering
        if current_steering == new_state:
            return
            
        if current_steering == "LEFT": pydirectinput.keyUp('a')
        elif current_steering == "RIGHT": pydirectinput.keyUp('d')
            
        if new_state == "LEFT": pydirectinput.keyDown('a')
        elif new_state == "RIGHT": pydirectinput.keyDown('d')
            
        current_steering = new_state

    def set_throttle(new_state):
        nonlocal current_throttle
        if current_throttle == new_state:
            return
            
        if current_throttle == "ACCEL": pydirectinput.keyUp('w')
        elif current_throttle == "BRAKE": pydirectinput.keyUp('s')
            
        if new_state == "ACCEL": pydirectinput.keyDown('w')
        elif new_state == "BRAKE": pydirectinput.keyDown('s')
            
        current_throttle = new_state

    print("Starting Virtual Steering Wheel with Accel/Brake. Press 'q' to quit.")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret: break
                
            frame = cv2.flip(frame, 1)
            h, w, c = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb_frame)
            
            angle_deg = 0.0
            depth_val = 0.0
            steering_text = "STEERING: CENTER"
            throttle_text = "THROTTLE: COAST"
            
            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                
                wrist_1 = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
                wrist_2 = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
                shoulder_1 = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
                shoulder_2 = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
                
                if wrist_1.visibility > 0.5 and wrist_2.visibility > 0.5:
                    pt1 = (int(wrist_1.x * w), int(wrist_1.y * h))
                    pt2 = (int(wrist_2.x * w), int(wrist_2.y * h))
                    
                    pts = sorted([pt1, pt2], key=lambda p: p[0])
                    left_pt = pts[0]
                    right_pt = pts[1]
                    
                    cv2.circle(frame, left_pt, 10, (0, 0, 255), -1)
                    cv2.putText(frame, "L", (left_pt[0] - 25, left_pt[1] - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
                    cv2.circle(frame, right_pt, 10, (0, 0, 255), -1)
                    cv2.putText(frame, "R", (right_pt[0] - 25, right_pt[1] - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
                    cv2.line(frame, left_pt, right_pt, (0, 255, 0), 6)
                    
                    dx = right_pt[0] - left_pt[0]
                    dy = right_pt[1] - left_pt[1]
                    angle_deg = np.degrees(np.arctan2(dy, dx))
                    
                    if angle_deg > 8:
                        set_steering("RIGHT")
                        steering_text = "STEERING: RIGHT [D]"
                    elif angle_deg < -8:
                        set_steering("LEFT")
                        steering_text = "STEERING: LEFT [A]"
                    else:
                        set_steering("STRAIGHT")
                        steering_text = "STEERING: CENTER"
                        
                    
                    dist_wrists = np.hypot(wrist_2.x - wrist_1.x, wrist_2.y - wrist_1.y)
                    dist_shoulders = np.hypot(shoulder_2.x - shoulder_1.x, shoulder_2.y - shoulder_1.y)
                    
                    push_ratio = dist_wrists / max(dist_shoulders, 0.01)
                    depth_val = push_ratio
                    
                    bar_y = int(np.clip(np.interp(push_ratio, [0.8, 1.6], [h-50, 50]), 50, h-50))
                    
                    if push_ratio > 1.4:
                        set_throttle("ACCEL")
                        throttle_text = "THROTTLE: GAS [W]"
                        color = (0, 255, 0) 
                    elif push_ratio < 1.05:
                        set_throttle("BRAKE")
                        throttle_text = "THROTTLE: BRAKE [S]"
                        color = (0, 0, 255) 
                    else:
                        set_throttle("NEUTRAL")
                        throttle_text = "THROTTLE: COAST"
                        color = (0, 255, 255)
                        
                    cv2.rectangle(frame, (w-50, 50), (w-30, h-50), (100, 100, 100), 2)
                    
                    y_accel = int(np.interp(1.4, [0.8, 1.6], [h-50, 50]))
                    y_brake = int(np.interp(1.05, [0.8, 1.6], [h-50, 50]))
                    cv2.line(frame, (w-60, y_accel), (w-20, y_accel), (0, 255, 0), 2)
                    cv2.line(frame, (w-60, y_brake), (w-20, y_brake), (0, 0, 255), 2)
                    
                    cv2.circle(frame, (w-40, bar_y), 12, color, -1)
                    
                else:
                    set_steering("STRAIGHT")
                    set_throttle("NEUTRAL")
                    steering_text = "ERROR: SHOW WRISTS"
            else:
                set_steering("STRAIGHT")
                set_throttle("NEUTRAL")
                steering_text = "ERROR: NO PERSON"
                
            cv2.putText(frame, f"Angle: {angle_deg:.1f} deg", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.putText(frame, f"Depth: {depth_val:.2f}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.putText(frame, steering_text, (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)
            cv2.putText(frame, throttle_text, (20, 170), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)
            
            cv2.imshow("Virtual Steering Wheel", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    finally:
        set_steering("STRAIGHT")
        set_throttle("NEUTRAL")
        cap.release()
        cv2.destroyAllWindows()
        pose.close()
        print("Virtual Steering Wheel terminated safely.")

if __name__ == "__main__":
    main()
