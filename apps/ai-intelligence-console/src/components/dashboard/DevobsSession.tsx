import { useSyncExternalStore } from 'react';
import { devobsAuth } from '../../services/devobsAuthFacade';

export function DevobsSession() {
  const status = useSyncExternalStore(devobsAuth.subscribe, devobsAuth.getSnapshot);
  if (status === 'disabled') return null;
  const signedIn = status === 'signed_in';
  return <section aria-label="جلسة Devobs" className="rounded-xl border border-slate-800 bg-slate-900 p-4 flex flex-wrap items-center justify-between gap-3">
    <div className="text-sm space-y-1">
      <p role="status" aria-live="polite" className="font-semibold">
        {status === 'unavailable' ? 'تسجيل دخول Devobs غير متاح حاليًا.'
          : status === 'busy' ? 'جارٍ استكمال تسجيل دخول Devobs…'
          : signedIn ? 'جلسة Devobs للقراءة جاهزة.' : 'تسجيل دخول Devobs'}
      </p>
      <p className="text-xs text-slate-400">هذه الجلسة منفصلة عن Google Workspace ولا تمنح صلاحية التشخيص.</p>
    </div>
    <button type="button" disabled={status === 'busy' || !devobsAuth.isConfigured()}
      onClick={() => { void (signedIn ? devobsAuth.signOut() : devobsAuth.signIn()); }}
      className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50">
      {signedIn ? 'إنهاء جلسة Devobs محليًا' : 'تسجيل الدخول إلى Devobs'}
    </button>
  </section>;
}
