# Resume Improviser

A Streamlit client and FastAPI backend that review PDF resumes with an OpenAI-compatible language model. Upload once, request feedback, update the target role, and request another feedback iteration. Results remain available in version history while the API process is running.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create or update `.env` for local development and fill in the real values:

```env
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4o-mini
JWT_SECRET_KEY=replace-with-a-long-random-value
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
MONGO_DATABASE=resume_db
API_URL=http://localhost:8000
STREAMLIT_URL=http://localhost:8501
```

Start two terminals from this folder:

```powershell
uvicorn backend:app --reload --port 8000
streamlit run app.py
```

Open the Streamlit URL shown in the terminal. API docs are available at `http://localhost:8000/docs`.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/auth/register` | Create an account |
| `POST` | `/auth/login` | Get a JWT bearer token |
| `POST` | `/resumes` | Upload and extract a PDF |
| `GET` | `/resumes` | List the current user's uploads |
| `GET` | `/resumes/{id}` | Read a resume and its versions |
| `PUT` | `/resumes/{id}` | Update the target role |
| `POST` | `/resumes/{id}/iterations` | Generate and store feedback |
| `GET` | `/resumes/{id}/versions` | Read feedback history |
| `DELETE` | `/resumes/{id}` | Delete an upload and its history |

## Deployment

Deploy the FastAPI service first (Render, Railway, or Fly.io):

```text
uvicorn backend:app --host 0.0.0.0 --port $PORT
```

Then deploy `app.py` on [Streamlit Community Cloud](https://share.streamlit.io/) with **Main file path** set to `app.py`. Add these values under the app's **Secrets** settings:

```toml
API_URL = "https://your-fastapi-service.example.com"
STREAMLIT_URL = "https://your-streamlit-app.streamlit.app"
```

The FastAPI service needs these environment variables:

```text
OPENAI_API_KEY=your_api_key
JWT_SECRET_KEY=your_stable_secret
MONGO_URI=mongodb+srv://...
MONGO_DATABASE=resume_db
STREAMLIT_URL=https://your-streamlit-app.streamlit.app
```

For a non-Streamlit host, the frontend command is:

```text
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```

Configure MongoDB Atlas network access and a database user before deployment. When `MONGO_URI` is absent, the API falls back to temporary in-memory storage for local development.
