import os
import uuid
import torch
import librosa

from fastapi import FastAPI, Depends, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq
from fastapi.middleware.cors import CORSMiddleware

os.makedirs("./db", exist_ok=True)
os.makedirs("./audio", exist_ok=True)

# define model + processor for transcription
MODEL_NAME = "openai/whisper-tiny"
processor = AutoProcessor.from_pretrained(MODEL_NAME)
model = AutoModelForSpeechSeq2Seq.from_pretrained(MODEL_NAME)
model.config.forced_decoder_ids = None
model.config.language = "en"
model.config.task = "transcribe"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB conn settings
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./db/local.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Entity
class Audio(Base):
    __tablename__ = "audio"
    id = Column(Integer, primary_key=True)
    filename = Column(String, index=True)
    filepath = Column(String)
    transcript = Column(String)
    created_on = Column(DateTime(timezone = True), default = lambda: datetime.now(tz=ZoneInfo("Asia/Singapore")))

# Setup on start
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
def health_check():
    return {"status": "ok"}

#GET /transcriptions
@app.get("/transcriptions")
def getAll(db: Session = Depends(get_db)):
    records = db.query(Audio).all()
    return [
        {
            "filename": record.filename,
            "transcript": record.transcript,
            "created_on": record.created_on.isoformat()
        }
        for record in records
    ]

#GET /search
@app.get("/search")
def search_by_filename(filename: str, db: Session = Depends(get_db)):
    records = db.query(Audio).filter(Audio.filename.ilike(f"%{filename}%")).all()
    return [
        {
            "filename": record.filename,
            "transcript": record.transcript,
            "created_on": record.created_on.isoformat()
        }
        for record in records
    ]


# POST /transcribe
@app.post("/transcribe")
async def transcribe_and_save(files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    results = []
    errors = []

    for file in files:
        # generate unique filepath
        _, ext = os.path.splitext(file.filename)
        audio_path = f"./audio/{uuid.uuid4().hex[:24]}{ext}"

        try:
            # write to file
            with open(audio_path, "wb") as f:
                f.write(await file.read())

            # load audio into raw audio with sampling rate of 16khz
            audio, _ = librosa.load(audio_path, sr=16000)
            # preprocess raw audio into log-mel spectrogram to feed into model
            inputs = processor(audio, sampling_rate=16000, return_tensors="pt")

            with torch.no_grad():
                #retrieve spectogram, add attention_mask. all ones since no padding
                input_features = inputs["input_features"]
                attention_mask = torch.ones(
                    input_features.shape[:2], dtype=torch.long, device=input_features.device
                )
                # generate tokens from logmel input
                generated_ids = model.generate(input_features, attention_mask=attention_mask)

            # decode tokens into text using processor
            transcript = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()

            audio_record = Audio(filename=file.filename, transcript=transcript, filepath=audio_path)
            db.add(audio_record)
            db.commit()
            db.refresh(audio_record)

            results.append({
                "filename": audio_record.filename,
                "transcript": audio_record.transcript,
                "created_on": audio_record.created_on.isoformat()
            })

        except Exception as e:
            db.rollback()
            if os.path.exists(audio_path):
                os.remove(audio_path)
            errors.append({"filename": file.filename, "error": str(type(e).__name__)})
            continue  # skip to next file

    # Return 207 Multi-Status if there's a mix of success and failure
    status_code = 207 if (results and errors) else (500 if errors else 200)
    return JSONResponse(
        status_code=status_code,
        content={"results": results, "errors": errors}
    )