import os
import sqlite3
import asyncio
import threading
import random
from flask import Flask, request, render_template_string, jsonify
from telethon import TelegramClient, functions, types
from telethon.errors import FloodWaitError, PeerFloodError
from telethon.sessions import StringSession

app = Flask(__name__)

# المجموعات المصدر العربية
COUNTRIES = {
    "AR": {
        "name": "عرب", 
        "links": [
            "https://t.me/KSAUX_X",             # المجموعة الأولى
            "https://t.me/+GMlqcOGG61JhMDA8"    # المجموعة الثانية
        ]
    }
}

DB_FILE = "jobs.db"
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS jobs 
                 (id TEXT PRIMARY KEY, api_id TEXT, api_hash TEXT, phone TEXT, otp TEXT, 
                  target_group TEXT, country TEXT, target_count INTEGER, current_count INTEGER, status TEXT)''')
    conn.commit()
    conn.close()
init_db()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>ترويج مجانا عضو العرب</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0f172a; color: white; text-align: center; padding: 30px 15px; margin: 0; }
        .box { background: #1e293b; padding: 25px; border-radius: 12px; display: inline-block; width: 100%; max-width: 450px; }
        h1 { color: #38bdf8; font-size: 24px;}
        input, select { width: 100%; padding: 12px; margin: 6px 0; border-radius: 6px; border: 1px solid #334155; background: #0f172a; color: white; box-sizing: border-box; }
        button { width: 100%; padding: 14px; background: #38bdf8; color: #0f172a; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; margin-top: 10px; }
        .info-box { background: rgba(56, 189, 248, 0.1); border-right: 4px solid #38bdf8; padding: 15px; margin-bottom: 15px; border-radius: 6px; font-size: 13px; text-align: right; line-height: 1.6;}
        .warn-box { background: rgba(239, 68, 68, 0.1); border-right: 4px solid #ef4444; padding: 15px; margin-bottom: 15px; border-radius: 6px; font-size: 13px; text-align: right; line-height: 1.6;}
        .progress-container { display: none; margin-top: 20px; text-align: right; }
        .progress-bg { width: 100%; background-color: #0f172a; border-radius: 8px; overflow: hidden; height: 20px; border: 1px solid #334155; }
        .progress-bar { height: 100%; background-color: #10b981; width: 0%; transition: width 0.5s ease; text-align: center; font-size: 12px; line-height: 18px; }
    </style>
</head>
<body>
    <div class="box">
        <h1>🚀 ترويج مجانا عضو العرب</h1>
        
        <div class="info-box">
            <strong>💡 إرشادات هامة جداً قبل البدء:</strong><br>
            1. احصل على <b>API_ID</b> و <b>API_HASH</b> من موقع <a href="https://my.telegram.org" target="_blank" style="color:#38bdf8;">my.telegram.org</a>.<br>
            2. احصل على <b>Chat ID</b> لمجموعتك من بوت <a href="https://t.me/userinfobot" target="_blank" style="color:#38bdf8;">@userinfobot</a>.<br>
            3. <b>الخطوة الأهم:</b> سيصلك كود (OTP) على تطبيق تيليجرام. <b>الموقع سيعرض لك الكود بعد بدء العملية، انسخه وضعه في الخانة المخصصة.</b>
        </div>

        <div class="warn-box">
            <strong>🛡️ لا تقلق بشأن أمان حسابك:</strong><br>
            عند دخول السكربت، قد يصلك إشعار أمني من تيليجرام يقول "تسجيل دخول جديد". <b>اضغط على "نعم، هذا أنا"</b> ولا تقلق، فلن يتم سرقة حسابك.<br><br>
            <strong>⚠️ تنبيه هام:</strong> إذا قمت بالضغط على "لا" أو "رفض" في إشعار تيليجرام، فسيتوقف السكربت فوراً ولن يتمكن من إضافة أي أعضاء.
        </div>

        <form id="step1Form">
            <input type="text" id="api_id" placeholder="API_ID" required>
            <input type="text" id="api_hash" placeholder="API_HASH" required>
            <input type="text" id="phone" placeholder="رقم هاتفك (مثال: +966...)" required>
            <input type="text" id="chat_id" placeholder="Chat ID لمجموعتك الهدف" required>
            
            <select id="country">
                {% for code, data in countries.items() %}
                    <option value="{{ code }}">{{ data.name }}</option>
                {% endfor %}
            </select>

            <select id="target_count">
                <option value="1000">1000 عضو</option>
                <option value="5000">5000 عضو</option>
                <option value="10000">10000 عضو</option>
                <option value="20000">20000 عضو</option>
            </select>

            <button type="submit" id="startBtn">إرسال الكود (OTP)</button>
        </form>

        <div id="otpSection" style="display: none; margin-top: 15px; border-top: 1px solid #334155; padding-top: 15px;">
            <p style="color: #10b981; font-weight: bold;">تم إرسال الكود! اذهب لتطبيق تيليجرام وانسخ الكود المكون من 5 أرقام وضعه هنا:</p>
            <input type="text" id="otp_code" placeholder="أدخل الكود هنا (5 أرقام)">
            <button onclick="sendOtp()" style="background: #10b981;">تأكيد الكود وبدء الترويج</button>
        </div>

        <div class="progress-container" id="progressContainer">
            <div class="progress-label">جاري الترويج <span id="progressText">0 / 0</span></div>
            <div class="progress-bg"><div class="progress-bar" id="progressBar">0%</div></div>
        </div>
    </div>

    <script>
        let currentJobId = null;
        let totalTarget = 0;

        document.getElementById('step1Form').onsubmit = async function(e) {
            e.preventDefault();
            const btn = document.getElementById('startBtn');
            btn.innerText = "جاري إرسال الكود...";
            
            const formData = {
                api_id: document.getElementById('api_id').value,
                api_hash: document.getElementById('api_hash').value,
                phone: document.getElementById('phone').value,
                chat_id: document.getElementById('chat_id').value,
                country: document.getElementById('country').value,
                target_count: document.getElementById('target_count').value
            };
            totalTarget = formData.target_count;

            try {
                const response = await fetch('/start_job', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(formData)
                });
                const data = await response.json();
                if (data.status === 'success') {
                    currentJobId = data.job_id;
                    document.getElementById('otpSection').style.display = 'block';
                    btn.innerText = "تم إرسال الكود، انظر بالأسفل";
                    btn.disabled = true;
                } else {
                    alert("خطأ: " + data.message);
                    btn.innerText = "إرسال الكود (OTP)";
                }
            } catch (err) {
                alert("فشل الاتصال.");
                btn.innerText = "إرسال الكود (OTP)";
            }
        };

        async function sendOtp() {
            const otp = document.getElementById('otp_code').value;
            if(!otp) { alert("أدخل الكود أولاً"); return; }
            
            document.getElementById('otpSection').style.display = 'none';
            document.getElementById('progressContainer').style.display = 'block';
            
            await fetch('/send_otp', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, 
                body: JSON.stringify({job_id: currentJobId, otp: otp})
            });
            
            pollStatus();
        }

        async function pollStatus() {
            const bar = document.getElementById('progressBar');
            const text = document.getElementById('progressText');
            const interval = setInterval(async () => {
                const res = await fetch('/status/' + currentJobId);
                const data = await res.json();
                let percent = (data.current / totalTarget) * 100;
                if(percent > 100) percent = 100;
                bar.style.width = percent + '%'; bar.innerText = Math.floor(percent) + '%';
                text.innerText = data.current + " / " + totalTarget;
                if (data.status === 'finished' || data.status === 'error') {
                    clearInterval(interval);
                    document.getElementById('startBtn').innerText = "بدء الترويج";
                    document.getElementById('startBtn').disabled = false;
                    document.getElementById('otpSection').style.display = 'none';
                }
            }, 2000);
        }
    </script>
</body>
</html>
"""

def run_promotion(job_id, api_id, api_hash, phone, otp, chat_id, country_code, target_count):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    def update_status(current, status="running"):
        c.execute("UPDATE jobs SET current_count=?, status=? WHERE id=?", (current, status, job_id))
        conn.commit()

    links = COUNTRIES[country_code]['links']
    
    async def job():
        client = TelegramClient(StringSession(), api_id, api_hash)
        try:
            await client.start(phone=phone, code_callback=lambda: otp)
            added_total = 0
            
            # خلط الروابط عشان السحب يكون عشوائي (شوي من هذا وشوي من ذاك)
            random.shuffle(links)
            
            for link in links:
                if added_total >= target_count: break
                try:
                    if '+' in link:
                        invite_hash = link.split('+')[-1]
                        invite = await client(functions.messages.CheckChatInviteRequest(invite_hash))
                        channel = invite.chat if isinstance(invite, types.ChatInviteAlready) else (await client(functions.messages.ImportChatInviteRequest(invite_hash))).chats[0]
                    else:
                        # رابط عام (Public Link)
                        username = link.split('/')[-1]
                        channel = await client.get_entity(username)
                except Exception as e: 
                    print(f"[-] Failed to join {link}: {e}")
                    continue

                try:
                    participants = await client.get_participants(channel, limit=min(500, target_count - added_total))
                except Exception as e:
                    print(f"[-] Failed to fetch members: {e}")
                    continue
                    
                target = await client.get_entity(chat_id)
                
                for user in participants:
                    if user.bot or user.is_self: continue
                    if added_total >= target_count: break
                    try:
                        await client(functions.channels.InviteToChannelRequest(channel=target, users=[user.id]))
                        added_total += 1
                        update_status(added_total)
                        await asyncio.sleep(random.uniform(5, 15))
                    except FloodWaitError as e:
                        await asyncio.sleep(e.seconds)
                    except PeerFloodError:
                        update_status(added_total, "error")
                        return

            update_status(added_total, "finished")
        except Exception as e:
            print(f"[-] Job error: {e}")
            update_status(added_total, "error")
        finally:
            await client.disconnect()
            conn.close()

    asyncio.run(job())

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, countries=COUNTRIES)

@app.route('/start_job', methods=['POST'])
def start_job():
    data = request.json
    job_id = str(random.randint(10000, 99999))
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO jobs (id, api_id, api_hash, phone, target_group, country, target_count, current_count, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (job_id, data.get('api_id'), data.get('api_hash'), data.get('phone'), data.get('chat_id'), data.get('country'), int(data.get('target_count')), 0, "waiting_otp"))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "job_id": job_id})

@app.route('/send_otp', methods=['POST'])
def send_otp():
    data = request.json
    job_id = data.get('job_id')
    otp = data.get('otp')
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT api_id, api_hash, phone, target_group, country, target_count FROM jobs WHERE id=?", (job_id,))
    row = c.fetchone()
    
    if row:
        threading.Thread(target=run_promotion, args=(job_id, row[0], row[1], row[2], otp, row[3], row[4], row[5]), daemon=True).start()
        c.execute("UPDATE jobs SET status='running' WHERE id=?", (job_id,))
        conn.commit()
        
    conn.close()
    return jsonify({"status": "success"})

@app.route('/status/<job_id>')
def get_status(job_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT current_count, status FROM jobs WHERE id=?", (job_id,))
    row = c.fetchone()
    conn.close()
    return jsonify({"current": row[0] if row else 0, "status": row[1] if row else "not_found"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)