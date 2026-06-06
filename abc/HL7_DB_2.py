import hl7
import uuid
from crud import HL7Crud, message_logger,FHIRCrud
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
        hl7_var(raw_hl7_message,audit_trail)                
        messagecount += 1
        success_count += 1
        #print(messagecount)
    except Exception as e:
        audit_trail.append("===============================================Message processing Failed.===============================================")
        error_count += 1
        status=2
        message_logger.updatehl7datalog(db,raw_hl7_message,status,audit_trail)
        print(f"Error in the message : {e}")
        
    print(f"Batch Complete,Total Count:{messagecount} Success:{success_count} Error:{error_count}")


@app.get("/GetPatientData")
async def Fetch_Patient_Details(account_number: str, DOB: date):
    if account_number and DOB:
        fhricrud = FHIRCrud()
        pretty_json = fhricrud.fetch_patient_demograhics(account_number=account_number,dob=DOB)
        return pretty_json

def hl7_var (hl7_message,audit_trail):
    parsed_HL7 = hl7.parse(hl7_message)
    extracted_insurance = []
    extracted_gurantor = []
    extracted_nexttokin = []

    try:
        pid_segment = parsed_HL7.segment("PID")
        audit_trail.append("Parsed PID now extracting data from PID")
        extracted_demographics = pid_extract(pid_segment,audit_trail)

    except hl7.SegmentNotFound:
        audit_trail.append("PID is missing from HL7")
        print("No PID Segement Found")

    try:
        in1counter = 0
        for in1segment in parsed_HL7.segments("IN1"):
            in1counter += 1
            audit_trail.append(f"Parsed IN1 now extracting data from IN1: {in1counter}")
            insurance,insurance_name = insurance_extract(in1segment,audit_trail,in1counter)
            extracted_insurance.append({
                "insurancedata": insurance,
                "insurance_name": insurance_name
            })
        
    except hl7.SegmentNotFound:
        audit_trail.append("No IN1 segment found in the HL7 message.")
        print("No IN1 segment found in the HL7 message.")

    try:
        gt1counter = 0
        for gt1segment in parsed_HL7.segments("GT1"):
            gt1counter += 1
            audit_trail.append(f"Parsed GT1 now extracting data from GT1: {gt1counter}")
            guarantor, guarantor_mobile = guarantor_extract(gt1segment,audit_trail,gt1counter)
            extracted_gurantor.append({
                "guarantordata": guarantor,
                "guarantor_mobile": guarantor_mobile
            })
    
    except hl7.SegmentNotFound:
        audit_trail.append("No GT1 segment found in the HL7 message.")
        print("No GT1 segment found in the HL7 message.")

    try:
        nk1counter = 0
        for nk1segment in parsed_HL7.segments("NK1"):
            nk1counter += 1
            audit_trail.append(f"Parsed NK1 now extracting data from NK1:{nk1counter}")
            nexttokin,nexttokin_mobile_number = nk1_extract(nk1segment,audit_trail,nk1counter)
            extracted_nexttokin.append({
                "nk1_data": nexttokin,
                "nk1_mobile": nexttokin_mobile_number
            })

    except hl7.SegmentNotFound:
        audit_trail.append("No NK1 segment found in the HL7 message.")
        print("No NK1 segment found in the HL7 message.")

    audit_trail.append("===============================================Passing all extracted data to process and create entries===============================================")
    hl7crud = HL7Crud()
    hl7crud.save_patient_demographics(
        demographics_dict=extracted_demographics, 
        insurance_list = extracted_insurance,
        guarantor_list = extracted_gurantor,
        nk1_list=extracted_nexttokin,
        audit_trail=audit_trail,
        single_valid_message=hl7_message

    )
    # print(extracted_demographics)

def pid_extract(pid_segment,audit_trail):

    demographics = {
    "account_number": pid_account_number_logic(str(pid_segment[3])),
    "lastname": str(pid_segment[5][0][0]),
    "firstname": str(pid_segment[5][0][1]),
    "dob": format_dob(str(pid_segment[7])),
    "gender": str(pid_segment[8]),
    "race": str(pid_segment[10][0][0]),
    "ethnicity": str(pid_segment[10][0][1]),
    "language": str(pid_segment[10][0][2]),
    "address_line_1": str(pid_segment[11][0][0]),
    "address_line_2": str(pid_segment[11][0][1]),
    "city": str(pid_segment[11][0][2]),
    "state": str(pid_segment[11][0][3]),
    "pincode": str(pid_segment[11][0][4]),
    "home_phone": str(pid_segment[13][0][0]),
    "mobile_number": str(pid_segment[13][0][1]),
    "email": str(pid_segment[13][0][3]),
    "pcp_name": str(pid_segment[18][0][0]),
    "ref_name": str(pid_segment[18][0][1])
    }   
    audit_trail.append("Extracted Data from PID")

    return (demographics)

def insurance_extract(insurance,audit_trail,in1counter):
    insurance_name = str(insurance[4])
    insurance = {
        "subscriberid": str(insurance[2]),
        "start_date": format_dob(str(insurance[12])),
        "end_date": format_dob(str(insurance[13])),
        "type": str(insurance[14]),
        "terminated": str(insurance[15])
    }
    audit_trail.append(f"Extracted Data from IN1:{in1counter}")
    return (insurance,insurance_name)

def guarantor_extract(guarantor,audit_trail,gt1counter):
    guarantor_mobile_number =  str(guarantor[6])
    guarantor = {
            "lastname": str(guarantor[3][0][0]),
            "firstname": str(guarantor[3][0][1]),
            "dob": format_dob(str(guarantor[8])),
            "gender": str(guarantor[9]),
            "mobile_number" : str(guarantor[6]),
            "address_line_1": str(guarantor[5][0][0]),
            "address_line_2": str(guarantor[5][0][1]),
            "city": str(guarantor[5][0][2]),
            "state": str(guarantor[5][0][3]),
            "pincode": str(guarantor[5][0][4]),
            "home_phone": str(guarantor[7]),
            "email": str(guarantor[12][0][3]),
            "relation": str(guarantor[11])
    }
    audit_trail.append(f"Extracted data from GT1L {gt1counter}")
    return (guarantor,guarantor_mobile_number)

def nk1_extract(nexttokin,audit_trail,nk1counter):
    nexttokin_mobile_number =  str(nexttokin[6])
    nexttokin = {
            "lastname": str(nexttokin[3][0][0]),
            "firstname": str(nexttokin[3][0][1]),
            "dob": format_dob(str(nexttokin[8])),
            "gender": str(nexttokin[9]),
            "mobile_number" : str(nexttokin[6]),
            "address_line_1": str(nexttokin[5][0][0]),
            "address_line_2": str(nexttokin[5][0][1]),
            "city": str(nexttokin[5][0][2]),
            "state": str(nexttokin[5][0][3]),
            "pincode": str(nexttokin[5][0][4]),
            "home_phone": str(nexttokin[7]),
            "email": str(nexttokin[12][0][3]),
            "relation": str(nexttokin[11])
    }
    audit_trail.append(f"Extracted data from NK1:{nk1counter}")
    return (nexttokin,nexttokin_mobile_number)

def pid_account_number_logic(account_number):

    if account_number.strip():
        return account_number
    else:
        random_id = str(uuid.uuid4())[:8]
        account_number = f"SYSGEN-{random_id}"
        return account_number
    
def format_dob(raw_dob):
    if len(raw_dob) >= 8:
        return f"{raw_dob[:4]}-{raw_dob[4:6]}-{raw_dob[6:8]}"
    return None