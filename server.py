import os
from datetime import datetime

import requests
from fastapi import FastAPI, File, UploadFile
from fastapi_utils.tasks import repeat_every

from config import swissmodel_token
from database import SessionLocal, engine
from models import Base, File
from util import (convert_pdb_to_mol2, extract_pdb_file_from_gz_file,
                  get_generated_files_from_project_id,
                  get_pdb_file_from_project_id,
                  start_automodel_from_fasta_file, upload_file_to_dropbox)

Base.metadata.create_all(bind=engine)
app = FastAPI()

@app.on_event("startup")
@repeat_every(seconds=30)
async def check_and_update_file_status():
    print("Updating files statuses")
    db = SessionLocal()
    files = db.query(File).all()
    for file in files:
        response = requests.get(
            f"https://swissmodel.expasy.org/project/{file.project_id}/models/summary/",
            headers={"Authorization": f"Token {swissmodel_token}"})
        file.status = response.json()["status"]
        file.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.commit()

        if file.status == "COMPLETED" and not file.converted:
            filename = get_pdb_file_from_project_id(file.project_id)
            extract_pdb_file_from_gz_file("tmp/" + filename)
            mol2_filename = convert_pdb_to_mol2()
            print("Finished converting to mol2")
            file.converted = True
            uploaded_file_link = upload_file_to_dropbox(mol2_filename)
            print(uploaded_file_link)
            file.url = uploaded_file_link
            db.commit()
    
    db.close() 

@app.get("/")
def read_root():
    return {"ok": True}

@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile):
    db = SessionLocal()

    # save file
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{timestamp}_{file.filename}"

    with open("tmp/" + filename, "wb") as buffer:
        buffer.write(file.file.read())

    f = open("tmp/" + filename, "r").read()

    project = start_automodel_from_fasta_file(f)

    if db.query(File).filter(File.project_id == project.get('project_id')).first():
        return {"message": "File already uploaded"}
    
    new_file = File(url=filename, project_id=project.get('project_id'), project_name=project.get('project_name'))
    db.add(new_file)
    db.commit()
    db.refresh(new_file)
    db.close()

    # return with status 200
    return {"message": "File successfully uploaded", "file": new_file}

    # # Fetch the bulk download of results from the parameter "download_url"
    # print("Fetch the results from: ", get_generated_files_from_project_id(project_id))

    # # Download the files
    # get_pdb_file_from_project_id(project_id)

    # # extract the pdb file from the gz file
    # extract_pdb_file_from_gz_file("tmp/01.pdb.gz")

    # # convert the pdb file to a mol2 file
    # convert_pdb_to_mol2()

    # os.remove("tmp/" + filename)

    # return {"message": "File successfully converted to mol2"}


@app.get("/status/{project_id}")
async def get_job_status(project_id: str):
    # Update the status from the server
        response = requests.get(
            f"https://swissmodel.expasy.org/project/{project_id}/models/summary/",
            headers={"Authorization": f"Token {swissmodel_token}"})

        # Update the status
        
        return response.json()


@app.get("/all-files/")
async def get_all_files():
    db = SessionLocal()
    files = db.query(File).all()
    db.close()

    return files