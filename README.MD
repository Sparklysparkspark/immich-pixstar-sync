# Immich → Pix-Star Favorites Sync

This service watches your Immich favorites and emails new ones to Pix-Star frames.

Each Immich user has:

- Their own Immich API key
  
- Their own Pix-Star frame email(s)
  

So favorites stay per-user: what John likes goes to John’s frame, what Jane likes goes to Jane’s frames, etc.

Once installed on your NAS, it runs in the background and keeps frames updated.

---

## 1. Set up your private repo (on your computer)

> **Important:** Never put API keys or emails in a public repo.

### 1.1 Create a PRIVATE repo from this project

- On your Git host (GitHub, Gitea, etc.), create a **new PRIVATE repository**.
  
- Either:
  
  - Use **“Use this template”** (if available), or
    
  - Clone this project locally and push it to your new private repo.
    

From now on, you only work with **your private repo**.

### 1.2 Edit the configuration files in your private repo

You only need to edit:

- `.env`
  
- `pixstar_mapping.json`
  

---

### 1.3 `.env`

Create or edit `.env` in the root of your private repo:

```env
IMMICH_BASE_URL=http://your-immich-host:2283/api
IMMICH_API_KEY=YourAdminApiKeyHere

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your.photomail.sender@gmail.com
SMTP_PASSWORD=your-app-password-here
SMTP_USE_TLS=true

POLL_INTERVAL_SECONDS=300
PIXSTAR_MAPPING_PATH=pixstar_mapping.json
STATE_PATH=pixstar_sync_state.json
```

**Notes:**

- `IMMICH_BASE_URL` **must end with `/api`**, for example:  
  `http://192.168.1.50:2283/api` or `https://photos.example.com/api`
  
- `IMMICH_API_KEY` should be an admin-level Immich API key that can list users.
  
- `SMTP_*` is the email account that will **send photos to Pix-Star** (often a Gmail with an app password).
  
- `POLL_INTERVAL_SECONDS` = how often to check for new favorites (300 = 5 minutes).
  
- Most people can leave `PIXSTAR_MAPPING_PATH` and `STATE_PATH` as-is.
  

---

### 1.4 `pixstar_mapping.json`

This file maps each Immich user to:

- Their Immich login email
  
- Their own Immich user API key
  
- One or more Pix-Star frame email addresses
  

Example:

```json
{
  "defaultPixstarEmails": [],
  "accounts": [
    {
      "immichUser": "john.doe@example.com",
      "immichApiKey": "YourApiKeyHere",
      "pixstarEmails": ["john-frame@mypixstar.com"]
    },
    {
      "immichUser": "jane.doe@example.com",
      "immichApiKey": "YourApiKeyHere",
      "pixstarEmails": [
        "jane-frame@mypixstar.com",
        "jane-frame2@mypixstar.com"
      ]
    }
  ]
}
```

**Fields:**

- `immichUser` – Immich user email (must exactly match the Immich account).
  
- `immichApiKey` – API key created **under that user’s Immich account**.  
  This is how the script knows whose favorites to read.
  
- `pixstarEmails` – One or more Pix-Star frame addresses for that user’s favorites.
  
- `defaultPixstarEmails` (optional) – Global default list; can usually stay as `[]`.  
  If a user has no `pixstarEmails` defined, their favorites will be sent to all emails in this list.  
  This is useful if you want users **without their own mapping** to have their favorites sent to a shared set of frames.
  
  - If you leave `pixstarEmails` empty for all users and only use `defaultPixstarEmails`, then **all users’ favorites** will go to **all addresses** in `defaultPixstarEmails`.

Commit your updated `.env` and `pixstar_mapping.json` to your **private repo**.  
You’re now ready to move to the NAS.

---

## 2. On your NAS: clone, install, and run

These steps happen once per NAS (except `run.sh` / `stop.sh`).

### 2.1 Clone your private repo onto the NAS

```bash
cd /opt
git clone https://your-git-host/your-user/immich-pixstar-sync.git
cd immich-pixstar-sync
```

Your edited `.env` and `pixstar_mapping.json` come along from your private repo.

### 2.2 Create a virtual environment & install dependencies (first time only)

```bash
cd /opt/immich-pixstar-sync
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

You only need to repeat this if you ever rebuild the Python environment.

### 2.3 Start the sync service with `run.sh`

From the project directory:

```bash
cd /opt/immich-pixstar-sync
./run.sh
```

`run.sh`:

- Activates the virtualenv
  
- Starts `python main.py` in the background
  
- Writes logs to `immich-pixstar.log`
  
- Saves the process ID in `immich-pixstar.pid`
  

The service keeps running after you log out or close SSH.

To check what it’s doing:

```bash
tail -f immich-pixstar.log
```

---

## 3. Stopping the service with `stop.sh`

To stop the background sync:

```bash
cd /opt/immich-pixstar-sync
./stop.sh
```

`stop.sh`:

- Reads the PID from `immich-pixstar.pid`
  
- Stops that process
  
- Cleans up the PID file
  

If it’s already stopped, you may see a harmless error; that’s fine.

---

## 4. Resend all favorites (after a frame reset)

If a Pix-Star frame is reset or its photomail folder is wiped, you can resend **all** favorites for one user or all users.

**Typical flow:**

1. Stop the background service:
  
  ```bash
  cd /opt/immich-pixstar-sync
  ./stop.sh
  ```
  
2. Activate the virtualenv:
  
  ```bash
  cd /opt/immich-pixstar-sync
  source .venv/bin/activate
  ```
  
3. **Resend all favorites for one user:**
  
  ```bash
  python main.py --resend-all --user john.doe@example.com
  ```
  
4. **Resend all favorites for all users:**
  
  ```bash
  python main.py --resend-all --all-users
  ```
  
5. Start the background sync again:
  
  ```bash
  ./run.sh
  ```
  

After that, the service goes back to “new favorites only” behavior.

---

## 5. Normal day-to-day usage

After initial setup:

- **After a reboot or NAS update:**
  
  ```bash
  cd /opt/immich-pixstar-sync
  ./run.sh
  ```
  
- **To stop the service:**
  
  ```bash
  cd /opt/immich-pixstar-sync
  ./stop.sh
  ```