# 🖥️ Déployer Aletheia sur un VPS (Hostinger / Ubuntu)

Guide copier-coller. On suppose un VPS Ubuntu et un accès **SSH en root**.
Aucune clé secrète n'est écrite dans ce fichier : tu les colles toi-même dans le
`.env` directement sur le serveur (étape 4).

---

## 1. Se connecter au VPS

Depuis ton ordinateur (remplace par l'IP de ton VPS, visible dans le panneau Hostinger) :

```bash
ssh root@TON_IP_VPS
```

## 2. Installer les outils de base

```bash
apt update && apt install -y python3 python3-venv python3-pip git
```

## 3. Récupérer le code

```bash
cd /root
git clone https://github.com/guillaumelacroix1-hash/dadrobot.git
cd dadrobot
git checkout claude/ai-debate-framework-setup-9mp1B
cd aletheia
```

## 4. Créer le fichier de secrets `.env`

```bash
nano .env
```

Colle ceci, en remplaçant par **tes nouvelles clés** (régénérées) :

```
APP_PASSWORD=ChoisisTonMotDePasse
SECRET_KEY=une-longue-chaine-aleatoire-au-hasard
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...
GROQ_API_KEY=
```

Enregistre : `Ctrl+O`, `Entrée`, puis `Ctrl+X` pour quitter.

## 5. Installer les dépendances Python

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

## 6. Test rapide (pour vérifier que ça démarre)

```bash
.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Ouvre dans ton navigateur : `http://TON_IP_VPS:8000`
Tu dois voir l'écran de connexion. Entre ton `APP_PASSWORD`.

> Si la page ne s'ouvre pas : le port 8000 est peut-être fermé. Ouvre-le dans le
> panneau **Hostinger ▸ Firewall** (autorise le port 8000 en TCP), ou installe le
> reverse proxy de l'étape 8 (recommandé).

Arrête le test avec `Ctrl+C` une fois validé.

---

## 7. Le faire tourner en permanence (service systemd)

Pour qu'Aletheia tourne 24h/24 et redémarre tout seul (au reboot ou en cas de crash) :

```bash
nano /etc/systemd/system/aletheia.service
```

Colle :

```ini
[Unit]
Description=Aletheia
After=network.target

[Service]
WorkingDirectory=/root/dadrobot/aletheia
ExecStart=/root/dadrobot/aletheia/.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Active-le :

```bash
systemctl daemon-reload
systemctl enable --now aletheia
systemctl status aletheia      # doit afficher "active (running)"
```

Commandes utiles :
- Voir les logs : `journalctl -u aletheia -f`
- Redémarrer après une mise à jour : `systemctl restart aletheia`

## 8. (Recommandé) Nom de domaine + HTTPS via Nginx

Si tu as un nom de domaine pointé sur l'IP du VPS (ex. `aletheia.tondomaine.com`) :

```bash
apt install -y nginx certbot python3-certbot-nginx
nano /etc/nginx/sites-available/aletheia
```

Colle (remplace le `server_name`) :

```nginx
server {
    listen 80;
    server_name aletheia.tondomaine.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
    }
}
```

Active + certificat HTTPS automatique :

```bash
ln -s /etc/nginx/sites-available/aletheia /etc/nginx/sites-enabled/
nginx -t && systemctl restart nginx
certbot --nginx -d aletheia.tondomaine.com
```

Ton labo est alors accessible en `https://aletheia.tondomaine.com`, 24h/24. 🎉

> Le bloc `Upgrade`/`Connection` est important : c'est lui qui fait passer le
> **WebSocket** (le débat en direct).

---

## Mettre à jour plus tard

```bash
cd /root/dadrobot && git pull
systemctl restart aletheia
```

## Rappels sécurité
- Le `.env` reste **uniquement sur le VPS**, jamais sur GitHub (protégé par `.gitignore`).
- Si une clé a fuité, régénère-la chez le fournisseur et mets la nouvelle dans `.env`.
