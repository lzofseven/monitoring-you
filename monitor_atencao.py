import cv2
import time
import os
import urllib.request
import vlc

# Silencia logs do sistema
os.environ["OPENCV_LOG_LEVEL"] = "OFF"

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
        
        # Inicializa o VLC
        self.instance = vlc.Instance("--quiet", "--no-video-title-show")
        self.player = self.instance.media_player_new()

    def download_video(self):
        if not os.path.exists(self.video_path):
            print(f"[*] Preparando vídeo...")
            try:
                req = urllib.request.Request(self.video_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response, open(self.video_path, 'wb') as out_file:
                    out_file.write(response.read())
            except Exception as e:
                print(f"[!] Erro no download: {e}")

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
            print("[!] Erro: Webcam não encontrada.")
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
        
        print("\n[+] Monitoramento Inteligente Ativado!")
        print("[>] O vídeo só aparecerá se você desviar o olhar.")
        
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
                        # PARA o vídeo e ESCONDE a janela imediatamente ao olhar
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

if __name__ == "__main__":
    monitor = AttentionMonitor()
    monitor.run()
