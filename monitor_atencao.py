import cv2
import time
import os
import urllib.request
import numpy as np
import subprocess
import sys

# Silencia logs do sistema
os.environ["OPENCV_LOG_LEVEL"] = "OFF"
sys.stderr = open(os.devnull, 'w')

VIDEO_URL = "https://i.imgur.com/pwRPAsT.mp4"
VIDEO_FILENAME = "video_alerta_v2.mp4"

class AttentionMonitor:
    def __init__(self):
        self.video_url = VIDEO_URL
        self.video_path = VIDEO_FILENAME
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        
        self.frames_para_disparar = 2 
        self.buffer_frames_perdidos = 0
        
        self.cap = None
        self.video_cap = None
        self.audio_process = None
        self.janela_nome = "MONITOR_SISTEMA"
        
        # Sua resolução de tela
        self.screen_w = 1366
        self.screen_h = 768

    def download_video(self):
        if not os.path.exists(self.video_path):
            try:
                req = urllib.request.Request(self.video_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response, open(self.video_path, 'wb') as out_file:
                    out_file.write(response.read())
            except Exception: pass

    def play_audio(self):
        if self.audio_process is None:
            # Toca apenas o áudio do vídeo em loop usando ffplay (nativo no Linux)
            cmd = ["ffplay", "-nodisp", "-loop", "0", self.video_path]
            self.audio_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop_audio(self):
        if self.audio_process:
            self.audio_process.terminate()
            self.audio_process = None

    def run(self):
        self.download_video()
        # Tenta indices de camera
        for i in [1, 0, 2]:
            self.cap = cv2.VideoCapture(i)
            if self.cap.isOpened(): break
        
        if not self.cap: return

        self.video_cap = cv2.VideoCapture(self.video_path)
        
        cv2.namedWindow(self.janela_nome, cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty(self.janela_nome, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        video_ativo = False
        
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret: continue

                frame = cv2.flip(frame, 1)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.equalizeHist(gray)

                # Detecção Rígida
                faces = self.face_cascade.detectMultiScale(gray, 1.1, 6, minSize=(100, 100))
                olhando = False
                for (x, y, w, h) in faces:
                    roi_gray = gray[y:y+h//2, x:x+w]
                    eyes = self.eye_cascade.detectMultiScale(roi_gray, 1.1, 10, minSize=(20, 20))
                    if len(eyes) >= 2:
                        olhando = True
                        for (ex, ey, ew, eh) in eyes:
                            cv2.rectangle(frame[y:y+h//2, x:x+w], (ex, ey), (ex+ew, ey+eh), (255, 0, 0), 2)
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

                # Composição do Frame Final
                if not olhando:
                    self.buffer_frames_perdidos += 1
                    if self.buffer_frames_perdidos >= self.frames_para_disparar:
                        v_ret, v_frame = self.video_cap.read()
                        if not v_ret:
                            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            v_ret, v_frame = self.video_cap.read()
                        
                        display_frame = cv2.resize(v_frame, (self.screen_w, self.screen_h))
                        self.play_audio()
                        video_ativo = True
                    else:
                        display_frame = np.zeros((self.screen_h, self.screen_w, 3), dtype=np.uint8)
                else:
                    self.buffer_frames_perdidos = 0
                    display_frame = np.zeros((self.screen_h, self.screen_w, 3), dtype=np.uint8)
                    if video_ativo:
                        self.stop_audio()
                        video_ativo = False

                # Adiciona a Câmera (PiP) no canto da imagem final
                pip_h, pip_w = 180, 240
                pip_small = cv2.resize(frame, (pip_w, pip_h))
                # Sobrepõe no canto superior direito
                display_frame[10:10+pip_h, self.screen_w-pip_w-10:self.screen_w-10] = pip_small

                cv2.imshow(self.janela_nome, display_frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27: break
                elif key == ord('c'): # Troca de camera
                    idx = (i + 1) % 3
                    self.cap.release()
                    self.cap = cv2.VideoCapture(idx)
                    
        except KeyboardInterrupt: pass
        finally:
            self.stop_audio()
            if self.cap: self.cap.release()
            if self.video_cap: self.video_cap.release()
            cv2.destroyAllWindows()

if __name__ == "__main__":
    AttentionMonitor().run()
