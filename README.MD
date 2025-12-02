# Immich → Pix-Star Favorites Sync

A lightweight Python service that watches your **Immich favorites** and automatically emails new ones to your **Pix-Star digital frames**.

Each Immich user has:

* Their **own Immich user API key**
* Their **own Pix-Star frame email(s)**

So favorites stay per-user: what John likes goes to John’s frame(s), what Jane likes goes to Jane’s frame(s), etc. Once installed on your NAS (or in a container), it runs in the background and keeps frames updated.

---

### ✅ Tested Immich version: **v2.3.1**

---

## 🔧 Installation Modes

You can run this service in two main ways:

1. **Standard Linux / “normal” NAS (recommended if you can run Python + venv)**
   Clone your **private repo**, create a Python virtualenv, run `./run.sh`.

2. **TrueNAS SCALE / Docker (no Python on host)**
   Use the pre-built Docker image (or build your own) and mount a config directory that contains `.env` and `pixstar_mapping.json`.

The configuration files are the same in both cases.

---

## 🚀 Overview

Immich → Pix-Star Favorites Sync:

* Polls Immich for each user’s **favorite photos**
* Tracks what’s already been sent using a small local state file
* Emails new favorites to that user’s **Pix-Star frame email(s)** via SMTP

All sensitive configuration lives in **your own PRIVATE repo** or on your own NAS, so you never put API keys or emails in a public repository or Docker image.

---

## 🧩 How It Works

1. You configure:

   * A global `.env` file (Immich base URL, admin API key, SMTP settings)
   * A `pixstar_mapping.json` file mapping Immich users → Immich user API keys → Pix-Star frame emails

2. The service:

   * Uses the **admin API key** from `.env` to discover users
   * Uses each user’s **own API key** to fetch their favorites
   * Sends **new** favorites (since the last run) to that user’s Pix-Star frame email(s)
   * Stores sync state in `pixstar_sync_state.json` so it doesn’t resend everything every time

You control how often it checks for new favorites using `POLL_INTERVAL_SECONDS`.

---

## ⚙️ Configure Your Private Repo (do this first)

> 💡 **Important:** Configure your repo **locally** and keep it **PRIVATE** before cloning it onto your NAS or using it to build a Docker image.

### 1️⃣ Create a PRIVATE repo from this project

On your Git host (GitHub, Gitea, etc.):

1. Create a **new PRIVATE repository**.
2. Either:

   * Use **“Use this template”** (if available), or
   * Clone this project locally and push it into your new **PRIVATE** repo.

From this point on, you only work with **your private copy**.

---

### 2️⃣ Edit configuration files in your private repo

You only need to edit:

* `.env`
* `pixstar_mapping.json`

Commit these changes to your private repo **before** cloning it onto your NAS or using Docker.

---

### 2.1 `.env`

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

* `IMMICH_BASE_URL` **must end with `/api`**, for example:
  `http://192.168.1.50:2283/api` or `https://photos.example.com/api`
* `IMMICH_API_KEY` should be an **admin-level** Immich API key that can list users.
* `SMTP_*` describes the email account that will **send photos to Pix-Star**
  (for example, a Gmail account using an app password).
* `POLL_INTERVAL_SECONDS` controls how often to check for new favorites
  (300 seconds = every 5 minutes).
* Most people can leave `PIXSTAR_MAPPING_PATH` and `STATE_PATH` as-is.

---

### 2.2 `pixstar_mapping.json`

This file maps each Immich user to:

* Their Immich login email
* Their **own** Immich user API key
* One or more Pix-Star frame email addresses

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

* `immichUser` – Immich user email (must exactly match the Immich account).
* `immichApiKey` – API key created **under that user’s Immich account**.
  This is how the script knows whose favorites to read.
* `pixstarEmails` – One or more Pix-Star frame addresses for that user.
* `defaultPixstarEmails` (optional) – Global default list; can usually stay as `[]`.
  If a user has no `pixstarEmails` defined, their favorites will be sent to all emails in this list.
  This is useful if you want users **without their own mapping** to have their favorites sent to a shared set of frames.

  * If you leave `pixstarEmails` empty for all users and only use `defaultPixstarEmails`, then **all users’ favorites** will go to **all addresses** in `defaultPixstarEmails`.

Once `.env` and `pixstar_mapping.json` are configured, **commit and push** them to your private repo.

---

### 2.3 Required Immich API permissions

The Immich API keys used by this service need specific permissions so it can see favorites, download photos, and look up users.

For the **admin-level API key** in `IMMICH_API_KEY` (from `.env`), make sure it has at least:

* `asset.read`
* `asset.download`
* `user.read`

For each **per-user API key** in `pixstar_mapping.json` (`immichApiKey`), grant at least:

* `asset.read`
* `asset.download`

These per-user keys are only used to read and download that user’s favorites.

---

## 🖥️ Standard Install: Linux / “Normal” NAS (Python venv)

These steps are for environments where you can run `python3 -m venv` and `pip` (e.g., Ubuntu, Debian, most NAS boxes with Python installed).

### 3️⃣ Clone your private repo onto the NAS

```bash
cd /opt
git clone https://your-git-host/your-user/immich-pixstar-sync.git
cd immich-pixstar-sync
```

Your edited `.env` and `pixstar_mapping.json` will come along from your private repo.

---

### 4️⃣ Create a virtual environment & install dependencies (first time only)

```bash
cd /opt/immich-pixstar-sync
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

You only need to repeat this if you ever rebuild the Python environment.

---

### 5️⃣ Start the sync service with `run.sh`

From the project directory:

```bash
cd /opt/immich-pixstar-sync
./run.sh
```

`run.sh`:

* Activates the virtual environment
* Starts `python main.py` in the background
* Writes logs to `immich-pixstar.log`
* Saves the process ID in `immich-pixstar.pid`

The service keeps running even after you log out of SSH.

To watch the logs:

```bash
tail -f immich-pixstar.log
```

---

### ⏹ Stopping the Service with `stop.sh`

To stop the background sync:

```bash
cd /opt/immich-pixstar-sync
./stop.sh
```

`stop.sh`:

* Reads the PID from `immich-pixstar.pid`
* Stops that process
* Cleans up the PID file

If the process is already stopped, you might see a small error or warning — that’s fine.

---

### 🔁 Resend All Favorites (e.g., after Pix-Star reset)

If a Pix-Star frame is reset or its photomail folder is cleared, you can resend **all** favorites for a single user or for all users.

**Example workflow:**

1. **Stop** the background service:

   ```bash
   cd /opt/immich-pixstar-sync
   ./stop.sh
   ```

2. **Activate** the virtual environment:

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

5. **Start** the background sync again:

   ```bash
   ./run.sh
   ```

After this, the service goes back to only sending **new** favorites as they appear.

---

### 📆 Day-to-Day Usage (standard install)

After the initial install:

* **After NAS reboot or updates:**

  ```bash
  cd /opt/immich-pixstar-sync
  ./run.sh
  ```

* **To stop the service:**

  ```bash
  cd /opt/immich-pixstar-sync
  ./stop.sh
  ```

As long as `run.sh` is running and your SMTP + Immich config is valid, new favorites will keep flowing automatically from Immich to your Pix-Star frames.

---

## 🐧 TrueNAS SCALE Install (via Docker)

TrueNAS SCALE doesn’t let you install Python + pip directly on the host, so the easiest way to run this service is as a **Docker container**.

The Docker image:

- Already includes Python and all dependencies
- Does **not** include your secrets
- Reads config files from a host folder that you mount into the container at `/config`

> ✅ Before you start:  
> Make sure you have **already created** `.env` and `pixstar_mapping.json` on your computer by following the steps above.

---

### 1️⃣ Create a config folder on TrueNAS

1. Open the **TrueNAS web UI**.
  
2. Go to **Storage → Datasets**.
  
3. Create (or pick) a dataset for configs, for example:
  
  - `YourPool/immich-pixstar-sync-config`
4. Note the **path**. It will look like:
  
  ```text
  /mnt/YourPool/immich-pixstar-sync-config
  ```
  

### 2️⃣ Put `.env` and `pixstar_mapping.json` into that folder

You have two easy options:

#### Option A – Use an SMB share (recommended)

1. In TrueNAS, go to **Shares → Windows Shares (SMB)**.
  
2. Create a new SMB share pointing to:
  
  `/mnt/YourPool/immich-pixstar-sync-config`
  
3. From your **Mac/PC**, connect to the share (e.g. `smb://truenas/immich-pixstar-sync-config`).
  
4. Copy your `.env` and `pixstar_mapping.json` files into that folder.
  

You should now see on TrueNAS:

`/mnt/YourPool/immich-pixstar-sync-config/.env /mnt/YourPool/immich-pixstar-sync-config/pixstar_mapping.json`

#### Option B – Use the TrueNAS Shell (if you like terminals)

From your computer, in the same folder as `.env` and `pixstar_mapping.json`:

`scp .env pixstar_mapping.json root@truenas:/mnt/YourPool/immich-pixstar-sync-config/`

(Replace `truenas` with your box’s hostname or IP, and `YourPool` with your pool name.)

---

### 3️⃣ Launch the Docker image in TrueNAS SCALE

Now wire the image to that config folder.

1. In the TrueNAS web UI, go to **Apps → Launch Docker Image**.
  
2. **Application Name**:  
  `immich-pixstar-sync` (or anything you like, all lowercase).
  
3. **Image → Repository**:
  
  `sparklysparkspark/immich-pixstar-sync`
  
4. **Tag**:
  
  `latest`
  
5. **Networking**:  
  Leave defaults (it only needs outbound HTTP/HTTPS + SMTP).
  
6. **Storage → Add Host Path Volume**:
  
  - **Type**: Host Path
    
  - **Host Path**:
    
    `/mnt/YourPool/immich-pixstar-sync-config`
    
  - **Mount Path** (inside container):
    
    `/config`
    
7. **Environment Variables** → Add:
  
  - Name: `PIXSTAR_MAPPING_PATH`  
    Value: `/config/pixstar_mapping.json`
    
  - Name: `STATE_PATH`  
    Value: `/config/pixstar_sync_state.json`
    

> ℹ️ All the other settings (Immich URL, admin API key, SMTP, poll interval, etc.) are read from `/config/.env`, which is the `.env` file you created earlier.

8. **Restart Policy**:  
  Set to **Always** (recommended) so it comes back after reboots.
  
9. Click **Save / Deploy**.
  

---

### 4️⃣ Check that it’s working

1. Go to **Apps → Installed Apps**.
  
2. Click your `immich-pixstar-sync` app.
  
3. Open the **Logs**.
  
4. You should see messages like:
  
  - syncing favorites
    
  - sending images
    
  - any errors talking to Immich / SMTP
    

The app will:

- Read config from `/config/.env` and `/config/pixstar_mapping.json`
  
- Write its state file to:
  
  `/mnt/YourPool/immich-pixstar-sync-config/pixstar_sync_state.json`
  

As long as the app is running and your config is correct, any **new favorites** in Immich will be emailed to the right Pix-Star frame(s).