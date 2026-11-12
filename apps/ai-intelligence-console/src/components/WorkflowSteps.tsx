import React, { useState } from 'react';
import { WORKFLOW_STAGES } from '../data/guidelines';
import { MessageSquare, Code2, PlayCircle, Sparkles, ChevronDown, CheckCircle2 } from 'lucide-react';

export const WorkflowSteps: React.FC = () => {
  const [selectedStepIndex, setSelectedStepIndex] = useState(0);

  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'MessageSquare':
        return <MessageSquare className="w-5 h-5" />;
      case 'Code2':
        return <Code2 className="w-5 h-5" />;
      case 'PlayCircle':
        return <PlayCircle className="w-5 h-5" />;
      case 'Sparkles':
        return <Sparkles className="w-5 h-5" />;
      default:
        return <CheckCircle2 className="w-5 h-5" />;
    }
  };

  return (
    <section id="workflow" className="py-16 md:py-20 border-b border-slate-200 dark:border-slate-800">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        {/* Section Header */}
        <div className="text-center max-w-2xl mx-auto mb-12">
          <div className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 mb-2">
            منظومة العمل المتكاملة
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white mb-3">
            كيف تسير رحلة بناء تطبيقك معي في 4 خطوات؟
          </h2>
          <p className="text-sm sm:text-base text-slate-600 dark:text-slate-300">
            أنت الموجه وصاحب الرؤية، وأنا المهندس التنفيذي الذي يحول كل كلمة إلى واقع برمجي متقن.
          </p>
        </div>

        {/* 4 Steps Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {WORKFLOW_STAGES.map((stage, idx) => {
            const isSelected = selectedStepIndex === idx;
            return (
              <button
                key={stage.step}
                onClick={() => setSelectedStepIndex(idx)}
                className={`text-right p-5 rounded-xl border transition-all text-slate-900 dark:text-slate-100 ${
                  isSelected
                    ? 'bg-indigo-50/80 dark:bg-indigo-950/40 border-indigo-400 dark:border-indigo-600 shadow-sm'
                    : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-bold font-mono px-2 py-1 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-md">
                    خطوة {stage.step}
                  </span>
                  <div
                    className={`p-2 rounded-lg ${
                      isSelected
                        ? 'bg-indigo-600 text-white'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300'
                    }`}
                  >
                    {getIcon(stage.iconName)}
                  </div>
                </div>

                <h3 className="text-base font-bold text-slate-900 dark:text-white mb-2">
                  {stage.title}
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed line-clamp-3">
                  {stage.action}
                </p>

                <div className="mt-4 pt-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs text-indigo-600 dark:text-indigo-400 font-medium">
                  <span>{isSelected ? 'المرحلة النشطة' : 'انقر لمعرفة التفاصيل'}</span>
                  <ChevronDown
                    className={`w-4 h-4 transition-transform ${isSelected ? 'rotate-180' : ''}`}
                  />
                </div>
              </button>
            );
          })}
        </div>

        {/* Selected Step Detailed Deep-Dive Card */}
        {WORKFLOW_STAGES[selectedStepIndex] && (
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-indigo-200 dark:border-indigo-900/60 p-6 sm:p-8 shadow-sm">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-lg">
                  {WORKFLOW_STAGES[selectedStepIndex].step}
                </div>
                <div>
                  <h4 className="text-lg font-bold text-slate-900 dark:text-white">
                    {WORKFLOW_STAGES[selectedStepIndex].title}
                  </h4>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    الدور المشترك بينك وبين مهندس الذكاء الاصطناعي
                  </p>
                </div>
              </div>
              <div className="text-xs text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/60 px-3 py-1.5 rounded-lg border border-indigo-200 dark:border-indigo-800 font-semibold self-start md:self-auto">
                نصيحة ذهبية لهذه الخطوة
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-6">
              <div className="space-y-3">
                <h5 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                  ماذا تفعل أنت؟
                </h5>
                <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
                  {WORKFLOW_STAGES[selectedStepIndex].action}
                </p>
              </div>

              <div className="space-y-3">
                <h5 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                  كيف تستفيد لأقصى درجة؟
                </h5>
                <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed bg-indigo-50/50 dark:bg-indigo-950/30 p-4 rounded-xl border border-indigo-100 dark:border-indigo-900/40">
                  {WORKFLOW_STAGES[selectedStepIndex].tip}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
};
