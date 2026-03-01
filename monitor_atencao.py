import cv2
import time
import os
import urllib.request
import vlc
import sys

# Silencia logs do sistema
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.*=false"
os.environ["QT_QPA_PLATFORM"] = "xcb" 
os.environ["OPENCV_LOG_LEVEL"] = "OFF"
os.environ["VLC_VERBOSE"] = "-1"
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
        self.janela_feedback = "Sua Camera"
        
        # Setup VLC
        self.instance = vlc.Instance("--quiet", "--no-video-title-show")
        self.player = self.instance.media_player_new()
        self.player.set_fullscreen(True)
        
        # Variáveis de controle de tempo (para não pausar)
        self.last_video_time = 0 # milissegundos
        self.time_when_hidden = 0 # segundos do sistema
        self.video_duration = 0 # milissegundos

    def download_video(self):
        if not os.path.exists(self.video_path):
            try:
                req = urllib.request.Request(self.video_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response, open(self.video_path, 'wb') as out_file:
                    out_file.write(response.read())
            except Exception: pass

    def run(self):
        self.download_video()
        for i in [1, 0, 2]:
            self.cap = cv2.VideoCapture(i)
            if self.cap.isOpened(): break
        
        if not self.cap: return

        media = self.instance.media_new(self.video_path)
        self.player.set_media(media)
        
        # Precisamos dar um play/stop rápido para o VLC ler a duração do arquivo
        self.player.play()
        time.sleep(0.5)
        self.video_duration = self.player.get_length()
        self.player.stop()
        
        cv2.namedWindow(self.janela_feedback, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.janela_feedback, 320, 240)
        
        print("[+] Monitoramento Ativado (Vídeo em tempo real)")
        
        video_ativo = False
        
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret: continue

                frame = cv2.flip(frame, 1)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.equalizeHist(gray)

                faces = self.face_cascade.detectMultiScale(gray, 1.1, 6, minSize=(100, 100))
                olhando = False
                for (x, y, w, h) in faces:
                    roi_gray = gray[y:y+h//2, x:x+w]
                    eyes = self.eye_cascade.detectMultiScale(roi_gray, 1.1, 10, minSize=(20, 20))
                    if len(eyes) >= 2: olhando = True

                cv2.imshow(self.janela_feedback, frame)
                try: cv2.setWindowProperty(self.janela_feedback, cv2.WND_PROP_TOPMOST, 1)
                except: pass

                if not olhando:
                    self.buffer_frames_perdidos += 1
                    if self.buffer_frames_perdidos >= self.frames_para_disparar:
                        if not video_ativo:
                            # Calcula quanto tempo passou enquanto estava oculto
                            tempo_passado = (time.time() - self.time_when_hidden) * 1000
                            new_time = (self.last_video_time + tempo_passado) % self.video_duration
                            
                            self.player.play()
                            self.player.set_time(int(new_time))
                            video_ativo = True
                else:
                    self.buffer_frames_perdidos = 0
                    if video_ativo:
                        # Salva o progresso e o momento atual antes de esconder
                        self.last_video_time = self.player.get_time()
                        self.time_when_hidden = time.time()
                        self.player.stop()
                        video_ativo = False

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27: break
                    
        except KeyboardInterrupt: pass
        finally:
            if self.cap: self.cap.release()
            self.player.stop()
            cv2.destroyAllWindows()

if __name__ == "__main__":
    AttentionMonitor().run()
