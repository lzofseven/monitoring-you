# Monitoring You 👁️

Um script Python inteligente que utiliza sua webcam para monitorar sua atenção. Se você desviar o olhar da tela, um vídeo de alerta (com áudio) será disparado instantaneamente.

## 🚀 Funcionalidades
- **Detecção Ultra Sensível:** Reação em tempo real (100ms) ao desvio de olhar.
- **Picture-in-Picture (PiP):** Uma janela flutuante da sua câmera aparece sobre o vídeo para você se monitorar.
- **Reprodução com Áudio:** Utiliza o motor do VLC para garantir sincronia perfeita de som e vídeo.
- **Modo Não-Pare:** O vídeo continua rodando em loop mesmo após você voltar a olhar (Versão V2).
- **Auto-Configurável:** Detecta automaticamente o índice correto da sua webcam.

## 🛠️ Requisitos do Sistema

Este script foi testado em **Linux (Ubuntu/Debian)**.

### 1. Instale o VLC Media Player
O motor de vídeo e áudio depende do VLC instalado no sistema:
```bash
sudo apt update && sudo apt install vlc -y
```

### 2. Prepare o Ambiente Python
Como sistemas Linux modernos protegem o ambiente Python global, **você deve usar um ambiente virtual (venv)**:

```bash
# Crie o ambiente virtual
python3 -m venv venv_monitor

# Ative o ambiente
source venv_monitor/bin/activate

# Instale as bibliotecas necessárias
pip install opencv-python python-vlc
```

## 📂 Como Rodar

### Opção A: Com o Ambiente Ativo (Recomendado)
```bash
source venv_monitor/bin/activate
python3 monitor_atencao.py
```

### Opção B: Comando Direto (Sem Ativar Manualmente)
Substitua `CAMINHO_PARA_SUA_VENV` pelo local onde você criou a pasta `venv_monitor`:
```bash
/caminho/para/venv_monitor/bin/python3 monitor_atencao.py
```

## ⌨️ Comandos Rápidos (Enquanto o script roda)
- **`ESC` ou `Q`**: Encerra o monitoramento e fecha todas as janelas.

## 📝 Notas
- Na primeira execução, o script baixará automaticamente o vídeo de alerta (`video_alerta_v2.mp4`).
- Se a sua câmera não for detectada, verifique se nenhum outro app (Zoom, Browser, Teams) está utilizando a webcam.

---
Desenvolvido com ❤️ por [lzofseven](https://github.com/lzofseven)
