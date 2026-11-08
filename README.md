# 🚀 Devobs Enterprise Console & SRE Command Center
### منظومة رصد وإدارة البنية التحتية، الخوادم، والعمليات السحابية الذكية

[![CI Build](https://github.com/hamedonassar95/Devobs/actions/workflows/ci.yml/badge.svg)](https://github.com/hamedonassar95/Devobs/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Node Version](https://img.shields.io/badge/Node-v20%2B-green.svg)](https://nodejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue.svg)](https://www.typescriptlang.org/)
[![React](https://img.shields.io/badge/React-19.0-61dafb.svg)](https://react.dev/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-v4-38bdf8.svg)](https://tailwindcss.com/)
[![Three.js](https://img.shields.io/badge/Three.js-3D_Visuals-black.svg)](https://threejs.org/)
[![Firebase](https://img.shields.io/badge/Firebase-Firestore-orange.svg)](https://firebase.google.com/)
[![Google Gemini](https://img.shields.io/badge/Gemini-3.8_Flash_%26_Live-8e75ff.svg)](https://ai.google.dev/)

---

## 📖 نظرة عامة (Overview)

منظومة **ServerOps Console** هي منصة متكاملة لهندسة موثوقية المواقع (SRE) وعمليات السحابة (DevOps). تدمج المنصة بين الرصد اللحظي للبنى التحتية، تفاعل ثلاثي الأبعاد لغرفة الخوادم وحرب الدفاع السيبراني، الذكاء الاصطناعي التوليدي عبر نماذج **Google Gemini**، الربط العميق مع خدمات **Google Workspace**، والتكامل التام مع **GitHub CI/CD Pipelines**.

---

## 🌟 الميزات التقنية الرئيسية (Key Features)

### 1. 🖥️ مراقبة الخوادم والأنظمة (Live Server Infrastructure)
- مراقبة حية لاستهلاك المعالج (CPU)، الذاكرة (RAM)، القرص التخزيني، وحركة الشبكة.
- إجراءات تشغيلية فورية: إعادة تشغيل سلسة (Graceful Restart)، وضع الصيانة (Maintenance Mode)، وإضافة خوادم جديدة.
- مزامنة حية سحابية عبر **Firebase Firestore** مع تخزين احتياطي محلي (Offline Resilient).

### 2. 🧊 غرفة الخوادم ثلاثية الأبعاد (Three.js 3D Server Room)
- محاكاة واقعية لمركز بيانات كبائن الخوادم (Racks) مع إضاءة PBR ونظام تبريد زجاجي.
- تدفق حزم بيانات نيون ثلاثية الأبعاد متزامنة مع نبض الخوادم الفعلي.
- تفاعل كامل بالنقر على أي كابينة لعرض القياسات اللحظية وتشخيص الأعطال.

### 3. 🛡️ لعبة الدفاع السيبراني ثلاثية الأبعاد (Cyber Shield 3D)
- لعبة تفاعلية مبنية بالكامل على Three.js للدفاع عن خوادم النظام ضد هجمات الـ DDoS والبرمجيات الخبيثة.
- أنظمة دفاعية ليزرية وموجات تصاعدية للأعداء مع نظام نقاط وتحفيز للفرق التشغيلية.

### 4. 🐙 تكامل GitHub الشامل (GitHub DevOps & CI/CD Hub)
- تتبع فوري لمسارات **GitHub Actions CI/CD** وحالات بناء وتدقيق المشروعات.
- استعراض سجل الـ Commits، الـ Branches، والـ Pull Requests.
- تحويل حوادث الخوادم التشغيلية (Incidents) إلى **GitHub Issues** تلقائياً بنموذج SRE موحد.
- توليد تقارير الإصدارات (Release Notes) والتغييرات بضغطة زر عبر **Gemini AI**.
- دليل تفاعلي ومرئي لربط ودفع المشروع إلى GitHub فوراً.

### 5. 🤖 مساعد DevOps الذكي (Gemini Copilot Suite)
- نموذج **Gemini 3.8 Flash** لتحليل الأسباب الجذرية للأعطال (RCA) فور وقوعها.
- تدقيق شامل للبنية التحتية (Health & Security Audit) بتقرير تنفيذي تفصيلي.
- محادثة تفاعلية مدعومة بالبحث المباشر عبر الإنترنت (**Google Search Grounding**).
- تفريغ الأوامر الصوتية وتحويل الصوت إلى نص (**gemini-3.5-transcribe**).
- استوديو وسائط الذكاء الاصطناعي لتوليد المخططات، الفيديو، والموسيقى التصويرية.

### 6. 💼 تكامل حزمة Google Workspace
- **Google Docs**: صياغة تقارير الحوادث الرسمية ووثائق ما بعد الوفاة (Post-Mortem).
- **Google Sheets**: تصدير وتحليل مقاييس الأداء وجداول الخوادم لحظياً.
- **Google Slides**: بناء عروض تقديمية لاجتماعات SRE وإدارة المخاطر.
- **Google Drive, Gmail, Chat, Tasks, Keep, Calendar, Forms**.

---

## 🛠️ التقنيات المستخدمة (Tech Stack)

| النطاق | التقنية المستخدمة |
|---|---|
| **الواجهة الأمامية** | React 19, TypeScript, Tailwind CSS v4, Lucide Icons, Motion |
| **الرسوم ثلاثية الأبعاد** | Three.js (WebGL, PBR Shaders, Orbit Controls) |
| **الواجهة الخلفية (Backend)** | Node.js, Express, tsx |
| **محرك الذكاء الاصطناعي** | `@google/genai` (Gemini 3.8 Flash, Lyria, Gemini Omni) |
| **قواعد البيانات السحابية** | Firebase Firestore (Real-time sync) |
| **الأتمتة والـ CI/CD** | GitHub Actions Workflows |

---

## ⚡ البدء السريع (Quick Start)

### المتطلبات المسبقة:
- [Node.js](https://nodejs.org/) الإصدار 20 أو أحدث.
- [Git](https://git-scm.com/) مثبت على جهازك.

### 1. تثبيت الحزم (Install Dependencies)
```bash
npm install
```

### 2. إعداد المتغيرات البيئية (Environment Setup)
قم بإنشاء ملف `.env` استناداً إلى `.env.example`:
```bash
cp .env.example .env
```
أضف مفتاح Gemini API الخاص بك:
```env
GEMINI_API_KEY=your_gemini_api_key_here
PORT=3000
```

### 3. تشغيل خادم التطوير (Run Development Server)
```bash
npm run dev
```
افتح المتصفح على: `http://localhost:3000`

### 4. بناء المشروع للإنتاج (Production Build)
```bash
npm run build
npm start
```

---

## 📤 كيفية رفع وربط المشروع بـ GitHub (Push to GitHub)

إذا كنت ترغب في رفع هذا المستودع إلى حسابك الشخصي أو المؤسسي على GitHub:

### الخطوة 1: المستودع على GitHub
المستودع المستهدف: [https://github.com/hamedonassar95/Devobs](https://github.com/hamedonassar95/Devobs)

### الخطوة 2: ربط المستودع المحلي بالبعيد ورفع الشيفرة
```bash
# تهيئة مستودع Git محلياً
git init -b main

# إضافة جميع الملفات
git add .

# إنشاء Commit
git commit -m "feat: complete Devobs AI Intelligence & automated CI/CD"

# ربط المستودع برابط مستودعك Devobs على GitHub
git remote add origin https://github.com/hamedonassar95/Devobs.git

# دفع الشيفرة المصدرية إلى الفرع الرئيسي
git push -u origin main
```

---

## 📂 هيكلة المشروع (Project Structure)

```text
├── .github/
│   └── workflows/
│       ├── ci.yml            # فحص TypeScript وبناء الحزم تلقائياً
│       └── deploy.yml        # مسار النشر السحابي المؤتمت
├── src/
│   ├── components/
│   │   ├── dashboard/        # مكونات لوحة القيادة والمراقبة
│   │   ├── github/           # وحدة التحكم وإدارة مستودعات وعمليات GitHub
│   │   ├── three/            # غرفة الخوادم ثلاثية الأبعاد (Three.js)
│   │   ├── game/             # لعبة الدفاع السيبراني 3D
│   │   ├── chat/             # مساعد Gemini الذكي والتحكم الصوتي
│   │   ├── studio/           # استوديو وسائط الذكاء الاصطناعي
│   │   └── workspace/        # تكاملات Google Docs, Sheets, Slides, etc.
│   ├── services/             # خدمات Firebase, Google APIs, و Gemini
│   ├── types/                # تعريفات TypeScript
│   ├── App.tsx               # التطبيق الرئيسي
│   └── main.tsx              # نقطة الدخول
├── server.ts                 # خادم Express ومسارات Gemini API
└── package.json              # الحزم والإعدادات
```

---

## 📄 الرخصة (License)
هذا المشروع مرخص تحت رخصة **MIT**. راجع ملف [LICENSE](LICENSE) لمزيد من التفاصيل.

---
**فريق التطوير**: تم التطوير بعناية لتقديم أرقى معايير مراقبة الخوادم وهندسة الأنظمة السحابية.
