import cv2
import time
import os
import urllib.request
import vlc
import sys
import numpy as np

# Silenciando avisos do sistema
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.*=false"
os.environ["OPENCV_LOG_LEVEL"] = "OFF"
os.environ["VLC_VERBOSE"] = "-1"

VIDEO_URL = "https://i.imgur.com/pwRPAsT.mp4"
VIDEO_FILENAME = "video_alerta_v2.mp4"

class AttentionMonitor:
    def __init__(self):
        self.video_path = VIDEO_FILENAME
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        # Modelo específico para quem usa óculos
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye_tree_eyeglasses.xml')
        
        # CLAHE para melhorar o contraste sem estourar o brilho (perfeito para olhos)
        self.clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        
        self.cap = None
        self.camera_idx = 1
        self.janela_feedback = "FEEDBACK_ULTRA_PRECISION"
        
        self.buffer_perdidos = 0
        self.limite_buffer = 4 # Sensibilidade equilibrada
        
        self.video_duration = 0
        self.last_pos = 0
        self.hide_time = 0
        self.is_playing = False

        self.instance = vlc.Instance("--quiet", "--no-video-title-show", "--key-quit=Esc")
        self.player = self.instance.media_player_new()
        self.player.set_fullscreen(True)

    def setup_resources(self):
        if not os.path.exists(self.video_path):
            urllib.request.urlretrieve(VIDEO_URL, self.video_path)
        m = self.instance.media_new(self.video_path)
        self.player.set_media(m)
        self.player.play()
        time.sleep(0.6)
        self.video_duration = self.player.get_length()
        self.player.stop()
        self.hide_time = time.time()

    def connect_camera(self, idx):
        if self.cap: self.cap.release()
        cap = cv2.VideoCapture(idx)
        return cap if cap.isOpened() else None

    def run(self):
        self.setup_resources()
        self.cap = self.connect_camera(self.camera_idx)
        if not self.cap: return

        cv2.namedWindow(self.janela_feedback, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.janela_feedback, 400, 300)

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret: continue

                frame = cv2.flip(frame, 1)
                
                # --- PROCESSAMENTO ANTI-FILTRO AZUL ---
                # Dividimos as cores e pegamos apenas o canal VERDE (Green)
                # O canal verde é o que melhor ignora reflexos de luz azul nas lentes
                b, g, r = cv2.split(frame)
                gray = self.clahe.apply(g) # Aplica contraste adaptativo no canal verde
                # --------------------------------------

                faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))
                olhando = False

                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    
                    # Focamos na área dos olhos
                    roi_gray = gray[y:y+int(h*0.6), x:x+w]
                    roi_color = frame[y:y+int(h*0.6), x:x+w]
                    
                    # Detecção de Alta Precisão (scaleFactor 1.05 analisa mais detalhes)
                    eyes = self.eye_cascade.detectMultiScale(roi_gray, 1.05, 12, minSize=(20, 20))
                    
                    if len(eyes) >= 2:
                        olhando = True
                        for (ex, ey, ew, eh) in eyes:
                            cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (255, 0, 0), 2)

                # UI de Status
                status_color = (0, 255, 0) if olhando else (0, 0, 255)
                status_text = "FOCADO" if olhando else "DESVIADO"
                cv2.putText(frame, f"STATUS: {status_text}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
                cv2.putText(frame, "C: Camera | ESC: Sair", (10, frame.shape[0]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                
                cv2.imshow(self.janela_feedback, frame)

                # Lógica do Vídeo
                if not olhando:
                    self.buffer_perdidos += 1
                    if self.buffer_perdidos >= self.limite_buffer:
                        if not self.is_playing:
                            elapsed = (time.time() - self.hide_time) * 1000
                            jump_to = (self.last_pos + elapsed) % self.video_duration
                            self.player.play()
                            self.player.set_time(int(jump_to))
                            self.is_playing = True
                else:
                    self.buffer_perdidos = 0
                    if self.is_playing:
                        self.last_pos = self.player.get_time()
                        self.hide_time = time.time()
                        self.player.stop()
                        self.is_playing = False

                key = cv2.waitKey(20) & 0xFF
                if key == 27 or key == ord('q'): break
                elif key == ord('c'):
                    self.camera_idx = (self.camera_idx + 1) % 3
                    self.cap = self.connect_camera(self.camera_idx)

        finally:
            if self.cap: self.cap.release()
            self.player.stop()
            cv2.destroyAllWindows()

if __name__ == "__main__":
    AttentionMonitor().run()
