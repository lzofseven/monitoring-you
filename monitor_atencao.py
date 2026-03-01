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
        
        # Carrega os modelos (Haar Cascades)
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        # eye_tree_eyeglasses costuma ser um pouco mais preciso para detectar se o olho está realmente aberto e focado
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye_tree_eyeglasses.xml')
        
        # AUMENTO DE SENSIBILIDADE: De 2 para 1. Piscou ou virou, dispara mais rápido.
        self.frames_para_disparar = 1 
        self.buffer_frames_perdidos = 0
        
        self.cap = None
        self.camera_indices = [1, 0, 2, 3, 4]
        self.idx = 0
        self.janela_feedback = "Sua Camera"
        
        # Setup VLC com atalho de teclado para fechar (ESC)
        vlc_flags = ["--quiet", "--no-video-title-show", "--no-xlib", "--key-quit=Esc"]
        self.instance = vlc.Instance(*vlc_flags)
        self.player = self.instance.media_player_new()
        self.player.set_fullscreen(True)
        
        # Event Manager para detectar se o VLC foi fechado por tecla
        self.event_manager = self.player.event_manager()
        self.should_stop = False
        def vlc_quit_event(event):
            self.should_stop = True
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, vlc_quit_event)
        self.event_manager.event_attach(vlc.EventType.MediaPlayerStopped, vlc_quit_event)
        
        # Variáveis de controle de tempo (para não pausar)
        self.last_video_time = 0 
        self.time_when_hidden = 0 
        self.video_duration = 0 

    def download_video(self):
        if not os.path.exists(self.video_path):
            try:
                req = urllib.request.Request(self.video_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response, open(self.video_path, 'wb') as out_file:
                    out_file.write(response.read())
            except Exception: pass

    def iniciar_camera(self, index):
        if self.cap: self.cap.release()
        cap = cv2.VideoCapture(index)
        return cap if cap.isOpened() else None

    def proxima_camera(self):
        self.idx = (self.idx + 1) % len(self.camera_indices)
        nova_cap = self.iniciar_camera(self.camera_indices[self.idx])
        if nova_cap:
            self.cap = nova_cap
            return True
        return False

    def run(self):
        self.download_video()
        # Inicia com a primeira da lista
        self.cap = self.iniciar_camera(self.camera_indices[self.idx])
        
        if not self.cap:
            # Tenta as outras se a primeira falhar
            for _ in range(len(self.camera_indices)):
                if self.proxima_camera(): break
        
        if not self.cap: return

        media = self.instance.media_new(self.video_path)
        self.player.set_media(media)
        
        self.player.play()
        time.sleep(0.5)
        self.video_duration = self.player.get_length()
        self.player.stop()
        
        cv2.namedWindow(self.janela_feedback, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.janela_feedback, 320, 240)
        
        video_ativo = False
        
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.01)
                    continue

                frame = cv2.flip(frame, 1)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.equalizeHist(gray)

                # Detecção do rosto mais rigorosa (minNeighbors=5 evita falsos rostos)
                faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))
                olhando = False
                
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    roi_gray = gray[y:y+h//2, x:x+w]
                    roi_color = frame[y:y+h//2, x:x+w]
                    
                    # Detecção dos olhos muito mais RÍGIDA
                    # minNeighbors alto (ex: 12) significa que o algoritmo tem que ter MUITA certeza
                    # que é um olho de frente. Se você olhar de lado, ele perde a certeza e dispara.
                    eyes = self.eye_cascade.detectMultiScale(roi_gray, 1.1, 12, minSize=(25, 25))
                    
                    # EXIGE que os dois olhos estejam perfeitamente visíveis
                    if len(eyes) >= 2:
                        olhando = True
                        for (ex, ey, ew, eh) in eyes:
                            cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (255, 0, 0), 2)
                            cv2.putText(frame, "OLHO DETECTADO", (x + ex, y + ey - 10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

                # Informações na tela
                cv2.putText(frame, "C: Trocar Camera", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                if olhando:
                    cv2.putText(frame, "STATUS: FOCADO", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                else:
                    cv2.putText(frame, "STATUS: DESVIADO", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                cv2.imshow(self.janela_feedback, frame)
                try: cv2.setWindowProperty(self.janela_feedback, cv2.WND_PROP_TOPMOST, 1)
                except: pass

                if not olhando:
                    self.buffer_frames_perdidos += 1
                    if self.buffer_frames_perdidos >= self.frames_para_disparar:
                        if not video_ativo:
                            tempo_passado = (time.time() - self.time_when_hidden) * 1000
                            new_time = (self.last_video_time + tempo_passado) % self.video_duration
                            self.player.play()
                            self.player.set_time(int(new_time))
                            video_ativo = True
                else:
                    self.buffer_frames_perdidos = 0
                    if video_ativo:
                        self.last_video_time = self.player.get_time()
                        self.time_when_hidden = time.time()
                        self.player.stop()
                        video_ativo = False

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27 or self.should_stop: 
                    break
                elif key == ord('c'):
                    self.proxima_camera()
                    
        except KeyboardInterrupt: pass
        finally:
            if self.cap: self.cap.release()
            self.player.stop()
            cv2.destroyAllWindows()

if __name__ == "__main__":
    AttentionMonitor().run()
