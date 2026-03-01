import cv2
import time
import os
import urllib.request
import vlc
import sys

# --- SILENCIADOR DE LOGS DO SISTEMA ---
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
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        
        self.frames_para_disparar = 3 
        self.buffer_frames_perdidos = 0
        
        self.cap = None
        self.camera_indices_tentados = [0, 1, 2, 3, 4]
        self.indice_atual_lista = 1 # Começa no 1 que é o seu padrão
        self.janela_feedback = "Sua Camera (Olhos)"
        
        # Inicializa o VLC
        vlc_flags = ["--quiet", "--no-video-title-show", "--no-xlib", "--avcodec-hw=none"]
        self.instance = vlc.Instance(*vlc_flags)
        self.player = self.instance.media_player_new()

    def download_video(self):
        if not os.path.exists(self.video_path):
            sys.stdout.write("[*] Preparando recursos...\n")
            sys.stdout.flush()
            try:
                req = urllib.request.Request(self.video_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response, open(self.video_path, 'wb') as out_file:
                    out_file.write(response.read())
            except Exception: pass

    def iniciar_camera(self, index):
        if self.cap: self.cap.release()
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            return cap
        return None

    def proxima_camera(self):
        sys.stdout.write("[*] Trocando de camera...\n")
        sys.stdout.flush()
        for _ in range(len(self.camera_indices_tentados)):
            self.indice_atual_lista = (self.indice_atual_lista + 1) % len(self.camera_indices_tentados)
            novo_index = self.camera_indices_tentados[self.indice_atual_lista]
            nova_cap = self.iniciar_camera(novo_index)
            if nova_cap:
                self.cap = nova_cap
                sys.stdout.write(f"[+] Mudou para camera no indice {novo_index}\n")
                sys.stdout.flush()
                return
        sys.stdout.write("[!] Nenhuma outra camera encontrada.\n")
        sys.stdout.flush()

    def run(self):
        self.download_video()
        # Inicia com a camera padrão (indice 1)
        self.cap = self.iniciar_camera(self.camera_indices_tentados[self.indice_atual_lista])
        
        if not self.cap:
            sys.stdout.write("[!] Erro: Webcam inicial não encontrada. Tentando proxima...\n")
            self.proxima_camera()
            if not self.cap: return

        media = self.instance.media_new(self.video_path)
        self.player.set_media(media)
        
        cv2.namedWindow(self.janela_feedback, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.janela_feedback, 320, 240)
        
        try: cv2.setWindowProperty(self.janela_feedback, cv2.WND_PROP_TOPMOST, 1)
        except: pass
        
        sys.stdout.write("\n" + "="*40 + "\n")
        sys.stdout.write(" MONITORAMENTO DE OLHOS ATIVADO \n")
        sys.stdout.write("="*40 + "\n")
        sys.stdout.write("[>] Tecla C: Trocar de Camera\n")
        sys.stdout.write("[>] Tecla ESC/Q: Sair\n\n")
        sys.stdout.flush()
        
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
                eyes = self.eye_cascade.detectMultiScale(gray, 1.3, 10, minSize=(30, 30))

                olhando = len(eyes) > 0

                # Feedback Visual
                frame_draw = frame.copy()
                for (ex, ey, ew, eh) in eyes:
                    cv2.rectangle(frame_draw, (ex, ey), (ex+ew, ey+eh), (255, 0, 0), 2)
                
                # Texto de ajuda na janela
                cv2.putText(frame_draw, "C: Trocar Camera", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.imshow(self.janela_feedback, frame_draw)

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
                if key == ord('q') or key == 27:
                    break
                elif key == ord('c'):
                    self.proxima_camera()
                    
        except KeyboardInterrupt: pass
        finally: self.limpar()

    def limpar(self):
        if self.cap: self.cap.release()
        if self.player: self.player.stop()
        cv2.destroyAllWindows()
        sys.stdout.write("\n[!] Monitoramento encerrado.\n")
        sys.stdout.flush()

if __name__ == "__main__":
    monitor = AttentionMonitor()
    monitor.run()
