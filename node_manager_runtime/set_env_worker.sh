#!/bin/bash
pip install psutil kubernetes joblib scikit-learn rapidfuzz

pip3 install "numpy<2"
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

pip3 install \
    tqdm \
    pandas \
    transformers \
    faiss-cpu \
    matplotlib \
    pillow \
    opencv-python-headless
    
pip3 install ultralytics

sudo wget --no-check-certificate -O vai3.5_kr260.zip https://www.xilinx.com/bin/public/openDownload?filename=vai3.5_kr260.zip
sudo unzip vai3.5_kr260.zip
cd vai3.5_kr260/target/runtime_deb/
sudo bash setup.sh
cd ..
sudo tar -xzf lack_lib.tar.gz
sudo cp -r lack_lib/* /usr/lib
cd ..
sudo cp ./xbutil_tool/xbutil2 /usr/bin/unwrapped/
echo 'export LD_LIBRARY_PATH=/usr/lib' >> ~/.bashrc
echo 'export PYTHONPATH=/usr/lib/python3.10/site-packages:$PYTHONPATH' >> ~/.bashrc
sudo apt-get update && sudo apt-get install -y python3-opencv



echo "[+] Estrazione manuale di libGL.so.1 da libgl1_1.6.0-1_arm64.deb"

PKG="/home/root/libgl1_1.6.0-1_arm64.deb"
TMPDIR="/home/root/libgl_temp"

# Pulizia eventuale
rm -rf "$TMPDIR"
mkdir -p "$TMPDIR"
cd "$TMPDIR" || exit 1

echo "[+] Estrazione pacchetto Debian..."
ar x "$PKG" || { echo "[!] Errore durante ar x"; exit 1; }
tar -xf data.tar.* || { echo "[!] Errore durante tar xf"; exit 1; }

echo "[+] Rimozione di eventuale symlink rotto /usr/lib/libGL.so.1"
[ -L /usr/lib/libGL.so.1 ] && rm -v /usr/lib/libGL.so.1

echo "[+] Copio le librerie in /usr/lib..."
cp -v ./usr/lib/aarch64-linux-gnu/libGL.so.* /usr/lib/ || exit 1

echo "[+] Creo link simbolico aggiornato..."
ln -sf /usr/lib/libGL.so.1.7.0 /usr/lib/libGL.so.1

echo "[+] Verifica finale:"
ls -l /usr/lib/libGL.so*

echo "[+] Pulizia cartella temporanea..."
rm -rf "$TMPDIR"

echo "[✅] Libreria libGL installata correttamente."


echo "[+] Estrazione manuale di libGLdispatch.so.0 da libglvnd0_1.6.0-1_arm64.deb"

PKG="/home/root/libglvnd0_1.6.0-1_arm64.deb"
TMPDIR="/home/root/libglvnd_temp"

# Pulizia eventuale
rm -rf "$TMPDIR"
mkdir -p "$TMPDIR"
cd "$TMPDIR" || exit 1

echo "[+] Estrazione pacchetto Debian..."
ar x "$PKG" || { echo "[!] Errore durante ar x"; exit 1; }
tar -xf data.tar.* || { echo "[!] Errore durante tar xf"; exit 1; }

echo "[+] Rimozione di eventuale symlink rotto /usr/lib/libGLdispatch.so.0"
[ -L /usr/lib/libGLdispatch.so.0 ] && rm -v /usr/lib/libGLdispatch.so.0

echo "[+] Copio le librerie in /usr/lib..."
cp -v ./usr/lib/aarch64-linux-gnu/libGLdispatch.so.* /usr/lib/ || exit 1

echo "[+] Creo link simbolico aggiornato..."
ln -sf /usr/lib/libGLdispatch.so.0.0.0 /usr/lib/libGLdispatch.so.0

echo "[+] Verifica finale:"
ls -l /usr/lib/libGLdispatch.so*

echo "[+] Pulizia cartella temporanea..."
rm -rf "$TMPDIR"

echo "[✅] Libreria libGLdispatch.so.0 installata correttamente."

echo "[+] Estrazione manuale di libGLX.so.0 da libglx0_1.6.0-1_arm64.deb"

PKG="/home/root/libglx0_1.6.0-1_arm64.deb"
TMPDIR="/home/root/libglx_temp"

# Pulizia eventuale
rm -rf "$TMPDIR"
mkdir -p "$TMPDIR"
cd "$TMPDIR" || exit 1

echo "[+] Estrazione pacchetto Debian..."
ar x "$PKG" || { echo "[!] Errore durante ar x"; exit 1; }
tar -xf data.tar.* || { echo "[!] Errore durante tar xf"; exit 1; }

echo "[+] Rimozione di eventuale symlink rotto /usr/lib/libGLX.so.0"
[ -L /usr/lib/libGLX.so.0 ] && rm -v /usr/lib/libGLX.so.0

echo "[+] Copio le librerie in /usr/lib..."
cp -v ./usr/lib/aarch64-linux-gnu/libGLX.so.* /usr/lib/ || exit 1

echo "[+] Creo link simbolico aggiornato..."
ln -sf /usr/lib/libGLX.so.0.0.0 /usr/lib/libGLX.so.0

echo "[+] Verifica finale:"
ls -l /usr/lib/libGLX.so*

echo "[+] Pulizia cartella temporanea..."
rm -rf "$TMPDIR"

echo "[✅] Libreria libGLX.so.0 installata correttamente."

