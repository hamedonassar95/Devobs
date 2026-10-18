# إصدار Neovim الليلي — مرجع للمساهمين

هذا توثيق للصفحة الرسمية [Nvim development (prerelease) build](https://github.com/neovim/neovim/releases/tag/nightly)، أُخذت بياناته في **18 أكتوبر 2026**. وسم `nightly` متحرك؛ قد تتغير النسخة والملفات والبصمات بعد هذا التاريخ. افتح صفحة الإصدار قبل أي تنزيل للحصول على أحدث القيم.

## علاقته بـ DevObs

Neovim محرر نصوص اختياري للمساهمين. هذا المرجع لا يضيف Neovim إلى التطبيق المنشور، ولا يجعله اعتماداً للمشروع أو شرطاً في CI/CD. ملفات التنزيل أدناه لبرنامج تنفيذي تابع لمشروع Neovim؛ لا ينفّذها سير عمل DevObs.

## بيانات الإصدار عند الالتقاط

| الحقل | القيمة |
| --- | --- |
| القناة | تطويرية تمهيدية (nightly prerelease)، وليست إصداراً مستقراً |
| رقم البناء | `NVIM v0.13.0-dev-1892+g9b7ec59580` |
| نوع البناء | `RelWithDebInfo` |
| LuaJIT | `2.1.1791988261` |
| وقت النشر | 17 أكتوبر 2026، 05:22:30 UTC |
| commit | [`9b7ec59580fddf671f7bf922f66ef114a59a51ee`](https://github.com/neovim/neovim/commit/9b7ec59580fddf671f7bf922f66ef114a59a51ee) |
| توثيق توقيع commit على GitHub | `verified: true`، السبب `valid` |

رسالة commit المعروضة في سجل المصدر تذكر إصلاح معالجة القيم الرقمية الخارجة عن النطاق في `iskeyword` و`isfname` و`isident`: تعاد رسالة الخطأ `E474` بدلاً من إنهاء Neovim أو الوصول إلى تأكيد فاشل. للمقارنة الكاملة بين تغييرات النسخ، استخدم رابط [Changelog](https://github.com/neovim/neovim/commit/9b7ec59580fddf671f7bf922f66ef114a59a51ee) وصفحة الأخبار في [runtime/doc/news.txt](https://github.com/neovim/neovim/blob/nightly/runtime/doc/news.txt) أو الأمر `:help news` داخل Neovim.

## طرق التثبيت المنشورة

- **Windows x64 وARM64:** نزّل ملف ZIP أو MSI الموافق للمعمارية. فك ضغط ZIP أو شغّل MSI، ثم شغّل `nvim.exe`. على Windows Server قد يلزم تثبيت `vcruntime*.dll` كما يشرح [دليل التثبيت](https://neovim.io/doc/install/#windows).
- **macOS x86_64 وarm64:** نزّل الأرشيف الموافق، نفّذ `xattr -c ./<archive>.tar.gz` لتجاوز تحذير المطور غير المعروف، فك الضغط بـ`tar xzvf <archive>.tar.gz`، ثم شغّل الملف داخل مجلد `bin`.
- **Linux x86_64 وarm64:** يتوفر AppImage أو tarball. لتشغيل AppImage نفّذ `chmod u+x <file>.appimage && ./<file>.appimage`. إذا لم يتوفر FUSE، يمكن استخراج AppImage بواسطة `./<file>.appimage --appimage-extract` ثم تشغيل `./squashfs-root/usr/bin/nvim`. أو فك tarball بـ`tar xzvf <archive>.tar.gz` وتشغيل الملف داخل `bin`.
- **Linux بإصدار glibc أقدم من المطلوب:** صفحة الإصدار تحيل إلى [بناءات glibc الأقدم غير المدعومة](https://github.com/neovim/neovim-releases).
- **أنظمة أخرى:** يمكن التثبيت عبر [مدير الحزم](https://github.com/neovim/neovim/blob/master/INSTALL.md#install-from-package).

## الملفات المنشورة في لقطة 18 أكتوبر 2026

يتضمن الجدول الملفات الثنائية وملفات التحديث التدريجي `.zsync` التي ظهرت ضمن الأصول. SHA-256 أدناه مأخوذ من بيانات GitHub API وقت الالتقاط؛ تحقّق من الصفحة الحية لأن وسم `nightly` يتغير. بعد التنزيل يمكن حساب البصمة عبر `sha256sum <file>` على Linux أو `shasum -a 256 <file>` على macOS.

| الملف | الحجم بالبايت | SHA-256 | التنزيل |
| --- | ---: | --- | --- |
| `nvim-linux-arm64.appimage` | 20580872 | `13342c094d1bd86501118b3cc47f4e14b68d26aec0d06b91c4d5e6519f12b2ad` | [تنزيل](https://github.com/neovim/neovim/releases/download/nightly/nvim-linux-arm64.appimage) |
| `nvim-linux-arm64.appimage.zsync` | 70571 | `e5a38ba2000692aedc575432032ba7bb5ead477ebab98de0ba53a06b8d3e6b46` | [تنزيل](https://github.com/neovim/neovim/releases/download/nightly/nvim-linux-arm64.appimage.zsync) |
| `nvim-linux-arm64.tar.gz` | 21803023 | `685f894026dd45c0084fe4ac1479c04fcf54ac7c00d83b33060a95c535938f9a` | [تنزيل](https://github.com/neovim/neovim/releases/download/nightly/nvim-linux-arm64.tar.gz) |
| `nvim-linux-x86_64.appimage` | 20576760 | `e80689b1b9c0b5c865481dc91110eec1f56cdaf55f8900a1bd49689628f3cc29` | [تنزيل](https://github.com/neovim/neovim/releases/download/nightly/nvim-linux-x86_64.appimage) |
| `nvim-linux-x86_64.appimage.zsync` | 70559 | `26fa57f21ff89eb3645bc7bb7d7030dfb53be35b7a7a785bc547eefbe8477ab3` | [تنزيل](https://github.com/neovim/neovim/releases/download/nightly/nvim-linux-x86_64.appimage.zsync) |
| `nvim-linux-x86_64.tar.gz` | 21645555 | `f80af6c7f5315da75609c3d043b3f10c9d8bf3f1ff4428779a3bf6a06b69222c` | [تنزيل](https://github.com/neovim/neovim/releases/download/nightly/nvim-linux-x86_64.tar.gz) |
| `nvim-macos-arm64.tar.gz` | 10072046 | `3382a2401670da6d7058138eeb4de2451b9c375ad39847a059c800258a4f69ca` | [تنزيل](https://github.com/neovim/neovim/releases/download/nightly/nvim-macos-arm64.tar.gz) |
| `nvim-macos-x86_64.tar.gz` | 10317168 | `d3eed1577854f9dee9cf8553f3205f18629c5f7a45f9af04557e82e2cdbb7818` | [تنزيل](https://github.com/neovim/neovim/releases/download/nightly/nvim-macos-x86_64.tar.gz) |
| `nvim-wasm-emscripten.zip` | 8221012 | `4fcd4510a4876efabc54c16fb31ead8238a9726984964fe363733a54e15e3452` | [تنزيل](https://github.com/neovim/neovim/releases/download/nightly/nvim-wasm-emscripten.zip) |
| `nvim-win-arm64.msi` | 19523333 | `301c2a83382d50d8493de6f3c18fce30d677e68d79f952301f7a4b138e443d4c` | [تنزيل](https://github.com/neovim/neovim/releases/download/nightly/nvim-win-arm64.msi) |
| `nvim-win-arm64.zip` | 19808616 | `974307f5214cd42376b8c3d19e08dfdda01be93301f01cc724113af5024f4262` | [تنزيل](https://github.com/neovim/neovim/releases/download/nightly/nvim-win-arm64.zip) |
| `nvim-win64.msi` | 19195654 | `e050666edf15379213c789f6532497c4f7e84ae363c4525cb3534b3fef31a03c` | [تنزيل](https://github.com/neovim/neovim/releases/download/nightly/nvim-win64.msi) |
| `nvim-win64.zip` | 19445126 | `ccdbc8715c91b94c549776cd19a0cb9e50ffa4af4e8cb3619dfa49ed18610538` | [تنزيل](https://github.com/neovim/neovim/releases/download/nightly/nvim-win64.zip) |

تُظهر صفحة GitHub أيضاً أرشيفي الشيفرة التلقائيين للوسم: [ZIP](https://github.com/neovim/neovim/archive/refs/tags/nightly.zip) و[TAR.GZ](https://github.com/neovim/neovim/archive/refs/tags/nightly.tar.gz). هذان الأرشيفان والأصول أعلاه يتبعان وسم `nightly` المتغير.
