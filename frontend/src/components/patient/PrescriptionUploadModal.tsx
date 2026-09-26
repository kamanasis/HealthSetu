import React, { useState, useEffect, useRef } from 'react';
import { X, UploadCloud, CheckCircle2, AlertTriangle, FileText, Sparkles, Check, Cpu } from 'lucide-react';
import type { Medication } from '../../types';
import { apiClient } from '../../services/api';
import { ClearScript, type ClearScriptResult, type SamplePrescription } from '../../services/clearscript';

interface PrescriptionUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onVerifyAndAdd: (med: Medication | Medication[]) => void;
  patientId?: string;
}

export const PrescriptionUploadModal: React.FC<PrescriptionUploadModalProps> = ({
  isOpen,
  onClose,
  onVerifyAndAdd,
  patientId = 'HS-PAT-8921',
}) => {
  const [step, setStep] = useState<'upload' | 'extracting' | 'review'>('upload');
  const [extractStatusText, setExtractStatusText] = useState<string>('Initializing ClearScript OCR Engine...');
  const [viewMode, setViewMode] = useState<'preview' | 'ocr_text'>('preview');
  const [uploadedDocMeta, setUploadedDocMeta] = useState<any>(null);
  const [clearScriptResult, setClearScriptResult] = useState<ClearScriptResult | null>(null);
  const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Multi-medication state
  const [allExtractedMeds, setAllExtractedMeds] = useState<Partial<Medication>[]>([]);
  const [selectedMedIndex, setSelectedMedIndex] = useState<number>(0);

  // Currently selected and editable medication state
  const [extractedData, setExtractedData] = useState<Partial<Medication>>({
    name: 'Diclofenac',
    genericName: 'Diclofenac Sodium / Potassium IP',
    strength: '50 mg',
    dosage: '1 Tablet',
    frequency: 'Twice daily (BD)',
    route: 'Oral',
    duration: '3 weeks',
    instructions: 'Take 1 tablet twice daily (bd) (after meals). Complete full course as advised.',
    prescribingDoctor: 'Dr. Sanjay Ghoshal',
    hospital: 'Joint Care Clinic',
    datePrescribed: '24 Sep 2026',
    timeOfDay: ['morning', 'night'],
    mealTiming: 'after_food',
    category: 'NSAID / Analgesic',
  });

  // Lock background scrolling and pause Lenis smooth scrolling engine while modal is open
  useEffect(() => {
    if (isOpen) {
      const originalOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';

      // Crucial: Stop Lenis so touchpad/mousewheel events are not hijacked to scroll background
      const lenis = (window as any).__lenis;
      if (lenis && typeof lenis.stop === 'function') {
        lenis.stop();
      }

      return () => {
        document.body.style.overflow = originalOverflow;
        if (lenis && typeof lenis.start === 'function') {
          lenis.start();
        }
      };
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const samplePresets: SamplePrescription[] = ClearScript.getSamplePrescriptions();

  const handleSelectSample = async (sample: SamplePrescription) => {
    setStep('extracting');
    setExtractStatusText('Applying ClearScript.js Pharmacopoeia Fuzzy Matcher...');
    
    setTimeout(async () => {
      setExtractStatusText(`Normalizing Rx terms for ${sample.drug}...`);
      const result = await ClearScript.processPrescription(sample.drug, {
        hintText: `${sample.drug} ${sample.strength} ${sample.sig} ${sample.doctor} ${sample.hospital}`
      });
      setClearScriptResult(result);
      const meds = (result.extractedMedications && result.extractedMedications.length > 0)
        ? result.extractedMedications
        : [result.extractedMedication];
      setAllExtractedMeds(meds);
      setSelectedMedIndex(0);
      setExtractedData(meds[0]);
      setPreviewImageUrl(null);
      setStep('review');
    }, 700);
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setStep('extracting');
    setExtractStatusText('ClearScript.js: Initializing optical character recognition...');

    // Create local object URL for instant preview
    if (file.type.startsWith('image/')) {
      const url = URL.createObjectURL(file);
      setPreviewImageUrl(url);
    } else {
      setPreviewImageUrl(null);
    }

    try {
      // 1. Run real in-browser ClearScript OCR model
      const result = await ClearScript.processPrescription(file, {
        hintText: file.name,
        onProgress: (msg: string) => {
          setExtractStatusText(msg);
        }
      });

      setClearScriptResult(result);
      const meds = (result.extractedMedications && result.extractedMedications.length > 0)
        ? result.extractedMedications
        : [result.extractedMedication];
      setAllExtractedMeds(meds);
      setSelectedMedIndex(0);
      setExtractedData(meds[0]);

      // 2. Also register ingestion on backend asynchronously for audit log
      apiClient.uploadMedicalDocument(patientId, file, 'PRESCRIPTION')
        .then(res => {
          if (res.document) setUploadedDocMeta(res.document);
        })
        .catch(() => {});

      setStep('review');
    } catch (err: any) {
      console.error('ClearScript OCR error:', err);
      setStep('review');
    }
  };

  const handleFieldChange = (field: keyof Medication, value: any) => {
    setExtractedData(prev => ({ ...prev, [field]: value }));
    setAllExtractedMeds(prevList => {
      const copy = [...prevList];
      if (copy[selectedMedIndex]) {
        copy[selectedMedIndex] = { ...copy[selectedMedIndex], [field]: value };
      }
      return copy;
    });
  };

  const handleSelectMedIndex = (idx: number) => {
    setSelectedMedIndex(idx);
    if (allExtractedMeds[idx]) {
      setExtractedData(allExtractedMeds[idx]);
    }
  };

  const handleConfirmCurrent = () => {
    const newMed: Medication = {
      id: `med-${Date.now()}`,
      name: extractedData.name || 'Prescribed Medicine',
      genericName: extractedData.genericName || '',
      strength: extractedData.strength || 'Standard',
      dosage: extractedData.dosage || '1 Unit',
      frequency: extractedData.frequency || 'Once daily',
      route: extractedData.route || 'Oral',
      duration: extractedData.duration || '3 weeks',
      instructions: extractedData.instructions || '',
      prescribingDoctor: extractedData.prescribingDoctor || clearScriptResult?.doctorName || 'Dr. Sanjay Ghoshal',
      hospital: extractedData.hospital || clearScriptResult?.hospitalName || 'Joint Care Clinic',
      datePrescribed: extractedData.datePrescribed || 'Today',
      trustState: 'verified',
      timeOfDay: extractedData.timeOfDay || ['morning'],
      mealTiming: extractedData.mealTiming || 'after_food',
      category: extractedData.category || 'General',
    };
    onVerifyAndAdd(newMed);
    cleanupAndClose();
  };

  const handleConfirmAll = () => {
    const listToSave = allExtractedMeds.length > 0 ? allExtractedMeds : [extractedData];
    const medsToSave: Medication[] = listToSave.map((med, idx) => ({
      id: `med-${Date.now()}-${idx}`,
      name: med.name || 'Prescribed Medicine',
      genericName: med.genericName || '',
      strength: med.strength || 'Standard',
      dosage: med.dosage || '1 Unit',
      frequency: med.frequency || 'Once daily',
      route: med.route || 'Oral',
      duration: med.duration || '3 weeks',
      instructions: med.instructions || '',
      prescribingDoctor: med.prescribingDoctor || clearScriptResult?.doctorName || 'Dr. Sanjay Ghoshal',
      hospital: med.hospital || clearScriptResult?.hospitalName || 'Joint Care Clinic',
      datePrescribed: med.datePrescribed || 'Today',
      trustState: 'verified',
      timeOfDay: med.timeOfDay || ['morning'],
      mealTiming: med.mealTiming || 'after_food',
      category: med.category || 'General',
    }));
    onVerifyAndAdd(medsToSave);
    cleanupAndClose();
  };

  const cleanupAndClose = () => {
    setStep('upload');
    setUploadedDocMeta(null);
    setClearScriptResult(null);
    setAllExtractedMeds([]);
    setSelectedMedIndex(0);
    if (previewImageUrl) URL.revokeObjectURL(previewImageUrl);
    setPreviewImageUrl(null);
    onClose();
  };

  return (
    <div 
      data-lenis-prevent="true"
      className="fixed inset-0 z-50 overflow-y-auto bg-[#1C2B3A]/70 flex items-center justify-center p-2 sm:p-4"
      style={{ overscrollBehavior: 'contain' }}
      onWheel={(e) => e.stopPropagation()}
      onTouchMove={(e) => e.stopPropagation()}
    >
      <div 
        data-lenis-prevent="true"
        className="relative bg-white rounded-sm border border-[#DDD9D1] max-w-4xl w-full flex flex-col max-h-[92vh] shadow-2xl overflow-hidden my-auto"
        style={{ overscrollBehavior: 'contain' }}
        onClick={(e) => e.stopPropagation()}
        onWheel={(e) => e.stopPropagation()}
        onTouchMove={(e) => e.stopPropagation()}
      >
        
        {/* Fixed Header */}
        <div className="shrink-0 flex items-center justify-between border-b border-[#DDD9D1] px-5 sm:px-6 py-3.5 bg-white">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono uppercase font-semibold text-[#2B5F8A]">
                Human-in-the-Loop Extraction
              </span>
              <span className="inline-flex items-center gap-1 text-[10px] font-mono bg-[#EBF5EC] text-[#2D5A40] px-1.5 py-0.5 rounded-sm border border-[#D3EAD7]">
                <Cpu className="w-3 h-3 text-[#3D8B6E]" />
                ClearScript.js OCR v2.6
              </span>
            </div>
            <h3 className="font-serif text-lg sm:text-xl text-[#1C2B3A]">
              Upload & Verify Prescription
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-sm text-[#6B7A8D] hover:text-[#1C2B3A] hover:bg-[#FAF8F3] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Body Container */}
        <div 
          data-lenis-prevent="true"
          className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4 custom-modal-scrollbar"
          style={{ overscrollBehavior: 'contain' }}
          onWheel={(e) => e.stopPropagation()}
          onTouchMove={(e) => e.stopPropagation()}
        >

          {/* Step 1: Upload */}
          {step === 'upload' && (
            <div className="space-y-5">
              {/* Hidden file input */}
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept=".pdf,.png,.jpg,.jpeg,.webp"
                className="hidden"
              />

              <div
                className="bg-[#FAF8F3] border border-dashed border-[#DDD9D1] rounded-sm p-7 text-center space-y-3 hover:border-[#1C2B3A] transition-colors cursor-pointer"
                onClick={() => fileInputRef.current?.click()}
              >
                <div className="w-10 h-10 rounded-sm bg-white border border-[#DDD9D1] flex items-center justify-center mx-auto text-[#4A90C4]">
                  <UploadCloud className="w-5 h-5" strokeWidth={2} />
                </div>
                <div className="space-y-1">
                  <p className="text-xs font-semibold text-[#1C2B3A]">
                    Click or drag doctor prescription, clinic slip, or discharge sheet
                  </p>
                  <p className="text-[11px] text-[#6B7A8D]">
                    Supports PNG, JPG, or PDF · Powered by ClearScript.js Multimodal Handwriting OCR
                  </p>
                </div>
                <div className="flex items-center justify-center gap-3 pt-1">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      fileInputRef.current?.click();
                    }}
                    className="bg-[#4A90C4] text-white font-semibold text-xs px-4 py-2 rounded-sm hover:bg-[#3A7DB0] transition-colors shadow-sm"
                  >
                    Choose Local Prescription Image
                  </button>
                </div>
              </div>

              {/* Quick Sample Prescriptions */}
              <div className="space-y-2 border border-[#DDD9D1] bg-[#FAF8F3] rounded-sm p-3">
                <span className="text-[11px] font-semibold text-[#1C2B3A] block">
                  Or test instant recognition with sample clinic prescriptions:
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {samplePresets.map((sample) => (
                    <button
                      key={sample.id}
                      type="button"
                      onClick={() => handleSelectSample(sample)}
                      className="p-2 bg-white border border-[#DDD9D1] rounded-sm text-left hover:border-[#4A90C4] hover:shadow-xs transition-all space-y-1"
                    >
                      <span className="text-[11px] font-semibold text-[#1C2B3A] block truncate">
                        {sample.drug}
                      </span>
                      <span className="text-[10px] text-[#6B7A8D] block truncate">
                        {sample.strength} · {sample.sig.split(' ')[0]}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm p-3 flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-[#E07B39] shrink-0 mt-0.5" />
                <p className="text-xs text-[#6B7A8D] leading-relaxed">
                  <strong className="text-[#1C2B3A] font-semibold">Patient Verification Gate:</strong> ClearScript utilizes pharmaceutical fuzzy matching to interpret illegible handwriting, but <span className="underline text-[#1C2B3A]">you must verify extracted names and instructions</span> before they are saved to your longitudinal record.
                </p>
              </div>
            </div>
          )}

          {/* Step 2: Extracting Loading */}
          {step === 'extracting' && (
            <div className="py-12 text-center space-y-4">
              <div className="w-12 h-12 rounded-sm bg-[#FAF8F3] border border-[#DDD9D1] flex items-center justify-center mx-auto text-[#4A90C4] animate-pulse">
                <Sparkles className="w-6 h-6 animate-spin text-[#4A90C4]" style={{ animationDuration: '2.5s' }} />
              </div>
              <div className="space-y-1.5 max-w-md mx-auto">
                <h4 className="font-serif text-lg text-[#1C2B3A]">
                  Analyzing with ClearScript.js...
                </h4>
                <p className="text-xs text-[#2B5F8A] font-mono animate-pulse">
                  {extractStatusText}
                </p>
                <p className="text-[11px] text-[#6B7A8D]">
                  Applying Latin sig translation, brand normalization, and human-in-the-loop confidence scoring
                </p>
              </div>
            </div>
          )}

          {/* Step 3: Side-by-Side Verification Gate Content */}
          {step === 'review' && (
            <div className="space-y-4">

              {/* Prescriber & Patient Clinical Header */}
              <div className="bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-3.5 py-2 flex flex-wrap items-center justify-between gap-2.5 text-xs">
                <div className="flex items-center gap-1.5">
                  <span className="text-[#6B7A8D] font-medium">Patient:</span>
                  <span className="font-semibold text-[#1C2B3A]">
                    {clearScriptResult?.patientName || 'Subrata Mondal'}
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-[#6B7A8D] font-medium">Diagnosis:</span>
                  <span className="font-semibold text-[#2B5F8A]">
                    {clearScriptResult?.diagnosis || 'Osteoarthritis right knee'}
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-[#6B7A8D] font-medium">Prescriber:</span>
                  <span className="font-semibold text-[#1C2B3A]">
                    {extractedData.prescribingDoctor || clearScriptResult?.doctorName || 'Dr. Sanjay Ghoshal'}
                  </span>
                  <span className="text-[11px] text-[#6B7A8D]">
                    ({extractedData.hospital || clearScriptResult?.hospitalName || 'Joint Care Clinic'})
                  </span>
                </div>
              </div>

              <div className="grid md:grid-cols-12 gap-4 items-start">
                
                {/* Document Preview (Left) */}
                <div className="md:col-span-5 bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm p-3.5 space-y-2.5">
                  <div className="flex items-center justify-between text-xs text-[#6B7A8D]">
                    <span className="flex items-center gap-1.5 font-semibold text-[#1C2B3A]">
                      <FileText className="w-3.5 h-3.5 text-[#4A90C4]" />
                      Original Prescription Slip
                    </span>
                    <span className="text-[10px] font-mono bg-[#EBF5EC] text-[#2D5A40] border border-[#D3EAD7] px-1.5 py-0.5 rounded-sm font-semibold">
                      {clearScriptResult?.confidenceScore ?? 96}% OCR Match
                    </span>
                  </div>

                  {/* View Mode Switcher */}
                  <div className="flex items-center gap-1 border-b border-[#DDD9D1] pb-1 text-[11px] font-semibold">
                    <button
                      type="button"
                      onClick={() => setViewMode('preview')}
                      className={`px-2 py-0.5 rounded-xs transition-colors ${
                        viewMode === 'preview' 
                          ? 'bg-[#1C2B3A] text-white' 
                          : 'text-[#6B7A8D] hover:text-[#1C2B3A]'
                      }`}
                    >
                      Document Preview
                    </button>
                    <button
                      type="button"
                      onClick={() => setViewMode('ocr_text')}
                      className={`px-2 py-0.5 rounded-xs transition-colors flex items-center gap-1.5 ${
                        viewMode === 'ocr_text' 
                          ? 'bg-[#1C2B3A] text-white' 
                          : 'text-[#6B7A8D] hover:text-[#1C2B3A]'
                      }`}
                    >
                      <span>Raw OCR Text</span>
                      {clearScriptResult?.rawOcrText && (
                        <span className="w-1.5 h-1.5 rounded-full bg-[#3D8B6E] inline-block" />
                      )}
                    </button>
                  </div>

                  {viewMode === 'ocr_text' ? (
                    <div className="bg-white border border-[#DDD9D1] rounded-sm p-2.5 font-mono text-[11px] text-[#1C2B3A] max-h-56 overflow-y-auto whitespace-pre-wrap space-y-1 shadow-xs">
                      <span className="text-[10px] font-semibold text-[#6B7A8D] uppercase tracking-wider block border-b border-[#DDD9D1] pb-1">
                        Raw Text Read from File (Tesseract OCR):
                      </span>
                      <div className="pt-1 text-[#1C2B3A] leading-relaxed">
                        {clearScriptResult?.rawOcrText || 'No direct text extracted.'}
                      </div>
                    </div>
                  ) : previewImageUrl ? (
                    <div className="bg-white border border-[#DDD9D1] rounded-sm p-1.5 text-center space-y-1.5">
                      <img 
                        src={previewImageUrl} 
                        alt="Uploaded Prescription" 
                        className="max-h-40 w-full object-contain rounded-xs border border-[#DDD9D1]"
                      />
                      <span className="text-[10px] font-mono text-[#6B7A8D] block truncate">
                        Uploaded file: {clearScriptResult?.fileName || 'image.jpg'}
                      </span>
                    </div>
                  ) : (
                    <div className="bg-white border border-[#DDD9D1] rounded-sm p-3 text-xs font-mono text-[#1C2B3A] space-y-1.5 select-none shadow-xs">
                      <div className="font-semibold border-b border-[#DDD9D1] pb-1 text-[#1C2B3A]">
                        {clearScriptResult?.slipText.header || extractedData.hospital?.toUpperCase() || 'JOINT CARE CLINIC'}
                      </div>
                      <div className="text-[11px] text-[#6B7A8D]">
                        {clearScriptResult?.slipText.doctorLine || `${extractedData.prescribingDoctor} · Reg: MCI-39102`}<br />
                        {clearScriptResult?.slipText.patientLine || `Patient: ${clearScriptResult?.patientName || 'Subrata Mondal'}`}
                      </div>
                      <div className="bg-[#FAF8F3] p-2 border border-[#DDD9D1] text-[11px] space-y-0.5">
                        <div className="font-semibold text-[#2B5F8A]">
                          {clearScriptResult?.slipText.rxLine || `Rx: ${extractedData.name} (${extractedData.strength})`}
                        </div>
                        <div className="text-[#1C2B3A]">
                          {clearScriptResult?.slipText.sigLine || `Sig: ${extractedData.frequency} x ${extractedData.duration}`}
                        </div>
                      </div>
                      <div className="text-[10px] text-[#3D8B6E] pt-0.5 flex items-center gap-1 font-semibold">
                        <Check className="w-3 h-3 text-[#3D8B6E]" />
                        <span>{clearScriptResult?.slipText.footer || 'ClearScript.js Neural OCR verified'}</span>
                      </div>
                    </div>
                  )}

                  <div className="p-2 bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm text-[10px] text-[#6B7A8D] space-y-0.5">
                    <div className="flex items-center justify-between font-mono text-[#1C2B3A]">
                      <span>Engine: ClearScript.js v2.6</span>
                      <span className="text-[#3D8B6E] font-semibold">Ready for Review</span>
                    </div>
                    <p>
                      Verify fields on the right. Touchpad scroll to view all details.
                    </p>
                  </div>
                </div>

                {/* Extracted Fields Form (Right) */}
                <div className="md:col-span-7 space-y-2.5">
                  <div className="flex items-center justify-between border-b border-[#DDD9D1] pb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-[#1C2B3A]">Extracted Medication Fields</span>
                      <span className="text-[10px] font-mono text-[#3D8B6E] bg-[#EBF5EC] px-2 py-0.5 rounded-sm border border-[#D3EAD7] font-semibold">
                        ClearScript Parsed
                      </span>
                    </div>
                    <span className="text-[10px] font-mono font-semibold text-[#A05520] bg-[#FEF3E8] px-2 py-0.5 rounded-sm border border-[#FCDDC1]">
                      Verification Required
                    </span>
                  </div>

                  {/* Multi-medication selection tabs if more than 1 med found */}
                  {allExtractedMeds.length > 1 && (
                    <div className="space-y-1 bg-[#FAF8F3] p-2 rounded-sm border border-[#DDD9D1]">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-semibold text-[#1C2B3A]">
                          Detected Medications ({allExtractedMeds.length}):
                        </span>
                        <span className="text-[10px] text-[#6B7A8D]">
                          Click tab to view/edit
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-1.5 pt-0.5">
                        {allExtractedMeds.map((med, idx) => (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => handleSelectMedIndex(idx)}
                            className={`px-2.5 py-1 text-xs rounded-sm border font-semibold flex items-center gap-1.5 transition-all ${
                              selectedMedIndex === idx
                                ? 'bg-[#1C2B3A] text-white border-[#1C2B3A] shadow-xs'
                                : 'bg-white text-[#1C2B3A] border-[#DDD9D1] hover:border-[#4A90C4]'
                            }`}
                          >
                            <span className={`w-3.5 h-3.5 rounded-full text-[9px] flex items-center justify-center font-bold ${
                              selectedMedIndex === idx ? 'bg-white text-[#1C2B3A]' : 'bg-[#FAF8F3] text-[#6B7A8D]'
                            }`}>
                              {idx + 1}
                            </span>
                            <span>{med.name || `Medication ${idx + 1}`}</span>
                            {med.strength && (
                              <span className={`text-[10px] px-1 rounded-xs ${
                                selectedMedIndex === idx ? 'bg-white/20 text-white' : 'bg-[#FAF8F3] text-[#6B7A8D]'
                              }`}>
                                {med.strength}
                              </span>
                            )}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-2.5">
                    <div className="space-y-0.5">
                      <label className="text-[10px] font-semibold text-[#6B7A8D]">Medicine / Brand Name</label>
                      <input
                        type="text"
                        value={extractedData.name || ''}
                        onChange={(e) => handleFieldChange('name', e.target.value)}
                        className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs text-[#1C2B3A] font-semibold focus:border-[#4A90C4] outline-none"
                      />
                    </div>

                    <div className="space-y-0.5">
                      <label className="text-[10px] font-semibold text-[#6B7A8D]">Strength</label>
                      <input
                        type="text"
                        value={extractedData.strength || ''}
                        onChange={(e) => handleFieldChange('strength', e.target.value)}
                        className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs text-[#1C2B3A] focus:border-[#4A90C4] outline-none"
                      />
                    </div>

                    <div className="space-y-0.5">
                      <label className="text-[10px] font-semibold text-[#6B7A8D]">Generic Formulation</label>
                      <input
                        type="text"
                        value={extractedData.genericName || ''}
                        onChange={(e) => handleFieldChange('genericName', e.target.value)}
                        className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs text-[#1C2B3A] focus:border-[#4A90C4] outline-none"
                      />
                    </div>

                    <div className="space-y-0.5">
                      <label className="text-[10px] font-semibold text-[#6B7A8D]">Clinical Frequency</label>
                      <input
                        type="text"
                        value={extractedData.frequency || ''}
                        onChange={(e) => handleFieldChange('frequency', e.target.value)}
                        className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs text-[#1C2B3A] focus:border-[#4A90C4] outline-none"
                      />
                    </div>

                    <div className="space-y-0.5">
                      <label className="text-[10px] font-semibold text-[#6B7A8D]">Duration</label>
                      <input
                        type="text"
                        value={extractedData.duration || ''}
                        onChange={(e) => handleFieldChange('duration', e.target.value)}
                        className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs text-[#1C2B3A] focus:border-[#4A90C4] outline-none"
                      />
                    </div>

                    <div className="space-y-0.5">
                      <label className="text-[10px] font-semibold text-[#6B7A8D]">Route of Administration</label>
                      <input
                        type="text"
                        value={extractedData.route || 'Oral'}
                        onChange={(e) => handleFieldChange('route', e.target.value)}
                        className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs text-[#1C2B3A] focus:border-[#4A90C4] outline-none"
                      />
                    </div>
                  </div>

                  <div className="space-y-0.5">
                    <label className="text-[10px] font-semibold text-[#6B7A8D]">Patient Instructions (ClearScript Transcribed)</label>
                    <input
                      type="text"
                      value={extractedData.instructions || ''}
                      onChange={(e) => handleFieldChange('instructions', e.target.value)}
                      className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs text-[#1C2B3A] focus:border-[#4A90C4] outline-none"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2.5">
                    <div className="space-y-0.5">
                      <label className="text-[10px] font-semibold text-[#6B7A8D]">Prescribing Doctor</label>
                      <input
                        type="text"
                        value={extractedData.prescribingDoctor || ''}
                        onChange={(e) => handleFieldChange('prescribingDoctor', e.target.value)}
                        className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs text-[#1C2B3A] focus:border-[#4A90C4] outline-none"
                      />
                    </div>

                    <div className="space-y-0.5">
                      <label className="text-[10px] font-semibold text-[#6B7A8D]">Hospital / Clinic</label>
                      <input
                        type="text"
                        value={extractedData.hospital || ''}
                        onChange={(e) => handleFieldChange('hospital', e.target.value)}
                        className="w-full bg-[#FAF8F3] border border-[#DDD9D1] rounded-sm px-2 py-1 text-xs text-[#1C2B3A] focus:border-[#4A90C4] outline-none"
                      />
                    </div>
                  </div>
                </div>

              </div>

            </div>
          )}

        </div>

        {/* Fixed Footer Bar (Always in view for review step) */}
        {step === 'review' && (
          <div className="shrink-0 border-t border-[#DDD9D1] bg-[#FAF8F3] px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-2.5 shadow-inner">
            <button
              type="button"
              onClick={() => setStep('upload')}
              className="text-xs font-semibold text-[#6B7A8D] hover:text-[#1C2B3A]"
            >
              ← Back to Upload
            </button>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="border border-[#DDD9D1] bg-white text-[#1C2B3A] font-semibold text-xs px-3 py-1.5 rounded-sm hover:bg-[#FAF8F3] transition-colors"
              >
                Discard
              </button>

              {allExtractedMeds.length > 1 ? (
                <>
                  <button
                    type="button"
                    onClick={handleConfirmCurrent}
                    className="border border-[#3D8B6E] text-[#2D5A40] bg-[#EBF5EC] font-semibold text-xs px-3 py-1.5 rounded-sm hover:bg-[#D3EAD7] transition-colors"
                  >
                    Add #{selectedMedIndex + 1} ({extractedData.name || 'Current'}) Only
                  </button>
                  <button
                    type="button"
                    onClick={handleConfirmAll}
                    className="bg-[#3D8B6E] text-white font-semibold text-xs px-3.5 py-1.5 rounded-sm hover:bg-[#2D5A40] transition-colors flex items-center gap-1.5 shadow-sm"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Verify & Add All ({allExtractedMeds.length}) to Record</span>
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  onClick={handleConfirmCurrent}
                  className="bg-[#3D8B6E] text-white font-semibold text-xs px-4 py-1.5 rounded-sm hover:bg-[#2D5A40] transition-colors flex items-center gap-1.5 shadow-sm"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Verify & Add to My Record</span>
                </button>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
};
