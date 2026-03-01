import cv2
import time
import os
import urllib.request
import vlc
import sys

# --- SILENCIADOR DE LOGS DO SISTEMA ---
# Esconde avisos de Qt, VA-API, libva e drivers de vídeo
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.*=false"
os.environ["QT_QPA_PLATFORM"] = "xcb" 
os.environ["OPENCV_LOG_LEVEL"] = "OFF"
os.environ["LIBVA_MESSAGING_LEVEL"] = "0"
os.environ["VLC_VERBOSE"] = "-1"

# Redireciona stderr para o limbo para silenciar mensagens de drivers que ignoram as variáveis acima
sys.stderr = open(os.devnull, 'w')

VIDEO_URL = "https://i.imgur.com/pwRPAsT.mp4"
VIDEO_FILENAME = "video_alerta_v2.mp4"

class AttentionMonitor:
    def __init__(self):
        self.video_url = VIDEO_URL
        self.video_path = VIDEO_FILENAME
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        self.frames_para_disparar = 2 
        self.buffer_frames_perdidos = 0
        
        self.cap = None
        self.janela_feedback = "Sua Camera (Feedback)"
        
        # Inicializa o VLC com flags ultra silenciosas
        vlc_flags = [
            "--quiet", 
            "--no-video-title-show", 
            "--no-xlib",
            "--avcodec-hw=none" # Evita erros de aceleração de hardware VA-API/VDPAU no terminal
        ]
        self.instance = vlc.Instance(*vlc_flags)
        self.player = self.instance.media_player_new()

    def download_video(self):
        if not os.path.exists(self.video_path):
            # Usamos stdout direto aqui pois redirecionamos stderr
            sys.stdout.write("[*] Preparando recursos (Vídeo V2)...\n")
            sys.stdout.flush()
            try:
                req = urllib.request.Request(self.video_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response, open(self.video_path, 'wb') as out_file:
                    out_file.write(response.read())
            except Exception:
                pass

    def iniciar_camera(self):
        for i in [1, 0, 2]:
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                return cap
            cap.release()
        return None

    def run(self):
        self.download_video()
        self.cap = self.iniciar_camera()
        
        if not self.cap:
            sys.stdout.write("[!] Erro: Webcam não encontrada.\n")
            return

        media = self.instance.media_new(self.video_path)
        self.player.set_media(media)
        
        # Janela de Feedback sempre ativa
        cv2.namedWindow(self.janela_feedback, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.janela_feedback, 320, 240)
        
        try:
            cv2.setWindowProperty(self.janela_feedback, cv2.WND_PROP_TOPMOST, 1)
        except:
            pass
        
        sys.stdout.write("\n" + "="*40 + "\n")
        sys.stdout.write(" MONITORAMENTO INTELIGENTE ATIVADO \n")
        sys.stdout.write("="*40 + "\n")
        sys.stdout.write("[>] O vídeo só aparecerá se você desviar o olhar.\n")
        sys.stdout.write("[>] Pressione ESC ou Q para encerrar.\n\n")
        sys.stdout.flush()
        
        video_ativo = False
        
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.01)
                    continue

                frame = cv2.flip(frame, 1)
                small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))

                olhando = len(faces) > 0

                # Feedback Visual
                frame_draw = frame.copy()
                for (x, y, w, h) in faces:
                    x, y, w, h = x*2, y*2, w*2, h*2
                    cv2.rectangle(frame_draw, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                cv2.imshow(self.janela_feedback, frame_draw)

                # Mantém a janelinha da camera sempre no topo
                try:
                    cv2.setWindowProperty(self.janela_feedback, cv2.WND_PROP_TOPMOST, 1)
                except:
                    pass

                if not olhando:
                    self.buffer_frames_perdidos += 1
                    if self.buffer_frames_perdidos >= self.frames_para_disparar:
                        if not video_ativo:
                            self.player.play()
                            video_ativo = True
                        
                        if self.player.get_state() == vlc.State.Ended:
                            self.player.stop()
                            self.player.play()
                else:
                    self.buffer_frames_perdidos = 0
                    if video_ativo:
                        self.player.stop()
                        video_ativo = False

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:
                    break
                    
        except KeyboardInterrupt:
            pass
        finally:
            self.limpar()

    def limpar(self):
        if self.cap: self.cap.release()
        if self.player: self.player.stop()
        cv2.destroyAllWindows()
        sys.stdout.write("\n[!] Monitoramento encerrado.\n")
        sys.stdout.flush()

if __name__ == "__main__":
    monitor = AttentionMonitor()
    monitor.run()
