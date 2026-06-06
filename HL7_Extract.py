import hl7
import uuid

class HL7_Extract:

    def hl7_var (self,hl7_message,audit_trail):
        parsed_HL7 = hl7.parse(hl7_message)
        extracted_insurance = []
        extracted_gurantor = []
        extracted_nexttokin = []

        try:
            pid_segment = parsed_HL7.segment("PID")
            audit_trail.append("Parsed PID now extracting data from PID")
            extracted_demographics = self._pid_extract(pid_segment,audit_trail)

        except hl7.SegmentNotFound:
            audit_trail.append("PID is missing from HL7")
            print("No PID Segement Found")

        try:
            in1counter = 0
            for in1segment in parsed_HL7.segments("IN1"):
                in1counter += 1
                audit_trail.append(f"Parsed IN1 now extracting data from IN1: {in1counter}")
                insurance,insurance_name = self._insurance_extract(in1segment,audit_trail,in1counter)
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
                guarantor, guarantor_mobile = self._guarantor_extract(gt1segment,audit_trail,gt1counter)
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
                nexttokin,nexttokin_mobile_number = self._nk1_extract(nk1segment,audit_trail,nk1counter)
                extracted_nexttokin.append({
                    "nk1_data": nexttokin,
                    "nk1_mobile": nexttokin_mobile_number
                })

        except hl7.SegmentNotFound:
            audit_trail.append("No NK1 segment found in the HL7 message.")
            print("No NK1 segment found in the HL7 message.")

        audit_trail.append("===============================================Passing all extracted data to process and create entries===============================================")
        
        return(extracted_demographics,extracted_insurance,extracted_gurantor,extracted_nexttokin,audit_trail,hl7_message)
        

    def _pid_extract(self,pid_segment,audit_trail):

        demographics = {
        "account_number": self._pid_account_number_logic(str(pid_segment[3])),
        "lastname": str(pid_segment[5][0][0]),
        "firstname": str(pid_segment[5][0][1]),
        "dob": self._format_dob(str(pid_segment[7])),
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

    def _insurance_extract(self, insurance, audit_trail, in1counter):
        insurance_name = str(insurance[4])
        insurance = {
            "subscriberid": str(insurance[2]),
            "start_date": self._format_dob(str(insurance[12])),
            "end_date": self._format_dob(str(insurance[13])),
            "type": str(insurance[14]),
            "terminated": str(insurance[15])
        }
        audit_trail.append(f"Extracted Data from IN1:{in1counter}")
        return (insurance,insurance_name)

    def _guarantor_extract(self,guarantor,audit_trail,gt1counter):
        guarantor_mobile_number =  str(guarantor[6])
        guarantor = {
                "lastname": str(guarantor[3][0][0]),
                "firstname": str(guarantor[3][0][1]),
                "dob": self._format_dob(str(guarantor[8])),
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

    def _nk1_extract(self,nexttokin,audit_trail,nk1counter):
        nexttokin_mobile_number =  str(nexttokin[6])
        nexttokin = {
                "lastname": str(nexttokin[3][0][0]),
                "firstname": str(nexttokin[3][0][1]),
                "dob": self._format_dob(str(nexttokin[8])),
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

    def _pid_account_number_logic(self,account_number):

        if account_number.strip():
            return account_number
        else:
            random_id = str(uuid.uuid4())[:8]
            account_number = f"SYSGEN-{random_id}"
            return account_number
        
    def _format_dob(self,raw_dob):
        if len(raw_dob) >= 8:
            return f"{raw_dob[:4]}-{raw_dob[4:6]}-{raw_dob[6:8]}"
        return None