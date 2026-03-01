# Monitoring You

Um script Python que monitora sua atenção através da webcam e dispara um vídeo de alerta quando você desvia o olhar.

## Funcionalidades
- Detecção de rosto ultra sensível (100ms).
- Picture-in-Picture (Sua câmera aparece sobre o vídeo).
- Reprodução de vídeo e áudio via VLC/Pygame.
- Interface semi-fullscreen para não bloquear o sistema.

## Requisitos
- Python 3
- OpenCV (`pip install opencv-python`)
- VLC Media Player (`sudo apt install vlc`)
- Python-VLC (`pip install python-vlc`)

## Como usar
```bash
python3 monitor_atencao.py
```
