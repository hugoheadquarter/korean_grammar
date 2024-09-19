import asyncio
import logging
import re
from typing import List
from openai import AsyncOpenAI, OpenAIError
from models import SubAgentOutput, TeacherAgentOutput, QuizMakerOutput, QuizQuestion
from config import API_KEY, MODEL_NAME

client = AsyncOpenAI(api_key=API_KEY)

teacher_prompt = """
You are a world-class Korean Language Teacher. Analyze the given sentence and the teaching assistants' feedback, then provide your assessment. Choose the most appropriate output format based on the complexity and nature of the correction needed, but do not explicitly state the format type in your response.

Use one of the following formats:

1. Concise Format with Mnemonic Devices (for simple corrections or basic rules):

Explanation: [Brief explanation of the main correction(s)]
**Examples**:
1. [First example sentence in Korean with (translation)]
2. [Second example sentence in Korean with (translation)]
3. [Third example sentence in Korean with (translation)]

2. Structured Academic Approach (for complex grammatical issues or nuanced concepts):

Explanation: [Detailed explanation of the grammar rule(s) or language concept(s) involved]
**Key Points**:
- [First main point]
- [Second main point]
- [Third main point (if applicable)]
**Examples**:
1. [First example sentence in Korean with (translation)]
2. [Second example sentence in Korean with (translation)]
3. [Third example sentence in Korean with (translation)]

Ensure your explanation is clear, concise, and educational. Focus on the most important aspects of the corrections or confirmations. Use bold text to emphasize important words/points.

Your response should be well-structured and contained entirely within the 'explanation' field of the JSON output. 

IMPORTANT: Never use # to make texts bigger
"""

async def sub_agent(category: str, prompt: str, sentence: str) -> SubAgentOutput:
    async def attempt_analysis():
        try:
            full_prompt = f"{prompt}\n\nIMPORTANT: You are strictly assessing ONLY the {category} aspect of the sentence. Do not consider any other aspects. If no mistakes are found in your specific category, simply output 'N/A' as your feedback."
            
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "SubAgentOutput",
                        "schema": SubAgentOutput.model_json_schema()
                    }
                },
                messages=[
                    {"role": "system", "content": full_prompt},
                    {"role": "user", "content": f"Analyze this Korean sentence: '{sentence}'"}
                ]
            )
            return SubAgentOutput.model_validate_json(response.choices[0].message.content)
        except OpenAIError as e:
            raise
        except Exception as e:
            raise

    for attempt in range(3):
        try:
            result = await attempt_analysis()
            return result
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)

    return SubAgentOutput(category=category, feedback="Error in processing feedback.")

async def process_sentence(sentence: str) -> TeacherAgentOutput:
    sub_agent_tasks = [
        sub_agent("Korean Grammar", "You are a Korean Grammar Expert specializing in Korean language instruction. Your task is to analyze sentences for grammatical correctness and provide clear, educational feedback. This could include: - Verb conjugations and tenses - Particle usage (은/는, 이/가, 을/를, etc.) - Sentence endings - Connectives (conjunctions) - Word order (SOV structure). Provide detailed explanations for any errors, suggest corrections, and explain the underlying grammatical principles. Your feedback should help learners understand and apply Korean grammar rules effectively.", sentence),
        sub_agent("Vocabulary and Usage", "As a Korean Vocabulary and Usage Specialist, your role is to enhance learners' word choice and idiomatic expression. Focus on: - Assessing the appropriateness of word choices in context - Identifying and correcting misused words or phrases - Suggesting more precise or natural alternatives for imprecise vocabulary - Explaining idiomatic expressions and colloquialisms - Highlighting commonly confused words (especially Sino-Korean vs. native Korean words). Provide clear explanations for your suggestions, considering the intended meaning and level of formality. Your feedback should expand learners' vocabulary and improve their ability to express themselves naturally in Korean.", sentence),
        sub_agent("Honorifics and Speech Levels", "As a Korean Honorifics and Speech Level Specialist, your job is to ensure correct and appropriate use of Korean's complex system of politeness. Focus on: - Correct use of honorific forms (존댓말) and plain forms (반말) - Appropriate selection of speech levels (해요체, 합쇼체, etc.) - Proper use of honorific particles and vocabulary - Consistency in honorific usage throughout sentences and conversations. Provide explanations for your corrections and their importance in Korean social and cultural contexts. Your feedback should enhance learners' understanding of Korean politeness rules and their application in various situations. IMPORTANT!!! If 나는 is used with formal verb ending, IT IS WRONG.", sentence),
    ]
    sub_agent_outputs = await asyncio.gather(*sub_agent_tasks)
    
    async def attempt_teacher_analysis():
        try:
            sub_agent_feedback = "\n".join([f"{output.category}: {output.feedback}" for output in sub_agent_outputs if output.feedback != 'N/A'])
            full_prompt = f"Analyze this Korean sentence and provide your feedback in JSON format.\n Original sentence: '{sentence}'\n\n ALWAYS follow this Instruction for your feedback: {teacher_prompt} \n\n Here are the teaching assistants' analyses:\n\n{sub_agent_feedback}"
            
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "TeacherAgentOutput",
                        "schema": TeacherAgentOutput.model_json_schema()
                    }
                },
                messages=[
                    {"role": "system", "content": "You are a world-class Korean Language Teacher."},
                    {"role": "user", "content": full_prompt}
                ]
            )

            result = TeacherAgentOutput.model_validate_json(response.choices[0].message.content)
            result.explanation = re.sub(r'^(\*\*Explanation\*\*|Explanation):\s*', '', result.explanation.strip())
            result.explanation = re.sub(r'^(<b>Explanation</b>|Explanation):\s*', '', result.explanation.strip())
            print("SUCEED: ", sentence)
            return result
        except OpenAIError as e:
            raise
        except Exception as e:
            raise

    for attempt in range(3):

        try:
            result = await attempt_teacher_analysis()
            return result
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)

    return TeacherAgentOutput(original_sentence=sentence, correct_sentence=sentence, explanation="Error in processing feedback.")

async def quiz_maker_agent(teacher_outputs: List[TeacherAgentOutput]) -> QuizMakerOutput:
    incorrect_sentences = [output for output in teacher_outputs if output.original_sentence != output.correct_sentence]
    all_questions = []

    async def generate_questions(output):
        prompt = f"""
Based on the following correction and explanation, generate 3 multiple-choice questions in Korean:
Original: {output.original_sentence}
Corrected: {output.correct_sentence}
Explanation: {output.explanation}

For each question, provide:
1. The question itself IN ENGLISH
2. Four possible answers in Korean
3. The correct answer (just the letter, e.g., "A")
4. A detailed explanation in English of why the answer is correct.

IMPORTANT!!! Ensure that each answer choice STARTS WITH the letter and parenthesis, like this:
A) [Korean answer text]
B) [Korean answer text]
C) [Korean answer text]
D) [Korean answer text]

Do not include any additional formatting or numbering before the letter choices.

Ensure the questions test understanding of the Korean language concepts explained in the correction. Focus on aspects such as grammar, particle usage, honorifics, vocabulary, and sentence structure that are unique to Korean.

DO NOT mix formal and informal expressions together (Example: using 나는 with formal verb ending. using 저는 with informal verb ending.)

Keep in mind that you do not have to use 저는 or 나는 all the time when it can be omitted. 
        """

        async def attempt_quiz_generation():
            try:
                response = await client.chat.completions.create(
                    model=MODEL_NAME,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "QuizMakerOutput",
                            "schema": QuizMakerOutput.model_json_schema()
                        }
                    },
                    messages=[
                        {"role": "system", "content": "You are a quiz maker for Korean language learners."},
                        {"role": "user", "content": prompt}
                    ]
                )
                return QuizMakerOutput.model_validate_json(response.choices[0].message.content).questions
            except OpenAIError as e:
                raise
            except Exception as e:
                raise

        for attempt in range(3):
            try:
                result = await attempt_quiz_generation()
                return result
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)

        return []

    question_tasks = [generate_questions(output) for output in incorrect_sentences]
    question_sets = await asyncio.gather(*question_tasks)
    
    for question_set in question_sets:
        all_questions.extend(question_set)

    return QuizMakerOutput(questions=all_questions)
