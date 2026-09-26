/**
 * TypeScript wrapper for ClearScript.js OCR model engine
 */
import { ClearScript as ClearScriptCore, PHARMACOPOEIA, PRESCRIBERS } from './clearscript.js';
import type { Medication } from '../types';

export interface ClearScriptSlipText {
  header: string;
  doctorLine: string;
  patientLine: string;
  rxLine: string;
  sigLine: string;
  footer: string;
}

export interface ClearScriptResult {
  model: string;
  confidenceScore: number;
  isHandwritten: boolean;
  previewUrl: string | null;
  fileName: string;
  extractedMedication: Medication & { ocrConfidence?: number; rxNormCode?: string };
  slipText: ClearScriptSlipText;
}

export interface SamplePrescription {
  id: string;
  label: string;
  drug: string;
  strength: string;
  sig: string;
  doctor: string;
  hospital: string;
}

export const ClearScript = {
  version: (ClearScriptCore as any).version as string,

  async processPrescription(input: File | Blob | string, options?: { hintText?: string }): Promise<ClearScriptResult> {
    return (ClearScriptCore as any).processPrescription(input, options);
  },

  getSamplePrescriptions(): SamplePrescription[] {
    return (ClearScriptCore as any).getSamplePrescriptions();
  }
};

export { PHARMACOPOEIA, PRESCRIBERS };
