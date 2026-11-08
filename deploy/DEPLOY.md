# نشر OMEGA AI مجاناً — خطوات يحيى

التكلفة: **$0**. لا بطاقة في أي خطوة. لا يُرفع `.env` ولا أي مفتاح أبداً.

## ما جهّزناه (v0.1.1 — جاهز للنشر)

- البريدج `bridge/omega_bridge.py` يقرأ `HOST`/`PORT` من البيئة (افتراضي محلي
  `127.0.0.1:8471` كما كان) + يرد CORS على نقاط GET — اللوحة تقدر تعيش على
  دومين آخر (Cloudflare Pages) وتكلم البريدج على Render.
- اللوحة `dashboard/index.html` تقبل `?api=https://<render-url>` — بلا
  `?api=` تخدم محلياً كما كانت (ونفس الشيء داخل Electron).
- `render.yaml` (Blueprint مجاني) + `requirements.txt` (stdlib فقط، صفر حزم).
- نسخ احتياطية قبل التعديل: `bridge/omega_bridge.py.bak_20261107_0935`
  و`dashboard/index.html.bak_20261107_0935` (على القرص، خارج git).

## الخطوة 1 — مستودع GitHub (له وحده)

1. حمّل حزمة الكود من رسالة الشات (ملف `omega-ai-v0.1.1.zip` — الكود كامل،
   commit `8bfe92c`) وفك الضغط على جهازك.
2. على github.com: حسابك (تنبيه صادق: إنشاء حساب جديد تصادف مع جدار
   DataDome فـ 2026-09-25 — إلا بلوكاك، قول ليا ونلقى طريق آخر).
   New repository، اسم `omega-ai`، **Private**.
3. في المستودع: Add file → Upload files → ارفع كل ملفات الحزمة المفكوكة.
4. تأكد: لا `.env` ولا `data/*.db` في المستودع (`.gitignore` يمنعهما).

## الخطوة 2 — البريدج على Render (مجاني)

1. أنشئ حساباً مجانياً على https://render.com (بالإيميل — بلا بطاقة) وقل «تم».
2. Render dashboard → **New → Blueprint** → اربط مستودع `omega-ai`.
3. الخدمة `omega-ai-bridge` تظهر من `render.yaml` (plan: free).
   تحقق: افتح `https://<اسم-خدمتك>.onrender.com/status` — لازم يرجع JSON
   فيه `"supervisor_importable": false` (صحيح على Render: النواة تبقى محلية).
4. ملاحظة صادقة: الخدمة المجانية **تنام بعد 15 دقيقة بلا طلبات** وتستيقظ
   في ~دقيقة. لإبقائها مستيقظة: حساب مجاني على UptimeRobot يفحص
   `https://<خدمتك>.onrender.com/status` كل 10 دقائق.

## الخطوة 3 — اللوحة على Cloudflare Pages (مجاني)

1. حساب مجاني على https://pages.cloudflare.com (بلا بطاقة).
2. Create application → Pages → Connect to Git → مستودع `omega-ai` →
   **Build output directory: `dashboard`** (بلا build command).
3. افتح رابط Pages هكذا: `https://<مشروعك>.pages.dev/?api=https://<خدمتك>.onrender.com`
   — اللوحة تعرض حالة البريدج المستضاف. بلا `?api=` تعرض رسالة "الجسر غير متصل"
   (صحيح: لا بريدج محلي على ذلك الجهاز).

## الحدود (لا ننساها)

- النواة الكاملة (venv ‏766MB‏) **لا تدخل** في Render المجاني — التشغيل الحقيقي
  للوكلاء يبقى على حاسوبك (Electron + `.env` بالمفتاح). المستضاف للعرض فقط.
- لا قرص دائم في Render المجاني — `data/omega.db` يُفقد عند إعادة النشر.
  الذاكرة طويلة الأمد تبقى محلية.
- `POST /run` يرجع 503 بصدق في v0.1 — التنفيذ يأتي في المرحلة 4.

## ما زال معلقاً على يحيى

- حساب Render + «تم» · مستودع GitHub · اختيار الشكل (ويب مستضاف / ويندوز `.exe` —
  الـ `.exe` يُوزع لاحقاً عبر GitHub Releases مجاناً حين يُبنى على ويندوز).
