from database import session, patient_demographics, insurance_master, insurance_demographics, next_to_kin, guarantor_demographics,guarantor_Patient_relation,relation_codes,next_to_kin_patient_relation,hl7datalog

class message_logger:
    @staticmethod
    def updatehl7datalog(db,single_valid_message,status,audit_trail,patientid=None):
        new_log = hl7datalog(data=single_valid_message,status=status,direction="INBOUND",processflow="\n".join(audit_trail),patientid=patientid)
        db.add(new_log)
        db.commit()

class HL7_Crud:

    def _check_exisiting_patient(self,db,account_number, dob,demographics_dict,audit_trail):
        hl7_demographics=demographics_dict

        exisiting_patient = db.query(patient_demographics).filter_by(account_number=account_number,dob=dob,deleteflag=False).first()
        if exisiting_patient:
            audit_trail.append(f"Found existing Patient:{exisiting_patient.id}, now updating the patient")
            patient = self._update_exisiting_patient(db,exisiting_patient.id,hl7_demographics,audit_trail)
            return patient
        else:
            audit_trail.append("No existing patient found, creating new patient")
            patient = patient_demographics(**demographics_dict)
            db.add(patient)
            db.flush()
            audit_trail.append(f"New Patient created, PatientID: {patient.id},AccountNumber:{patient.account_number}")
            return patient
            

    def _update_exisiting_patient(self,db,id,demographics_dict,audit_trail):
        patient = db.query(patient_demographics).get(id)
        # audit_trail.append(f"Updating patient:{patient.id}")
        # Removed Repetitive code and used for Loop for cleaner code and maintainability
        for key, value in demographics_dict.items():
            if value is not None and value != "":
                audit_trail.append(f"Updating patient:{patient.id},Data: {key},{value}")
                setattr(patient, key, value)
        audit_trail.append(f'''===============================================Updated patient:{patient.id}===============================================''')
        db.flush()
        
        return patient

    def _insurance_check_create(self,db,insurance_name,audit_trail):
        exisiting_insurance = db.query(insurance_master).filter_by(name=insurance_name,deleteflag=False).first()
        if exisiting_insurance:
            audit_trail.append(f"Found insurance: {insurance_name}, InsuranceID: {exisiting_insurance.id}")
            return exisiting_insurance.id
        else:
            new_master= insurance_master(name=insurance_name)
            db.add(new_master)
            db.flush()
            audit_trail.append(f"Did not Found insurance: {insurance_name} hence created new insurance: {insurance_name}, InsuranceID: {new_master.id}")
            return new_master.id

    def _guarantor_check(self,db,guarantor_mobile_number,guarantor,patientid,gurantor_relation_code,audit_trail):
        patientid=patientid
        gurantor_relation_code=gurantor_relation_code

        if not guarantor_mobile_number or not guarantor_mobile_number.strip():
            audit_trail.append(f"Mobile Number is not present in HL7 for Guarantor:{guarantor['lastname']} {guarantor['firstname']} {guarantor['dob']}")
            #print(f"Error: Mobile number is not present for Guarantor {guarantor.get('firstname', '')} {guarantor.get('lastname', '')}. Skipping.")
            return None
        
        exisiting_guarantor = db.query(guarantor_demographics).filter_by(mobile_number=guarantor_mobile_number, deleteflag=False).first()

        if exisiting_guarantor:
            audit_trail.append(f"Found Guarantor: {exisiting_guarantor.id}")
            self._update_existing_guarantor(db,exisiting_guarantor.id,guarantor,audit_trail)
            exisiting_relation = db.query(guarantor_Patient_relation).filter_by(guarantorid=exisiting_guarantor.id,patientid=patientid,deleteflag=False).first()

            if exisiting_relation:
                audit_trail.append(f'''Relation is already present with Patient, GRID: {exisiting_guarantor.id}, PatientID: {patientid}, RelationID: {exisiting_relation.id}, Relation: {exisiting_relation.relationid}''')
                exisiting_relation.relationid = gurantor_relation_code
                audit_trail.append(f'''Relation updated for GRID: {exisiting_guarantor.id}, PatientID: {patientid}, RelationID: {exisiting_relation.id}, Relation: {exisiting_relation.relationid}''')

                db.query(guarantor_Patient_relation).filter(
                    guarantor_Patient_relation.guarantorid == exisiting_guarantor.id,
                    guarantor_Patient_relation.patientid == patientid,
                    guarantor_Patient_relation.deleteflag == False,
                    guarantor_Patient_relation.id != exisiting_relation.id 
                ).update({"deleteflag": True})
                db.flush()
                audit_trail.append('''All other Guarantor Relation inactivated other than received in HL7''')
                return exisiting_relation.id
            else:
                audit_trail.append(f'''No Relation is present with Patient, GRID: {exisiting_guarantor.id}, PatientID: {patientid}, Hence creating new relation''')
                return self._guarantor_relation_mapping(db,exisiting_guarantor.id,patientid,gurantor_relation_code,audit_trail)
        else:
            new_guarantor = guarantor_demographics(**guarantor)
            db.add(new_guarantor)
            db.flush()
            audit_trail.append(f'''No Guarantor Found with Mobile Number: {guarantor_mobile_number} Hence created GuarantorID: {new_guarantor.id} ''')
            audit_trail.append(f'''Creating new Relation with new Guarantor, GRID: {new_guarantor.id}, PatientID: {patientid}''')
            return self._guarantor_relation_mapping(db,new_guarantor.id,patientid,gurantor_relation_code,audit_trail)      

    def _update_existing_guarantor(self,db,guarantor_id,guranator,audit_trail):
        guranator_record = db.query(guarantor_demographics).get(guarantor_id)
        
        # Removed Repetitive code and used for Loop for cleaner code and maintainability
        for key, value in guranator.items():
            if value is not None and value != "":
                audit_trail.append(f"Updating Guarantor: {guarantor_id}, Data: {key},{value}")
                setattr(guranator_record, key, value)
        audit_trail.append(f"Updated Guarantor: {guarantor_id}")
        db.flush()
        
    def _guarantor_relation_mapping(self,db,guarantor_id,patientid,relation_code,audit_trail):
        guarantor_mapping = guarantor_Patient_relation(guarantorid=guarantor_id,patientid=patientid,relationid=relation_code)
        db.add(guarantor_mapping)
        db.flush()
        audit_trail.append(f'''Relation is created with Patient, GRID: {guarantor_id}, PatientID: {patientid}, Realtion: {relation_code},guarantor_Patient_relationID: {guarantor_mapping.id} ''')
        return guarantor_mapping.id

    def _nexttokin_check(self,db,nexttokin_mobile_number,nexttokin,patientid,nexttokin_relation_code,audit_trail):
        patientid=patientid
        nexttokin_relation_code=nexttokin_relation_code

        if not nexttokin_mobile_number or not nexttokin_mobile_number.strip():
            audit_trail.append(f"Mobile Number is not present in HL7 for Guarantor:{nexttokin['lastname']} {nexttokin['firstname']} {nexttokin['dob']}")
            #print(f"Error: Mobile number is not present for Next to Kin {nexttokin.get('firstname', '')} {nexttokin.get('lastname', '')}. Skipping.")
            return None

        exisiting_nexttokin = db.query(next_to_kin).filter_by(mobile_number=nexttokin_mobile_number,deleteflag=False).first()
        
        if exisiting_nexttokin:
            audit_trail.append(f'''Found Next To Kin: {exisiting_nexttokin.id}''')
            self._update_exisiting_nexttokin(db,exisiting_nexttokin.id,nexttokin,audit_trail)
            exsiting_nk1relation = db.query(next_to_kin_patient_relation).filter_by(nkid=exisiting_nexttokin.id,patientid=patientid,deleteflag=False).first()
            if exsiting_nk1relation:
                audit_trail.append(f'''Relation is already present with Patient, NKID: {exsiting_nk1relation.id}, PatientID: {patientid}, RelationID: {exsiting_nk1relation.id}, Relation: {exsiting_nk1relation.relationid}''')
                exsiting_nk1relation.relationid = nexttokin_relation_code
                audit_trail.append(f'''Relation updated for NKID: {exsiting_nk1relation.id}, PatientID: {patientid}, RelationID: {exsiting_nk1relation.id}, Relation: {exsiting_nk1relation.relationid}''')
                db.flush()
                db.query(next_to_kin_patient_relation).filter(
                    next_to_kin_patient_relation.nkid == exisiting_nexttokin.id,
                    next_to_kin_patient_relation.patientid == patientid,
                    next_to_kin_patient_relation.deleteflag == False,
                    next_to_kin_patient_relation.id != exsiting_nk1relation.id 
                ).update({"deleteflag": True})
                db.flush()
                audit_trail.append('''All other NK1 Relation inactivated other than received in HL7''')
                return exsiting_nk1relation.id
            else:
                audit_trail.append(f'''No Relation is present with Patient, NKID: {exisiting_nexttokin.id}, PatientID: {patientid}, Hence creating new relation''')
                return self._nexttokin_relation_mapping(db,exisiting_nexttokin.id,patientid,nexttokin_relation_code,audit_trail)
                
        else:
            new_nexttokin = next_to_kin(**nexttokin)
            db.add(new_nexttokin)
            db.flush()
            audit_trail.append(f'''No Next to Kin Found with Mobile Number: {nexttokin_mobile_number} Hence created NKID: {new_nexttokin.id} ''')
            audit_trail.append(f'''Creating new Relation with new Next to Kin, NKID: {new_nexttokin.id}, PatientID: {patientid}''')
            return self._nexttokin_relation_mapping(db,new_nexttokin.id,patientid,nexttokin_relation_code,audit_trail)
            

    def _update_exisiting_nexttokin(self,db,nk1_id,nexttokin,audit_trail):
        
        nk1_record = db.query(next_to_kin).get(nk1_id)
        
        for key,value in nexttokin.items():
            if value is not None and value != "":
                audit_trail.append(f'''Updating Next To Kin :{nk1_id}, {key} {value}''')
                setattr(nk1_record,key,value)
        audit_trail.append(f'''UpdatedNext To Kin: {nk1_id}''')
        db.flush()

    def _nexttokin_relation_mapping(self,db,nexttokinid,patientid,nexttokin_relation_code,audit_trail):
        nexttokin_mapping=next_to_kin_patient_relation(nkid=nexttokinid,patientid=patientid,relationid=nexttokin_relation_code)
        db.add(nexttokin_mapping)
        audit_trail.append(f'''Relation is created with Patient, GRID: {nexttokinid}, PatientID: {patientid}, Realtion: {nexttokin_relation_code},next_to_kin_patient_relation: {nexttokin_mapping.id}''')
        db.flush()

        return nexttokin_mapping.id

    def save_patient_demographics(self,demographics_dict,guarantor_list,nk1_list,insurance_list,audit_trail,single_valid_message):
        db = session()
        try:
            if demographics_dict ["account_number"] and demographics_dict["dob"]:
                audit_trail.append("===============Checking for Existing Patient===============")
                exisiting_new_patient_id = self._check_exisiting_patient(db,demographics_dict ["account_number"], demographics_dict["dob"],demographics_dict,audit_trail)

            if insurance_list:
                
                db.query(insurance_demographics).filter_by(patientid=exisiting_new_patient_id.id).delete() #Delete all exisiting Insurances
                db.flush()
                audit_trail.append(f"Deleted all existing insurance for Patient ID:{exisiting_new_patient_id.id}")

                for ins_item in insurance_list:
                    insurancedata = ins_item["insurancedata"]
                    insurance_name = ins_item["insurance_name"]
                    audit_trail.append(f"Checking insurance: {insurance_name}")
                    master_id = self._insurance_check_create(db, insurance_name,audit_trail)
                    insurancedata["insid"] = master_id
                    insurancedata["patientid"] = exisiting_new_patient_id.id 
                    audit_trail.append(f"Mapping insurance: {insurance_name} {master_id} to Patient: {exisiting_new_patient_id.id}")
                    new_policy = insurance_demographics(**insurancedata)
                    db.add(new_policy)
                    audit_trail.append(f"Mapped insurance: {insurance_name} {master_id} to Patient: {exisiting_new_patient_id.id}")
                    db.flush()

            if guarantor_list:            
                active_relation_ids=[]
                for gt1_item in guarantor_list:
                    guarantor_data = gt1_item["guarantordata"]
                    guarantor_mobile = gt1_item["guarantor_mobile"]
                    gurantor_relation_code = guarantor_data.pop("relation", None)
                    patientid = exisiting_new_patient_id.id
                    audit_trail.append(f"Checking Guarantor using mobile_number:{guarantor_mobile}")
                    relation_id = self._guarantor_check(db, guarantor_mobile,guarantor_data,patientid,gurantor_relation_code,audit_trail)

                    if relation_id:
                        active_relation_ids.append(relation_id)
                        audit_trail.append(f"Append All Active GR RelationID:{active_relation_ids}")

                if active_relation_ids:
                    deactive_GRrelation = db.query(guarantor_Patient_relation).filter(
                        guarantor_Patient_relation.patientid == exisiting_new_patient_id.id,
                        guarantor_Patient_relation.deleteflag == False,
                        ~guarantor_Patient_relation.id.in_(active_relation_ids) 
                    ).update({"deleteflag": True})
                    audit_trail.append(f"Remove all existing GR Relation which are not received in HL7, Count: ({deactive_GRrelation})")
                    db.flush()
                    
            
            if nk1_list:

                active_nk1relation_ids=[]
                for nk1_item in nk1_list:
                    nk1_data = nk1_item["nk1_data"]
                    nk1_mobile = nk1_item["nk1_mobile"]
                    nexttokin_relation_code = nk1_data.pop("relation",None)
                    patientid = exisiting_new_patient_id.id
                    audit_trail.append(f'''Checking Next To Kin using Mobile Number:{nk1_mobile}''')
                    relation_id = self._nexttokin_check(db, nk1_mobile,nk1_data,patientid,nexttokin_relation_code,audit_trail)

                    if relation_id:
                        active_nk1relation_ids.append(relation_id)
                        audit_trail.append(f"Append All Active NK1 RelationID:{active_relation_ids}")

                if active_nk1relation_ids:
                    deactive_NKRelation = db.query(next_to_kin_patient_relation).filter(
                        next_to_kin_patient_relation.patientid == exisiting_new_patient_id.id,
                        next_to_kin_patient_relation.deleteflag == False,
                        ~next_to_kin_patient_relation.id.in_(active_nk1relation_ids) 
                    ).update({"deleteflag": True})
                    audit_trail.append(f"Remove all existing NK1 Relation which are not received in HL7, Count: ({deactive_NKRelation})")
                    db.flush() 

            db.commit()
            db.refresh(exisiting_new_patient_id)
            audit_trail.append(f"===============================================Flow Ended Successfully===============================================")
            status = 1
            return message_logger.updatehl7datalog(db,single_valid_message,status,audit_trail,exisiting_new_patient_id.id)
        except Exception as e:
            db.rollback()
            audit_trail.append(f"Error saving patient demographics: {e}")
            print(f"Error saving patient demographics: {e}")
            status = 2 
            message_logger.updatehl7datalog(db,single_valid_message,status,audit_trail,exisiting_new_patient_id)
        finally:
            audit_trail.append("DB Connection Closed")
            db.close()

