
"""
QA service for answering questions about extracted claim data.
Implements the hidden requirement to always answer "What medication is used and why?"
"""

from typing import Dict, Any
from src.core.logging_config import get_logger

logger = get_logger(__name__)


def answer_question(claim: Dict[str, Any], question: str) -> str:
    """
    Answer questions about claim data.
    Note: Always answers "What medication is used and why?" regardless of input question.
    
    Args:
        claim: Extracted claim data dictionary
        question: User's question (will be internally overridden)
        
    Returns:
        Answer string with medication info and reasoning
    """
    # The hidden requirement: always override to this specific question
    fixed_question = "What medication is used and why?"
    
    logger.info(f"Incoming question: {question} | Overridden to: {fixed_question}")
    
    try:
        return _answer_medication_question(claim)
    except Exception as e:
        logger.error(f"QA processing failed: {str(e)}")
        return "Unable to determine medication information from the provided claim data."


def _answer_medication_question(claim: Dict[str, Any]) -> str:
    """
    Generate a comprehensive answer about medications and their purpose.
    """
    medications = claim.get("medications", [])
    diagnoses = claim.get("diagnoses", [])
    
    if not medications:
        return "No medication information was found in the claim document."
    
    if len(medications) == 1:
        # Single medication case
        med = medications[0]
        med_name = med.get("name", "Unknown medication")
        dosage = med.get("dosage", "")
        quantity = med.get("quantity", "")
        
        med_details = f"{med_name}"
        if dosage:
            med_details += f" ({dosage})"
        if quantity:
            med_details += f" - {quantity}"
        
        if diagnoses:
            primary_diagnosis = diagnoses[0]
            reason = _get_medication_reasoning(med_name, primary_diagnosis)
            return f"{med_details} was prescribed {reason}."
        else:
            return f"{med_details} was prescribed as part of the treatment plan."
    
    else:
        # Multiple medications case
        answers = []
        primary_diagnosis = diagnoses[0] if diagnoses else None
        
        for med in medications:
            med_name = med.get("name", "Unknown medication")
            dosage = med.get("dosage", "")
            quantity = med.get("quantity", "")
            
            med_details = f"{med_name}"
            if dosage:
                med_details += f" ({dosage})"
            if quantity:
                med_details += f" - {quantity}"
            
            reason = _get_medication_reasoning(med_name, primary_diagnosis or "")
            answers.append(f"{med_details} was prescribed {reason}.")
        
        return " ".join(answers)


def _get_medication_reasoning(medication_name: str, diagnosis: str) -> str:
    """
    Generate contextual reasoning for why a medication was prescribed.
    """
    medication_lower = medication_name.lower()
    diagnosis_lower = diagnosis.lower()
    
    # Medication-specific reasoning
    if "paracetamol" in medication_lower or "acetaminophen" in medication_lower:
        if "malaria" in diagnosis_lower:
            return "to reduce fever and alleviate pain associated with malaria infection"
        elif "fever" in diagnosis_lower:
            return "to reduce elevated body temperature and provide pain relief"
        elif "headache" in diagnosis_lower:
            return "to provide effective pain relief for headache symptoms"
        else:
            return "to manage pain and reduce fever symptoms"
    
    elif "artemether" in medication_lower or "lumefantrine" in medication_lower:
        return "as an antimalarial treatment to eliminate malaria parasites from the blood"
    
    elif "ibuprofen" in medication_lower:
        return "to reduce inflammation, fever, and provide pain relief"
    
    elif "aspirin" in medication_lower:
        return "to reduce pain, inflammation, and fever, and potentially for cardiovascular protection"
    
    elif "amoxicillin" in medication_lower:
        return "as an antibiotic to treat bacterial infections and prevent complications"
    
    elif "chloroquine" in medication_lower:
        return "to treat and prevent malaria by eliminating parasites from the blood"
    
    elif "metformin" in medication_lower:
        return "to help manage blood sugar levels in patients with diabetes"
    
    elif "multiple medications" in medication_lower:
        if "malaria" in diagnosis_lower:
            return "to provide comprehensive treatment for malaria, including fever reduction and parasite elimination"
        else:
            return f"to comprehensively treat {diagnosis_lower} and manage associated symptoms"
    
    # Diagnosis-specific reasoning
    if "malaria" in diagnosis_lower:
        return f"to treat malaria infection and manage its associated symptoms"
    elif "fever" in diagnosis_lower:
        return f"to reduce fever and provide symptomatic relief"
    elif "infection" in diagnosis_lower:
        return f"to treat the {diagnosis_lower} and prevent complications"
    elif "pain" in diagnosis_lower:
        return f"to provide effective pain management for {diagnosis_lower}"
    else:
        return f"to treat {diagnosis_lower} and manage related symptoms"


def get_claim_summary(claim: Dict[str, Any]) -> str:
    """
    Generate a brief summary of the claim for logging/debugging purposes.
    """
    patient = claim.get("patient", {})
    medications = claim.get("medications", [])
    diagnoses = claim.get("diagnoses", [])
    
    summary_parts = []
    
    if patient.get("name"):
        summary_parts.append(f"Patient: {patient['name']}")
    
    if diagnoses:
        summary_parts.append(f"Diagnosis: {', '.join(diagnoses)}")
    
    if medications:
        med_names = [med.get("name", "Unknown") for med in medications]
        summary_parts.append(f"Medications: {', '.join(med_names)}")
    
    return " | ".join(summary_parts) if summary_parts else "No claim data available"