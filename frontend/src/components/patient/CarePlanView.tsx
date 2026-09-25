import React, { useState } from 'react';
import { Volume2, VolumeX, CheckCircle, Clock, Utensils, AlertCircle, Sparkles } from 'lucide-react';
import type { Medication } from '../../types';

interface CarePlanViewProps {
  medications: Medication[];
}

export const CarePlanView: React.FC<CarePlanViewProps> = ({ medications }) => {
  const [language, setLanguage] = useState<'en' | 'hi'>('en');
  const [completedTasks, setCompletedTasks] = useState<Record<string, boolean>>({});
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);

  const toggleTask = (id: string) => {
    setCompletedTasks(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const speakCarePlan = () => {
    if (!('speechSynthesis' in window)) {
      alert('Text-to-speech is not supported on this browser.');
      return;
    }

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    const script = language === 'hi'
      ? `नमस्ते रोहन शर्मा। आपकी आज की दवाएं हैं: सुबह नाश्ते से पहले टेल्मिसार्टन 40 मिलीग्राम। दोपहर में भोजन के साथ मेटफॉर्मिन 500 मिलीग्राम। रात को भोजन के बाद एटोरवास्टेटिन 20 मिलीग्राम। कृपया नियमित समय पर दवा लें।`
      : `Hello Rohan Sharma. Here is your daily care schedule: In the morning, take Telmisartan 40 milligrams before breakfast with a glass of water. In the morning and evening, take Metformin 500 milligrams with food. At bedtime, take Atorvastatin 20 milligrams after dinner. Stay well hydrated.`;

    const utterance = new SpeechSynthesisUtterance(script);
    utterance.lang = language === 'hi' ? 'hi-IN' : 'en-IN';
    utterance.rate = 0.95;

    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
    setIsSpeaking(true);
  };

  const periods = [
    { key: 'morning', titleEn: 'Morning', titleHi: 'सुबह', time: '08:00 AM' },
    { key: 'afternoon', titleEn: 'Afternoon', titleHi: 'दोपहर', time: '01:30 PM' },
    { key: 'evening', titleEn: 'Evening', titleHi: 'शाम', time: '07:30 PM' },
    { key: 'bedtime', titleEn: 'Bedtime', titleHi: 'रात / सोने से पहले', time: '10:00 PM' },
  ] as const;

  return (
    <div className="bg-white rounded-sm border border-[#DDD9D1] p-6 space-y-6">
      
      {/* Header with Language Selector & Audio TTS */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#DDD9D1] pb-4">
        <div>
          <span className="text-[10px] uppercase font-mono tracking-wider text-[#6B7A8D]">
            {language === 'hi' ? 'दैनिक उपचार योजना' : 'Personalized Adherence'}
          </span>
          <h3 className="font-serif text-xl text-[#1C2B3A]">
            {language === 'hi' ? 'दैनिक देखभाल योजना' : 'Daily Care & Medication Schedule'}
          </h3>
        </div>

        <div className="flex items-center gap-3">
          {/* Audio TTS Button */}
          <button
            onClick={speakCarePlan}
            className={`flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-sm transition-colors border ${
              isSpeaking
                ? 'bg-[#D94F7A] border-[#D94F7A] text-white animate-pulse'
                : 'bg-[#FAF8F3] text-[#2D5A40] border-[#DDD9D1] hover:border-[#1C2B3A]'
            }`}
          >
            {isSpeaking ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
            <span>{isSpeaking ? (language === 'hi' ? 'बोलना बंद करें' : 'Stop Audio') : (language === 'hi' ? 'योजना सुनें' : 'Listen to Plan')}</span>
          </button>

          {/* Multilingual Selector */}
          <div className="flex items-center bg-[#FAF8F3] p-0.5 rounded-sm border border-[#DDD9D1]">
            <button
              onClick={() => setLanguage('en')}
              className={`px-2.5 py-1 rounded-sm text-xs font-semibold transition-colors ${
                language === 'en' ? 'bg-white text-[#1C2B3A] border border-[#DDD9D1]' : 'text-[#6B7A8D]'
              }`}
            >
              EN
            </button>
            <button
              onClick={() => setLanguage('hi')}
              className={`px-2.5 py-1 rounded-sm text-xs font-semibold transition-colors ${
                language === 'hi' ? 'bg-white text-[#1C2B3A] border border-[#DDD9D1]' : 'text-[#6B7A8D]'
              }`}
            >
              हिन्दी
            </button>
          </div>
        </div>
      </div>

      {/* Clinical Rule Notice */}
      <div className="bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm p-3.5 flex items-center justify-between text-xs text-[#6B7A8D]">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[#4A90C4]" />
          <span>
            {language === 'hi'
              ? 'नैदानिक सुरक्षा: दवा का नाम, शक्ति और खुराक अनुवाद में अपरिवर्तित रहते हैं।'
              : 'Clinical Rule: Medicine names, active strengths, and dosages remain strictly untranslated.'}
          </span>
        </div>
        <span className="font-semibold text-[#2D5A40] bg-[#EBF5EC] border border-[#D3EAD7] px-2 py-0.5 rounded-sm text-[10px]">
          {language === 'hi' ? 'सत्यापित योजना' : 'Doctor Verified'}
        </span>
      </div>

      {/* Daily Time Periods Grid (divide-x border layout) */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 border border-[#DDD9D1] divide-y lg:divide-y-0 lg:divide-x divide-[#DDD9D1] bg-white rounded-sm">
        {periods.map(period => {
          const medsInPeriod = medications.filter(m => m.timeOfDay.includes(period.key));

          return (
            <div
              key={period.key}
              className="p-4 flex flex-col justify-between space-y-4"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-[#DDD9D1] pb-2">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-[#1C2B3A]">
                    <Clock className="w-3.5 h-3.5 text-[#4A90C4]" />
                    <span>{language === 'hi' ? period.titleHi : period.titleEn}</span>
                  </div>
                  <span className="text-[10px] text-[#6B7A8D] font-mono">
                    {period.time}
                  </span>
                </div>

                {medsInPeriod.length === 0 ? (
                  <p className="text-xs text-[#6B7A8D] italic py-4 text-center">
                    {language === 'hi' ? 'इस समय कोई दवा नहीं है' : 'No medications scheduled'}
                  </p>
                ) : (
                  <div className="space-y-2">
                    {medsInPeriod.map(med => {
                      const taskId = `${period.key}-${med.id}`;
                      const isDone = completedTasks[taskId];

                      return (
                        <div
                          key={med.id}
                          onClick={() => toggleTask(taskId)}
                          className={`p-2.5 rounded-sm border transition-colors cursor-pointer select-none ${
                            isDone
                              ? 'bg-[#EBF5EC] border-[#D3EAD7] opacity-80'
                              : 'bg-white border-[#DDD9D1] hover:border-[#1C2B3A]'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <div className={`text-xs font-semibold ${isDone ? 'line-through text-[#2D5A40]' : 'text-[#1C2B3A]'}`}>
                                {med.name} {med.strength}
                              </div>
                              <div className="text-[11px] text-[#6B7A8D]">
                                {med.dosage} · {med.frequency}
                              </div>
                            </div>
                            <div className={`w-3.5 h-3.5 rounded-none border flex items-center justify-center shrink-0 mt-0.5 ${
                              isDone ? 'bg-[#3D8B6E] border-[#3D8B6E] text-white' : 'border-[#DDD9D1] bg-white'
                            }`}>
                              {isDone && <CheckCircle className="w-3 h-3" />}
                            </div>
                          </div>

                          <div className="flex items-center gap-1 text-[10px] text-[#6B7A8D] mt-2 pt-1 border-t border-[#DDD9D1]">
                            <Utensils className="w-3 h-3 text-[#E07B39]" />
                            <span>
                              {med.mealTiming === 'before_food'
                                ? (language === 'hi' ? 'भोजन से पहले' : 'Before food')
                                : (language === 'hi' ? 'भोजन के बाद' : 'After food')}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              <div className="text-[11px] text-[#6B7A8D] pt-2 border-t border-[#DDD9D1] flex items-center justify-between">
                <span>{medsInPeriod.length} {language === 'hi' ? 'दवाएं' : 'scheduled'}</span>
                {medsInPeriod.length > 0 && (
                  <span className="text-[#3D8B6E] font-semibold text-[10px]">
                    {medsInPeriod.every(m => completedTasks[`${period.key}-${m.id}`])
                      ? (language === 'hi' ? 'पूर्ण' : 'Completed')
                      : (language === 'hi' ? 'बाकी है' : 'Pending')}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Warning signs */}
      <div className="border-t border-[#DDD9D1] pt-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-[#6B7A8D]">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-[#D94F7A]" />
          <span>
            {language === 'hi'
              ? 'यदि सांस लेने में कठिनाई या सीने में दर्द हो, तो तुरंत आपातकालीन सेवा 108 डायल करें।'
              : 'Warning Signs: If you experience acute chest tightness or sudden breathlessness, contact emergency care immediately.'}
          </span>
        </div>
        <span className="font-semibold text-[#1C2B3A]">Physician: Dr. Priya Nair (AIIMS)</span>
      </div>

    </div>
  );
};
