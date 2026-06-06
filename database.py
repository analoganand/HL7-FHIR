from sqlalchemy import create_engine, Column, Integer, String,ForeignKey,Date,DateTime,Boolean,Text,CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, sessionmaker
import subprocess
import sys

db_url = "postgresql://postgres:fhirdb@localhost:5432/HL7_FHIR"
engine = create_engine(db_url)
session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class patient_demographics(Base):
    __tablename__ = "patient_demographics"

    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String, unique=True, index=True)
    lastname = Column(String)
    firstname = Column(String)
    dob = Column(Date)
    gender = Column(String)
    race = Column(String)
    ethnicity = Column(String)
    language = Column(String)
    address_line_1 = Column(String)
    address_line_2 = Column(String)
    city = Column(String)
    state = Column(String)
    pincode = Column(String)
    home_phone = Column(String)
    mobile_number = Column(String)
    email = Column(String)
    pcp_name = Column(String)
    ref_name = Column(String)
    deleteflag = Column(Boolean, default=False)

class insurance_master(Base):
    __tablename__ = "insurance_master"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    deleteflag = Column(Boolean, default=False)

class insurance_demographics(Base):
    __tablename__ = "insurance_demographics"

    id = Column(Integer, primary_key=True, index=True)
    insid = Column(Integer,ForeignKey("insurance_master.id"))
    patientid = Column(Integer,ForeignKey("patient_demographics.id"))
    subscriberid = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    type = Column(Integer)
    inactive = Column(Boolean, default=False)
    terminated = Column(Integer)

class next_to_kin(Base):
    __tablename__ = "next_to_kin"

    id = Column(Integer, primary_key=True, index=True)
    # patientid = Column(Integer,ForeignKey("patient_demographics.id"))
    lastname = Column(String)
    firstname = Column(String)
    dob = Column(Date)
    gender = Column(String)
    address_line_1 = Column(String)
    address_line_2 = Column(String)
    city = Column(String)
    state = Column(String)
    pincode = Column(String)
    home_phone = Column(String)
    mobile_number = Column(String)
    email = Column(String,unique=True)
    deleteflag = Column(Boolean, default=False)

class next_to_kin_patient_relation(Base):
    __tablename__ = 'next_to_kin_patient_relation'
    
    id = Column(Integer,primary_key=True,index =True)
    patientid = Column(Integer,ForeignKey("patient_demographics.id"))
    nkid = Column(Integer, ForeignKey("next_to_kin.id"))
    deleteflag = Column(Boolean, default=False)
    relationid = Column(Integer,ForeignKey("relation_codes.code"))


class guarantor_demographics(Base):
    __tablename__ = "guarantor_demographics"

    id = Column(Integer, primary_key=True, index=True)
    # patientid = Column(Integer,ForeignKey("patient_demographics.id"))
    lastname = Column(String)
    firstname = Column(String)
    dob = Column(Date)
    gender = Column(String)
    address_line_1 = Column(String)
    address_line_2 = Column(String)
    city = Column(String)
    state = Column(String)
    pincode = Column(String)
    home_phone = Column(String)
    mobile_number = Column(String)
    email = Column(String,unique=True)
    # relation = Column(String)
    deleteflag = Column(Boolean, default=False)


class guarantor_Patient_relation(Base):
    __tablename__ = "guarantor_Patient_relation"

    id = Column(Integer, primary_key=True, index=True)
    patientid = Column(Integer,ForeignKey("patient_demographics.id"))
    guarantorid = Column(Integer,ForeignKey("guarantor_demographics.id"))
    relationid = Column(Integer,ForeignKey("relation_codes.code"))
    deleteflag = Column(Boolean, default=False)

class relation_codes(Base):
    __tablename__ = "relation_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(Integer,unique=True)
    description = Column(String)


class hl7datalog(Base):
    __tablename__ = "hl7datalog"

    id = Column(Integer, primary_key=True, index=True)
    data = Column(Text)
    processedtime = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Integer, CheckConstraint('status IN (1, 2)'), nullable=False)
    direction = Column(String(10), CheckConstraint("direction IN ('INBOUND', 'OUTBOUND')"), nullable=False)
    processflow = Column(Text)
    patientid = Column(Integer, ForeignKey("patient_demographics.id"))
    

Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    print("Scanning for database changes...")
    
    try:
        subprocess.run(["alembic", "revision", "--autogenerate", "-m", "auto_sync"], check=True)
        
        print("Applying updates to PostgreSQL...")
        subprocess.run(["alembic", "upgrade", "head"], check=True)
        
        print("Database is perfectly synced!")
    except subprocess.CalledProcessError as e:
        print(f"Migration failed: {e}")