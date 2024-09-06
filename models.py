from pydantic import BaseModel
from typing import List

class SubAgentOutput(BaseModel):
    category: str
    feedback: str

class TeacherAgentOutput(BaseModel):
    original_sentence: str
    correct_sentence: str
    explanation: str

class QuizQuestion(BaseModel):
    question: str
    choices: List[str]
    answer: str
    explanation: str

class QuizMakerOutput(BaseModel):
    questions: List[QuizQuestion]