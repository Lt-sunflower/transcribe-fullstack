# backend

Backend transcription service using openai/whisper-tiny model

---

## Getting Started

### Clone the repository

```bash
git clone https://github.com/lt-sunflower/transcribe-fullstack.git
cd transcribe-fullstack/backend
```

### Install dependencies

```bash
pip install -r docker/requirements.txt
```

### Configure environment variables

Create a `.env` file in the root of the project:

```bash
cp .env.example .env
```

### Start the development server

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

Interactive docs are available at `http://localhost:8000/docs`.

---

## Running Tests

```bash
pytest test_main.py -v
```

---

## Docker

### Build and start the container

```bash
cd docker
```

```bash
docker-compose up --build
```

### Start without rebuilding

```bash
docker-compose up
```

### Stop the container

```bash
docker-compose down
```

The API will also be available at `http://localhost:8000`.