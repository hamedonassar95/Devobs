(() => {
  const KEY = 'devobs_creator_planner_v1';
  const statuses = { idea: 'فكرة', script: 'كتابة النص', production: 'تصوير أو مونتاج', scheduled: 'مجدول', published: 'منشور' };
  const types = { short: 'Shorts', long: 'فيديو طويل' };
  const form = document.querySelector('#idea-form');
  const list = document.querySelector('#idea-list');
  const message = document.querySelector('#form-message');
  let ideas = readIdeas();
  let editingId = null;

  function readIdeas() {
    try {
      const saved = JSON.parse(localStorage.getItem(KEY) || '[]');
      return Array.isArray(saved) ? saved.filter(item => item && typeof item.id === 'string' && typeof item.title === 'string') : [];
    } catch {
      return [];
    }
  }

  function saveIdeas() {
    try {
      localStorage.setItem(KEY, JSON.stringify(ideas));
      return true;
    } catch {
      message.textContent = 'تعذر الحفظ في المتصفح. صدّر نسخة احتياطية أو أفرغ مساحة ثم حاول مجددًا.';
      return false;
    }
  }

  function addText(parent, tag, text, className) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    node.textContent = text;
    parent.append(node);
    return node;
  }

  function render() {
    const query = document.querySelector('#filter-search').value.trim().toLocaleLowerCase('ar');
    const type = document.querySelector('#filter-type').value;
    const status = document.querySelector('#filter-status').value;
    const filtered = ideas.filter(item => (type === 'all' || item.type === type) && (status === 'all' || item.status === status) && (!query || `${item.title} ${item.notes} ${item.trend}`.toLocaleLowerCase('ar').includes(query)));
    document.querySelector('#stat-total').textContent = ideas.length;
    document.querySelector('#stat-shorts').textContent = ideas.filter(item => item.type === 'short').length;
    document.querySelector('#stat-long').textContent = ideas.filter(item => item.type === 'long').length;
    document.querySelector('#stat-published').textContent = ideas.filter(item => item.status === 'published').length;
    list.replaceChildren();
    if (!filtered.length) {
      addText(list, 'p', ideas.length ? 'لا توجد أفكار تطابق عوامل التصفية.' : 'ابدأ بإضافة فكرة، ثم حدد صيغتها وموعدها ومرحلتها. يمكنك أيضًا تحميل خطة بداية قابلة للتعديل.', 'empty');
      if (!ideas.length) {
        const starter = addText(list, 'button', 'إضافة خطة بداية من 16 فكرة', 'button accent');
        starter.type = 'button';
        starter.addEventListener('click', addStarterPlan);
      }
      return;
    }
    filtered.sort((a, b) => (a.date || '9999').localeCompare(b.date || '9999'));
    for (const item of filtered) {
      const card = document.createElement('article');
      card.className = 'idea-card';
      addText(card, 'h3', item.title);
      const badges = document.createElement('div');
      badges.className = 'badges';
      addText(badges, 'span', types[item.type] || types.short, 'badge');
      addText(badges, 'span', statuses[item.status] || statuses.idea, `badge ${item.status}`);
      card.append(badges);
      if (item.date) addText(card, 'p', `موعد النشر: ${item.date}`, 'idea-meta');
      if (item.trend) {
        const trend = addText(card, 'p', `Google Trends: ${item.trend}`, 'idea-trend');
        if (/^https:\/\/trends\.google\.com\//i.test(item.trend)) {
          trend.replaceChildren(document.createTextNode('Google Trends: '));
          const link = document.createElement('a');
          link.href = item.trend;
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          link.textContent = 'افتح المصدر ↗';
          trend.append(link);
        }
      }
      if (item.notes) addText(card, 'p', item.notes, 'idea-notes');
      const actions = document.createElement('div');
      actions.className = 'card-actions';
      const edit = addText(actions, 'button', 'تعديل', 'button quiet compact');
      edit.type = 'button';
      edit.addEventListener('click', () => editIdea(item));
      const remove = addText(actions, 'button', 'حذف', 'button quiet compact danger');
      remove.type = 'button';
      remove.addEventListener('click', () => deleteIdea(item.id));
      card.append(actions);
      list.append(card);
    }
  }

  function resetEditor() {
    editingId = null;
    form.reset();
    document.querySelector('#form-title').textContent = 'أضف فكرة فيديو';
    document.querySelector('#save-button').textContent = 'حفظ الفكرة';
    document.querySelector('#cancel-edit').hidden = true;
  }

  function editIdea(item) {
    editingId = item.id;
    document.querySelector('#idea-title').value = item.title;
    document.querySelector('#idea-type').value = item.type;
    document.querySelector('#idea-status').value = item.status;
    document.querySelector('#idea-date').value = item.date || '';
    document.querySelector('#idea-trend').value = item.trend || '';
    document.querySelector('#idea-notes').value = item.notes || '';
    document.querySelector('#form-title').textContent = 'عدّل فكرة الفيديو';
    document.querySelector('#save-button').textContent = 'حفظ التعديل';
    document.querySelector('#cancel-edit').hidden = false;
    document.querySelector('#idea-title').focus();
  }

  function deleteIdea(id) {
    ideas = ideas.filter(item => item.id !== id);
    if (saveIdeas()) render();
  }

  function addStarterPlan() {
    const starters = [
      ['long', 'كيف تبني وردًا قرآنيًا تستطيع الاستمرار عليه؟', 'فيديو طويل: خطوات عملية وتجربة شخصية، مع تجنب تقديم حكم ديني بلا مصدر.'],
      ['short', 'طريقة بسيطة لاختيار وقت ثابت لوردك اليومي', 'Short: افتح بسؤال، ثم قدّم خطوة واحدة قابلة للتطبيق.'],
      ['short', 'ماذا تفعل إذا فاتك يوم من وردك؟', 'Short: نصيحة عملية متزنة، واذكر مصدرًا موثوقًا إذا أضفت توجيهًا دينيًا.'],
      ['short', 'ثلاث دقائق للبدء بقراءة يومية منتظمة', 'Short: تجربة أو اقتراح شخصي واضح، لا تقدمه كحكم شرعي.'],
      ['long', 'قصة أصحاب الكهف: ثلاث وقفات من الآيات والتفسير', 'فيديو طويل: اختر تفسيرًا موثوقًا، واذكر المصدر ورقم الآيات في الفيديو والوصف.'],
      ['short', 'سؤال سريع: ما الفكرة التي تذكرها قصة أصحاب الكهف؟', 'Short: اعرض سؤالًا ثم اربط الإجابة بآية ومصدر تفسير.'],
      ['short', 'وقفة واحدة من قصة أصحاب الكهف', 'Short: فكرة واحدة موثقة، مع دعوة المشاهد لمشاهدة الشرح الكامل.'],
      ['short', 'هل تعرف أين تتحقق من تفسير آية؟', 'Short: اعرض خطوات الوصول إلى مصدر تفسير معروف.'],
      ['long', 'كيف تتحقق من مصدر حديث قبل إعادة نشره؟', 'فيديو طويل: اشرح خطوات البحث، وحدود التحقق، ومصدرًا موثوقًا لكل مثال.'],
      ['short', 'قبل نشر مقطع ديني: تحقق من هذه النقطة', 'Short: خطوة تحقق واحدة، ثم رابط للمصادر في الوصف.'],
      ['short', 'كيف تميّز الاقتباس من الحديث المنسوب؟', 'Short: اشرح طريقة التحقق دون الجزم بصحة رواية لم تراجع مصدرها.'],
      ['short', 'ثلاثة أسئلة اسألها قبل مشاركة معلومة دينية', 'Short: المصدر؟ النص الكامل؟ من شرحها؟'],
      ['long', 'كيف تبحث عن تفسير آية من مصادر موثوقة؟', 'فيديو طويل: تطبيق عملي على آية يختارها الجمهور، مع ذكر المراجع.'],
      ['short', 'ما الفرق بين معنى الكلمة وتفسير الآية؟', 'Short: تعريف مبسط ومراجعته مع مصدر تفسير قبل التصوير.'],
      ['short', 'اختر آية لشرحها في الفيديو القادم', 'Short: اطلب اقتراحات الجمهور، ثم راجع الآية ومصدر تفسيرها قبل اعتمادها.'],
      ['short', 'كيف أضع مصدر المعلومة الدينية في وصف الفيديو؟', 'Short: اعرض مثالًا عمليًا لمصدر ورابط واضح.']
    ].map(([type, title, notes]) => ({ id: globalThis.crypto?.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`, title, type, status: 'idea', date: '', trend: '', notes: `مسودة بداية غير مؤكدة بالرواج؛ اختبر الموضوع عبر Google Trends قبل الإنتاج. ${notes}`, createdAt: new Date().toISOString() }));
    ideas = [...ideas, ...starters];
    if (saveIdeas()) {
      render();
      message.textContent = 'أضيفت 16 فكرة كبداية. راجع Trends والمصادر وحدد المواعيد قبل التصوير.';
    }
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    const previous = editingId ? ideas.find(item => item.id === editingId) : null;
    const idea = {
      id: editingId || (globalThis.crypto?.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`),
      title: document.querySelector('#idea-title').value.trim(),
      type: document.querySelector('#idea-type').value,
      status: document.querySelector('#idea-status').value,
      date: document.querySelector('#idea-date').value,
      trend: document.querySelector('#idea-trend').value.trim(),
      notes: document.querySelector('#idea-notes').value.trim(),
      createdAt: previous?.createdAt || new Date().toISOString()
    };
    if (!idea.title) return;
    ideas = previous ? ideas.map(item => item.id === editingId ? idea : item) : [...ideas, idea];
    if (saveIdeas()) {
      render();
      resetEditor();
      message.textContent = 'تم حفظ الفكرة على هذا الجهاز.';
    }
  });

  document.querySelector('#cancel-edit').addEventListener('click', resetEditor);
  form.addEventListener('reset', () => { message.textContent = ''; });
  for (const id of ['#filter-search', '#filter-type', '#filter-status']) document.querySelector(id).addEventListener('input', render);
  document.querySelector('#trends-form').addEventListener('submit', event => {
    event.preventDefault();
    const query = document.querySelector('#trend-query').value.trim();
    const country = document.querySelector('#trend-country').value.trim().toUpperCase();
    const params = new URLSearchParams({ date: 'today 3-m', gprop: 'youtube', q: query });
    if (country) params.set('geo', country);
    window.open(`https://trends.google.com/trends/explore?${params}`, '_blank', 'noopener,noreferrer');
  });
  document.querySelector('#export-button').addEventListener('click', () => {
    const blob = new Blob([JSON.stringify({ version: 1, exportedAt: new Date().toISOString(), ideas }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'youtube-content-plan.json';
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  document.querySelector('#import-file').addEventListener('change', async event => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (ideas.length && !window.confirm('سيستبدل الاستيراد الخطة الحالية. هل صدّرت نسخة احتياطية وتريد المتابعة؟')) {
      event.target.value = '';
      return;
    }
    try {
      const data = JSON.parse(await file.text());
      const incoming = Array.isArray(data) ? data : data.ideas;
      if (!Array.isArray(incoming) || incoming.some(item => !item || typeof item.title !== 'string' || !types[item.type] || !statuses[item.status])) throw new Error('invalid');
      ideas = incoming.map(item => ({ id: typeof item.id === 'string' ? item.id : `${Date.now()}-${Math.random()}`, title: item.title.slice(0, 120), type: item.type, status: item.status, date: typeof item.date === 'string' ? item.date : '', trend: typeof item.trend === 'string' ? item.trend.slice(0, 500) : '', notes: typeof item.notes === 'string' ? item.notes.slice(0, 3000) : '', createdAt: item.createdAt || new Date().toISOString() }));
      if (saveIdeas()) { render(); message.textContent = 'تم استيراد النسخة الاحتياطية.'; }
    } catch {
      message.textContent = 'تعذر استيراد الملف. اختر نسخة JSON صادرة من هذه الأداة.';
    } finally {
      event.target.value = '';
    }
  });
  render();
})();
