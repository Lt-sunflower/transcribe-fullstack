import io
from unittest.mock import MagicMock, patch
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = "sqlite:///:memory:"

import sys
sys.modules["torch"] = MagicMock()
sys.modules["whisper"] = MagicMock()
sys.modules["librosa"] = MagicMock()
sys.modules["transformers"] = MagicMock()

from main import app, Base, Audio, get_db
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
_shared_conn = engine.connect()

TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=_shared_conn
)

Base.metadata.create_all(bind=_shared_conn)

def override_get_db():
    """Replace the real DB dependency with the test session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def add_record(db, filename="test.wav", transcript="hello world", filepath="./audio/test.wav"):
    record = Audio(
        filename=filename,
        transcript=transcript,
        filepath=filepath,
        created_on=datetime(2026, 1, 1, 12, 0, 0),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

def clear_db():
    db = TestingSessionLocal()
    db.query(Audio).delete()
    db.commit()
    db.close()

def make_audio_file(filename="test.wav", content=b"fake-audio-bytes"):
    return (filename, io.BytesIO(content), "audio/wav")

class TestGetAll:
    def setup_method(self):
        clear_db()

    def test_returns_all_records(self):
        db = TestingSessionLocal()
        add_record(db, filename="a.wav")
        add_record(db, filename="b.wav")
        db.close()

        response = client.get("/transcriptions")
        assert response.status_code == 200
        assert len(response.json()) == 2

class TestSearchByFilename:
    def setup_method(self):
        clear_db()

    def test_search_exact_match(self):
        db = TestingSessionLocal()
        add_record(db, filename="interview.wav")
        db.close()

        response = client.get("/search?filename=interview")
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["filename"] == "interview.wav"

    def test_search_no_match(self):
        db = TestingSessionLocal()
        add_record(db, filename="other.wav")
        db.close()

        response = client.get("/search?filename=nonexistent")
        assert response.status_code == 200
        assert response.json() == []

class TestTranscribe:
    def setup_method(self):
        clear_db()

    @patch("main.librosa.load", return_value=([0.0] * 16000, 16000))
    @patch("main.processor")
    @patch("main.model")
    @patch("os.makedirs")
    def test_single_file_returns_200(self, mock_makedirs, mock_model, mock_processor, mock_librosa):
        mock_processor.return_value = {"input_features": MagicMock()}
        mock_model.generate.return_value = MagicMock()
        mock_processor.batch_decode.return_value = [" hello world "]
        with patch("builtins.open", MagicMock()):
            res = client.post("/transcribe", files={"files": make_audio_file()})
        assert res.status_code == 200
        body = res.json()
        assert "results" in body
        assert len(body["results"]) == 1

    @patch("main.librosa.load", return_value=([0.0] * 16000, 16000))
    @patch("main.processor")
    @patch("main.model")
    @patch("os.makedirs")
    def test_multiple_files_all_processed(self, mock_makedirs, mock_model, mock_processor, mock_librosa):
        mock_processor.return_value = {"input_features": MagicMock()}
        mock_model.generate.return_value = MagicMock()
        mock_processor.batch_decode.return_value = [" hello "]
        with patch("builtins.open", MagicMock()):
            res = client.post("/transcribe", files=[
                ("files", make_audio_file("a.wav")),
                ("files", make_audio_file("b.wav")),
            ])
        assert res.status_code == 200
        results = res.json()["results"]
        assert len(results) == 2
        assert {r["filename"] for r in results} == {"a.wav", "b.wav"}

    @patch("main.librosa.load", side_effect=Exception("librosa error"))
    @patch("os.makedirs")
    @patch("os.remove")
    def test_error_returns_500(self, mock_remove, mock_makedirs, mock_librosa):
        with patch("builtins.open", MagicMock()):
            res = client.post("/transcribe", files={"files": make_audio_file()})
        assert res.status_code == 500
        assert "errors" in res.json()