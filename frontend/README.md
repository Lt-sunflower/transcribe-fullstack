# frontend

Frontend UI for transcription service

---

## Getting started

### Clone the repository

```bash
git clone https://github.com/lt-sunflower/transcribe-fullstack.git
cd transcribe-fullstack/frontend
```

### Install dependencies
 
```bash
npm install
```

### Start the development server
 
```bash
npm start
```

The app will be available at `http://localhost:3000`.

---

## Running Tests
 
```bash
npm test
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

The app will also be available at `http://localhost:3000`.