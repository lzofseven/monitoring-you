import cv2
import time
import os
import urllib.request
import vlc
import sys

# --- SILENCIADOR DE LOGS ---
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.*=false"
os.environ["QT_QPA_PLATFORM"] = "xcb" 
os.environ["OPENCV_LOG_LEVEL"] = "OFF"
os.environ["LIBVA_MESSAGING_LEVEL"] = "0"
os.environ["VLC_VERBOSE"] = "-1"
sys.stderr = open(os.devnull, 'w')

VIDEO_URL = "https://i.imgur.com/pwRPAsT.mp4"
VIDEO_FILENAME = "video_alerta_v2.mp4"

class AttentionMonitor:
    def __init__(self):
        self.video_url = VIDEO_URL
        self.video_path = VIDEO_FILENAME
        
        # Carrega detectores de Rosto e Olhos
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        
        self.frames_para_disparar = 2 
        self.buffer_frames_perdidos = 0
        
        self.cap = None
        self.camera_indices = [1, 0, 2, 3, 4]
        self.idx = 0
        self.janela_feedback = "Sua Camera (Vigilante)"
        
        vlc_flags = ["--quiet", "--no-video-title-show", "--no-xlib", "--avcodec-hw=none"]
        self.instance = vlc.Instance(*vlc_flags)
        self.player = self.instance.media_player_new()

    def download_video(self):
        if not os.path.exists(self.video_path):
            sys.stdout.write("[*] Baixando recursos...\n")
            sys.stdout.flush()
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
        self.cap = self.iniciar_camera(self.camera_indices[self.idx])
        sys.stdout.write(f"[*] Trocando para camera {self.camera_indices[self.idx]}\n")
        sys.stdout.flush()

    def run(self):
        self.download_video()
        self.cap = self.iniciar_camera(self.camera_indices[self.idx])
        
        if not self.cap:
            sys.stdout.write("[!] Erro: Webcam não encontrada.\n")
            return

        media = self.instance.media_new(self.video_path)
        self.player.set_media(media)
        
        cv2.namedWindow(self.janela_feedback, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.janela_feedback, 320, 240)
        
        sys.stdout.write("\n" + "="*40 + "\n")
        sys.stdout.write(" MODO VIGILANTE MÁXIMO ATIVADO \n")
        sys.stdout.write("="*40 + "\n")
        sys.stdout.write("[>] Detecção: Rosto Frontal + Olhos\n")
        sys.stdout.write("[>] Se você desviar o rosto OU o olhar, o vídeo toca.\n")
        sys.stdout.write("[>] Teclas: C (Camera), ESC/Q (Sair)\n\n")
        sys.stdout.flush()
        
        video_ativo = False
        
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret: continue

                frame = cv2.flip(frame, 1)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.equalizeHist(gray) # Melhora detecção em luz ruim

                # 1. Procura o ROSTO primeiro (tem que ser de frente)
                faces = self.face_cascade.detectMultiScale(gray, 1.1, 6, minSize=(100, 100))
                
                olhando = False
                
                for (x, y, w, h) in faces:
                    # Desenha o rosto no feedback
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    
                    # 2. Dentro do ROSTO, procura os OLHOS
                    roi_gray = gray[y:y+h//2, x:x+w] # Só olha na metade superior do rosto
                    roi_color = frame[y:y+h//2, x:x+w]
                    
                    eyes = self.eye_cascade.detectMultiScale(roi_gray, 1.1, 10, minSize=(20, 20))
                    
                    if len(eyes) >= 2: # Exige detectar os dois olhos para ser mais rigoroso
                        olhando = True
                        for (ex, ey, ew, eh) in eyes:
                            cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (255, 0, 0), 2)

                # Feedback Visual
                cv2.putText(frame, "C: Trocar Camera", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.imshow(self.janela_feedback, frame)

                try: cv2.setWindowProperty(self.janela_feedback, cv2.WND_PROP_TOPMOST, 1)
                except: pass

                if not olhando:
                    self.buffer_frames_perdidos += 1
                    if self.buffer_frames_perdidos >= self.frames_para_disparar:
                        if not video_ativo:
                            self.player.play()
                            video_ativo = True
                        if self.player.get_state() == vlc.State.Ended:
                            self.player.stop(); self.player.play()
                else:
                    self.buffer_frames_perdidos = 0
                    if video_ativo:
                        self.player.stop()
                        video_ativo = False

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27: break
                elif key == ord('c'): self.proxima_camera()
                    
        except KeyboardInterrupt: pass
        finally: self.limpar()

    def limpar(self):
        if self.cap: self.cap.release()
        if self.player: self.player.stop()
        cv2.destroyAllWindows()
        sys.stdout.write("\n[!] Monitoramento encerrado.\n")
        sys.stdout.flush()

if __name__ == "__main__":
    AttentionMonitor().run()
