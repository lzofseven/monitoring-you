import cv2
import time
import os
import urllib.request
import vlc
import sys
import numpy as np

# Silenciando avisos inúteis do sistema
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.*=false"
os.environ["OPENCV_LOG_LEVEL"] = "OFF"
os.environ["VLC_VERBOSE"] = "-1"

VIDEO_URL = "https://i.imgur.com/pwRPAsT.mp4"
VIDEO_FILENAME = "video_alerta_v2.mp4"

class AttentionMonitor:
    def __init__(self):
        self.video_path = VIDEO_FILENAME
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye_tree_eyeglasses.xml')
        
        self.cap = None
        self.camera_idx = 1
        self.janela_feedback = "FEEDBACK_MONITOR"
        
        # Ajuste de Sensibilidade
        self.buffer_perdidos = 0
        self.limite_buffer = 5 # Precisa de 5 frames seguidos sem olhar para disparar
        
        # Estado do Vídeo
        self.video_duration = 0
        self.last_pos = 0
        self.hide_time = 0
        self.is_playing = False

        # VLC Setup
        self.instance = vlc.Instance("--quiet", "--no-video-title-show", "--key-quit=Esc")
        self.player = self.instance.media_player_new()
        self.player.set_fullscreen(True)

    def setup_resources(self):
        if not os.path.exists(self.video_path):
            print("[*] Baixando video...")
            urllib.request.urlretrieve(VIDEO_URL, self.video_path)
        
        # Abre e fecha rápido para pegar a duração
        m = self.instance.media_new(self.video_path)
        self.player.set_media(m)
        self.player.play()
        time.sleep(0.6)
        self.video_duration = self.player.get_length()
        self.player.stop()
        self.hide_time = time.time()

    def connect_camera(self):
        for i in [self.camera_idx, 0, 2, 3]:
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                self.camera_idx = i
                return cap
        return None

    def run(self):
        self.setup_resources()
        self.cap = self.connect_camera()
        if not self.cap:
            print("[!] Erro: Câmera não encontrada.")
            return

        cv2.namedWindow(self.janela_feedback, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.janela_feedback, 320, 240)

        print("[+] Monitor iniciado. Pressione ESC para sair.")

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret: 
                    time.sleep(0.1)
                    continue

                frame = cv2.flip(frame, 1)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.equalizeHist(gray)

                # Detecção de Rosto
                faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))
                olhando = False

                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    roi_gray = gray[y:y+h//2, x:x+w]
                    roi_color = frame[y:y+h//2, x:x+w]
                    # Detecção de Olhos (Sensibilidade equilibrada)
                    eyes = self.eye_cascade.detectMultiScale(roi_gray, 1.1, 10, minSize=(25, 25))
                    
                    if len(eyes) >= 2:
                        olhando = True
                        for (ex, ey, ew, eh) in eyes:
                            cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (0, 0, 255), 2)
                            cv2.putText(frame, "OLHO", (x+ex, y+ey-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

                # Status na tela
                status_color = (0, 255, 0) if olhando else (0, 0, 255)
                status_text = "FOCADO" if olhando else "DESVIADO"
                cv2.putText(frame, f"STATUS: {status_text}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
                cv2.imshow(self.janela_feedback, frame)

                # Logica do Vídeo (Com Buffer de Sensibilidade)
                if not olhando:
                    self.buffer_perdidos += 1
                    if self.buffer_perdidos >= self.limite_buffer:
                        if not self.is_playing:
                            # Calcula onde o vídeo deveria estar
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

                # Comandos de Teclado
                key = cv2.waitKey(30) & 0xFF
                if key == 27 or key == ord('q'): # ESC ou Q
                    break
                elif key == ord('c'): # Trocar Camera
                    self.camera_idx = (self.camera_idx + 1) % 4
                    self.cap.release()
                    self.cap = self.connect_camera()

        except Exception as e:
            print(f"[!] Erro inesperado: {e}")
        finally:
            self.cap.release()
            self.player.stop()
            cv2.destroyAllWindows()

if __name__ == "__main__":
    AttentionMonitor().run()
