/** Local prototype actions are advisories, never infrastructure operations. */
export type DemoAction = 'restart' | 'redeploy' | 'rollback';

const MESSAGES: Readonly<Record<DemoAction, string>> = Object.freeze({
  restart: 'محاكاة فقط: لم يتم تنفيذ إعادة تشغيل أي خادم.',
  redeploy: 'محاكاة فقط: لم يتم تنفيذ إعادة نشر أي خدمة.',
  rollback: 'محاكاة فقط: لم يتم تنفيذ تراجع عن أي إصدار.',
});

export function previewDemoAction(action: DemoAction) {
  const message = MESSAGES[action];
  if (typeof message !== 'string') throw new TypeError('invalid_demo_action');
  return Object.freeze({
    action,
    mode: 'demo_only' as const,
    performed: false,
    modifiedInfrastructure: false,
    message,
  });
}
