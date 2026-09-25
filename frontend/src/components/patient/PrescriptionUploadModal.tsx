import React, { useState } from 'react';
import { X, UploadCloud, CheckCircle2, AlertTriangle, FileText, Sparkles, Edit3 } from 'lucide-react';
import { Medication } from '../../types';

interface PrescriptionUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onVerifyAndAdd: (med: Medication) => void;
}

export const PrescriptionUploadModal: React.FC<PrescriptionUploadModalProps> = ({
  isOpen,
  onClose,
  onVerifyAndAdd,
}) => {
  const [step, setStep] = useState<'upload' | 'extracting' | 'review'>('upload');
  
  // Sample extracted medication for review
  const [extractedData, setExtractedData] = useState<Partial<Medication>>({
    name: 'Amlodipine Besylate',
    genericName: 'Amlodipine 5mg IP',
    strength: '5 mg',
    dosage: '1 Tablet',
    frequency: 'Once daily (OD)',
    route: 'Oral',
    duration: '30 Days',
    instructions: 'Take in the morning after breakfast',
    prescribingDoctor: 'Dr. Vikrant Mehta, MD',
    hospital: 'Fortis Escorts Heart Institute',
    datePrescribed: '25 Sep 2026',
    timeOfDay: ['morning'],
    mealTiming: 'after_food',
    category: 'Antihypertensive',
  });

  if (!isOpen) return null;

  const handleSimulateUpload = () => {
    setStep('extracting');
    setTimeout(() => {
      setStep('review');
    }, 1400);
  };

  const handleConfirm = () => {
    const newMed: Medication = {
      id: `med-${Date.now()}`,
      name: extractedData.name || 'Prescribed Medicine',
      genericName: extractedData.genericName || '',
      strength: extractedData.strength || 'Standard',
      dosage: extractedData.dosage || '1 Unit',
      frequency: extractedData.frequency || 'Once daily',
      route: extractedData.route || 'Oral',
      duration: extractedData.duration || '30 Days',
      instructions: extractedData.instructions || '',
      prescribingDoctor: extractedData.prescribingDoctor || 'Treating Physician',
      hospital: extractedData.hospital || 'Participating Clinic',
      datePrescribed: extractedData.datePrescribed || 'Today',
      trustState: 'verified', // Once verified by patient, moves to verified
      timeOfDay: extractedData.timeOfDay || ['morning'],
      mealTiming: extractedData.mealTiming || 'after_food',
      category: extractedData.category || 'General',
    };
    onVerifyAndAdd(newMed);
    setStep('upload');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#1C2B3A]/40 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl border border-[#DDD9D1] max-w-3xl w-full p-6 sm:p-8 shadow-xl space-y-6">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-[#DDD9D1] pb-4">
          <div>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#EBF4FB] text-[#2B5F8A]">
              Human-in-the-Loop Extraction
            </div>
            <h3 className="font-serif text-2xl font-bold text-[#1C2B3A] mt-1">
              Upload & Verify Prescription
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-[#6B7A8D] hover:text-[#1C2B3A] hover:bg-[#F0EDE7] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Step 1: Upload */}
        {step === 'upload' && (
          <div className="space-y-6">
            <div className="bg-[#FAF8F3] border-2 border-dashed border-[#DDD9D1] rounded-2xl p-8 text-center space-y-4 hover:border-[#4A90C4] transition-colors cursor-pointer"
                 onClick={handleSimulateUpload}>
              <div className="w-14 h-14 rounded-2xl bg-white border border-[#DDD9D1] flex items-center justify-center mx-auto text-[#4A90C4] shadow-sm">
                <UploadCloud className="w-7 h-7" strokeWidth={1.8} />
              </div>
              <div className="space-y-1">
                <p className="text-sm font-bold text-[#1C2B3A]">
                  Click to upload prescription or diagnostic slip
                </p>
                <p className="text-xs text-[#6B7A8D]">
                  Supports high-resolution PNG, JPG, or PDF (Max 15MB)
                </p>
              </div>
              <button
                type="button"
                className="bg-[#4A90C4] text-white font-semibold text-xs px-5 py-2.5 rounded-xl hover:bg-[#3A7DB0] transition-colors shadow-sm"
              >
                Select Prescription File
              </button>
            </div>

            <div className="bg-[#FEF3E8] border border-[#FCDDC1] rounded-xl p-3.5 flex items-start gap-3">
              <AlertTriangle className="w-4 h-4 text-[#E07B39] shrink-0 mt-0.5" />
              <p className="text-xs text-[#A05520] leading-relaxed">
                <strong className="font-bold">Patient Trust Rule:</strong> HealthSetu uses AI vision to extract medication names and dosage instructions, but <span className="underline">you must review and confirm</span> the extracted fields before they become trusted health data.
              </p>
            </div>
          </div>
        )}

        {/* Step 2: Extracting Loading */}
        {step === 'extracting' && (
          <div className="py-12 text-center space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-[#EBF4FB] border border-[#D5E8F8] flex items-center justify-center mx-auto text-[#4A90C4] animate-pulse">
              <Sparkles className="w-8 h-8 animate-spin" style={{ animationDuration: '3s' }} />
            </div>
            <div className="space-y-1">
              <h4 className="font-serif text-xl font-bold text-[#1C2B3A]">
                Analyzing Prescription Document...
              </h4>
              <p className="text-xs text-[#6B7A8D]">
                Extracting medicine name, strength, frequency, and prescribing physician
              </p>
            </div>
          </div>
        )}

        {/* Step 3: Side-by-Side Verification Gate */}
        {step === 'review' && (
          <div className="space-y-6">
            <div className="grid md:grid-cols-12 gap-6 items-start">
              
              {/* Document Preview (Left) */}
              <div className="md:col-span-5 bg-[#FAF8F3] border border-[#DDD9D1] rounded-2xl p-4 space-y-3">
                <div className="flex items-center justify-between text-xs font-bold text-[#6B7A8D]">
                  <span className="flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-[#4A90C4]" />
                    Original Prescription
                  </span>
                  <span className="text-[10px] bg-white border border-[#DDD9D1] px-2 py-0.5 rounded-full">
                    Scanned Slip
                  </span>
                </div>

                <div className="bg-white border border-[#DDD9D1] rounded-xl p-3 text-xs font-mono text-[#1C2B3A] space-y-2 select-none shadow-inner">
                  <div className="font-bold border-b border-[#DDD9D1] pb-1">
                    FORTIS ESCORTS HEART INSTITUTE
                  </div>
                  <div className="text-[11px] text-[#6B7A8D]">
                    Dr. Vikrant Mehta · Reg: MCI-39102<br />
                    Patient: Rohan Sharma (42 M)
                  </div>
                  <div className="bg-[#FAF8F3] p-2 rounded border border-[#DDD9D1]/60 text-[11px]">
                    Rx:<br />
                    <span className="font-bold text-[#2B5F8A]">Tab. Amlodipine 5mg</span><br />
                    1 tab OD morning after food x 30 days
                  </div>
                  <div className="text-[10px] text-[#6B7A8D] pt-1">
                    Signed: V. Mehta · 25/09/2026
                  </div>
                </div>

                <p className="text-[11px] text-[#6B7A8D]">
                  Compare the extracted data on the right with the uploaded slip.
                </p>
              </div>

              {/* Extracted Fields Form (Right) */}
              <div className="md:col-span-7 space-y-3.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-[#1C2B3A]">Extracted Medication Fields</span>
                  <span className="text-xs font-bold text-[#A05520] bg-[#FEF3E8] px-2.5 py-0.5 rounded-full border border-[#FCDDC1]">
                    Verification Required
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-[11px] font-bold text-[#6B7A8D]">Medicine Name</label>
                    <input
                      type="text"
                      value={extractedData.name}
                      onChange={(e) => setExtractedData({ ...extractedData, name: e.target.value })}
                      className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-xl px-3 py-2 text-xs text-[#1C2B3A] font-semibold focus:ring-1 focus:ring-[#4A90C4] outline-none"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-bold text-[#6B7A8D]">Strength</label>
                    <input
                      type="text"
                      value={extractedData.strength}
                      onChange={(e) => setExtractedData({ ...extractedData, strength: e.target.value })}
                      className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-xl px-3 py-2 text-xs text-[#1C2B3A] font-semibold focus:ring-1 focus:ring-[#4A90C4] outline-none"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-bold text-[#6B7A8D]">Frequency</label>
                    <input
                      type="text"
                      value={extractedData.frequency}
                      onChange={(e) => setExtractedData({ ...extractedData, frequency: e.target.value })}
                      className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-xl px-3 py-2 text-xs text-[#1C2B3A] font-semibold focus:ring-1 focus:ring-[#4A90C4] outline-none"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-bold text-[#6B7A8D]">Duration</label>
                    <input
                      type="text"
                      value={extractedData.duration}
                      onChange={(e) => setExtractedData({ ...extractedData, duration: e.target.value })}
                      className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-xl px-3 py-2 text-xs text-[#1C2B3A] font-semibold focus:ring-1 focus:ring-[#4A90C4] outline-none"
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-bold text-[#6B7A8D]">Instructions</label>
                  <input
                    type="text"
                    value={extractedData.instructions}
                    onChange={(e) => setExtractedData({ ...extractedData, instructions: e.target.value })}
                    className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-xl px-3 py-2 text-xs text-[#1C2B3A] font-semibold focus:ring-1 focus:ring-[#4A90C4] outline-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-[11px] font-bold text-[#6B7A8D]">Prescribing Doctor</label>
                    <input
                      type="text"
                      value={extractedData.prescribingDoctor}
                      onChange={(e) => setExtractedData({ ...extractedData, prescribingDoctor: e.target.value })}
                      className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-xl px-3 py-2 text-xs text-[#1C2B3A] focus:ring-1 focus:ring-[#4A90C4] outline-none"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-bold text-[#6B7A8D]">Hospital / Clinic</label>
                    <input
                      type="text"
                      value={extractedData.hospital}
                      onChange={(e) => setExtractedData({ ...extractedData, hospital: e.target.value })}
                      className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-xl px-3 py-2 text-xs text-[#1C2B3A] focus:ring-1 focus:ring-[#4A90C4] outline-none"
                    />
                  </div>
                </div>
              </div>

            </div>

            {/* Modal Actions */}
            <div className="pt-4 border-t border-[#DDD9D1] flex items-center justify-between">
              <button
                type="button"
                onClick={() => setStep('upload')}
                className="text-xs font-bold text-[#6B7A8D] hover:text-[#1C2B3A] px-3 py-2"
              >
                ← Back to Upload
              </button>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="border border-[#DDD9D1] bg-white text-[#1C2B3A] font-semibold text-xs px-4 py-2.5 rounded-xl hover:bg-[#FAF8F3] transition-colors"
                >
                  Discard
                </button>
                <button
                  type="button"
                  onClick={handleConfirm}
                  className="bg-[#3D8B6E] text-white font-semibold text-xs px-6 py-2.5 rounded-xl hover:bg-[#2D5A40] transition-colors shadow-sm flex items-center gap-2"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Verify & Add to My Timeline</span>
                </button>
              </div>
            </div>

          </div>
        )}

      </div>
    </div>
  );
};
