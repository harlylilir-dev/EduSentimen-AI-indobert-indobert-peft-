from fastapi import FastAPI

app = FastAPI(title="EduSentiment AI Backend")

@app.get("/")
def root():
    return {"message": "Hello World"}