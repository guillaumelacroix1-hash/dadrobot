#!/usr/bin/env bash
# =====================================================================
#  Aletheia — installation tout-en-un sur un VPS Ubuntu (lancer en root)
#
#  Usage :
#    ANTHROPIC_API_KEY=sk-ant-... OPENROUTER_API_KEY=sk-or-... \
#    APP_PASSWORD=TonMotDePasse bash setup.sh
#
#  Les clés ne sont JAMAIS écrites dans le dépôt : elles ne servent qu'à
#  générer le fichier .env local sur le serveur (permissions 600).
# =====================================================================
set -euo pipefail

REPO="https://github.com/guillaumelacroix1-hash/dadrobot.git"
BRANCH="claude/ai-debate-framework-setup-9mp1B"
DEST="/root/dadrobot"
APPDIR="$DEST/aletheia"
PORT="${PORT:-8000}"

echo "==> [1/6] Installation des outils système"
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git curl openssl

echo "==> [2/6] Récupération du code (branche $BRANCH)"
if [ -d "$DEST/.git" ]; then
  git -C "$DEST" fetch --all --quiet
  git -C "$DEST" checkout "$BRANCH"
  git -C "$DEST" pull origin "$BRANCH"
else
  git clone "$REPO" "$DEST"
  git -C "$DEST" checkout "$BRANCH"
fi
cd "$APPDIR"

echo "==> [3/6] Environnement Python + dépendances"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -r requirements.txt

echo "==> [4/6] Génération du fichier .env (secrets)"
APP_PASSWORD="${APP_PASSWORD:-$(openssl rand -hex 8)}"
SECRET_KEY="$(openssl rand -hex 32)"
umask 077
cat > .env <<EOF
APP_PASSWORD=$APP_PASSWORD
SECRET_KEY=$SECRET_KEY
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-}
GROQ_API_KEY=${GROQ_API_KEY:-}
EOF
chmod 600 .env

echo "==> [5/6] Service systemd (démarrage 24h/24 + redémarrage auto)"
cat > /etc/systemd/system/aletheia.service <<EOF
[Unit]
Description=Aletheia
After=network.target

[Service]
WorkingDirectory=$APPDIR
ExecStart=$APPDIR/.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port $PORT
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now aletheia
sleep 2
systemctl restart aletheia

echo "==> [6/6] Vérification"
IP="$(curl -fsS https://ifconfig.me 2>/dev/null || echo TON_IP_VPS)"
echo
echo "======================================================"
echo "  ✅ Aletheia est installé et lancé."
echo "  🔗 Lien   : http://$IP:$PORT"
echo "  🔑 Mot de passe : $APP_PASSWORD"
echo "  📜 Logs   : journalctl -u aletheia -f"
echo "======================================================"
echo "  Si la page ne s'ouvre pas : ouvre le port $PORT (TCP)"
echo "  dans Hostinger ▸ Firewall, puis réessaie le lien."
echo
