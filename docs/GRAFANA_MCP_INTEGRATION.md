# تكامل Grafana MCP المحلي والاختياري

## الفائدة والنطاق

يوصل خادم Grafana MCP الرسمي Codex بمكدس المراقبة المحلي في Devobs. يستطيع Codex البحث في لوحات Grafana وقراءة إعداد مصدر البيانات وتشغيل استعلامات Prometheus المحدودة. يفيد هذا في فهم مؤشرات المكدس المحلي أثناء التطوير.

الإعداد **اختياري وغير مفعّل افتراضيًا**. المثال في [`.codex/examples/grafana-mcp-readonly.toml`](../.codex/examples/grafana-mcp-readonly.toml) ليس جزءًا من `.codex/config.toml` أو CI أو الموقع. لا يبدأ Grafana أو خادم MCP من تلقاء نفسه، ولا يرسل بيانات إلى خدمة Grafana مستضافة. يجب أن تكون Grafana المحلية شغّالة على `127.0.0.1:3000`؛ راجع [دليل المراقبة المحلي](../monitoring/README.md).

## المصدر والترخيص والتثبيت

- **VERIFIED:** الخادم [grafana/mcp-grafana](https://github.com/grafana/mcp-grafana) مشروع مفتوح المصدر برخصة Apache-2.0. ثُبّت الاختيار على الإصدار `v2.3.0`، مصدره `c8cafb67854c45e79f8f9b5fca7d9b3a403f1771`.
- **VERIFIED:** حزمة Windows x64 الرسمية [mcp-grafana_Windows_x86_64.zip](https://github.com/grafana/mcp-grafana/releases/download/v2.3.0/mcp-grafana_Windows_x86_64.zip) لها SHA-256 التالي حسب ملف checksums الرسمي: `13049249ff4e5251ee60ba38ea47e6aba96c20939fbf133915b482a93827edfe`.
- **VERIFIED:** إصدار الخادم يدعم STDIO و`--disable-write` و`--disable-api` و`--enabled-tools` وملف الرمز `GRAFANA_SERVICE_ACCOUNT_TOKEN_FILE`. `--disable-write` يخفي أدوات التعديل، و`--disable-api` يحجب أداة طلب Grafana العامة التي قد تتجاوز قيود الاستعلام.
- **VERIFIED:** يوثق upstream أن PromQL وLogQL أدوات استعلام لا تعبّر عن الكتابة، وأن استعلامات SQL الخام تُزال في وضع `--disable-write`. الإعداد هنا يتيح فئة Prometheus فقط ولا يتيح Loki أو SQL أو API أو أدوات التنبيه أو الإدارة. حد الاستعلام يضبط نافذة Prometheus إلى 24 ساعة و5000 نقطة لكل سلسلة؛ وهو حد لحجم الطلب، وليس سقفًا مضمونًا لعدد السلاسل أو كل عمل داخلي للمصدر.

نزّل حزمة `v2.3.0` من صفحة [الإصدارات الرسمية](https://github.com/grafana/mcp-grafana/releases/tag/v2.3.0)، ثم تحقق منها قبل فك الضغط:

```powershell
Get-FileHash .\mcp-grafana_Windows_x86_64.zip -Algorithm SHA256
```

طابق الناتج مع البصمة أعلاه، ثم فك الأرشيف بمجلد محلي مثل `%LOCALAPPDATA%\Devobs\mcp-grafana\2.3.0`. لا تستخدم نسخة `latest` غير مثبتة.

## إعداد Grafana محليًا على Windows

1. شغّل المكدس المحلي وفق [`monitoring/README.md`](../monitoring/README.md)، ثم افتح `http://127.0.0.1:3000`.
2. أنشئ Service Account بدور **Viewer**. امنحه قراءة اللوحات والاستعلام عن مصدر Prometheus فقط؛ لا تمنحه دور Admin أو Editor أو صلاحيات تغيير التنبيهات واللوحات. إذا كان إصدار Grafana يدعم نطاق RBAC للمصدر، قصّر النطاق على UID `prometheus`.
3. أنشئ token للحساب وخزّنه في ملف محلي خارج المستودع، مع صلاحية قراءة لحساب Windows المستخدم فقط. لا تضع token في ملف إعداد Codex أو مستودع Git.
4. خزّن الرمز محليًا في PowerShell. النص يتحول مؤقتًا في ذاكرة العملية، والملف المحلي يحتوي الرمز بصيغة نصية مع ACL لحساب Windows الحالي:

   ```powershell
   $tokenPath = Join-Path $env:LOCALAPPDATA "Devobs\secrets\grafana-mcp-token.txt"
   New-Item -ItemType Directory -Force (Split-Path $tokenPath) | Out-Null
   $secureToken = Read-Host "Grafana service account token" -AsSecureString
   $plainToken = [System.Net.NetworkCredential]::new("", $secureToken).Password
   [System.IO.File]::WriteAllText($tokenPath, $plainToken, [System.Text.UTF8Encoding]::new($false))
   $plainToken = $null
   icacls $tokenPath /inheritance:r /grant:r "$($env:USERNAME):(R,W)"
   ```

   احذف الملف بعد إبطال الرمز من Grafana عند إيقاف التكامل.
5. انسخ جدول `[mcp_servers.grafana]` من المثال إلى `%USERPROFILE%\.codex\config.toml`. عدّل `command` إلى المسار المطلق لـ`mcp-grafana.exe`، و`GRAFANA_SERVICE_ACCOUNT_TOKEN_FILE` إلى مسار ملفك المحلي. أضف الجدول دون استبدال إعدادات MCP الحالية. لا تنسخه إلى إعداد المستودع العام.
6. افتح `/mcp` في Codex، وتحقق من ظهور Grafana، ثم ابدأ بطلب قراءة بسيط مثل: «اعرض أسماء لوحات Devobs ومصدر Prometheus، من دون تعديل أي شيء».

يوفر خادم Grafana فلاتر أدوات إضافية، لكن خفض الأدوات في MCP لا يغني عن RBAC في Grafana. فئة الاستعلام قد تكشف قيم المقاييس التي يستطيع token قراءتها، لذا استخدمها مع المكدس المحلي فقط وراجع البيانات قبل إرسال أي جزء منها في المحادثة. لا توصل هذه الإعدادات بسجلات العملاء أو traces أو Grafana Cloud.

## الإيقاف والتحقق

- لإيقاف التكامل، احذف جدول Grafana من ملف Codex الشخصي وأعد تشغيل Codex.
- لإبطال الوصول، احذف token من Grafana واحذف الملف المحلي. لا يؤثر ذلك على ملفات أو إعدادات Devobs.
- **UNVERIFIED:** لم نشغّل Grafana أو Docker، ولم ننشئ Service Account أو token، ولم ننفذ استدعاء MCP حيًا. CI يثبت سلامة المثال المكتوب فقط؛ قبول Codex runtime يبقى **OPEN**.
- AI-9 وP01 يبقيان على حالتهما السابقة؛ هذا التكامل لا يغيّر أي بوابة جاهزية أو إعداد نشر.

## مصادر رسمية

- [Grafana MCP v2.3.0](https://github.com/grafana/mcp-grafana/tree/v2.3.0)
- [إرشادات الخادم وأعلام CLI في الإصدار المثبت](https://github.com/grafana/mcp-grafana/blob/v2.3.0/README.md)
- [بناء وتثبيت إصدار Windows](https://github.com/grafana/mcp-grafana/blob/v2.3.0/docs/sources/set-up/install-the-binary.md)
- [إنشاء Service Account وtoken](https://grafana.com/docs/grafana/latest/administration/service-accounts/)
- [إعداد Codex لخوادم MCP](https://developers.openai.com/codex/mcp)
