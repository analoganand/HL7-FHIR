import uuid
from database import session, patient_demographics, insurance_master, insurance_demographics, next_to_kin, guarantor_demographics,guarantor_Patient_relation,relation_codes,next_to_kin_patient_relation,hl7datalog
from fhir.resources.bundle import Bundle
from fhir.resources.patient import Patient
from fhir.resources.coverage import Coverage
from fhir.resources.relatedperson import RelatedPerson
from fhir.resources.reference import Reference

class FHIR_Crud:
    
    def fetch_patient_demograhics(self,account_number,dob):
        db= session() 

        patient = db.query(patient_demographics).filter_by(account_number=account_number,dob=dob,deleteflag=False).first()
        patientid= patient.id

        all_insurance = self._fetch_patient_insurance (db,patientid)
        all_gurantors = self._fetch_patient_Guarantor(db,patientid)
        all_next_to_kin = self._fetch_patient_next_to_kin(db,patientid)

        return self._create_fhir_json(db,all_insurance,all_gurantors,all_next_to_kin,patient)

    def create_transactional_json(self,searchset_json):

        if searchset_json.get("resourceType") == "Bundle":
            searchset_json["type"] = "transaction"
            searchset_json.pop("total",None)

            if "entry" in searchset_json:
                for entry in searchset_json["entry"]:
                    resource = entry.get("resource",{})

                    res_type = resource.get("resourceType")
                    res_id = resource.get("id")
                    
                    if res_type and res_id:
                        entry["request"] = {
                            "method": "PUT",
                            "url": f"{res_type}/{res_id}"
                        }
                    
        return searchset_json


    def _fetch_patient_insurance(self,db,id):

        query_insurance_Master = db.query(insurance_master,insurance_demographics).join(insurance_demographics, insurance_master.id == insurance_demographics.insid).filter(insurance_demographics.patientid == id, insurance_demographics.inactive == False).all()

        final_insurance_list = self._fetch_multiple_records(query_insurance_Master, "Insurance") or []

        return final_insurance_list
    
    def _fetch_patient_Guarantor(self,db,id):
        
        query_Guarantor_Master = db.query(guarantor_demographics,guarantor_Patient_relation).join(guarantor_Patient_relation, guarantor_demographics.id == guarantor_Patient_relation.guarantorid).filter(guarantor_Patient_relation.patientid == id, guarantor_Patient_relation.deleteflag==False,guarantor_demographics.deleteflag==False).all()

        return self._fetch_multiple_records(query_Guarantor_Master, "GT1_Details") or []
    
    def _fetch_patient_next_to_kin(self,db,id):

        query_nextto_kin_Master = db.query(next_to_kin,next_to_kin_patient_relation).join(next_to_kin_patient_relation, next_to_kin.id == next_to_kin_patient_relation.nkid).filter(next_to_kin_patient_relation.patientid == id, next_to_kin.deleteflag==False,next_to_kin_patient_relation.deleteflag==False).all()

        return self._fetch_multiple_records(query_nextto_kin_Master, "NK1_Details") or []
    
    def _fetch_multiple_records(self, data, record_type):
        flat_records = []

        for table_1_obj, table_2_obj in data:
            dict_1 = table_1_obj.__dict__.copy()
            dict_2 = table_2_obj.__dict__.copy()

            dict_1.pop('_sa_instance_state', None)
            dict_2.pop('_sa_instance_state', None)

            flat_dict = {**dict_1}

            for key, value in dict_2.items():
                if key in flat_dict:
                    flat_dict[f"{record_type}_{key}"] = value
                else:
                    flat_dict[key] = value

            flat_dict["record_type"] = record_type
            flat_records.append(flat_dict)

        return flat_records
        
    def _related_person_json (self,data,patientid,prefix,relation_dict):
        random_id = str(uuid.uuid4())[:8]
        relation_desc_new =""
        relation_code = data.get("relationid")
        if relation_code:
            relation_desc_new = relation_dict.get(int(relation_code))

        gender = str(data.get("gender", "")).upper()
        fhir_gender = "male" if gender == "M" else "female" if gender =="F" else "unknown"
                
        fhir_related_person = RelatedPerson(
            id = f"{prefix}-{data['mobile_number']}-{random_id}",
            active = not data.get("deleteflag",False),
            patient = Reference(reference=f"Patient/{patientid}"),
            relationship = [{"coding": [{"code": str(relation_desc_new)}]}],
            name = [{"family" : str(data.get("lastname")),"given": [str(data.get("firstname"))]}],
            gender = fhir_gender,
            birthDate = data.get("dob"),
            address = [{"line": [str(data.get("address_line_1","")),str(data.get("address_line_2",""))],
                        "city": str(data.get("city","")),
                        "state": str(data.get("state","")),
                        "postalCode": str(data.get("pincode",""))}],
            telecom = [{"system": "phone", "value": str(data.get("home_phone")), "use": "home"},
                    {"system": "phone", "value": str(data.get("mobile_number")), "use": "mobile"},
                    {"system": "email", "value": str(data.get("email"))}])
        return fhir_related_person

    def _create_fhir_json(self,db,all_insurance,all_gurantors,all_next_to_kin,patient):
               

        relation_desc = db.query(relation_codes.code, relation_codes.description).all()
        
        relation_desc_dict = {relation.code: relation.description for relation in relation_desc }
        

        patient_db = patient
        insurance_list = all_insurance
        guarantor_list = all_gurantors
        nk1_list = all_next_to_kin
    
        bundle_entries = []

        fhir_patient = Patient(
            
            id=patient_db.account_number,
            active= not patient_db.deleteflag,

            identifier=[{
                "system": "urn:oid:sysgen",
                "value": patient_db.account_number
                }],

            name=[{
                "use": "official",
                "family": patient_db.lastname,
                "given": [patient_db.firstname]
                }],

            gender="male" if patient_db.gender == "M" else "female" if patient_db.gender == "F" else "unknown",

            birthDate=patient_db.dob,
        
            address=[{
                "line": [patient_db.address_line_1, patient_db.address_line_2],
                "city": patient_db.city,
                "state": patient_db.state,
                "postalCode": patient_db.pincode
            }],
            telecom=[{"system": "phone", "value": patient_db.home_phone, "use": "home"},
                    {"system": "phone", "value": patient_db.mobile_number, "use": "mobile"},
                    {"system": "email", "value": patient_db.email}],
            
            communication=[{"language": {"text": patient_db.language}}],
            
            generalPractitioner=[{"display": patient_db.pcp_name}]         
            )
        
        bundle_entries.append({"resource": fhir_patient})

        for ins_list in insurance_list:
            random_id_ins = str(uuid.uuid4())[:8]
            coverage_status = "cancelled" if ins_list.get("inactive") else "active"

            coverage_period = {}
            if ins_list.get("start_date"):
                coverage_period["start"] = ins_list["start_date"]
            if ins_list.get("end_date"):
                coverage_period["end"] = ins_list["end_date"]

            insurance_name = ins_list.get("name")
            
            fhir_insurances = Coverage(
                id = f"INS-{ins_list['id']}-{random_id_ins}",
                kind = "Insurance",
                status = coverage_status,
                subscriberId = [{ "value":str (ins_list.get("subscriberid"))}] if ins_list.get("subscriberid") else None,
                period=coverage_period if coverage_period else None,
                type = {"coding":[{"code": str(ins_list.get("type"))}]} if ins_list.get("type") else None,
                insurer = Reference(display=insurance_name),
                beneficiary = Reference(reference=f"Patient/{patient_db.account_number}"))
            
            bundle_entries.append({"resource": fhir_insurances})
        
        for gt1_list in guarantor_list:
           fhir_guarantor = self._related_person_json(data=gt1_list,patientid= patient_db.account_number,prefix='GT1',relation_dict=relation_desc_dict)
           bundle_entries.append({"resource": fhir_guarantor})

        for nk1_list in nk1_list:
           fhir_next_to_kin = self._related_person_json(data=nk1_list,patientid= patient_db.account_number,prefix='NK1',relation_dict=relation_desc_dict)
           bundle_entries.append({"resource": fhir_next_to_kin})

        fhir_bundle = Bundle(
            type="searchset", 
            total=len(bundle_entries),
            entry=bundle_entries
        )

        return fhir_bundle.model_dump(exclude_none=True)