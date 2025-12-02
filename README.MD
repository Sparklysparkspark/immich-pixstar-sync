# Immich → Pix-Star Favorites Sync

A lightweight Python service that watches your **Immich favorites** and automatically emails new ones to your **Pix-Star digital frames**.

Each Immich user has:

* Their **own Immich user API key**
* Their **own Pix-Star frame email(s)**

So favorites stay per-user: what John likes goes to John’s frame(s), what Jane likes goes to Jane’s frame(s), etc. Once installed on your NAS, it runs in the background and keeps frames updated.

---

### ✅ Tested Immich version: **v2.3.1**

---

## 🚀 Overview

Immich → Pix-Star Favorites Sync:

* Polls Immich for each user’s **favorite photos**
* Tracks what’s already been sent using a small local state file
* Emails new favorites to that user’s **Pix-Star frame email(s)** via SMTP

All configuration lives in **your own PRIVATE repo**, so you never put API keys or emails in a public repository.

---

## 🧩 How It Works

1. You configure:

   * A global `.env` file (Immich base URL, admin API key, SMTP settings)
   * A `pixstar_mapping.json` file mapping Immich users → Immich user API keys → Pix-Star frame emails

2. On your NAS, the service:

   * Uses the **admin API key** from `.env` to discover users
   * Uses each user’s **own API key** to fetch their favorites
   * Sends **new** favorites (since the last run) to that user’s Pix-Star frame email(s)
   * Stores sync state in `pixstar_sync_state.json` so it doesn’t resend everything every time

You control how often it checks for new favorites using `POLL_INTERVAL_SECONDS`.

---

## ⚙️ Setup (on your computer first)

> 💡 **Important:** Configure your repo **locally** and keep it **PRIVATE** before cloning it onto your NAS.

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

Commit these changes to your private repo **before** cloning it onto your NAS.

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
* `defaultPixstarEmails` (optional):

  * A global list of Pix-Star emails used when a user has no `pixstarEmails` set.
  * If all `pixstarEmails` are empty and only `defaultPixstarEmails` is used, then **all users’ favorites** go to **all addresses** in `defaultPixstarEmails`.

Once `.env` and `pixstar_mapping.json` are configured, **commit and push** them to your private repo. You’re ready to move to the NAS.

---

### 2.3 Required Immich API permissions

The Immich API keys used by this service need specific permissions so it can see favorites, download photos, and look up users.

For the **admin-level API key** in `IMMICH_API_KEY` (from `.env`), make sure it has at least:

* `asset.read`
* `asset.download`
* `user.read`

Why these are needed:

* `asset.read` – lets the service see which assets exist and which ones are marked as favorites.
* `asset.download` – lets the service download the image data to attach to emails sent to Pix-Star.
* `user.read` – lets the service look up Immich users and match them to entries in `pixstar_mapping.json`.

For each **per-user API key** in `pixstar_mapping.json` (`immichApiKey`), grant at least:

* `asset.read`
* `asset.download`

These per-user keys are only used to read and download that user’s favorites. Giving them `user.read` as well is optional but harmless.

---

## 🖥️ Install & Run on Your NAS

These steps are done **on the NAS** where Immich can be reached.

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

## ⏹ Stopping the Service with `stop.sh`

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

## 🔁 Resend All Favorites (e.g., after Pix-Star reset)

If a Pix-Star frame is reset or its photomail folder is cleared, you can resend **all** favorites for a single user or for all users.

### Example workflow

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

## 📆 Day-to-Day Usage

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
