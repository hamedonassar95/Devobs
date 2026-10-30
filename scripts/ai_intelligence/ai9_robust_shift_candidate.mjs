export const AI9_ROBUST_SHIFT_POLICY = Object.freeze({
  version: 'ai9-robust-shift-confirmation-v1',
  classification: 'synthetic_development_only',
  reference_points: 30,
  recent_points: 3,
  mad_multiplier: 4,
});

export function robustShiftDecision(_metric, _index, _confirmed) {
  throw new Error('robust_shift_not_implemented');
}
