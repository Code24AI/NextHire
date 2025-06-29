# NextHire: AI-Enhanced Interview Platform

## Overview

NextHire is an advanced interviewing platform designed to streamline job application processing, enhance HR management, and improve the candidate experience. By leveraging cutting-edge AI technologies, NextHire automates key recruitment stages, including job posting, candidate screening, coding interviews, and applicant evaluation.

## Features

### HR Functionalities
- **Account Management**: HR professionals can create and securely log into dedicated accounts.
- **Job Posting with AI Assistance**:
  - Generate comprehensive job descriptions using an AI-driven assistant based on simple prompts.
  - Review, modify, and approve AI-generated job posts before publishing.
  - Automatically publish approved job listings on the platform.
- **Dashboard Features**:
  - View analytics: total job postings, applications received, and detailed applicant lists by job.
  - Access candidate evaluation metrics, including scores, strengths, and weaknesses.
  - View shortlisted applicants and AI-generated recommendations for top candidates.

### Candidate Functionalities
- **Account and Profile Management**: Candidates can create accounts and securely log in.
- **Job Application Process**:
  - Browse job postings and view detailed job information.
  - Submit applications with pre-filled profile data, editable before submission.
  - Track applied jobs via the candidate dashboard.
- **Interview and Coding Challenge**:
  - Shortlisted candidates receive interview invitation emails.
  - Access coding challenges using a specific Job ID (restricted to shortlisted candidates who haven’t attempted the interview and whose deadlines haven’t expired).
  - Coding challenges include:
    - A built-in timer to manage test duration.
    - A versatile code editor supporting multiple programming languages.
    - Automatic submission of solutions upon timer completion.
  - View results and feedback on the candidate dashboard.

### Visitor Access
- Browse job postings without an account.
- Access additional functionalities by registering and logging in.
- Interact with a 24/7 chatbot for FAQs and customer support.

### AI Integration
NextHire incorporates specialized AI bots and assistants:
- **Job Creation Assistant**: Generates detailed job postings from HR prompts.
- **Candidate Scoring Bot**: Evaluates candidates against job requirements.
- **Automated Email Bot**: Sends job-specific emails to candidates.
- **Coding Challenge Creation Bot**: Generates unique coding challenges for specific job posts.
- **Coding Evaluation Bot**: Assesses coding challenge submissions based on accuracy, efficiency, and other metrics.
- **Candidate Recommendation Bot**: Recommends top candidates with detailed suitability explanations.
- **Customer Support Chatbot**: Provides 24/7 assistance for visitor inquiries.

## Project Structure
- **backend/**: Contains the backend code, built with Python (likely using FastAPI for the API, given Uvicorn usage).
- **frontend/**: Contains the frontend code, built with HTML, CSS, and JavaScript.
- **requirements.txt**: Lists Python dependencies for the backend.
- **.env**: Stores environment variables for configuration (e.g., API keys, database URLs).

## Setup Instructions

### Prerequisites
- **Conda**: Install Miniconda or Anaconda to manage the Python environment.
- **Node.js**: Optional for frontend development (if using tools like live-server).
- **Git**: To clone the repository.

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/nexthire.git
cd nexthire
```

### 2. Set Up the Conda Environment
Create and activate a Conda environment for the backend:
```bash
conda create -n nexthire python=3.9
conda activate nexthire
```

### 3. Install Backend Dependencies
Install the required Python packages from `requirements.txt`:
```bash
pip install -r backend/requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the `backend/` directory to store environment variables (e.g., database URLs, API keys). Example:
```bash
touch backend/.env
```
Add necessary configurations to `backend/.env`, such as:
```
DATABASE_URL=your_database_url
API_KEY=your_api_key
```

### 5. Run the Backend
Navigate to the backend directory and start the FastAPI server using Uvicorn:
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
- The backend API will be available at `http://localhost:8000`.
- The `--reload` flag enables auto-reload for development.

### 6. Run the Frontend
The frontend is built with HTML, CSS, and JavaScript and can be served using a simple HTTP server. You can use `live-server` (a Node.js package) or any static file server.

#### Install live-server (Optional)
```bash
npm install -g live-server
```

#### Serve the Frontend
Navigate to the frontend directory and start the server:
```bash
cd frontend
live-server --port=8080
```
- The frontend will be available at `http://localhost:8080`.
- Alternatively, open `frontend/index.html` directly in a browser for static testing (some features requiring API calls may not work without the backend).

### 7. Access the Application
- **Backend API**: `http://localhost:8000` (e.g., for API documentation if using FastAPI).
- **Frontend**: `http://localhost:8080` (or the port specified for `live-server`).
- Ensure the backend is running before accessing the frontend, as it may rely on API calls.

## Development Notes
- **Backend**: Located in the `backend/` folder, likely using FastAPI. Ensure all endpoints are tested and environment variables are correctly set in `.env`.
- **Frontend**: Located in the `frontend/` folder, built with vanilla HTML, CSS, and JavaScript. Ensure API endpoints are correctly configured to communicate with the backend.
- **AI Integration**: Ensure AI services (e.g., job creation, candidate scoring) are properly configured with API keys or service endpoints in the `.env` file.

## Contributing
Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit your changes (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.
