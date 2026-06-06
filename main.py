import httpx
from HL7_Extract import HL7_Extract
from FHIR_Crud import FHIR_Crud
from HL7_Crud import HL7_Crud, message_logger
from database import session
from fastapi import FastAPI,Body
from datetime import date

app =FastAPI(title="Healthcare Interoperability Core")

@app.post("/process_hl7")
async def Read_ADT_Over_HTTP(raw_message: str = Body(..., media_type="text/plain")):
    raw_hl7_message = raw_message.replace('\r\n', '\r').replace('\n', '\r')
    messagecount = 0
    success_count = 0
    error_count = 0  
    db=session()
    audit_trail = []
    audit_trail.append("===============================================Message successfully extracted from file===============================================")
    try:
        
        audit_trail.append("===============================================Starting Message Processing===============================================")
        hl7_processor = HL7_Extract()
        extracted_demographics,extracted_insurance,extracted_gurantor,extracted_nexttokin,audit_trail,hl7_message = hl7_processor.hl7_var(raw_hl7_message,audit_trail)   

        hl7crud = HL7_Crud()
        hl7crud.save_patient_demographics(demographics_dict=extracted_demographics,insurance_list = extracted_insurance,guarantor_list=extracted_gurantor,nk1_list=extracted_nexttokin,audit_trail=audit_trail,single_valid_message=hl7_message)

        messagecount += 1
        success_count += 1

    except Exception as e:
        audit_trail.append("===============================================Message processing Failed.===============================================")
        error_count += 1
        status=2
        message_logger.updatehl7datalog(db,raw_hl7_message,status,audit_trail)
        print(f"Error in the message : {e}")
        
    return f"Batch Complete,Total Count:{messagecount} Success:{success_count} Error:{error_count}"


@app.get("/GetPatientData")
async def Fetch_Patient_Details(account_number: str, DOB: date):
    if account_number and DOB:
        fhircrud = FHIR_Crud()
        pretty_json = fhircrud.fetch_patient_demograhics(account_number=account_number,dob=DOB)
        return pretty_json
    
@app.post("/GetPatientData_to_PostOnHAPIServer")
async def Fetch_JSON_Transaction(searchset_json: dict):
    if searchset_json:
        fhircrud = FHIR_Crud()
        transactional_json = fhircrud.create_transactional_json(searchset_json)
        return transactional_json    
    

@app.post("/Patient/CreatePatient")
async def Create_Patient(patient: dict):
    async with httpx.AsyncClient() as client:
            response = await client.post("https://hapi.fhir.org/baseR4",json=patient)
            data = response.json()
            print(type(data))
            patientid = data.get("id")

            if patientid:
                 return {
            "status": "success", 
            "message": "Patient created successfully!",
            "patient_id": patientid
                }
            else:
                return {
                "status": "error",
                "message": "Failed to create patient.",
                "hapi_response": data  
                }

    return